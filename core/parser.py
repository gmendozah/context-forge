import logging
from typing import List, Dict
logger = logging.getLogger(__name__)
def parse_master_cv(file_path: str) -> List[Dict[str, str]]:
    """Reads 'master_cv.md' and splits it deterministically by Level 3 headers (###)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    lines = content.splitlines()
    chunks = []
    current_heading = "Preamble"
    current_content = []
    
    for line in lines:
        if line.startswith('## ') or line.startswith('### '):
            content_str = '\n'.join(current_content).strip()
            # Save the previous chunk only if it has actual content
            if content_str:
                chunks.append({
                    "heading": current_heading,
                    "content": content_str
                })
            current_heading = line.strip()
            current_content = []
        else:
            current_content.append(line)
            
    # Add the last chunk
    content_str = '\n'.join(current_content).strip()
    if content_str:
        chunks.append({
            "heading": current_heading,
            "content": content_str
        })
        
    logger.info(f"Parsed {len(chunks)} sections from {file_path}")
    return chunks
def read_job_description(file_path: str) -> str:
    """Helper to read the raw text from 'jd.txt'."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            logger.info(f"Successfully read job description from {file_path}")
            return content
    except FileNotFoundError:
        logger.error(f"Job description file not found: {file_path}")
        return ""
