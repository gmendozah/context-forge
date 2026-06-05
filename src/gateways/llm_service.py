import logging
from abc import ABC, abstractmethod
from typing import Optional
from google import genai
from google.genai import types
from src.domain.models import ResumePayload, CoverLetterPayload

logger = logging.getLogger(__name__)

class LLMService(ABC):
    @abstractmethod
    async def tailor_resume(self, cv_content: str, jd_content: str, prompt_template: str) -> ResumePayload:
        pass

    @abstractmethod
    async def generate_cover_letter(self, partial_cv_content: str, jd_content: str, company_content: str, prompt_template: str) -> CoverLetterPayload:
        pass

class GeminiLLMService(LLMService):
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.5-flash", temperature: float = 0.2, top_p: float = 0.8):
        # The genai.Client picks up GEMINI_API_KEY from env automatically if api_key is None
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p

    async def tailor_resume(self, cv_content: str, jd_content: str, prompt_template: str) -> ResumePayload:
        logger.info(f"Sending tailor resume request to Gemini API (model: {self.model_name})...")
        
        # Format the prompt using replace to avoid formatting failures on curly braces in system instructions
        prompt = prompt_template.replace("{jd_content}", jd_content).replace("{master_cv_content}", cv_content)
        
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            response_mime_type="application/json",
            response_schema=ResumePayload,
        )
        
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        
        return ResumePayload.model_validate_json(response.text)

    async def generate_cover_letter(self, partial_cv_content: str, jd_content: str, company_content: str, prompt_template: str) -> CoverLetterPayload:
        logger.info(f"Sending cover letter generation request to Gemini API (model: {self.model_name})...")
        
        prompt = (prompt_template
                  .replace("{jd_content}", jd_content)
                  .replace("{partial_master_cv_content}", partial_cv_content)
                  .replace("{company_content}", company_content))
        
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            response_mime_type="application/json",
            response_schema=CoverLetterPayload,
        )
        
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        
        return CoverLetterPayload.model_validate_json(response.text)
