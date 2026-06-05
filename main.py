import argparse
import asyncio
import logging
import sys
from typing import Optional

from src.infrastructure.config import AppConfig
from src.gateways.llm_service import GeminiLLMService
from src.gateways.compiler_service import TypstCompilerService
from src.application.compile_resume import CompileResumeUseCase
from src.application.tailor_resume import TailorResumeUseCase
from src.application.compile_cover_letter import CompileCoverLetterUseCase
from src.application.generate_cover_letter import GenerateCoverLetterUseCase

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ContextForge")

def main():
    parser = argparse.ArgumentParser(description="ContextForge - Clean Architecture Resume & Cover Letter tailoring engine")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to run")
    
    # Subcommand: resume
    resume_parser = subparsers.add_parser("resume", help="Tailor and compile a professional resume")
    resume_parser.add_argument("--cv", type=str, help="Path to master CV markdown file (overrides config)")
    resume_parser.add_argument("--jd", type=str, help="Path to job description text file (overrides config)")
    resume_parser.add_argument("--json", type=str, help="Path to a pre-existing resume JSON. If provided, compiles PDF directly without hitting the API.")
    resume_parser.add_argument("--pdf", type=str, help="Path to output PDF (overrides config)")
    resume_parser.add_argument("--template", type=str, help="Path to Typst template (overrides config)")
    
    # Subcommand: cover-letter
    cl_parser = subparsers.add_parser("cover-letter", help="Generate and compile a tailored cover letter and research briefing")
    cl_parser.add_argument("--cv", type=str, help="Path to partial master CV markdown file (overrides config)")
    cl_parser.add_argument("--jd", type=str, help="Path to job description text file (overrides config)")
    cl_parser.add_argument("--company", type=str, help="Path to company description profile text file (overrides config)")
    cl_parser.add_argument("--json", type=str, help="Path to a pre-existing cover letter JSON. If provided, compiles PDFs directly without hitting the API.")
    cl_parser.add_argument("--pdf", type=str, help="Path to output cover letter PDF (overrides config)")
    cl_parser.add_argument("--research", type=str, help="Path to output research briefing PDF (overrides config)")
    cl_parser.add_argument("--template", type=str, help="Path to cover letter Typst template (overrides config)")
    cl_parser.add_argument("--research-template", type=str, help="Path to research briefing Typst template (overrides config)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = AppConfig(args.config)
    
    # Initialize compiler gateway
    compiler_service = TypstCompilerService()
    
    # Setup LLM service only if needed (not compiling from pre-existing JSON)
    llm_service: Optional[GeminiLLMService] = None
    if not args.json:
        if not config.api_key:
            logger.error("GEMINI_API_KEY environment variable is not set. Please set it in .env or the shell.")
            sys.exit(1)
        llm_service = GeminiLLMService(
            api_key=config.api_key,
            model_name=config.get_model_name(),
            temperature=config.get_hyperparams().get("temperature", 0.2),
            top_p=config.get_hyperparams().get("top_p", 0.8)
        )

    if args.command == "resume":
        # Resolve file paths
        cv_path = args.cv or config.get_path("file_paths", "master_cv", default="master_cv.md")
        jd_path = args.jd or config.get_path("file_paths", "job_description", default="jd.txt")
        output_pdf_path = args.pdf or config.get_path("file_paths", "output_pdf", default="artifacts/resume.pdf")
        template_path = args.template or config.get_path("file_paths", "typst_template", default="templates/resume.typ")
        
        if args.json:
            # Non-Agentic compiler execution
            use_case = CompileResumeUseCase(compiler_service)
            try:
                use_case.execute(args.json, output_pdf_path, template_path)
                logger.info(f"Resume PDF compiled successfully from JSON: {output_pdf_path}")
            except Exception as e:
                logger.error(f"Failed to compile resume from JSON: {e}")
                sys.exit(1)
        else:
            # Agentic tailoring pipeline execution
            output_json_path = config.get_path("file_paths", "resume_json", default="artifacts/resume.json")
            prompt_template_path = config.get_path("prompts", "tailor_resume", default="prompts/tailor_resume.md")
            
            use_case = TailorResumeUseCase(llm_service, compiler_service)
            logger.info("Executing agentic resume tailoring pipeline...")
            try:
                asyncio.run(use_case.execute(
                    cv_path=cv_path,
                    jd_path=jd_path,
                    prompt_template_path=prompt_template_path,
                    output_json_path=output_json_path,
                    output_pdf_path=output_pdf_path,
                    template_path=template_path
                ))
                logger.info(f"Resume tailored and compiled! PDF: {output_pdf_path}, JSON: {output_json_path}")
            except Exception as e:
                logger.error(f"Agentic resume tailoring failed: {e}")
                sys.exit(1)

    elif args.command == "cover-letter":
        # Resolve file paths
        cv_path = args.cv or config.get_path("file_paths", "partial_master_cv", default="partial_master_cv.md")
        jd_path = args.jd or config.get_path("file_paths", "job_description", default="jd.txt")
        company_path = args.company or config.get_path("file_paths", "company_profile", default="company.txt")
        output_pdf_path = args.pdf or config.get_path("file_paths", "output_cover_letter_pdf", default="artifacts/cover_letter.pdf")
        output_research_pdf_path = args.research or config.get_path("file_paths", "output_research_pdf", default="artifacts/research.pdf")
        template_path = args.template or config.get_path("file_paths", "cover_letter_template", default="templates/cover_letter.typ")
        research_template_path = args.research_template or config.get_path("file_paths", "research_template", default="templates/research.typ")
        
        if args.json:
            # Non-Agentic cover letter compilation execution
            use_case = CompileCoverLetterUseCase(compiler_service)
            try:
                use_case.execute(
                    json_path=args.json,
                    output_pdf_path=output_pdf_path,
                    output_research_pdf_path=output_research_pdf_path,
                    template_path=template_path,
                    research_template_path=research_template_path
                )
                logger.info(f"Cover Letter compiled to: {output_pdf_path}, Research compiled to: {output_research_pdf_path}")
            except Exception as e:
                logger.error(f"Failed to compile cover letter from JSON: {e}")
                sys.exit(1)
        else:
            # Agentic cover letter generation execution
            output_json_path = config.get_path("file_paths", "cover_letter_json", default="artifacts/cover_letter.json")
            prompt_template_path = config.get_path("prompts", "cover_letter", default="prompts/cover_letter.md")
            
            use_case = GenerateCoverLetterUseCase(llm_service, compiler_service)
            logger.info("Executing agentic cover letter pipeline...")
            try:
                asyncio.run(use_case.execute(
                    cv_path=cv_path,
                    jd_path=jd_path,
                    company_path=company_path,
                    prompt_template_path=prompt_template_path,
                    output_json_path=output_json_path,
                    output_pdf_path=output_pdf_path,
                    output_research_pdf_path=output_research_pdf_path,
                    template_path=template_path,
                    research_template_path=research_template_path
                ))
                logger.info(f"Cover Letter & Research compiled! CL PDF: {output_pdf_path}, Research PDF: {output_research_pdf_path}, JSON: {output_json_path}")
            except Exception as e:
                logger.error(f"Agentic cover letter generation failed: {e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
