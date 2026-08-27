from diskcache import Cache
from pathlib import Path
from .constants import RECIPES_ROOT
import yaml
from jinja2 import Template,Environment
import requests
import pprint
import re
import json
rebuild_all_cache = Cache("rebuild_all_cache")



@rebuild_all_cache.memoize(expire=3600)
def download_repodata(url):
    print(f"downloading repodata from {url}")
    response = requests.get(url)
    response.raise_for_status()
    repodata = response.json()
    return repodata

@rebuild_all_cache.memoize(expire=36000)
def download_noarch_repodata():
    print("downloading noarch repodata from conda-forge, bioconda and microsoft channels")
    noarch_repodata_urls = {
        'conda-forge': 'https://conda.anaconda.org/conda-forge/noarch/repodata.json',
        # 'bioconda': 'https://conda.anaconda.org/bioconda/noarch/repodata.json',
        # 'microsoft': 'https://conda.anaconda.org/microsoft/noarch/repodata.json',
    }
    repodata = {}
    for channel, url in noarch_repodata_urls.items():
        print("downloading repodata for channel:", channel)
        repodata[channel] = download_repodata(url)
    return repodata

# @rebuild_all_cache.memoize(expire=36000)
def compute_noarch_set():
    def get_pkg_and_pkgconda(pkgdata):
        pkg_name = pkgdata.get("name")
        pkg_version = pkgdata.get("version")
        pkg_build = pkgdata.get("build")
        return (pkg_name, pkg_version, pkg_build)

    repodata = download_noarch_repodata()
    as_str = json.dumps(repodata, indent=2)
    with open("noarch_repodata.json", "w") as f:
        f.write(as_str)
    noarch_pkg_set = set()
    for channel, channel_repodata in repodata.items():
        for pkgdata in channel_repodata.get("packages", {}).values():
            pkg_name = pkgdata.get("name")
            noarch_pkg_set.add(pkg_name)
        for pkgdata in channel_repodata.get("packages.conda", {}).values():
            pkg_name = pkgdata.get("name")
            noarch_pkg_set.add(pkg_name)
    return noarch_pkg_set


def rebuild_all():
    
    noarch_pkg_set = compute_noarch_set()
    assert "pybind11" in noarch_pkg_set, "pybind11 is not in the noarch package set, something is wrong with the repodata download"


    wasm_recipe_dirs = [
        Path(RECIPES_ROOT) / "recipes_emscripten",
        Path(RECIPES_ROOT) / "recipes_wasm",
    ]

    native_recipe_dirs = [
        Path(RECIPES_ROOT) / "recipes_native",
    ]

    print("computing recipes to provided packages mapping for wasm recipes")
    recipes_path_to_packages_provided = {}
    for recipe_dir in wasm_recipe_dirs :
        print(f"computing recipes to provided packages mapping for recipe_dir: {recipe_dir}")
        ret = get_recipes_to_provided_pkgs_mapping(recipe_dir)
        recipes_path_to_packages_provided.update(ret)

    print("reverse mapping: check which recipes provide a given package")
    # reverse mapping: check which recipes provide a given package
    package_to_recipes_mapping = {}
    for recipe_path, packages_provided in recipes_path_to_packages_provided.items():
        for pkg_name in packages_provided:
            if pkg_name not in package_to_recipes_mapping:
                package_to_recipes_mapping[pkg_name] = [recipe_path]
            else:
                package_to_recipes_mapping[pkg_name].append(recipe_path)
                print(f"WARNING: Package {pkg_name} is provided by multiple recipes: {package_to_recipes_mapping[pkg_name]} and {recipe_path}")


    print("computing recipes to needed packages mapping for native recipes")
    recipes_path_to_packages_needed = {}
    for recipe_dir in wasm_recipe_dirs:
        print(f"computing recipes to needed packages mapping for recipe_dir: {recipe_dir}")
        ret = get_recipes_to_needed_pkgs_mapping(recipe_dir)
        recipes_path_to_packages_needed.update(ret)


    recipes_recipe_deps_mapping = {}
    for recipe_path, packages_needed in recipes_path_to_packages_needed.items():
        print("checking which recipes provide the needed packages for recipe:", recipe_path)
        recipe_deps = []
        for pkg_name in packages_needed:
            if pkg_name in package_to_recipes_mapping:
                recipe_deps.extend(package_to_recipes_mapping[pkg_name])
            else:
                if pkg_name not in noarch_pkg_set:
                    print(f"WARNING: Package {pkg_name} is needed by recipe {recipe_path} but is not provided by any recipe and is not a noarch package")
        recipes_recipe_deps_mapping[recipe_path] = recipe_deps


    
def iterate_recipes(recipe_dirs):
    for recipe_dir in recipe_dirs:
        for recipe_path in recipe_dir.iterdir():
            if recipe_path.is_dir():
                recipe_yaml_path = recipe_path / "recipe.yaml"
                if recipe_yaml_path.exists():
                    with open(recipe_yaml_path, "r") as f:
                        recipe_yaml = yaml.safe_load(f)
                        yield recipe_path, recipe_yaml


def render_name(recipe_yaml, name):
    if "${{" in name:
        # render the name using the recipe_yaml context
        context = recipe_yaml.get("context", {})
        env = Environment(
            variable_start_string="${{",
            variable_end_string="}}",
        )
        template = env.from_string(name)
        context = recipe_yaml.get("context", {})

        return template.render(context)
    return name

#@rebuild_all_cache.memoize(expire=3600)
def get_recipes_to_provided_pkgs_mapping(recipe_dir):
    # find out what packages are provided by each recipe in the given recipe_dir
    recipes_path_to_packages_provided = {}
    for recipe_path, recipe_yaml in iterate_recipes([recipe_dir]):
        # multi-output or normal recipe?
        outputs = recipe_yaml.get("outputs", [])
        if outputs:
            # remove staging
            outputs = [output for output in outputs if output.get("staging") is None]
            packages_provided = [output.get("package", {}).get("name") for output in outputs]
        else:
            packages_provided = [recipe_yaml.get("package", {}).get("name")]

        for i, pkg_name in enumerate(packages_provided):
            if pkg_name is not None:
                packages_provided[i] = render_name(recipe_yaml, pkg_name)
            else:
                raise RuntimeError(f"Recipe {recipe_path} does not provide a package name in recipe.yaml")
        recipes_path_to_packages_provided[recipe_path] = packages_provided
    return recipes_path_to_packages_provided

def sanitize_dependency_name(name):
    # remove version constraints and build strings from dependency names
    # e.g. "libpng >=1.6.37,<1.7.0a0" -> "libpng"
    # e.g. "libpng 1.6.37 hbc83047_0" -> "libpng"
    # e.g. "libpng >=1.6.37,<1.7.0a0 py39hbc83047_0" -> "libpng"
    # e.g. "libpng 1.6.37 hbc83047_0 py39hbc83047_0" -> "libpng"

    name = re.split('<=|>=|<|>|=| ', name)[0]


    if name is None:
        raise ValueError("Dependency name cannot be None")
    name = name.split()[0]
    name = name.split("=")[0]

    if ">=" in name or "<=" in name or ">" in name or "<" in name:
        raise ValueError(f"Dependency name {name} contains version constraints, which is not allowed")
    return name


# the dependency list
# are not only strings, but may also contain if else statements
# atm we dont support nested if else statements
def extract_flat_deps(deps):
    if deps is None:
        return []
    items = []
    for item in deps:
        if isinstance(item, str):
            items.append(item)
        elif isinstance(item, dict):
            for key,value in item.items():
                if key == 'if':
                    continue
                elif key == 'then' or key == 'else':
                    if isinstance(value, list):
                        for v in value:
                            if isinstance(v, str):
                                items.append(v)
                            else:
                                raise ValueError(f"Unexpected value type in dependency dict: {v}")
                    elif isinstance(value, str):
                        items.append(value)
                    else:
                        raise ValueError(f"Unexpected value type in dependency dict: {value}")
                else:
                    raise ValueError(f"Unexpected key in dependency dict: {key}")
        else:
            raise ValueError(f"Unexpected item type in dependency list: {item}")
    return items

def get_required_packages_from_recipe(recipe_yaml):
    packages_needed = []
    if outputs := recipe_yaml.get("outputs"):
        # remove staging
        outputs = [output for output in outputs if output.get("staging") is None]
        for output in outputs:
            requirements = output.get("requirements", {})
            host_reqs = extract_flat_deps(requirements.get("host", []))
            run_reqs = extract_flat_deps(requirements.get("run", []))
            packages_needed.extend(host_reqs + run_reqs)
            if run_reqs is None:
                run_reqs = []
            if host_reqs is None:
                host_reqs = []
    else:
        requirements = recipe_yaml.get("requirements", {})
        host_reqs = extract_flat_deps(requirements.get("host", []))
        run_reqs = extract_flat_deps(requirements.get("run", []))
        if run_reqs is None:
            run_reqs = []
        if host_reqs is None:
            host_reqs = []
        packages_needed.extend(host_reqs + run_reqs)

    for i, pkg_name in enumerate(packages_needed):
        if pkg_name is not None:
            try:
                packages_needed[i] = sanitize_dependency_name(pkg_name)
            except ValueError as e:
                raise RuntimeError(f"Recipe {pkg_name} errored") from e
        else:
            raise RuntimeError(f"Recipe {recipe_path} does not provide a package name in recipe.yaml")

    
    return packages_needed

def get_recipes_to_needed_pkgs_mapping(recipe_dir):
    # find out what packages are needed by each recipe in the given recipe_dir
    recipes_path_to_packages_needed = {}
    for recipe_path, recipe_yaml in iterate_recipes([recipe_dir]):
        try:
            packages_needed = get_required_packages_from_recipe(recipe_yaml)
        except Exception as e:
            raise RuntimeError(f"Error processing recipe {recipe_path}: {e}") from e
        print(f"Recipe {recipe_path} needs packages: {packages_needed}")
        recipes_path_to_packages_needed[recipe_path] = packages_needed
    return recipes_path_to_packages_needed