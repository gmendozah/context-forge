import logging
import re
import shutil
import subprocess
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Pydantic Data Schemas ---

class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None

class SkillCategory(BaseModel):
    name: str
    items: List[str]

class BulletEntry(BaseModel):
    type: str = "bullet"  # "bullet" or "subheading"
    text: str

class JobEntry(BaseModel):
    company: str
    role: str
    dates: str
    location: str
    description: Optional[str] = None
    bullets: List[BulletEntry] = Field(default_factory=list)

class ProjectEntry(BaseModel):
    name: str
    description: Optional[str] = None
    link: Optional[str] = None
    dates: Optional[str] = None

class EducationEntry(BaseModel):
    institution: str
    degree: str
    dates: str
    location: Optional[str] = None

class CertificationEntry(BaseModel):
    name: str
    issuer: Optional[str] = None
    dates: Optional[str] = None

class ResumePayload(BaseModel):
    name: str
    title: str
    contact_info: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    skills: List[SkillCategory] = Field(default_factory=list)
    experience: List[JobEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)

# --- Formatting Helpers ---

def markdown_to_typst(text: str) -> str:
    """Converts basic Markdown syntax (bold, italics, links) into Typst syntax.
    Escapes special Typst control characters (&, #) in plain text segments.
    """
    if not text:
        return ""
        
    parts = text.split("`")
    for i in range(len(parts)):
        if i % 2 == 0:
            t = parts[i]
            t = t.replace("&", r"\&")
            t = t.replace("#", r"\#")
            
            # Convert bold/italics
            t = re.sub(r'\*\*(.*?)\*\*', r'__TEMP_BOLD__\1__TEMP_BOLD__', t)
            t = re.sub(r'\*(.*?)\*', r'_\1_', t)
            t = t.replace('__TEMP_BOLD__', '*')
            
            # Convert links: [text](url) -> link("url")[text]
            t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'link("\2")[\1]', t)
            
            parts[i] = t
            
    return "`".join(parts)

def to_typst_val(val, is_content: bool = False) -> str:
    """Formats Python data types into Typst syntax format."""
    if val is None:
        return "none"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, str):
        if is_content:
            if not val.strip():
                return "none"
            return f"[{val}]"
        else:
            escaped = val.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
    elif isinstance(val, list):
        items = [to_typst_val(x, is_content) for x in val]
        return f"({', '.join(items)})"
    elif isinstance(val, dict):
        parts = []
        for k, v in val.items():
            val_is_content = is_content or (k in ['text', 'description'])
            if k == 'items' and isinstance(v, list):
                formatted_v = to_typst_val(v, is_content=False)
            elif k == 'bullets' and isinstance(v, list):
                formatted_v = to_typst_val(v, is_content=False)
            else:
                formatted_v = to_typst_val(v, val_is_content)
            parts.append(f"{k}: {formatted_v}")
        return f"({', '.join(parts)})"
    return str(val)

# --- Main Generation & Compilation Engine ---

def generate_resume(data: dict, output_path: str) -> None:
    """Validates the input resume data dictionary, generates the Typst source code,
    and compiles it into a high-quality PDF at output_path.
    """
    logger.info("Validating resume data payload using Pydantic...")
    payload = ResumePayload.model_validate(data)
    
    # Standard template path relative to generator
    template_path = "templates/template.typ"
    
    body_parts = [
        f'#import "{template_path}": resume, resume_header, section_header, job_entry, project_entry, skill_category\n',
        '#show: resume\n'
    ]
    
    # 1. Header
    contact_info_typst = to_typst_val(payload.contact_info)
    body_parts.append(
        f'#resume_header(\n'
        f'  name: {to_typst_val(payload.name)},\n'
        f'  title: {to_typst_val(payload.title)},\n'
        f'  contact_info: {contact_info_typst}\n'
        f')\n'
    )
    
    # 2. Professional Summary
    if payload.summary:
        body_parts.append('#section_header("Professional Summary")')
        body_parts.append(f'[{markdown_to_typst(payload.summary)}]\n')
        
    # 3. Technical Skills Matrix
    if payload.skills:
        body_parts.append('#section_header("Technical Skills Matrix")')
        for skill in payload.skills:
            items_typst = to_typst_val(skill.items)
            body_parts.append(f'#skill_category(category: {to_typst_val(skill.name)}, items: {items_typst})')
        body_parts.append('')
        
    # 4. Professional Experience
    if payload.experience:
        body_parts.append('#section_header("Professional Experience")')
        for job in payload.experience:
            bullets_data = []
            for b in job.bullets:
                bullets_data.append({
                    "type": b.type,
                    "text": markdown_to_typst(b.text)
                })
            bullets_typst = to_typst_val(bullets_data)
            desc_val = to_typst_val(markdown_to_typst(job.description), is_content=True) if job.description else "none"
            
            body_parts.append(
                f'#job_entry(\n'
                f'  company: {to_typst_val(job.company)},\n'
                f'  role: {to_typst_val(job.role)},\n'
                f'  dates: {to_typst_val(job.dates)},\n'
                f'  location: {to_typst_val(job.location)},\n'
                f'  description: {desc_val},\n'
                f'  bullets: {bullets_typst}\n'
                f')'
            )
        body_parts.append('')
        
    # 5. Projects & Open Source
    if payload.projects:
        body_parts.append('#section_header("Projects & Open Source")')
        for proj in payload.projects:
            desc_val = to_typst_val(markdown_to_typst(proj.description), is_content=True) if proj.description else "none"
            link_val = to_typst_val(proj.link) if proj.link else "none"
            dates_val = to_typst_val(proj.dates) if proj.dates else "none"
            
            body_parts.append(
                f'#project_entry(\n'
                f'  name: {to_typst_val(proj.name)},\n'
                f'  description: {desc_val},\n'
                f'  link: {link_val},\n'
                f'  dates: {dates_val}\n'
                f')'
            )
        body_parts.append('')
        
    # 6. Education
    if payload.education:
        body_parts.append('#section_header("Formal Education")')
        for edu in payload.education:
            loc_str = f" ({edu.location})" if edu.location else ""
            edu_str = f"{edu.degree} — {edu.institution}{loc_str} | {edu.dates}"
            body_parts.append(f'- [{markdown_to_typst(edu_str)}]')
        body_parts.append('')
        
    # 7. Certifications & Training
    if payload.certifications:
        body_parts.append('#section_header("Advanced Certifications & Specialized Training")')
        for cert in payload.certifications:
            issuer_str = f" from {cert.issuer}" if cert.issuer else ""
            date_str = f" ({cert.dates})" if cert.dates else ""
            cert_str = f"{cert.name}{issuer_str}{date_str}"
            body_parts.append(f'- [{markdown_to_typst(cert_str)}]')
        body_parts.append('')
        
    # 8. Languages
    if payload.languages:
        body_parts.append('#section_header("Languages")')
        for lang in payload.languages:
            body_parts.append(f'- [{markdown_to_typst(lang)}]')
        body_parts.append('')

    typst_content = "\n".join(body_parts)
    
    # Resolve typst source file path corresponding to output_path
    typ_source_path = output_path.rsplit(".", 1)[0] + ".typ"
    
    with open(typ_source_path, "w", encoding="utf-8") as f:
        f.write(typst_content)
        
    logger.info(f"Typst source code written to: {typ_source_path}")
    
    # Subprocess/Python Compilation with Typst
    compiled = False
    
    # 1. Try using the python-typst package
    try:
        import typst
        logger.info(f"Compiling {typ_source_path} to PDF using Python 'typst' package...")
        typst.compile(typ_source_path, output=output_path)
        logger.info(f"Successfully compiled PDF to: {output_path}")
        compiled = True
    except ImportError:
        logger.info("Python 'typst' package not installed. Attempting to fall back to Typst CLI...")
    except Exception as e:
        logger.error(f"Python 'typst' compilation failed: {e}. Attempting to fall back to Typst CLI...")
        
    if compiled:
        return

    # 2. Fallback to Typst CLI
    typst_bin = shutil.which("typst")
    if not typst_bin:
        logger.warning(
            "Typst executable not found in system PATH and Python 'typst' package was unavailable. PDF compilation skipped. "
            "Please install Typst CLI (https://typst.app/) or run 'pip install typst' to compile the generated typst file automatically: "
            f"typst compile {typ_source_path} {output_path}"
        )
        return
        
    try:
        logger.info(f"Compiling {typ_source_path} to PDF using Typst CLI...")
        subprocess.run(
            [typst_bin, "compile", typ_source_path, output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.info(f"Successfully compiled PDF to: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Typst compilation failed (exit code {e.returncode}).\n"
            f"Command: {e.cmd}\n"
            f"Stdout: {e.stdout}\n"
            f"Stderr: {e.stderr}"
        )
        raise RuntimeError(f"Typst compilation failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error compiling Typst file: {e}")
        raise

