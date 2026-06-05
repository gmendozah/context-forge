from typing import List, Optional
from pydantic import BaseModel, Field

# --- Resume Models ---

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
    awards: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)

# --- Cover Letter & Research Models ---

class CompanyResearch(BaseModel):
    company_name: str
    mission_and_values: str
    role_challenges: List[str] = Field(default_factory=list)
    notable_projects: List[str] = Field(default_factory=list)
    why_candidate_fits: str

class CoverLetterPayload(BaseModel):
    recipient_name: str
    recipient_title: str
    company_name: str
    date: str
    salutation: str
    body_paragraphs: List[str] = Field(default_factory=list)
    signoff: str
    candidate_name: str
    candidate_title: str
    candidate_contact: List[str] = Field(default_factory=list)
    company_research: CompanyResearch
