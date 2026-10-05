
import contextlib
import shutil
import tempfile
import os
from .rattler_build import build_with_rattler
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from hashlib import sha256
import fnmatch
import shutil
from ruamel.yaml import YAML
from .constants import RECIPES_EMSCRIPTEN_DIR, TO_MIGRATE_RECIPES_EMSCRIPTEN_DIR
import contextlib
import json
from .git_utils import (
    bot_github_user_ctx, 
    git_branch_ctx, 
    make_pr_for_recipe, 
    automerge_is_enabled,
    set_bot_user,
    get_current_branch_name
)

def iter_outputs(recipe):
    is_multi_output = "outputs" in recipe and len(recipe["outputs"]) > 1
    if is_multi_output:
        for output in recipe["outputs"]:
            yield output
    else:
        yield recipe
    
def iter_requirements(output):
    if "requirements" in output:
        yield output["requirements"]
    
    if "test" in output and "requirements" in output["test"]:
        yield output["test"]["requirements"]

def replace_in_list(lst, old, new):
    return [new if x == old else x for x in lst]


def migrate_recipe(recipe_dir, output_dir):
    recipe_dir = Path(recipe_dir)
    output_dir = Path(output_dir)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    dest_dir = output_dir / recipe_dir.name
    if not dest_dir.exists():
        shutil.copytree(recipe_dir, dest_dir)

    # read the file
    recipe_file = dest_dir / "recipe.yaml"
    with open(recipe_file) as file:
        recipe = YAML().load(file)

    for output in iter_outputs(recipe):
        for req in iter_requirements(output):
           if 'host' in req:
                req['host'] = replace_in_list(req['host'], "python", "python-dev")
    
    # write the modified recipe back to the file
    with open(recipe_file, "w") as file:
        YAML().dump(recipe, file)

    
def hash_recipe_content(recipe_content):
    """
    Computes the SHA-256 hash of the given recipe content.

    Args:
        recipe_content (str): Content of the recipe.yaml file.

    Returns:
        str: SHA-256 hash of the recipe content.
    """         
    return sha256(recipe_content.encode("utf-8")).hexdigest()


def get_recipe_hash_build_pkg(pkg_path):
    """
    Extracts the recipe.yaml file from a built package and computes its hash.

    Args:
        pkg_path (str or Path): Path to the built package (.tar.bz2 file).

    Returns:
        str: SHA-256 hash of the recipe.yaml content.
    """
    with TemporaryDirectory() as temp_dir:
        subprocess.run(["tar", "-xzf", str(pkg_path), "-C", temp_dir], check=True)
        # read the recipe.yaml file from the extracted contents
        conda_meta_dir = Path(temp_dir) / "info" / "recipe"/"recipe.yaml"
        if not conda_meta_dir.exists():
            raise FileNotFoundError(f"Recipe file not found in package {pkg_path}")
        # read the recipe.yaml file
        with open(conda_meta_dir, "r") as f:
            return hash_recipe_content(f.read())


def build_with_rattler_wrapper(*args, **kwargs):
    """ 
    Wrapper around the build_with_rattler function that handles subprocess.TimeoutExpired exceptions.

    Args:
        *args: Positional arguments to pass to build_with_rattler.
        **kwargs: Keyword arguments to pass to build_with_rattler.
    """
    try:
        ret = build_with_rattler(*args, **kwargs,  format='tar-bz2', log_style='simple', continue_on_failure=True)
        return ret
    except subprocess.TimeoutExpired:
        print("Build timed out, continuing with other recipes...")

ON_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'


def get_github_user_ctx(use_bot):
    
    @contextlib.contextmanager
    def empty_context_manager():
        yield

    if ON_GITHUB_ACTIONS:
        # We are on GitHub Actions, we **cannot** **restore** the user account
        # therefore we just set the bot user and use an empty context manager
        set_bot_user()
        user_ctx = empty_context_manager
    else:
        if use_bot:
            user_ctx = bot_github_user_ctx
        else:
            user_ctx = empty_context_manager
    return user_ctx



def pkg_list_to_branch_name(pkg_list, max_branch_name_length=100):
    name =  "migrate_6x_" + "_".join(pkg_list)
    if len(name) > max_branch_name_length:
        name = name[:max_branch_name_length]
    return name

PR_TITLE_PREFIX = "[6x-Migration]"

def pkg_list_to_pr_title(pkg_list, max_title_length=100):
    title = PR_TITLE_PREFIX + " " + ", ".join(pkg_list)
    if len(title) > max_title_length:
        title = title[:max_title_length]
    return title

def generate_pr_body(successful_builds):
    return "Migrated recipes:\n" + "\n".join(
        f"- {recipe}" for recipe in successful_builds
    )
def pr_body_to_pkg_list(pr_body):
    lines = pr_body.splitlines()
    return [line[2:] for line in lines if line.startswith("- ")]



def get_list_of_already_migrating_recipes():
    command = [
            "gh", "pr", "list",
            # "--author", "emscripten-forge-bot",
            "--base", "emscripten-6x",
            "--json", "number,title,body",
            "--limit", "200" # default is only 30
        ]
    result = subprocess.check_output(command).decode()
    result = json.loads(result)
    # print("Fetched PRs:", result)
    already_migrating = []
    for pr in result:
        title = pr.get("title", "")
        # print("Processing PR title:", title)
        if title.startswith(PR_TITLE_PREFIX):
            body = pr.get("body", "")
            already_migrating.extend(pr_body_to_pkg_list(body))
    return set(already_migrating)

    
def post_tentative_build( filtered_to_migrate_dir, output_dir, target_platform, pkg_to_recipe_dir):
    # check which recipes were successfully built
    successful_builds = set()

    # iterate over all pkgs in outputdir/{target-platform}
    target_output_dir = output_dir / target_platform
    if target_output_dir.exists():
        for pkg_file in target_output_dir.iterdir():

            if pkg_file.is_file() and str(pkg_file).endswith(".tar.bz2"):
                recipe_hash = get_recipe_hash_build_pkg(pkg_file)
                if recipe_hash in pkg_to_recipe_dir:
                    successful_builds.add(pkg_to_recipe_dir[recipe_hash])
    if not successful_builds:
        print("No successful builds.")
        return
    successful_builds = list(successful_builds)

    print(f"Successfully built recipes: {successful_builds}")
    # new branch name 
    branch_name = pkg_list_to_branch_name(successful_builds)
    with git_branch_ctx(branch_name, stash_current=False):



        # move build recipes from filtered_to_migrate_dir
        # to the actual recipe dir RECIPES_EMSCRIPTEN_DIR
        # copy filtered_to_migrate_dir/<RECIPE> to RECIPES_EMSCRIPTEN_DIR/<RECIPE> 
        for recipe_dir in successful_builds:

            # this is the recipe where we already applied some transformations
            # (ie python in host ist renamed to python-dev, and similar changes)
            src_dir_modified = filtered_to_migrate_dir / recipe_dir

            # where the original recipe is located
            src_dir_original = TO_MIGRATE_RECIPES_EMSCRIPTEN_DIR / recipe_dir

            dst_dir = RECIPES_EMSCRIPTEN_DIR / recipe_dir

            
            if  dst_dir.exists():
                raise RuntimeError(f"Destination directory {dst_dir} already exists")
            
            shutil.copytree(src_dir_modified, dst_dir)
            print(f"Copied {src_dir_modified} to {dst_dir}") 


            # delete the old file via git
            subprocess.run(["git", "rm", "-r", str(src_dir_original)], check=True)

            # call git add to add RECIPES_EMSCRIPTEN_DIR / recipe_dir 
            subprocess.run(["git", "add", str(dst_dir)], check=True)

            # make commit for that recipe
            subprocess.run(["git", "commit", "-m", f"Migrate recipe {recipe_dir}"], check=True)

        # push the changes to the remote(with force if necessary)
        subprocess.run(["git", "push", "--force", "origin", branch_name], check=True)


        pr_title = pkg_list_to_pr_title(successful_builds)

        pr_body = generate_pr_body(successful_builds)

        # get current user
        if ON_GITHUB_ACTIONS:
            head = branch_name
        else:
            current_user = subprocess.check_output(['git', 'config', 'user.name']).decode().strip()
            head = f"{current_user}:{branch_name}"

        args = ['gh', 'pr', 'create',
                "--repo", "emscripten-forge/recipes",
                '--base', "emscripten-6x",
                "--head", head,
                '--title', pr_title, '--body', pr_body,
                '--label', '6x'
        ]

        # call gh to create a PR
        subprocess.check_call(args, cwd=os.getcwd())
            




def build_pkg_to_recipe_dir(to_migrate_dir):
    pkg_to_recipe_dir = {}
    for recipe_dir in to_migrate_dir.iterdir():
        if recipe_dir.is_dir() and (recipe_dir / "recipe.yaml").exists():
            # load the recipe.yaml content
            recipe_content = (recipe_dir / "recipe.yaml").read_text()
            # compute hash
            recipe_hash = hash_recipe_content(recipe_content)
            pkg_to_recipe_dir[recipe_hash] = recipe_dir.name
    return pkg_to_recipe_dir


def copy_selected_recipes(to_migrate_dir, already_migrating,  wildcards, wildcards_ignore, recipe_transformations, output_dir):
    to_migrate_dir = Path(to_migrate_dir)
    output_dir = Path(output_dir)

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    print("wildcards to ignore:", wildcards_ignore)
    print("wildcards to include:", wildcards)
    for recipe_dir in to_migrate_dir.iterdir():
        if recipe_dir.is_dir() and (recipe_dir / "recipe.yaml").exists():
            # dir_name
            dir_name = recipe_dir.name
            if wildcards is None or any(fnmatch.fnmatch(dir_name, wc) for wc in wildcards):

                if wildcards_ignore is not None and any(fnmatch.fnmatch(dir_name, wc) for wc in wildcards_ignore):
                    continue

                if dir_name in already_migrating:
                    continue

                migrate_recipe(recipe_dir, output_dir)



    
def build_tentative(output_dir=None,
                    target_platform='emscripten-wasm32', 
                    timeout=None, 
                    wildcards=None,
                    wildcards_ignore=None):
    """
    entry point for tentative building
    """

    if wildcards is None:
        wildcards = ['*']
    if wildcards_ignore is None:
        wildcards_ignore = []




    # create temp dir
    with TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        if output_dir is None:
            output_dir = temp_dir / "outdir"
        output_dir.mkdir(parents=True)

        filtered_to_migrate_dir = temp_dir / "filtered_to_migrate"
        filtered_to_migrate_dir.mkdir(parents=True)
        
        already_migrating = get_list_of_already_migrating_recipes()
        print("Already migrating recipes:", already_migrating)
        copy_selected_recipes(TO_MIGRATE_RECIPES_EMSCRIPTEN_DIR, already_migrating, wildcards, wildcards_ignore, recipe_transformations=[], output_dir=filtered_to_migrate_dir)


        # map recipe.yaml content to directory name 
        # st. we can later map the successful builds 
        # back to their respective recipe dir
        pkg_to_recipe_dir = build_pkg_to_recipe_dir(filtered_to_migrate_dir)

        # build all pkgs
        if 1:
            build_with_rattler_wrapper(recipes_dir=filtered_to_migrate_dir, output_dir=output_dir, 
                            target_platform=target_platform, skip_existing="local", 
                            timeout=timeout)


        subprocess.check_call(['gh', 'repo', 'set-default', 'emscripten-forge/recipes'], cwd=os.getcwd())

        pr_target_branch = "emscripten-6x"
        with get_github_user_ctx(use_bot=False)():

            # we want to make th changes ontop of pr_target_branch
            # but after the script we want to switch back to whatever branch we were on before
            with git_branch_ctx(pr_target_branch, stash_current=True, auto_delete=False, new_branch=False):


                # after the build, process the results
                post_tentative_build(filtered_to_migrate_dir=filtered_to_migrate_dir,
                                    output_dir=output_dir, 
                                    target_platform=target_platform, 
                                    pkg_to_recipe_dir=pkg_to_recipe_dir)

        