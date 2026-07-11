"""
parser.py
---------
Handles extraction of raw text and lightweight structured signals
(emails, phone numbers, years of experience, education level, section
presence) from an uploaded resume PDF.

Uses pdfplumber for text extraction (pure-Python, no system deps like
poppler required, unlike pdf2image).
"""

import re
import io
from dataclasses import dataclass, field
from typing import List, Optional

import pdfplumber


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}")

# Patterns like "5+ years", "3 years of experience", "over 4 years"
EXPERIENCE_RE = re.compile(
    r"(\d{1,2})\+?\s*(?:years|yrs)\b(?:\s*(?:of)?\s*experience)?",
    re.IGNORECASE,
)

DEGREE_KEYWORDS = {
    "phd": ["phd", "ph.d", "doctorate", "doctoral"],
    "master": ["master", "m.s.", "msc", "m.sc", "mba", "m.tech", "mtech"],
    "bachelor": ["bachelor", "b.s.", "bsc", "b.sc", "b.tech", "btech", "b.e.", "be "],
    "associate": ["associate degree", "diploma"],
}
DEGREE_RANK = {"phd": 4, "master": 3, "bachelor": 2, "associate": 1, "none": 0}

SECTION_KEYWORDS = {
    "experience": ["experience", "employment history", "work history"],
    "education": ["education", "academic background"],
    "skills": ["skills", "technical skills", "core competencies"],
    "projects": ["projects", "personal projects"],
    "certifications": ["certification", "certificate", "licenses"],
    "summary": ["summary", "objective", "profile"],
}


@dataclass
class ResumeData:
    raw_text: str = ""
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    years_experience: Optional[float] = None
    highest_degree: str = "none"
    sections_found: List[str] = field(default_factory=list)
    word_count: int = 0
    page_count: int = 0


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF given as raw bytes."""
    text_chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    return "\n".join(text_chunks)


def _detect_years_experience(text: str) -> Optional[float]:
    matches = EXPERIENCE_RE.findall(text)
    if not matches:
        return None
    years = [float(m) for m in matches if m.isdigit()]
    if not years:
        return None
    # Assume the resume's own "X years experience" claim is the most
    # reliable signal; take the max mentioned (guards against a stray
    # "2 years" inside an unrelated sentence undercutting a senior claim).
    return max(years)


def _detect_highest_degree(text: str) -> str:
    lowered = text.lower()
    best = "none"
    for degree, keywords in DEGREE_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                if DEGREE_RANK[degree] > DEGREE_RANK[best]:
                    best = degree
    return best


def _detect_sections(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            found.append(section)
    return found


def parse_resume(file_bytes: bytes) -> ResumeData:
    """Full parse pipeline: text extraction + structured signal detection."""
    text = extract_text_from_pdf(file_bytes)

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)

    data = ResumeData(
        raw_text=text,
        emails=list(dict.fromkeys(EMAIL_RE.findall(text))),
        phones=list(dict.fromkeys(
            m.group(0).strip() for m in PHONE_RE.finditer(text)
            if 7 <= len(re.sub(r"\D", "", m.group(0))) <= 15
            and not re.fullmatch(r"\(?\d{4}\)?\s*-\s*\d{4}\)?", m.group(0).strip())
        )),
        years_experience=_detect_years_experience(text),
        highest_degree=_detect_highest_degree(text),
        sections_found=_detect_sections(text),
        word_count=len(text.split()),
        page_count=page_count,
    )
    return data
