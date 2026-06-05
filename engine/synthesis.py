import logging
import json
from google import genai
from google.genai import types
from google.genai.errors import APIError
from core.prompts import load_prompt, render_prompt

logger = logging.getLogger(__name__)

DEFAULT_SYNTHESIS_PROMPT = """You are an elite technical resume writer and executive career coach.
We have successfully tailored the individual experience sections of the candidate's CV to align with a target Job Description (JD).

Now, your goal is to perform a high-level synthesis of these tailored experiences to produce two critical deliverables:
1. A high-impact **Professional Summary** for the top of the resume.
2. A compelling, tailored **Cover Letter** addressing the hiring manager.

### TARGET JOB DESCRIPTION:
{jd_content}

### TAILORED EXPERIENCE SECTIONS:
{tailored_experience}

---

### INSTRUCTIONS AND GUIDELINES:

#### 1. Professional Summary (Resume Header)
- **Length**: Exactly 3 to 5 sentences.
- **Content**: Highlight the candidate's years of experience, core technical expertise (specifically mobile engineering and AI-augmented workflows), and primary value proposition.
- **Tone**: Senior, authoritative, results-oriented, and tailored directly to the core challenges mentioned in the JD.
- **Keywords**: Seamlessly weave in high-priority skills and methodologies requested in the JD without sounding forced.

#### 2. Cover Letter
- **Length**: Approximately 300 to 400 words.
- **Structure**:
  - **Salutation**: Professional and standard (e.g., "Dear Hiring Team," or "Dear Hiring Manager,").
  - **Introduction**: Grab attention by stating interest in the specific role, referencing the company, and summarizing the candidate's professional identity.
  - **Body Paragraphs**: Focus on 1-2 major technical achievements from the tailored experience sections that directly solve pain points outlined in the JD. Clearly connect the candidate's expertise (e.g., engineering efficiency, systems design) to the team's needs.
  - **AI & Modern Workflow Mention**: Integrate how the candidate leverages AI-augmented workflows and modern tooling to accelerate delivery and ensure code quality.
  - **Conclusion & Call to Action**: Reiterate value, express enthusiasm for discussing how they can contribute, and close professionally.
- **Tone**: Confident, professional, engaging, and personalized. Avoid generic templates and clichés.

---

### OUTPUT FORMAT:
You must return your response as a raw JSON object with exactly two keys: "summary" and "cover_letter". 
Do NOT wrap the JSON in markdown code blocks (e.g., do not use ```json ... ```). Return ONLY the raw, parseable JSON string.

Example structure:
{
  "summary": "Professional Summary text...",
  "cover_letter": "Cover Letter text..."
}
"""


async def run_synthesis_pipeline(
    tailored_experience: str, jd_content: str, config: dict
) -> dict:
    """Runs the sequential LLM synthesis phase to generate the tailored Professional Summary and Cover Letter."""
    if not jd_content:
        logger.warning("Job Description is empty. Skipping synthesis phase.")
        return {"summary": "", "cover_letter": ""}

    model_name = config.get("model_selections", {}).get(
        "synthesis_model", "gemini-3.5-flash"
    )
    hyperparams = config.get("hyperparameters", {})

    # Load synthesis prompt template
    prompt_config_path = config.get("prompts", {}).get("synthesis")
    prompt_template = load_prompt(
        config_path=prompt_config_path,
        default_path="prompts/synthesis.txt",
        default_content=DEFAULT_SYNTHESIS_PROMPT,
    )

    prompt = render_prompt(
        prompt_template,
        {"jd_content": jd_content, "tailored_experience": tailored_experience},
    )

    generation_config = types.GenerateContentConfig(
        temperature=hyperparams.get("temperature", 0.3),
        top_p=hyperparams.get("top_p", 0.85),
        response_mime_type="application/json",
    )

    client = genai.Client()

    try:
        logger.info(f"Running synthesis pipeline with model '{model_name}'...")
        response = await client.aio.models.generate_content(
            model=model_name, contents=prompt, config=generation_config
        )
        logger.info("Successfully received response from synthesis model.")

        try:
            data = json.loads(response.text)
            return {
                "summary": data.get("summary", "").strip(),
                "cover_letter": data.get("cover_letter", "").strip(),
            }
        except json.JSONDecodeError as je:
            logger.error(
                f"Failed to parse JSON response from synthesis model: {je}. Raw response: {response.text}"
            )
            return {
                "summary": "",
                "cover_letter": "",
                "error": f"JSON parsing error: {je}",
            }

    except APIError as e:
        logger.error(f"API Error in synthesis pipeline: {e}")
        return {"summary": "", "cover_letter": "", "error": f"API Error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error in synthesis pipeline: {e}")
        return {"summary": "", "cover_letter": "", "error": f"Unexpected Error: {e}"}
