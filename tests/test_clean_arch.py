import unittest
from unittest.mock import Mock, AsyncMock, patch
import json
from src.domain.models import ResumePayload, CoverLetterPayload
from src.application.compile_resume import CompileResumeUseCase
from src.application.tailor_resume import TailorResumeUseCase
from src.application.compile_cover_letter import CompileCoverLetterUseCase
from src.application.generate_cover_letter import GenerateCoverLetterUseCase

class TestCleanArchitecture(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Sample Resume Data
        self.mock_resume_data = {
            "name": "Geovani Mendoza",
            "title": "Senior Mobile Engineer",
            "contact_info": ["La Paz, Bolivia", "geovani@example.com"],
            "summary": "Experienced engineer.",
            "skills": [{"name": "Mobile", "items": ["Flutter", "Swift"]}],
            "experience": [
                {
                    "company": "Dozuki",
                    "role": "Senior Engineer",
                    "dates": "2023-2025",
                    "location": "Remote",
                    "bullets": [{"type": "bullet", "text": "Built some cool stuff."}]
                }
            ],
            "projects": [],
            "education": [],
            "certifications": [],
            "awards": [],
            "languages": []
        }

        # Sample Cover Letter Data
        self.mock_cover_letter_data = {
            "recipient_name": "John Doe",
            "recipient_title": "Hiring Director",
            "company_name": "InnovateCorp",
            "date": "June 5, 2026",
            "salutation": "Dear John",
            "body_paragraphs": ["I am writing to apply...", "My background..."],
            "signoff": "Sincerely",
            "candidate_name": "Geovani Mendoza",
            "candidate_title": "Senior Engineer",
            "candidate_contact": ["La Paz, Bolivia", "geovani@example.com"],
            "company_research": {
                "company_name": "InnovateCorp",
                "mission_and_values": "Innovate and create.",
                "role_challenges": ["Scaling the platform"],
                "notable_projects": ["Core API rewrite"],
                "why_candidate_fits": "Fits the engineering culture."
            }
        }

    def test_resume_schema_validation(self):
        payload = ResumePayload.model_validate(self.mock_resume_data)
        self.assertEqual(payload.name, "Geovani Mendoza")
        self.assertEqual(payload.experience[0].company, "Dozuki")

    def test_cover_letter_schema_validation(self):
        payload = CoverLetterPayload.model_validate(self.mock_cover_letter_data)
        self.assertEqual(payload.recipient_name, "John Doe")
        self.assertEqual(payload.company_research.company_name, "InnovateCorp")

    def test_compile_resume_use_case(self):
        mock_compiler = Mock()
        mock_compiler.compile_pdf.return_value = True
        use_case = CompileResumeUseCase(mock_compiler)

        mock_json_content = json.dumps(self.mock_resume_data)
        with patch("builtins.open", unittest.mock.mock_open(read_data=mock_json_content)):
            use_case.execute("resume.json", "resume.pdf")

        mock_compiler.generate_resume_source.assert_called_once()
        mock_compiler.compile_pdf.assert_called_once()

    async def test_tailor_resume_use_case(self):
        mock_llm = AsyncMock()
        mock_compiler = Mock()
        mock_compiler.compile_pdf.return_value = True
        
        parsed_payload = ResumePayload.model_validate(self.mock_resume_data)
        mock_llm.tailor_resume.return_value = parsed_payload
        
        use_case = TailorResumeUseCase(mock_llm, mock_compiler)

        with patch("builtins.open", unittest.mock.mock_open(read_data="mock data")):
            with patch("json.dump") as mock_json_dump:
                await use_case.execute(
                    cv_path="cv.md",
                    jd_path="jd.txt",
                    prompt_template_path="prompt.md",
                    output_json_path="output.json",
                    output_pdf_path="output.pdf"
                )
                mock_json_dump.assert_called_once()
                
        mock_llm.tailor_resume.assert_called_once()
        mock_compiler.generate_resume_source.assert_called_once()
        mock_compiler.compile_pdf.assert_called_once()

    def test_compile_cover_letter_use_case(self):
        mock_compiler = Mock()
        mock_compiler.compile_pdf.return_value = True
        use_case = CompileCoverLetterUseCase(mock_compiler)

        mock_json_content = json.dumps(self.mock_cover_letter_data)
        with patch("builtins.open", unittest.mock.mock_open(read_data=mock_json_content)):
            use_case.execute("cover_letter.json", "cover_letter.pdf", "research.pdf")

        mock_compiler.generate_cover_letter_source.assert_called_once()
        mock_compiler.generate_research_source.assert_called_once()
        self.assertEqual(mock_compiler.compile_pdf.call_count, 2)

    async def test_generate_cover_letter_use_case(self):
        mock_llm = AsyncMock()
        mock_compiler = Mock()
        mock_compiler.compile_pdf.return_value = True
        
        parsed_payload = CoverLetterPayload.model_validate(self.mock_cover_letter_data)
        mock_llm.generate_cover_letter.return_value = parsed_payload
        
        use_case = GenerateCoverLetterUseCase(mock_llm, mock_compiler)

        with patch("builtins.open", unittest.mock.mock_open(read_data="mock data")):
            with patch("json.dump") as mock_json_dump:
                await use_case.execute(
                    cv_path="cv.md",
                    jd_path="jd.txt",
                    company_path="company.txt",
                    prompt_template_path="prompt.md",
                    output_json_path="output.json",
                    output_pdf_path="output.pdf",
                    output_research_pdf_path="research.pdf"
                )
                
        mock_llm.generate_cover_letter.assert_called_once()
        mock_compiler.generate_cover_letter_source.assert_called_once()
        mock_compiler.generate_research_source.assert_called_once()
        self.assertEqual(mock_compiler.compile_pdf.call_count, 2)

if __name__ == "__main__":
    unittest.main()
