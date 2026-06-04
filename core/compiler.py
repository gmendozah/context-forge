import logging
import re
import shutil
import subprocess
from typing import List, Dict

logger = logging.getLogger(__name__)

def markdown_to_typst(text: str) -> str:
    """Converts basic Markdown syntax (bold, italics, links) into Typst syntax.
    Escapes special Typst control characters (&, #) in plain text segments,
    while leaving inline code segments unmodified.
    """
    if not text:
        return ""
        
    # Split by inline code blocks backticks to leave code blocks untouched
    parts = text.split("`")
    for i in range(len(parts)):
        # Even indices are text outside of inline code blocks
        if i % 2 == 0:
            t = parts[i]
            
            # Escape Typst special characters
            t = t.replace("&", r"\&")
            t = t.replace("#", r"\#")
            
            # Convert markdown bold/italics
            # Using temporary token to avoid asterisk clash
            t = re.sub(r'\*\*(.*?)\*\*', r'__TEMP_BOLD__\1__TEMP_BOLD__', t)
            t = re.sub(r'\*(.*?)\*', r'_\1_', t)
            t = t.replace('__TEMP_BOLD__', '*')
            
            # Convert markdown links: [text](url) -> link("url")[text]
            t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'link("\2")[\1]', t)
            
            parts[i] = t
            
    return "`".join(parts)

def to_typst_val(val, is_content: bool = False) -> str:
    """Formats Python data types into Typst syntax format."""
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
            # In Typst dicts, keys are identifiers.
            # Decide if value should be treated as rich content based on its key name
            val_is_content = is_content or (k in ['text', 'description'])
            
            if k == 'items' and isinstance(v, list):
                # Skills items lists are list of strings
                formatted_v = to_typst_val(v, is_content=False)
            elif k == 'bullets' and isinstance(v, list):
                # Experience bullets lists are list of dicts
                formatted_v = to_typst_val(v, is_content=False)
            else:
                formatted_v = to_typst_val(v, val_is_content)
                
            parts.append(f"{k}: {formatted_v}")
        return f"({', '.join(parts)})"
    return str(val)

def parse_simple_list_section(results: List[Dict], heading_keywords: List[str]) -> List[str]:
    """Helper to locate a section by keywords and extract its bullet list as Typst-formatted items."""
    content = ""
    for res in results:
        h = res.get("heading", "").lower()
        if any(kw in h for kw in heading_keywords):
            content = res.get("tailored_content", "")
            break
            
    items = []
    if content:
        for line in content.splitlines():
            l = line.strip().lstrip("-* ").strip()
            if l:
                items.append(l)
    return items

def parse_sections_to_structured_data(results: List[Dict], tailored_summary: str) -> Dict:
    """Parses CV chunks back into clean, structured Python objects for Typst template consumption."""
    
    # 1. Personal & Contact Information
    name = ""
    title = ""
    contact_info = []
    personal_content = ""
    
    for res in results:
        h = res.get("heading", "").lower()
        if "personal" in h or "contact" in h:
            personal_content = res.get("tailored_content", "")
            break
            
    if personal_content:
        for line in personal_content.splitlines():
            line_stripped = line.strip().lstrip("-* ").strip()
            if not line_stripped:
                continue
            if ":" in line_stripped:
                key, val = line_stripped.split(":", 1)
                val_clean = val.strip().replace("**", "").replace("*", "")
                
                if "name" in key.lower():
                    name = val_clean
                elif "title" in key.lower():
                    title = val_clean
                else:
                    # Clean up common URL details for a cleaner header display
                    if "linkedin.com" in val_clean.lower():
                        clean_val = val_clean.replace("https://", "").replace("http://", "").replace("www.", "")
                        if clean_val.endswith("/"):
                            clean_val = clean_val[:-1]
                        contact_info.append(clean_val)
                    elif "github.com" in val_clean.lower():
                        clean_val = val_clean.replace("https://", "").replace("http://", "").replace("www.", "")
                        if clean_val.endswith("/"):
                            clean_val = clean_val[:-1]
                        contact_info.append(clean_val)
                    else:
                        contact_info.append(val_clean)
            else:
                contact_info.append(line_stripped)

    # 2. Professional Summary
    # Use tailored summary if generated, otherwise extract from summary section
    summary = tailored_summary
    if not summary:
        for res in results:
            h = res.get("heading", "").lower()
            if "summary" in h:
                summary = res.get("tailored_content", "").strip()
                break

    # 3. Technical Skills Matrix
    skills = []
    skills_content = ""
    for res in results:
        h = res.get("heading", "").lower()
        if "skills" in h or "matrix" in h:
            skills_content = res.get("tailored_content", "")
            break
            
    if skills_content:
        for line in skills_content.splitlines():
            line_stripped = line.strip().lstrip("-* ").strip()
            if not line_stripped:
                continue
            match = re.match(r'^\s*\*\*(.*?)\*\*:\s*(.*)$', line_stripped)
            if not match:
                match = re.match(r'^\s*(.*?):\s*(.*)$', line_stripped)
                
            if match:
                cat_name = match.group(1).strip()
                cat_items_str = match.group(2).strip()
                cat_items = [item.strip() for item in cat_items_str.split(",")]
                skills.append({
                    "name": cat_name,
                    "items": cat_items
                })

    # 4. Professional Experience
    experience = []
    for res in results:
        heading = res.get("heading", "")
        if not heading.startswith("### "):
            continue
            
        heading_clean = heading.replace("###", "").strip()
        parts = re.split(r'[——-]', heading_clean, maxsplit=1)
        company = parts[0].strip()
        location = parts[1].strip() if len(parts) > 1 else ""
        
        content = res.get("tailored_content", "")
        lines = content.splitlines()
        
        job_title = ""
        dates = ""
        description = ""
        bullets = []
        
        first_line_idx = -1
        for i, line in enumerate(lines):
            if line.strip():
                first_line_idx = i
                break
                
        if first_line_idx != -1:
            title_line = lines[first_line_idx].strip()
            title_parts = title_line.split("|")
            if len(title_parts) > 1:
                job_title = title_parts[0].strip().replace("**", "").replace("*", "")
                dates = title_parts[1].strip().replace("**", "").replace("*", "")
            else:
                job_title = title_line.replace("**", "").replace("*", "")
                
            overview_idx = -1
            for i in range(first_line_idx + 1, len(lines)):
                l = lines[i].strip()
                if not l:
                    continue
                if (l.startswith("*") and l.endswith("*")) or (l.startswith("_") and l.endswith("_")):
                    description = l.strip("*_ ").strip()
                    overview_idx = i
                break
                
            start_idx = max(first_line_idx + 1, overview_idx + 1)
            for i in range(start_idx, len(lines)):
                l = lines[i].strip()
                if not l:
                    continue
                if l.startswith("#### "):
                    subheading_text = l.replace("#### ", "").strip()
                    bullets.append({
                        "type": "subheading",
                        "text": subheading_text
                    })
                elif l.startswith("- ") or l.startswith("* "):
                    bullet_text = l[2:].strip()
                    bullets.append({
                        "type": "bullet",
                        "text": bullet_text
                    })
                    
        experience.append({
            "company": company,
            "location": location,
            "title": job_title,
            "dates": dates,
            "description": description,
            "bullets": bullets
        })

    # 5. Simple Lists (Education, Certifications, Awards, Languages)
    education = parse_simple_list_section(results, ["education", "academic"])
    certifications = parse_simple_list_section(results, ["certification", "training"])
    awards = parse_simple_list_section(results, ["honor", "award"])
    languages = parse_simple_list_section(results, ["language"])

    return {
        "name": name or "Candidate Name",
        "title": title or "Software Engineer",
        "contact_info": contact_info,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "awards": awards,
        "languages": languages
    }

def generate_typst_file(data: dict, template_path: str, output_typ_path: str) -> None:
    """Generates the compiled Typst source file importing the template and supplying variables."""
    # Ensure template_path is formatted with forward slashes for Typst import compatibility
    template_import_path = template_path.replace("\\", "/")
    
    with open(output_typ_path, "w", encoding="utf-8") as f:
        f.write(f'#import "{template_import_path}": resume\n\n')
        f.write('#show: resume.with(\n')
        f.write(f'  name: {to_typst_val(data["name"])},\n')
        f.write(f'  title: {to_typst_val(data["title"])},\n')
        f.write(f'  contact_info: {to_typst_val(data["contact_info"])},\n')
        f.write(f'  summary: {to_typst_val(data["summary"], is_content=True)},\n')
        f.write(f'  skills: {to_typst_val(data["skills"])},\n')
        f.write(f'  experience: {to_typst_val(data["experience"])},\n')
        f.write(f'  education: {to_typst_val(data["education"], is_content=True)},\n')
        f.write(f'  certifications: {to_typst_val(data["certifications"], is_content=True)},\n')
        f.write(f'  awards: {to_typst_val(data["awards"], is_content=True)},\n')
        f.write(f'  languages: {to_typst_val(data["languages"], is_content=True)},\n')
        f.write(')\n')
        
    logger.info(f"Successfully generated Typst markup at '{output_typ_path}'")

def compile_pdf(typ_path: str, pdf_path: str) -> bool:
    """Invokes Typst subprocess to compile the Typst document to PDF."""
    typst_path = shutil.which("typst")
    if not typst_path:
        logger.warning(
            "Typst executable not found in system PATH.\n"
            "Cannot compile PDF directly. However, the Typst markup has been successfully generated at:\n"
            f"  {typ_path}\n"
            "To compile it to PDF manually, please install Typst (https://typst.app/) and run:\n"
            f"  typst compile {typ_path} {pdf_path}"
        )
        return False
        
    try:
        logger.info(f"Compiling Typst file '{typ_path}' to '{pdf_path}'...")
        result = subprocess.run(
            [typst_path, "compile", typ_path, pdf_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.info(f"Successfully compiled PDF to '{pdf_path}'.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Typst compilation failed (exit code {e.returncode}).\n"
            f"Command: {e.cmd}\n"
            f"Stdout: {e.stdout}\n"
            f"Stderr: {e.stderr}"
        )
        return False
    except Exception as e:
        logger.error(f"Unexpected error compiling Typst file: {e}")
        return False
