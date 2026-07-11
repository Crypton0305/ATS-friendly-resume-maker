# AI Resume Screening Co-Pilot

A Streamlit app that helps HR teams screen resumes faster: upload a resume
PDF + candidate photo + info, get an explainable 0–100 score and hiring
recommendation, approve/reject as a human reviewer, and export a PDF report.

## Features

- **Resume parsing** — extracts text, emails, phone numbers, years of
  experience, highest degree, and resume sections from an uploaded PDF
  (`pdfplumber`, no system dependencies required).
- **Candidate scoring (0–100)** — weighted, rule-based score across:
  - Skill Match (50%) — against an HR-defined required-skills list
  - Experience (25%) — detected years vs. minimum required
  - Education (15%) — detected degree vs. minimum required
  - Resume Completeness (10%) — presence of standard resume sections
- **Hiring recommendation** — Strong Hire / Hire / Maybe / No Hire bands.
- **Explainable AI panel** — every score component links back to concrete
  evidence (matched/missing skills, detected years, detected degree,
  detected sections) — no black-box model.
- **Human-in-the-loop review** — HR can Approve / Reject / mark Pending,
  with a named reviewer and free-text comments, before any decision is
  final.
- **Downloadable PDF report** — candidate photo, info, full score
  breakdown, explainability notes, and the HR decision, generated with
  `fpdf2`.

## Project structure

```
resume-copilot/
├── app.py                 # Streamlit UI (4 tabs: Intake, Results, HR Review, Report)
├── modules/
│   ├── parser.py           # PDF text extraction + signal detection
│   ├── skills_db.py         # Built-in skill taxonomy for "bonus skills" detection
│   ├── scorer.py            # Weighted scoring engine + explainability
│   └── report.py            # PDF report generation (fpdf2)
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to use

1. **Sidebar** — set the job title, required skills (comma-separated),
   minimum years of experience, and minimum education level. These are
   the requirements every candidate is scored against.
2. **Candidate Intake tab** — enter candidate info, upload their resume
   PDF and (optionally) a photo, then click **Analyze Candidate**.
3. **Screening Results tab** — view the overall score, recommendation,
   component breakdown chart/table, and the explainability panel
   (matched/missing/bonus skills, detected experience & education, raw
   extracted text).
4. **HR Review tab** — the human reviewer approves, rejects, or holds the
   candidate, with optional comments. This decision is recorded and
   flows into the report — the AI never makes the final call alone.
5. **Report tab** — generate and download a PDF report combining
   everything above.

Click **Start New Screening** in the sidebar at any point to clear state
and screen the next candidate.

## Customizing the scoring logic

- Add/remove skills in `modules/skills_db.py` to change what shows up
  under "Other Skills Detected".
- Adjust component weights in `modules/scorer.py` (`WEIGHTS` dict) or the
  recommendation score bands (`RECOMMENDATION_BANDS`).
- The scorer is intentionally rule-based/transparent rather than an LLM
  call, so every number in the UI is traceable to a specific regex/keyword
  match in the resume — this is what powers the explainability panel. If
  you want to swap in an LLM-based semantic matcher for skills, that would
  slot into `modules/scorer.py::_find_skills_in_text`.
