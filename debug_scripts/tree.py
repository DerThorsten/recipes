# list all files in a directory and create a json file with the list of files
import os
import json




if __name__ == "__main__":
    import argparse

    # directory is the first argument
    parser = argparse.ArgumentParser(description="List all files in a directory and create a json file with the list of files")
    parser.add_argument("directory", type=str, help="Directory to list files in")
    parser.add_argument("output_file", type=str, help="Output json file")
    args = parser.parse_args()

    # create a dictionary with the list of files in each subdirectory
    files = []
    # recursively list all files in the directory
    for root, dirs, filenames in os.walk(args.directory):
        for filename in filenames:
            # get the relative path of the file
            relative_path = os.path.relpath(os.path.join(root, filename), args.directory)
            files.append(relative_path)

    # write the dictionary to a json file
    with open(args.output_file, "w") as f:
        json.dump(files, f, indent=4)