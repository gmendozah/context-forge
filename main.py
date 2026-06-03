import argparse
import asyncio
import logging
import sys
import yaml

from core.parser import parse_master_cv, read_job_description
from engine.orchestrator import run_parallel_pipeline

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
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        sys.exit(1)

async def main():
    parser = argparse.ArgumentParser(description="ContextForge - AI-augmented local CLI CV compiler")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--cv", type=str, help="Path to master_cv.md (overrides config)")
    parser.add_argument("--jd", type=str, help="Path to jd.txt (overrides config)")
    args = parser.parse_args()

    logger.info("Initializing ContextForge CLI Phase 1...")

    # Load configuration
    config = load_config(args.config)
    
    # Resolve file paths
    cv_path = args.cv or config.get("file_paths", {}).get("master_cv", "master_cv.md")
    jd_path = args.jd or config.get("file_paths", {}).get("job_description", "jd.txt")

    logger.info(f"Master CV path: {cv_path}")
    logger.info(f"Job Description path: {jd_path}")

    # Parse inputs
    chunks = parse_master_cv(cv_path)
    if not chunks:
        logger.error("Failed to parse Master CV or CV is empty. Exiting.")
        sys.exit(1)

    jd_content = read_job_description(jd_path)
    if not jd_content:
        logger.warning("Job Description is empty. Will proceed, but tailoring will be limited.")

    # Run the parallel async pipeline
    logger.info("Executing async LLM parallel pipeline...")
    results = await run_parallel_pipeline(chunks, jd_content, config)

    # Output intermediate structured results safely
    logger.info("Pipeline execution complete. Structured output:")
    for res in results:
        print("\n" + "="*50)
        print(f"HEADING: {res.get('heading')}")
        print("-" * 50)
        print(f"{res.get('tailored_content')}")
        print("="*50 + "\n")

if __name__ == "__main__":
    # Use standard library asyncio to run the async entry point
    asyncio.run(main())
