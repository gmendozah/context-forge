import os
import logging

logger = logging.getLogger(__name__)

def load_prompt(config_path: str, default_path: str, default_content: str) -> str:
    """Loads a prompt template from a configured path, falling back to a default path,
    and finally falling back to a default hardcoded template if not found.
    
    Args:
        config_path (str): Path to prompt template from config (can be None).
        default_path (str): Default path to search for the template file.
        default_content (str): The hardcoded fallback content if no file is found.
        
    Returns:
        str: The loaded or fallback prompt template content.
    """
    path = config_path or default_path
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Loaded prompt template from: {path}")
                return content
        except Exception as e:
            logger.warning(f"Failed to read prompt from {path}: {e}. Using fallback.")
            
    # Try default path if config path was different and failed
    if path != default_path and default_path and os.path.exists(default_path):
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"Loaded prompt template from default path: {default_path}")
                return content
        except Exception as e:
            logger.warning(f"Failed to read prompt from default path {default_path}: {e}.")

    logger.info("Using default hardcoded prompt template.")
    return default_content

def render_prompt(template: str, variables: dict) -> str:
    """Replaces placeholders in the template with the provided variables.
    Placeholders are formatted as {variable_name}.
    This avoids using str.format() which can raise errors if the template
    contains literal curly braces (e.g. JSON strings or code snippets).
    
    Args:
        template (str): The prompt template containing placeholders.
        variables (dict): A dictionary of variable names to their values.
        
    Returns:
        str: The rendered prompt.
    """
    rendered = template
    for key, value in variables.items():
        placeholder = f"{{{key}}}"
        rendered = rendered.replace(placeholder, str(value))
    return rendered
