import logging
import json
from typing import Optional
from src.domain.models import ResumePayload
from src.gateways.compiler_service import CompilerService

logger = logging.getLogger(__name__)

class CompileResumeUseCase:
    def __init__(self, compiler_service: CompilerService):
        self.compiler_service = compiler_service

    def execute(self, json_path: str, pdf_path: str, template_path: Optional[str] = None) -> None:
        logger.info(f"Executing CompileResumeUseCase on {json_path}...")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read/parse JSON from {json_path}: {e}")
            raise

        try:
            payload = ResumePayload.model_validate(data)
        except Exception as e:
            logger.error(f"JSON validation against ResumePayload schema failed: {e}")
            raise

        # Resolve output typst file path
        typ_path = pdf_path.rsplit(".", 1)[0] + ".typ"
        
        # Generate typst markup
        self.compiler_service.generate_resume_source(payload, template_path, typ_path)
        
        # Compile markup to PDF
        success = self.compiler_service.compile_pdf(typ_path, pdf_path)
        if not success:
            logger.error(f"Failed to compile PDF from Typst source {typ_path}")
            raise RuntimeError("Typst compilation failed.")
        
        logger.info("CompileResumeUseCase execution completed successfully.")
