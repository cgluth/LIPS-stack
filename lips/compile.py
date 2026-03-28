from .files import load_html, extract_contents
from .api import API
import sys, os
import json
from pathlib import Path
import argparse
from dotenv import load_dotenv
import time

def main():
    # Load .env from the folder where python is run
    project_root = Path.cwd()  # current working directory
    dotenv_path = project_root / ".env"

    if not dotenv_path.exists():
        raise FileNotFoundError(f".env file not found at {dotenv_path}")

    load_dotenv(dotenv_path=dotenv_path)
    
    # 1. Take the first argument as a path to the input folder
    parser = argparse.ArgumentParser(description="Process input folder for API response.")
    parser.add_argument("input_folder", help="Path to the input folder")
    args = parser.parse_args()

    input_folder = Path(args.input_folder)
    if not input_folder.exists():
        print(f"Error: Input folder '{input_folder}' does not exist.")
        sys.exit(1)

    # Ensure output folder exists
    output_folder = input_folder / "out"
    output_folder.mkdir(exist_ok=True)

    # 2. Load prompt template
    prompt_template_path = input_folder / "configs" / "prompt-template.html"
    if not prompt_template_path.exists():
        print(f"Error: Prompt template '{prompt_template_path}' does not exist.")
        sys.exit(1)

    prompt = load_html(prompt_template_path)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    
    # 3. Write prompt to ./inputfolder/out/prompt.html
    prompt_output_path = output_folder / f"{timestamp}.html"
    prompt_output_path.write_text(prompt, encoding="utf-8")
    print(f"Prompt written to {prompt_output_path}")

    # 4. Load API config from ./inputfolder/config/api.json
    api_config_path = input_folder / "configs" / "api.json"
    if not api_config_path.exists():
        print(f"Error: API config '{api_config_path}' does not exist.")
        sys.exit(1)

    with open(api_config_path, "r", encoding="utf-8") as f:
        api_config = json.load(f)

    # 5. Initialize API
    api = API(api_config)

    # 6. Get response from API
    response = api.get_response(prompt)

    # 9. Write the extracted content to ./inputfolder/out/out.contents

    response_output_path = output_folder / f"{timestamp}.log"
    response_output_path.write_text(response, encoding="utf-8")
    print(f"Response content written to {response_output_path}")

    contents = extract_contents(response)
    
    for path, content in contents.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Overwriting {path}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == "__main__":
    main()
