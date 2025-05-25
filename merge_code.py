import os
import sys


def should_exclude(file_path):
    # Exclude .DS_Store files
    if os.path.basename(file_path) == ".DS_Store":
        return True
    # Exclude files that are inside any directory named "migrations"
    if "migrations" in file_path.split(os.sep):
        return True
    # Exclude log files
    if file_path.lower().endswith(".log"):
        return True
    # Exclude files in any directory named "staticfiles"
    if "staticfiles" in file_path.split(os.sep):
        return True
    # Exclude files in any directory named "staticfiles"
    if "__pycache__" in file_path.split(os.sep):
        return True
    # Add more exclusion rules here if necessary
    return False


def merge_code(directories, output_file="merged_code.txt"):
    with open(output_file, "w", encoding="utf-8") as outfile:
        for directory in directories:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if should_exclude(file_path):
                        continue

                    # Get the path relative to the base directory for a cleaner header
                    relative_path = os.path.relpath(file_path, directory)
                    outfile.write(f"# {directory}/{relative_path}\n")

                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"// Error reading file: {e}\n")

                    # Separate file sections by extra newlines
                    outfile.write("\n\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python merge_code.py <output_file> <directory1> [directory2 ...]")
    else:
        output_file = sys.argv[1]
        directories = sys.argv[2:]
        merge_code(directories, output_file)
