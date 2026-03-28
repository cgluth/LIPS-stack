import os, sys
import re

def load_html(path_to_html):
    def process_file_tag(match):
        file_path =  match.group(1)
        if not os.path.isfile(file_path):
            # Create an empty file if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('')
            print(f"Info: File '{file_path}' not found. Created empty file.")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f'<file src="{match.group(1)}">{content}</file>'

    def process_folder_tag(match):
        folder_path = match.group(1)
        if not os.path.isdir(folder_path):
            # Create folder if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)
            print(f"Info: Folder '{folder_path}' not found. Created empty folder.")
        return contents_from_folder(folder_path, parenthesis="<>")

    # Read the main HTML file
    with open(path_to_html, 'r', encoding='utf-8') as f:
        html_content = f.read()

    base_path = os.path.dirname(path_to_html)

    # First replace all <file> tags
    html_content = re.sub(
        r'<file src="(.+?)"></file>',
        lambda m: process_file_tag(m),
        html_content
    )

    # Then replace all <folder> tags recursively
    while re.search(r'<folder src="(.+?)"></folder>', html_content):
        html_content = re.sub(
            r'<folder src="(.+?)"></folder>',
            lambda m: process_folder_tag(m),
            html_content
        )

    return html_content


def extract_contents(text):
    """
    Extracts all [file src="..."] ... [/file] blocks from a text.
    Returns a flat dictionary: {file_path: content}
    Folders are ignored; only files are extracted.
    """
    # Regex to match file blocks
    file_pattern = re.compile(r'\[file\s+src="([^"]+)"\]\s*(.*?)\s*\[/file\]', re.DOTALL)
    
    result = {}
    for match in file_pattern.finditer(text):
        path = match.group(1).strip()
        content = match.group(2).strip()
        result[path] = content
    
    return result


def load_contents(filepath):
    """
    Loads a text file and extracts all file contents using extract_contents.
    Returns a flat dictionary: {file_path: content}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    return extract_contents(text)

def contents_from_folder(path_to_folder, parenthesis="[]", skip=None):
    """
    Recursively reads all files in path_to_folder and returns a string
    in [folder]/[file] syntax.

    Arguments:
    - path_to_folder: root folder to start
    - parenthesis: 2-character string for brackets, e.g., "[]" or "{}"
    - skip: list of folder or file names to ignore (default: ["__pycache__"])
    """
    if len(parenthesis) != 2:
        raise ValueError("parenthesis must be a 2-character string, e.g., '[]' or '{}'")

    if skip is None:
        skip = ["__pycache__"]

    open_br, close_br = parenthesis[0], parenthesis[1]

    def folder_to_string(folder_path):
        parts = [f"{open_br}folder src=\"{folder_path}\"{close_br}"]

        for entry in sorted(os.listdir(folder_path)):
            if entry in skip:
                continue  # skip specified files/folders

            full_path = os.path.join(folder_path, entry)

            if os.path.isfile(full_path):
                # Safe read with replacement for invalid UTF-8
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                parts.append(f"{open_br}file src=\"{full_path}\"{close_br}\n{content}\n{open_br}/file{close_br}")
            elif os.path.isdir(full_path):
                # Recursively process subfolder
                parts.append(folder_to_string(full_path))

        parts.append(f"{open_br}/folder{close_br}")
        return "\n".join(parts)

    return folder_to_string(path_to_folder)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python files.py path_to_html")
        sys.exit(1)

    path_to_html = sys.argv[1]
    result = load_html(path_to_html)
    print(result)