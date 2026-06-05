import logging
import json
from typing import Optional
from src.domain.models import ResumePayload
from src.gateways.llm_service import LLMService
from src.gateways.compiler_service import CompilerService

logger = logging.getLogger(__name__)

class TailorResumeUseCase:
    def __init__(self, llm_service: LLMService, compiler_service: CompilerService):
        self.llm_service = llm_service
        self.compiler_service = compiler_service

    async def execute(
        self,
        cv_path: str,
        jd_path: str,
        prompt_template_path: str,
        output_json_path: str,
        output_pdf_path: str,
        template_path: Optional[str] = None
    ) -> ResumePayload:
        logger.info("Executing TailorResumeUseCase...")
        
        # Load CV
        try:
            with open(cv_path, "r", encoding="utf-8") as f:
                cv_content = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Master CV file not found at: {cv_path}")
            raise

        # Load JD
        try:
            with open(jd_path, "r", encoding="utf-8") as f:
                jd_content = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Job Description file not found at: {jd_path}")
            raise

        # Load Prompt Template
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                prompt_template = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt template file not found at: {prompt_template_path}")
            raise

        # Tailor CV using LLM
        payload = await self.llm_service.tailor_resume(cv_content, jd_content, prompt_template)
        
        # Save tailored JSON
        try:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(payload.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved tailored resume JSON to: {output_json_path}")
        except Exception as e:
            logger.error(f"Failed to write tailored JSON to {output_json_path}: {e}")
            raise

        # Compile PDF
        typ_path = output_pdf_path.rsplit(".", 1)[0] + ".typ"
        self.compiler_service.generate_resume_source(payload, template_path, typ_path)
        
        success = self.compiler_service.compile_pdf(typ_path, output_pdf_path)
        if not success:
            logger.error(f"Failed to compile PDF from Typst source {typ_path}")
            raise RuntimeError("Typst compilation failed.")

        logger.info("TailorResumeUseCase execution completed successfully.")
        return payload
