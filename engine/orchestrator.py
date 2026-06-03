import asyncio
import logging
from typing import List, Dict
from google import genai
from google.genai import types
from google.genai.errors import APIError
logger = logging.getLogger(__name__)
async def process_chunk_async(
    client: genai.Client, 
    chunk: Dict[str, str], 
    jd_content: str, 
    config: dict
) -> Dict[str, str]:
    """Processes a single CV chunk concurrently against the JD."""
    model_name = config.get("model_selections", {}).get("parallel_model", "gemini-3.5-flash")
    hyperparams = config.get("hyperparameters", {})
    
    prompt = f"""
You are an expert technical resume writer.
Your task is to tailor a specific section of a candidate's CV to better align with the provided Job Description (JD).
### Guidelines:
1. Prioritize semantic alignment with the JD.
2. Calibrate action verbs to match the tone and requirements of the JD.
3. Match technical terminology exactly as it appears in the JD.
4. CRITICAL: Do NOT omit or summarize hard metrics, numbers, or key technical achievements.
5. Maintain the original markdown formatting of the content.
### Job Description:
{jd_content}
### CV Section ({chunk.get('heading', 'Unknown')}):
{chunk.get('content', '')}
Please provide the tailored CV section below:
"""
    generation_config = types.GenerateContentConfig(
        temperature=hyperparams.get("temperature", 0.2),
        top_p=hyperparams.get("top_p", 0.8),
    )
    max_retries = 3
    heading = chunk.get('heading')
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Sending request for chunk '{heading}' (Attempt {attempt + 1})")
            # Uses the modern client.aio asynchronous interface
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=generation_config
            )
            logger.info(f"Successfully processed chunk '{heading}'")
            return {
                "heading": heading,
                "original_content": chunk.get("content"),
                "tailored_content": response.text
            }
        except APIError as e:
            logger.warning(f"API Error processing chunk '{heading}': {e}. Retry {attempt + 1}/{max_retries}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to process chunk '{heading}' after {max_retries} attempts.")
                return {
                    "heading": heading,
                    "original_content": chunk.get("content"),
                    "tailored_content": f"ERROR: Failed to process. Original content retained.\n\n{chunk.get('content')}"
                }
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.error(f"Unexpected error processing chunk '{heading}': {e}")
            return {
                "heading": heading,
                "original_content": chunk.get("content"),
                "tailored_content": f"ERROR: {e}\n\n{chunk.get('content')}"
            }
async def run_parallel_pipeline(
    chunks: List[Dict[str, str]], 
    jd_content: str, 
    config: dict
) -> List[Dict[str, str]]:
    """Runs the async LLM pipeline for all CV chunks in parallel."""
    if not jd_content:
        logger.warning("Job Description is empty. Skipping processing and returning original chunks.")
        return [{"heading": c.get("heading"), "tailored_content": c.get("content")} for c in chunks]
    # Initialize the modern google-genai client.
    # It will automatically pick up GEMINI_API_KEY from the environment.
    client = genai.Client()
    
    logger.info(f"Starting parallel processing for {len(chunks)} chunks...")
    
    tasks = [
        process_chunk_async(client, chunk, jd_content, config)
        for chunk in chunks
    ]
    
    # Execute all API calls concurrently
    results = await asyncio.gather(*tasks)
    
    logger.info("Completed parallel pipeline processing.")
    return list(results)
