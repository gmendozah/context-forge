import os
import logging
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class AppConfig:
    def __init__(self, config_path: str = "config.yaml"):
        # Load environment variables from .env
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        self.config_data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config_data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to read yaml config from {config_path}: {e}. Using empty defaults.")
        else:
            logger.warning(f"Config file not found at: {config_path}. Using empty defaults.")

    def get_model_name(self) -> str:
        return self.config_data.get("model_selections", {}).get("parallel_model", "gemini-3.5-flash")

    def get_hyperparams(self) -> dict:
        return self.config_data.get("hyperparameters", {"temperature": 0.2, "top_p": 0.8})

    def get_path(self, *keys, default=None) -> str:
        """Helper to safely fetch nested values (like file paths) from the config yaml."""
        curr = self.config_data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default
        return curr or default
