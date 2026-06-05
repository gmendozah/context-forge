import logging
import json
from typing import Optional
from src.domain.models import CoverLetterPayload
from src.gateways.compiler_service import CompilerService

logger = logging.getLogger(__name__)

class CompileCoverLetterUseCase:
    def __init__(self, compiler_service: CompilerService):
        self.compiler_service = compiler_service

    def execute(
        self,
        json_path: str,
        output_pdf_path: str,
        output_research_pdf_path: str,
        template_path: Optional[str] = None,
        research_template_path: Optional[str] = None
    ) -> None:
        logger.info(f"Executing CompileCoverLetterUseCase on {json_path}...")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read/parse JSON from {json_path}: {e}")
            raise

        try:
            payload = CoverLetterPayload.model_validate(data)
        except Exception as e:
            logger.error(f"JSON validation against CoverLetterPayload schema failed: {e}")
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

        logger.info("CompileCoverLetterUseCase execution completed successfully.")
