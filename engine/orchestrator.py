import asyncio
import logging
from typing import List, Dict
from google import genai
from google.genai import types
from google.genai.errors import APIError
from core.prompts import load_prompt, render_prompt

logger = logging.getLogger(__name__)

DEFAULT_TAILOR_CHUNK_PROMPT = """You are an elite technical resume writer and career strategist specializing in software engineering and technology roles.
Your task is to tailor a specific section of a candidate's CV (Curriculum Vitae) to align with a target Job Description (JD).

Here is the context you must work with:

### TARGET JOB DESCRIPTION:
{jd_content}

### CURRENT CV SECTION:
Heading: {section_heading}
Content:
{section_content}

---

### INSTRUCTIONS AND GUIDELINES:

1. **Strategic Tailoring & Semantic Alignment**:
   - Analyze the target JD to identify key themes, core technologies, methodologies, and leadership/seniority expectations.
   - Tailor the CV section to highlight experiences, skills, and projects that directly address those requirements.
   - Translate candidate accomplishments into terms that resonate with the hiring manager's specific stack and workflow (e.g. if the JD emphasizes "scalable microservices" and the CV says "backend APIs", align the phrasing to highlight scalability and microservice architecture where technically accurate).

2. **Action Verbs & Impact Calibration (X-Y-Z Formula)**:
   - Begin accomplishments with strong, active verbs that match the seniority level of the JD (e.g., *designed, architected, spearheaded, optimized, pioneered* for senior roles).
   - Whenever possible, format achievements using the Google X-Y-Z formula: "Accomplished [X], as measured by [Y], by doing [Z]."
   - **CRITICAL**: Do NOT omit, weaken, or summarize hard metrics, percentages, dollar amounts, or numbers. Keep existing quantitative impact fully intact and emphasize its relevance to the JD's goals.

3. **Natural Technical Vocabulary Integration**:
   - Match technical terms, frameworks, tools, and methodologies exactly as they are written in the JD (e.g., capitalization, specific naming like "CI/CD" vs "continuous integration"), but do so naturally.
   - Avoid keyword stuffing. The tailored content must read professionally, flow logically, and sound like it was written by a human expert, not an SEO bot.

4. **Strict Content Integrity & Truthfulness**:
   - **CRITICAL**: Do NOT invent or hallucinate new facts, projects, technologies, metrics, roles, or responsibilities. You may rephrase, reorganize, and emphasize existing experiences, but you must NEVER add unearned credentials or technologies the candidate has not used.
   - If a technology or skill from the JD is not mentioned or implied in the current section, do not fabricate a lie about using it.

5. **Structural & Formatting Constraints**:
   - Maintain the original Markdown structure (headers, bullet points, bold/italic text).
   - Only tailor the text content; do not change the underlying markdown formatting scheme.
   - **OUTPUT LIMITATION**: Do not include any introductory or concluding remarks, explanations, or meta-commentary (such as "Here is the tailored section:"). Return ONLY the raw, tailored CV section content.
"""

async def process_chunk_async(
    client: genai.Client, 
    chunk: Dict[str, str], 
    jd_content: str, 
    config: dict,
    prompt_template: str
) -> Dict[str, str]:
    """Processes a single CV chunk concurrently against the JD."""
    model_name = config.get("model_selections", {}).get("parallel_model", "gemini-3.5-flash")
    hyperparams = config.get("hyperparameters", {})
    
    prompt = render_prompt(
        prompt_template,
        {
            "jd_content": jd_content,
            "section_heading": chunk.get('heading', 'Unknown'),
            "section_content": chunk.get('content', '')
        }
    )

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

    # Fallback return in case the loop completes without returning (e.g., if max_retries is 0 or loop completes without hitting returns)
    return {
        "heading": heading,
        "original_content": chunk.get("content"),
        "tailored_content": f"ERROR: Loop completed without producing result. Original content retained.\n\n{chunk.get('content')}"
    }
async def run_parallel_pipeline(
    chunks: List[Dict[str, str]], 
    jd_content: str, 
    config: dict
) -> List[Dict[str, str]]:
    """Runs the async LLM pipeline for all CV chunks in parallel."""
    if not jd_content:
        logger.warning("Job Description is empty. Skipping processing and returning original chunks.")
        return [{"heading": c.get("heading"), "original_content": c.get("content"), "tailored_content": c.get("content")} for c in chunks]
    
    # Load tailor prompt template
    prompt_config_path = config.get("prompts", {}).get("tailor_chunk")
    prompt_template = load_prompt(
        config_path=prompt_config_path,
        default_path="prompts/tailor_chunk.txt",
        default_content=DEFAULT_TAILOR_CHUNK_PROMPT
    )

    # Initialize the modern google-genai client.
    # It will automatically pick up GEMINI_API_KEY from the environment.
    client = genai.Client()
    
    chunking_config = config.get("chunking", {})
    skip_sections = chunking_config.get("skip_sections", [])
    
    api_limits = config.get("api_limits", {})
    concurrency_limit = api_limits.get("concurrency_limit", 3)
    request_delay = api_limits.get("request_delay", 0.5)
    
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    logger.info(
        f"Starting parallel processing for {len(chunks)} chunks "
        f"(Concurrency limit: {concurrency_limit}, Delay: {request_delay}s, "
        f"Skip list size: {len(skip_sections)})"
    )
    
    async def worker(chunk: Dict[str, str], idx: int) -> Dict[str, str]:
        heading = chunk.get("heading", "")
        # Check if the section should be skipped for tailoring
        if any(heading.strip() == skip.strip() for skip in skip_sections):
            logger.info(f"Skipping tailoring for section '{heading}' (present in skip_sections)")
            return {
                "heading": heading,
                "original_content": chunk.get("content"),
                "tailored_content": chunk.get("content")
            }
            
        if idx > 0 and request_delay > 0:
            delay_sec = idx * request_delay
            logger.debug(f"Staggering chunk '{heading}': waiting {delay_sec:.2f}s before execution")
            await asyncio.sleep(delay_sec)
            
        async with semaphore:
            return await process_chunk_async(client, chunk, jd_content, config, prompt_template)
            
    tasks = [
        worker(chunk, idx)
        for idx, chunk in enumerate(chunks)
    ]
    
    # Execute all API calls concurrently
    results = await asyncio.gather(*tasks)
    
    logger.info("Completed parallel pipeline processing.")
    return list(results)
