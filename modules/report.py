"""
report.py
---------
Builds a downloadable PDF summary report for a screened candidate:
profile info, photo, score breakdown, explainability notes, and the
HR (human-in-the-loop) decision + comments.

Uses fpdf2 (pure Python, no system dependencies).
"""

import io
import tempfile
import os
from datetime import datetime

from fpdf import FPDF

PRIMARY = (30, 64, 175)      # indigo
GREEN = (21, 128, 61)
AMBER = (180, 130, 15)
RED = (185, 28, 28)
GREY = (90, 90, 90)

TONE_COLORS = {"success": GREEN, "warning": AMBER, "error": RED}


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*PRIMARY)
        self.cell(0, 10, "AI Resume Screening Co-Pilot - Candidate Report", ln=True)
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.6)
        self.line(10, 20, 200, 20)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")


def _section_title(pdf: ReportPDF, text: str):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 8, text, ln=True)
    pdf.set_text_color(0, 0, 0)


def _kv_row(pdf: ReportPDF, key: str, value: str):
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 6, key, ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, value if value else "-")


def _bullet_list(pdf: ReportPDF, items, color=(0, 0, 0)):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*color)
    if not items:
        pdf.cell(0, 6, "  - None", ln=True)
    for item in items:
        pdf.multi_cell(0, 6, f"  - {item}")
    pdf.set_text_color(0, 0, 0)


def generate_report(
    candidate_info: dict,
    resume_data,
    score_breakdown,
    hr_decision: dict,
    photo_bytes: bytes = None,
) -> bytes:
    """Return the finished PDF report as raw bytes."""
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # --- Candidate header block (photo + basic info) ---
    photo_path = None
    if photo_bytes:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(photo_bytes)
        tmp.close()
        photo_path = tmp.name
        pdf.image(photo_path, x=165, y=24, w=30, h=30)

    pdf.set_xy(10, 24)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, candidate_info.get("name", "Unknown Candidate"), ln=True)

    pdf.set_x(10)
    _kv_row(pdf, "Position Applied:", candidate_info.get("position", ""))
    pdf.set_x(10)
    _kv_row(pdf, "Email:", candidate_info.get("email", ""))
    pdf.set_x(10)
    _kv_row(pdf, "Phone:", candidate_info.get("phone", ""))
    pdf.set_x(10)
    _kv_row(pdf, "Screened On:", datetime.now().strftime("%Y-%m-%d %H:%M"))

    if photo_path:
        pdf.set_y(58)
    pdf.ln(4)

    # --- Score summary ---
    _section_title(pdf, "Overall Screening Score")
    tone_color = TONE_COLORS.get(score_breakdown.recommendation_tone, GREY)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*tone_color)
    pdf.cell(60, 16, f"{score_breakdown.overall_score:.1f} / 100", ln=False)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 16, score_breakdown.recommendation, ln=True)
    pdf.set_text_color(0, 0, 0)

    # --- Component breakdown table ---
    _section_title(pdf, "Score Breakdown")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 235, 245)
    pdf.cell(60, 7, "Component", border=1, fill=True)
    pdf.cell(40, 7, "Raw Score", border=1, fill=True)
    pdf.cell(40, 7, "Weight", border=1, fill=True)
    pdf.cell(40, 7, "Contribution", border=1, fill=True, ln=True)

    pdf.set_font("Helvetica", "", 10)
    rows = [
        ("Skill Match", score_breakdown.skill_score, "50%", score_breakdown.component_contributions.get("skills", 0)),
        ("Experience", score_breakdown.experience_score, "25%", score_breakdown.component_contributions.get("experience", 0)),
        ("Education", score_breakdown.education_score, "15%", score_breakdown.component_contributions.get("education", 0)),
        ("Resume Completeness", score_breakdown.completeness_score, "10%", score_breakdown.component_contributions.get("completeness", 0)),
    ]
    for name, raw, weight, contrib in rows:
        pdf.cell(60, 7, name, border=1)
        pdf.cell(40, 7, f"{raw:.1f}", border=1)
        pdf.cell(40, 7, weight, border=1)
        pdf.cell(40, 7, f"{contrib:.1f}", border=1, ln=True)

    # --- Explainability ---
    _section_title(pdf, "Explainable AI Insights")
    _bullet_list(pdf, score_breakdown.reasoning)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Matched Required Skills:", ln=True)
    _bullet_list(pdf, score_breakdown.matched_skills, GREEN)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Missing Required Skills:", ln=True)
    _bullet_list(pdf, score_breakdown.missing_skills, RED)

    if score_breakdown.bonus_skills:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Other Skills Detected (not required, for context):", ln=True)
        _bullet_list(pdf, score_breakdown.bonus_skills)

    # --- HR decision ---
    _section_title(pdf, "HR Decision (Human-in-the-Loop)")
    decision = hr_decision.get("decision", "Pending")
    decision_color = {"Approved": GREEN, "Rejected": RED}.get(decision, AMBER)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*decision_color)
    pdf.cell(0, 8, f"Decision: {decision}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Reviewed by: {hr_decision.get('reviewer', '-')}", ln=True)
    pdf.cell(0, 6, f"Reviewed on: {hr_decision.get('timestamp', '-')}", ln=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Comments:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, hr_decision.get("comments") or "-")

    if photo_path and os.path.exists(photo_path):
        os.remove(photo_path)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        out = out.encode("latin-1")
    else:
        out = bytes(out)
    return out
