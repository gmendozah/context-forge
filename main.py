import argparse
import asyncio
import logging
import sys
import yaml
from dotenv import load_dotenv

from core.parser import parse_master_cv, read_job_description
from engine.orchestrator import run_parallel_pipeline
from engine.synthesis import run_synthesis_pipeline
from core.compiler import parse_sections_to_structured_data
from generator import generate_resume

# Load local environment variables from .env file at startup
load_dotenv()

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
    parser.add_argument("--strategy", type=str, choices=["by_header_depth", "by_section", "single_document"], help="Chunking strategy (overrides config)")
    parser.add_argument("--dry-run", action="store_true", help="Print parsed chunks and exit without calling the LLM API")
    args = parser.parse_args()

    logger.info("Initializing ContextForge CLI Phase 1...")

    # Load configuration
    config = load_config(args.config)
    
    # Resolve file paths
    cv_path = args.cv or config.get("file_paths", {}).get("master_cv", "master_cv.md")
    jd_path = args.jd or config.get("file_paths", {}).get("job_description", "jd.txt")
    
    # Resolve chunking strategy
    chunking_config = config.get("chunking", {})
    strategy = args.strategy or chunking_config.get("strategy", "by_header_depth")

    logger.info(f"Master CV path: {cv_path}")
    logger.info(f"Job Description path: {jd_path}")
    logger.info(f"Chunking strategy: {strategy}")

    # Parse inputs
    chunks = parse_master_cv(cv_path, strategy=strategy)
    if not chunks:
        logger.error("Failed to parse Master CV or CV is empty. Exiting.")
        sys.exit(1)

    if args.dry_run:
        logger.info(f"Dry Run: Parsed {len(chunks)} chunks from Master CV:")
        for idx, chunk in enumerate(chunks, 1):
            print(f"\n[{idx}/{len(chunks)}] Heading: {chunk['heading']}")
            print(f"Content Length: {len(chunk['content'])} characters")
            print("-" * 30)
            preview = chunk['content'][:150].replace('\n', ' ')
            print(f"Preview: {preview}...")
        sys.exit(0)

    jd_content = read_job_description(jd_path)
    if not jd_content:
        logger.warning("Job Description is empty. Will proceed, but tailoring will be limited.")

    # Run the parallel async pipeline
    logger.info("Executing async LLM parallel pipeline...")
    results = await run_parallel_pipeline(chunks, jd_content, config)

    # Output intermediate structured results safely
    logger.info("Pipeline execution complete. Structured output generated.")

    # Concurrently aggregate tailored experience sections for synthesis input
    tailored_experiences_list = []
    for res in results:
        heading = res.get("heading", "")
        if heading.startswith("### "):
            tailored_experiences_list.append(f"{heading}\n{res.get('tailored_content')}")
    tailored_experiences_str = "\n\n".join(tailored_experiences_list)

    # Run Phase 2: Sequential Synthesis for summary and cover letter
    logger.info("Executing synthesis pipeline (Professional Summary & Cover Letter)...")
    synthesis_res = await run_synthesis_pipeline(tailored_experiences_str, jd_content, config)
    tailored_summary = synthesis_res.get("summary", "")
    cover_letter = synthesis_res.get("cover_letter", "")

    # Save the Cover Letter if generated
    if cover_letter:
        cl_path = config.get("file_paths", {}).get("output_cover_letter", "cover_letter.txt")
        try:
            with open(cl_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            logger.info(f"Successfully saved Cover Letter to: {cl_path}")
        except Exception as e:
            logger.error(f"Error saving Cover Letter file: {e}")

    # Run Phase 3: Typst compilation
    logger.info("Parsing results into structured resume data...")
    structured_data = parse_sections_to_structured_data(results, tailored_summary)
    
    output_pdf_path = config.get("file_paths", {}).get("output_pdf", "resume.pdf")
    
    try:
        generate_resume(structured_data, output_pdf_path)
    except Exception as e:
        logger.error(f"Failed to generate resume: {e}")

if __name__ == "__main__":
    # Use standard library asyncio to run the async entry point
    asyncio.run(main())
