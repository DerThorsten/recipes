
import json

def show_missing_packages(old_path, new_path):
    with open(old_path) as f:
        old_repodata = json.load(f)
    with open(new_path) as f:
        new_repodata = json.load(f)
    
    packages_old = set()
    packages_new = set()

    for key, value in old_repodata["packages"].items():
        packages_old.add(value["name"])
    
    for key, value in new_repodata["packages"].items():
        packages_new.add(value["name"])

    missing_packages = list(packages_old - packages_new)
    missing_packages.sort()

    print(f"Found {len(missing_packages)} missing packages")
    for name in missing_packages:
        print(name)