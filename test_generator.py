import logging
import sys
from pydantic import ValidationError
from generator import generate_resume, ResumePayload

# Configure simple logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("test_generator")

# 1. Complete Mock Payload matching a Senior Engineer's Profile
mock_data = {
    "name": "Geovani Mendoza",
    "title": "Senior Mobile Engineer | AI-Augmented Developer",
    "contact_info": [
        "La Paz, Bolivia",
        "geovanimendoza.h@gmail.com",
        "+591 68055274",
        "linkedin.com/in/geovanimendozah",
        "github.com/gmendozah"
    ],
    "summary": "Senior Mobile Engineer with over 8 years of experience architecting high-performance applications. Specialized in Flutter, React Native, and native platforms, integrated with advanced agentic AI workflows.",
    "skills": [
        {
            "name": "Cross-Platform Ecosystems",
            "items": ["Flutter", "Dart", "React Native"]
        },
        {
            "name": "Native Ecosystems",
            "items": ["iOS (Swift, SwiftUI)", "Android (Kotlin, Jetpack Compose)"]
        }
    ],
    "experience": [
        {
            "company": "Dozuki",
            "role": "Senior Mobile Engineer",
            "dates": "Jun 2023 – Dec 2025",
            "location": "San Luis Obispo, California (Remote)",
            "description": "Led the architectural overhaul of an enterprise industrial mobile ecosystem, transforming a legacy monolith into an offline-first platform.",
            "bullets": [
                {
                    "type": "subheading",
                    "text": "Architecture & Core Engineering"
                },
                {
                    "type": "bullet",
                    "text": "Spearheaded decoupling of legacy guide-screen monoliths into a Clean Architecture framework using BLoC/Cubit, supporting a **600% surge** in mobile traffic."
                },
                {
                    "type": "bullet",
                    "text": "Engineered a high-integrity, offline-first synchronization engine using SQLite and Isar, restoring dynamic logins for enterprise clients."
                }
            ]
        }
    ],
    "projects": [
        {
            "name": "ContextForge",
            "description": "Local CLI engine and asynchronous language pipeline designed to tailor high-density CVs concurrently using Gemini models.",
            "link": "github.com/gmendozah/context-forge",
            "dates": "2026"
        }
    ],
    "education": [
        {
            "institution": "Universidad Católica Boliviana San Pablo",
            "degree": "Systems Engineer",
            "dates": "2013 - 2018",
            "location": "La Paz, Bolivia"
        }
    ],
    "certifications": [
        {
            "name": "iOS Developer Professional Certificate",
            "issuer": "Meta (Coursera)",
            "dates": "2026"
        }
    ],
    "languages": [
        "Spanish (Native)",
        "English (C2 Level Certified)"
    ]
}

def run_tests():
    logger.info("--- Test Case 1: Validating Pydantic Payload Parsing ---")
    try:
        payload = ResumePayload.model_validate(mock_data)
        logger.info("Successfully validated ResumePayload structure!")
        logger.info(f"Name parsed: {payload.name}")
        logger.info(f"Skills category count: {len(payload.skills)}")
        logger.info(f"Experience entries count: {len(payload.experience)}")
    except ValidationError as e:
        logger.error(f"Pydantic Validation failed unexpectedly: {e}")
        sys.exit(1)
        
    logger.info("\n--- Test Case 2: Validation Failures on Missing Required Fields ---")
    invalid_data = mock_data.copy()
    del invalid_data["name"]  # Remove required field
    try:
        ResumePayload.model_validate(invalid_data)
        logger.warning("Warning: Invalid payload did not trigger ValidationError!")
    except ValidationError as e:
        logger.info("Successfully caught validation error as expected:")
        for err in e.errors():
            logger.info(f"  Field: {'.'.join(str(loc) for loc in err['loc'])} | Error: {err['msg']}")
            
    logger.info("\n--- Test Case 3: Generating Typst Source and Compiling PDF ---")
    try:
        generate_resume(mock_data, "test_resume.pdf")
        logger.info("generate_resume executed without Python exceptions.")
        logger.info("Generated source file: test_resume.typ")
    except Exception as e:
        logger.error(f"Generation/Compilation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
