"""
scorer.py
---------
Turns parsed resume data + HR-specified job requirements into:
  - a 0-100 candidate score
  - a hiring recommendation label
  - a fully explainable breakdown (what was matched/missing and why)

This is a transparent, rule-based scoring engine on purpose: every number
that feeds the final score is traceable back to a concrete piece of
evidence in the resume, which is what makes the "explainable AI" panel
possible. No black-box model is used for the score itself.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict

from modules.skills_db import SKILL_TAXONOMY, all_known_skills
from modules.parser import ResumeData, DEGREE_RANK


# Weights for each scoring component. Must sum to 1.0.
WEIGHTS = {
    "skills": 0.50,
    "experience": 0.25,
    "education": 0.15,
    "completeness": 0.10,
}

RECOMMENDATION_BANDS = [
    (85, "Strong Hire", "success"),
    (70, "Hire", "success"),
    (50, "Maybe / Interview Further", "warning"),
    (0, "No Hire", "error"),
]


@dataclass
class ScoreBreakdown:
    overall_score: float = 0.0
    recommendation: str = ""
    recommendation_tone: str = "warning"

    skill_score: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    bonus_skills: List[str] = field(default_factory=list)

    experience_score: float = 0.0
    years_found: float = 0.0
    years_required: float = 0.0

    education_score: float = 0.0
    degree_found: str = "none"
    degree_required: str = "none"

    completeness_score: float = 0.0
    sections_found: List[str] = field(default_factory=list)
    sections_missing: List[str] = field(default_factory=list)

    component_contributions: Dict[str, float] = field(default_factory=dict)
    reasoning: List[str] = field(default_factory=list)


def _find_skills_in_text(text: str, skills: List[str]) -> List[str]:
    lowered = text.lower()
    found = []
    for skill in skills:
        pattern = r"(?<![a-zA-Z0-9+#.])" + re.escape(skill.lower()) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, lowered):
            found.append(skill)
    return found


def score_candidate(
    resume: ResumeData,
    required_skills: List[str],
    min_years_experience: float,
    required_degree: str,
) -> ScoreBreakdown:
    bd = ScoreBreakdown()
    reasoning = []

    # ---- 1. Skill match ----
    required_skills = [s.strip() for s in required_skills if s.strip()]
    if required_skills:
        matched = _find_skills_in_text(resume.raw_text, required_skills)
        missing = [s for s in required_skills if s not in matched]
        skill_pct = (len(matched) / len(required_skills)) * 100 if required_skills else 0
    else:
        matched, missing, skill_pct = [], [], 0

    # Bonus skills: things the candidate has from the general taxonomy
    # that weren't explicitly required, shown for context (not scored).
    known = all_known_skills()
    all_found = _find_skills_in_text(resume.raw_text, known)
    bonus = [s for s in all_found if s not in [m.lower() for m in matched]]

    bd.matched_skills = matched
    bd.missing_skills = missing
    bd.bonus_skills = sorted(bonus)[:15]
    bd.skill_score = round(skill_pct, 1)
    reasoning.append(
        f"Matched {len(matched)}/{len(required_skills)} required skills "
        f"({bd.skill_score}%)." if required_skills else
        "No required skills were specified by HR, so skill match score is 0."
    )

    # ---- 2. Experience ----
    years_found = resume.years_experience or 0.0
    bd.years_found = years_found
    bd.years_required = min_years_experience
    if min_years_experience <= 0:
        exp_score = 100.0
        reasoning.append("No minimum experience requirement was set.")
    elif years_found >= min_years_experience:
        exp_score = 100.0
        reasoning.append(
            f"Candidate's resume indicates ~{years_found:.0f} years of experience, "
            f"meeting the {min_years_experience:.0f}-year requirement."
        )
    else:
        exp_score = max(0.0, (years_found / min_years_experience) * 100)
        reasoning.append(
            f"Candidate's resume indicates ~{years_found:.0f} years of experience, "
            f"below the {min_years_experience:.0f}-year requirement."
        )
    bd.experience_score = round(exp_score, 1)

    # ---- 3. Education ----
    bd.degree_found = resume.highest_degree
    bd.degree_required = required_degree
    req_rank = DEGREE_RANK.get(required_degree, 0)
    found_rank = DEGREE_RANK.get(resume.highest_degree, 0)
    if req_rank == 0:
        edu_score = 100.0
        reasoning.append("No specific education requirement was set.")
    elif found_rank >= req_rank:
        edu_score = 100.0
        reasoning.append(
            f"Highest detected degree ('{resume.highest_degree}') meets the "
            f"'{required_degree}' requirement."
        )
    elif found_rank > 0:
        edu_score = 60.0
        reasoning.append(
            f"Highest detected degree ('{resume.highest_degree}') is below the "
            f"'{required_degree}' requirement."
        )
    else:
        edu_score = 20.0
        reasoning.append("No recognizable degree was detected in the resume text.")
    bd.education_score = edu_score

    # ---- 4. Completeness / resume quality ----
    all_sections = ["experience", "education", "skills", "projects", "certifications", "summary"]
    found_sections = resume.sections_found
    missing_sections = [s for s in all_sections if s not in found_sections]
    completeness_pct = (len(found_sections) / len(all_sections)) * 100
    # Small penalty if resume is extremely short (likely thin content)
    if resume.word_count < 150:
        completeness_pct *= 0.7
        reasoning.append("Resume text is unusually short, which may indicate thin content.")
    bd.sections_found = found_sections
    bd.sections_missing = missing_sections
    bd.completeness_score = round(completeness_pct, 1)
    reasoning.append(
        f"Resume contains {len(found_sections)}/{len(all_sections)} expected sections."
    )

    # ---- Weighted overall score ----
    contributions = {
        "skills": bd.skill_score * WEIGHTS["skills"],
        "experience": bd.experience_score * WEIGHTS["experience"],
        "education": bd.education_score * WEIGHTS["education"],
        "completeness": bd.completeness_score * WEIGHTS["completeness"],
    }
    overall = sum(contributions.values())
    bd.component_contributions = {k: round(v, 1) for k, v in contributions.items()}
    bd.overall_score = round(overall, 1)

    for threshold, label, tone in RECOMMENDATION_BANDS:
        if bd.overall_score >= threshold:
            bd.recommendation = label
            bd.recommendation_tone = tone
            break

    bd.reasoning = reasoning
    return bd
