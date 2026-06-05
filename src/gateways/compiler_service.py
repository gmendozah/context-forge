import logging
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from src.domain.models import ResumePayload, CoverLetterPayload

logger = logging.getLogger(__name__)

# --- Helper Formatting Functions ---

def format_contact_info_to_typst(contact_info: List[str]) -> str:
    """Identifies and wraps URLs/emails in active link/mailto elements for Typst,
    while escaping Typst control characters in the display text.
    """
    parts = []
    url_regex = re.compile(
        r'^(https?://)?(www\.)?([a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+)(/[^\s]*)?$',
        re.IGNORECASE
    )
    for item in contact_info:
        item_strip = item.strip()
        if not item_strip:
            continue
        
        # Check for email
        if "@" in item_strip:
            escaped_display = item_strip.replace("&", "\\&").replace("#", "\\#").replace("@", "\\@")
            parts.append(f'link("mailto:{item_strip}")[{escaped_display}]')
        # Check for URL
        elif any(domain in item_strip.lower() for domain in ["github.com", "linkedin.com", "portfolio", "http://", "https://"]) or url_regex.match(item_strip):
            dest = item_strip
            if not (dest.startswith("http://") or dest.startswith("https://")):
                dest = "https://" + dest
            escaped_display = item_strip.replace("&", "\\&").replace("#", "\\#").replace("@", "\\@")
            parts.append(f'link("{dest}")[{escaped_display}]')
        else:
            # Plain string literal
            escaped = item_strip.replace("\\", "\\\\").replace('"', '\\"').replace("&", "\\&").replace("#", "\\#")
            parts.append(f'"{escaped}"')
    return f"({', '.join(parts)})"


def markdown_to_typst(text: str) -> str:
    """Converts basic Markdown syntax (bold, italics, links) into Typst syntax.
    Escapes special Typst control characters (&, #) in plain text segments,
    while leaving inline code segments unmodified.
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
            t = re.sub(r"\*\*(.*?)\*\*", r"__TEMP_BOLD__\1__TEMP_BOLD__", t)
            t = re.sub(r"\*(.*?)\*", r"_\1_", t)
            t = t.replace("__TEMP_BOLD__", "*")

            # Convert links: [text](url) -> link("url")[text]
            t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'link("\2")[\1]', t)

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
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
    elif isinstance(val, list):
        items = [to_typst_val(x, is_content) for x in val]
        return f"({', '.join(items)})"
    elif isinstance(val, dict):
        parts = []
        for k, v in val.items():
            val_is_content = is_content or (k in ["text", "description"])
            if k == "items" and isinstance(v, list):
                formatted_v = to_typst_val(v, is_content=False)
            elif k == "bullets" and isinstance(v, list):
                formatted_v = to_typst_val(v, is_content=False)
            else:
                formatted_v = to_typst_val(v, val_is_content)
            parts.append(f"{k}: {formatted_v}")
        return f"({', '.join(parts)})"
    return str(val)

# --- Default Typst Template Styles ---

DEFAULT_RESUME_STYLE = r"""// Design Tokens & Configuration function
#let resume(body) = {
  // Strict Single-Column Layout: Margins 1.5cm
  set page(
    paper: "us-letter",
    margin: (x: 1.5cm, y: 1.5cm),
    footer: context [
      #align(right)[
        #text(fill: rgb("#4b5563"), size: 8pt)[
          Page #counter(page).display("1 of 1", both: true)
        ]
      ]
    ]
  )

  // Typography: Clean sans-serif with explicit weight hierarchy
  set text(
    font: ("Liberation Sans", "Arial", "Nimbus Sans", "Helvetica"),
    size: 9.5pt,
    fill: rgb("#1a202c"), // Off-black
  )

  // Spacing & Alignment
  set par(justify: true, leading: 0.55em)

  body
}

// Header Component
#let resume_header(name: "", title: "", contact_info: ()) = {
  align(center)[
    #block(spacing: 1em)[
      #text(size: 18pt, weight: "bold", fill: rgb("#111827"))[#name] \
      #v(2pt)
      #text(size: 10.5pt, weight: "medium", fill: rgb("#4b5563"))[#title] \
      #v(5pt)
      #text(size: 8.5pt, fill: rgb("#4b5563"))[#contact_info.join("   |   ")]
    ]
  ]
  v(0.1em)
}

// Section Header with visual divider rule
#let section_header(title) = {
  v(0.4em)
  block(width: 100%, breakable: false)[
    #text(size: 10.5pt, weight: "bold", fill: rgb("#111827"))[#title]
    #v(-0.45em)
    #line(length: 100%, stroke: 0.5pt + luma(100))
  ]
  v(0.2em)
}

// Experience Entry Component (Title/Company on left, Dates/Location on right)
#let job_entry(company: "", role: "", dates: "", location: "", description: none, bullets: ()) = {
  let intro-count = 0
  if bullets.len() > 0 {
    if bullets.at(0).type == "subheading" and bullets.len() > 1 {
      intro-count = 2
    } else {
      intro-count = 1
    }
  }
  let intro-bullets = bullets.slice(0, intro-count)
  let rest-bullets = bullets.slice(intro-count)

  block(width: 100%, breakable: false)[
    #grid(
      columns: (1fr, auto),
      row-gutter: 0.25em,
      text(weight: "bold", size: 9.5pt, fill: rgb("#111827"))[#company],
      text(style: "italic", size: 9pt, fill: rgb("#4b5563"))[#location],
      text(weight: "medium", style: "italic", size: 9.5pt, fill: rgb("#1f2937"))[#role],
      text(size: 9pt, fill: rgb("#4b5563"))[#dates]
    )
    #v(0.1em)
    #if description != none [
      #text(size: 9pt, style: "italic", fill: rgb("#4b5563"))[#description]
      #v(0.2em)
    ]
    #for bullet in intro-bullets [
      #if bullet.type == "subheading" [
        #v(0.3em)
        #block(width: 100%, breakable: false)[
          #text(weight: "bold", size: 9pt, fill: rgb("#1f2937"))[#bullet.text]
        ]
        #v(0.1em)
      ] else [
        #list.item(bullet.text)
      ]
    ]
  ]
  
  for bullet in rest-bullets [
    #if bullet.type == "subheading" [
      #v(0.3em)
      #block(width: 100%, breakable: false)[
        #text(weight: "bold", size: 9pt, fill: rgb("#1f2937"))[#bullet.text]
      ]
      #v(0.1em)
    ] else [
      #list.item(bullet.text)
    ]
  ]
  v(0.5em)
}

// Project Entry Component
#let project_entry(name: "", description: none, link: none, dates: none) = {
  block(width: 100%, breakable: false)[
    #grid(
      columns: (1fr, auto),
      text(weight: "bold", size: 9.5pt, fill: rgb("#111827"))[
        #name
        #if link != none [
          #let target = link
          #if not (target.starts-with("http://") or target.starts-with("https://")) {
            target = "https://" + target
          }
          #text(size: 8.5pt, weight: "regular", fill: rgb("#3b82f6"))[ (#std.link(target)[#link]) ]
        ]
      ],
      if dates != none { text(size: 9pt, fill: rgb("#4b5563"))[#dates] }
    )
  ]
  v(0.1em)
  if description != none {
    text(size: 9pt, fill: rgb("#4b5563"))[#description]
    v(0.3em)
  }
}

// Skills Row Component
#let skill_category(category: "", items: ()) = {
  grid(
    columns: (auto, 1fr),
    column-gutter: 0.8em,
    row-gutter: 0.6em,
    align(right)[
      #text(weight: "bold", fill: rgb("#1f2937"))[#category:]
    ],
    align(left)[
      #text(fill: rgb("#374151"))[#items.join(", ")]
    ]
  )
}
"""

DEFAULT_COVER_LETTER_STYLE = r"""
#let cover_letter(
  candidate_name: "",
  candidate_title: "",
  candidate_contact: (),
  recipient_name: "",
  recipient_title: "",
  company_name: "",
  date: "",
  salutation: "",
  body_paragraphs: (),
  signoff: "",
  body
) = {
  set page(
    paper: "us-letter",
    margin: (x: 2cm, y: 2cm)
  )
  set text(
    font: ("Liberation Sans", "Arial", "Helvetica"),
    size: 10pt,
    fill: rgb("#1a202c")
  )
  set par(justify: true, leading: 0.65em)

  // Header
  align(center)[
    #text(size: 18pt, weight: "bold", fill: rgb("#111827"))[#candidate_name] \
    #v(2pt)
    #text(size: 10pt, weight: "medium", fill: rgb("#4b5563"))[#candidate_title] \
    #v(4pt)
    #text(size: 8.5pt, fill: rgb("#4b5563"))[#candidate_contact.join("   |   ")]
  ]
  
  v(1cm)

  // Date
  text(weight: "medium")[#date]
  v(1em)

  // Recipient details
  grid(
    columns: (1fr),
    row-gutter: 0.25em,
    text(weight: "bold")[#recipient_name],
    text(style: "italic", fill: rgb("#374151"))[#recipient_title],
    text(fill: rgb("#1f2937"))[#company_name]
  )

  v(1.5em)

  // Salutation
  [#salutation,]
  v(1em)

  // Body paragraphs
  for paragraph in body_paragraphs [
    #paragraph
    #v(1em)
  ]

  v(1.5em)

  // Signoff
  [
    #signoff, \ \ \
    #text(weight: "bold")[#candidate_name]
  ]
}
"""

DEFAULT_RESEARCH_STYLE = r"""
#let research_briefing(
  company_name: "",
  mission_and_values: "",
  role_challenges: (),
  notable_projects: (),
  why_candidate_fits: "",
  candidate_name: "",
  body
) = {
  set page(
    paper: "us-letter",
    margin: (x: 2cm, y: 2cm)
  )
  set text(
    font: ("Liberation Sans", "Arial", "Helvetica"),
    size: 10pt,
    fill: rgb("#1a202c")
  )
  set par(justify: true, leading: 0.6em)

  // Title
  align(center)[
    #text(size: 16pt, weight: "bold", fill: rgb("#111827"))[Company Research Briefing: #company_name] \
    #v(2pt)
    #text(size: 9.5pt, style: "italic", fill: rgb("#4b5563"))[Prepared for #candidate_name]
  ]
  
  v(1em)

  // Section: Mission & Values
  block(width: 100%, breakable: false)[
    #text(size: 11pt, weight: "bold", fill: rgb("#1f2937"))[Company Mission & Core Values]
    #v(-0.4em)
    #line(length: 100%, stroke: 0.5pt + luma(150))
  ]
  [#mission_and_values]
  v(1.2em)

  // Section: Role & Technical Challenges
  block(width: 100%, breakable: false)[
    #text(size: 11pt, weight: "bold", fill: rgb("#1f2937"))[Key Role & Alignment Challenges]
    #v(-0.4em)
    #line(length: 100%, stroke: 0.5pt + luma(150))
  ]
  for challenge in role_challenges [
    #list.item(challenge)
  ]
  v(1.2em)

  // Section: Notable Projects & Initiatives
  block(width: 100%, breakable: false)[
    #text(size: 11pt, weight: "bold", fill: rgb("#1f2937"))[Notable Projects & Initiatives]
    #v(-0.4em)
    #line(length: 100%, stroke: 0.5pt + luma(150))
  ]
  for project in notable_projects [
    #list.item(project)
  ]
  v(1.2em)

  // Section: Why Candidate Fits
  block(width: 100%, breakable: false)[
    #text(size: 11pt, weight: "bold", fill: rgb("#1f2937"))[Strategic Fit Narrative]
    #v(-0.4em)
    #line(length: 100%, stroke: 0.5pt + luma(150))
  ]
  [#why_candidate_fits]
}
"""

class CompilerService(ABC):
    @abstractmethod
    def generate_resume_source(self, data: ResumePayload, template_path: Optional[str], output_path: str) -> None:
        pass

    @abstractmethod
    def generate_cover_letter_source(self, data: CoverLetterPayload, template_path: Optional[str], output_path: str) -> None:
        pass

    @abstractmethod
    def generate_research_source(self, data: CoverLetterPayload, template_path: Optional[str], output_path: str) -> None:
        pass

    @abstractmethod
    def compile_pdf(self, typ_path: str, pdf_path: str) -> bool:
        pass


class TypstCompilerService(CompilerService):
    def generate_resume_source(self, data: ResumePayload, template_path: Optional[str], output_path: str) -> None:
        logger.info("Generating Typst source code for resume...")
        
        # Decide whether to import external template or inline the default style
        use_inline_default = (template_path is None) or (template_path == "templates/resume.typ")
        
        body_parts = []
        if use_inline_default:
            body_parts.append(DEFAULT_RESUME_STYLE)
        else:
            # Format path with forward slashes for Typst import compatibility
            import_path = template_path.replace("\\", "/")
            body_parts.append(
                f'#import "{import_path}": resume, resume_header, section_header, job_entry, project_entry, skill_category'
            )

        body_parts.append("#show: resume\n")

        # 1. Header
        contact_info_typst = format_contact_info_to_typst(data.contact_info)
        body_parts.append(
            f"#resume_header(\n"
            f"  name: {to_typst_val(data.name)},\n"
            f"  title: {to_typst_val(data.title)},\n"
            f"  contact_info: {contact_info_typst}\n"
            f")\n"
        )

        # 2. Professional Summary
        if data.summary:
            body_parts.append('#section_header("Professional Summary")')
            body_parts.append(markdown_to_typst(data.summary))

        # 3. Technical Skills Matrix
        if data.skills:
            body_parts.append('#section_header("Technical Skills Matrix")')
            for skill in data.skills:
                items_typst = to_typst_val(skill.items)
                body_parts.append(
                    f"#skill_category(category: {to_typst_val(skill.name)}, items: {items_typst})"
                )
            body_parts.append("")

        # 4. Professional Experience
        if data.experience:
            body_parts.append('#section_header("Professional Experience")')
            for job in data.experience:
                bullets_data = []
                for b in job.bullets:
                    bullets_data.append({"type": b.type, "text": markdown_to_typst(b.text)})
                bullets_typst = to_typst_val(bullets_data)
                desc_val = (
                    to_typst_val(markdown_to_typst(job.description), is_content=True)
                    if job.description
                    else "none"
                )

                body_parts.append(
                    f"#job_entry(\n"
                    f"  company: {to_typst_val(job.company)},\n"
                    f"  role: {to_typst_val(job.role)},\n"
                    f"  dates: {to_typst_val(job.dates)},\n"
                    f"  location: {to_typst_val(job.location)},\n"
                    f"  description: {desc_val},\n"
                    f"  bullets: {bullets_typst}\n"
                    f")"
                )
            body_parts.append("")

        # 5. Projects & Open Source
        if data.projects:
            body_parts.append('#section_header("Projects & Open Source")')
            for proj in data.projects:
                desc_val = (
                    to_typst_val(markdown_to_typst(proj.description), is_content=True)
                    if proj.description
                    else "none"
                )
                link_val = to_typst_val(proj.link) if proj.link else "none"
                dates_val = to_typst_val(proj.dates) if proj.dates else "none"

                body_parts.append(
                    f"#project_entry(\n"
                    f"  name: {to_typst_val(proj.name)},\n"
                    f"  description: {desc_val},\n"
                    f"  link: {link_val},\n"
                    f"  dates: {dates_val}\n"
                    f")"
                )
            body_parts.append("")

        # 6. Education
        if data.education:
            body_parts.append('#section_header("Formal Education")')
            for edu in data.education:
                loc_str = f" ({edu.location})" if edu.location else ""
                edu_str = f"{edu.degree} — {edu.institution}{loc_str} | {edu.dates}"
                body_parts.append(f"- {markdown_to_typst(edu_str)}")
            body_parts.append("")

        # 7. Certifications & Training
        if data.certifications:
            body_parts.append(
                '#section_header("Advanced Certifications & Specialized Training")'
            )
            for cert in data.certifications:
                issuer_str = f" from {cert.issuer}" if cert.issuer else ""
                date_str = f" ({cert.dates})" if cert.dates else ""
                cert_str = f"{cert.name}{issuer_str}{date_str}"
                body_parts.append(f"- {markdown_to_typst(cert_str)}")
            body_parts.append("")

        # 8. Awards
        if data.awards:
            body_parts.append('#section_header("Honors & Awards")')
            for award in data.awards:
                body_parts.append(f"- {markdown_to_typst(award)}")
            body_parts.append("")

        # 9. Languages
        if data.languages:
            body_parts.append('#section_header("Languages")')
            for lang in data.languages:
                body_parts.append(f"- {markdown_to_typst(lang)}")
            body_parts.append("")

        typst_content = "\n".join(body_parts)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(typst_content)
        logger.info(f"Typst resume source written to: {output_path}")

    def generate_cover_letter_source(self, data: CoverLetterPayload, template_path: Optional[str], output_path: str) -> None:
        logger.info("Generating Typst source code for cover letter...")
        
        use_inline_default = (template_path is None) or (template_path == "templates/cover_letter.typ")
        
        body_parts = []
        if use_inline_default:
            body_parts.append(DEFAULT_COVER_LETTER_STYLE)
        else:
            import_path = template_path.replace("\\", "/")
            body_parts.append(f'#import "{import_path}": cover_letter')

        body_parts.append("#show: cover_letter.with(\n")
        body_parts.append(f"  candidate_name: {to_typst_val(data.candidate_name)},\n")
        body_parts.append(f"  candidate_title: {to_typst_val(data.candidate_title)},\n")
        body_parts.append(f"  candidate_contact: {to_typst_val(data.candidate_contact)},\n")
        body_parts.append(f"  recipient_name: {to_typst_val(data.recipient_name)},\n")
        body_parts.append(f"  recipient_title: {to_typst_val(data.recipient_title)},\n")
        body_parts.append(f"  company_name: {to_typst_val(data.company_name)},\n")
        body_parts.append(f"  date: {to_typst_val(data.date)},\n")
        body_parts.append(f"  salutation: {to_typst_val(data.salutation)},\n")
        
        # We parse formatting inside paragraph text
        parsed_paragraphs = [markdown_to_typst(p) for p in data.body_paragraphs]
        body_parts.append(f"  body_paragraphs: {to_typst_val(parsed_paragraphs, is_content=True)},\n")
        body_parts.append(f"  signoff: {to_typst_val(data.signoff)}\n")
        body_parts.append(")\n")
        
        typst_content = "\n".join(body_parts)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(typst_content)
        logger.info(f"Typst cover letter source written to: {output_path}")

    def generate_research_source(self, data: CoverLetterPayload, template_path: Optional[str], output_path: str) -> None:
        logger.info("Generating Typst source code for company research briefing...")
        
        use_inline_default = (template_path is None) or (template_path == "templates/research.typ")
        
        body_parts = []
        if use_inline_default:
            body_parts.append(DEFAULT_RESEARCH_STYLE)
        else:
            import_path = template_path.replace("\\", "/")
            body_parts.append(f'#import "{import_path}": research_briefing')

        res = data.company_research
        body_parts.append("#show: research_briefing.with(\n")
        body_parts.append(f"  company_name: {to_typst_val(res.company_name)},\n")
        body_parts.append(f"  mission_and_values: {to_typst_val(markdown_to_typst(res.mission_and_values), is_content=True)},\n")
        
        parsed_challenges = [markdown_to_typst(c) for c in res.role_challenges]
        body_parts.append(f"  role_challenges: {to_typst_val(parsed_challenges, is_content=True)},\n")
        
        parsed_projects = [markdown_to_typst(p) for p in res.notable_projects]
        body_parts.append(f"  notable_projects: {to_typst_val(parsed_projects, is_content=True)},\n")
        
        body_parts.append(f"  why_candidate_fits: {to_typst_val(markdown_to_typst(res.why_candidate_fits), is_content=True)},\n")
        body_parts.append(f"  candidate_name: {to_typst_val(data.candidate_name)}\n")
        body_parts.append(")\n")
        
        typst_content = "\n".join(body_parts)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(typst_content)
        logger.info(f"Typst research briefing source written to: {output_path}")

    def compile_pdf(self, typ_path: str, pdf_path: str) -> bool:
        compiled = False
        
        # 1. Try python package
        try:
            import typst
            logger.info(f"Compiling {typ_path} to PDF using Python 'typst' package...")
            typst.compile(typ_path, output=pdf_path)
            logger.info(f"Successfully compiled PDF to: {pdf_path}")
            compiled = True
        except ImportError:
            logger.info("Python 'typst' package not installed. Falling back to Typst CLI...")
        except Exception as e:
            logger.error(f"Python 'typst' compilation failed: {e}. Falling back to Typst CLI...")
            
        if compiled:
            return True

        # 2. Fallback to Typst CLI
        typst_bin = shutil.which("typst")
        if not typst_bin:
            logger.warning(
                f"Typst executable not found in PATH. PDF compilation skipped for {typ_path}. "
                f"Please compile manually: typst compile {typ_path} {pdf_path}"
            )
            return False

        try:
            logger.info(f"Compiling {typ_path} to PDF using Typst CLI...")
            subprocess.run(
                [typst_bin, "compile", typ_path, pdf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            logger.info(f"Successfully compiled PDF to: {pdf_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Typst CLI compilation failed (exit code {e.returncode}). Stderr: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error compiling Typst: {e}")
            return False
