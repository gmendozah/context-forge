import argparse
import logging
import sys
import yaml
import json

from generator import generate_resume

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Configuration file not found: {config_path}. Using empty defaults.")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="ContextForge - Local JSON to Typst PDF compiler")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--json", type=str, help="Path to tailored resume JSON file (overrides config)")
    parser.add_argument("--pdf", type=str, help="Path to output PDF file (overrides config)")
    args = parser.parse_args()

    logger.info("Initializing ContextForge JSON Compiler...")

    # Load configuration
    config = load_config(args.config)
    
    # Resolve file paths
    json_path = args.json or config.get("file_paths", {}).get("resume_json", "resume.json")
    output_pdf_path = args.pdf or config.get("file_paths", {}).get("output_pdf", "resume.pdf")
    typst_template_path = config.get("file_paths", {}).get("typst_template", "templates/resume.typ")

    logger.info(f"Loading resume data from: {json_path}")
    
    # Load JSON file
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"JSON resume file not found at: {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON file {json_path}: {e}")
        sys.exit(1)

    logger.info(f"Compiling resume data to Typst PDF at: {output_pdf_path} (template: {typst_template_path})")
    
    try:
        generate_resume(resume_data, output_pdf_path, typst_template_path)
        logger.info("Resume generated successfully!")
    except Exception as e:
        logger.error(f"Failed to generate resume: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
