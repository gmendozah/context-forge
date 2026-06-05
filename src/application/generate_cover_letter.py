import logging
import json
from typing import Optional
from src.domain.models import CoverLetterPayload
from src.gateways.llm_service import LLMService
from src.gateways.compiler_service import CompilerService

logger = logging.getLogger(__name__)

class GenerateCoverLetterUseCase:
    def __init__(self, llm_service: LLMService, compiler_service: CompilerService):
        self.llm_service = llm_service
        self.compiler_service = compiler_service

    async def execute(
        self,
        cv_path: str,
        jd_path: str,
        company_path: str,
        prompt_template_path: str,
        output_json_path: str,
        output_pdf_path: str,
        output_research_pdf_path: str,
        template_path: Optional[str] = None,
        research_template_path: Optional[str] = None
    ) -> CoverLetterPayload:
        logger.info("Executing GenerateCoverLetterUseCase...")
        
        # Load CV
        try:
            with open(cv_path, "r", encoding="utf-8") as f:
                cv_content = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Partial CV file not found at: {cv_path}")
            raise

        # Load JD
        try:
            with open(jd_path, "r", encoding="utf-8") as f:
                jd_content = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Job Description file not found at: {jd_path}")
            raise

        # Load Company details
        try:
            with open(company_path, "r", encoding="utf-8") as f:
                company_content = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Company profile file not found at: {company_path}")
            raise

        # Load Prompt Template
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                prompt_template = f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt template file not found at: {prompt_template_path}")
            raise

        # Generate cover letter & research via LLM
        payload = await self.llm_service.generate_cover_letter(
            cv_content, jd_content, company_content, prompt_template
        )

        # Save to JSON
        try:
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(payload.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved generated cover letter JSON to: {output_json_path}")
        except Exception as e:
            logger.error(f"Failed to write cover letter JSON to {output_json_path}: {e}")
            raise

        # Generate and Compile Cover Letter PDF
        cl_typ_path = output_pdf_path.rsplit(".", 1)[0] + ".typ"
        self.compiler_service.generate_cover_letter_source(payload, template_path, cl_typ_path)
        success_cl = self.compiler_service.compile_pdf(cl_typ_path, output_pdf_path)
        if not success_cl:
            logger.error(f"Failed to compile Cover Letter PDF to {output_pdf_path}")
            raise RuntimeError("Cover Letter Typst compilation failed.")

        # Generate and Compile Research Briefing PDF
        res_typ_path = output_research_pdf_path.rsplit(".", 1)[0] + ".typ"
        self.compiler_service.generate_research_source(payload, research_template_path, res_typ_path)
        success_res = self.compiler_service.compile_pdf(res_typ_path, output_research_pdf_path)
        if not success_res:
            logger.error(f"Failed to compile Research Briefing PDF to {output_research_pdf_path}")
            raise RuntimeError("Research Briefing Typst compilation failed.")

        logger.info("GenerateCoverLetterUseCase execution completed successfully.")
        return payload
