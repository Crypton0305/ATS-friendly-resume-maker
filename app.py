"""
AI Resume Screening Co-Pilot
=============================
A Streamlit application that helps HR teams screen candidates faster:

  1. Upload a resume (PDF), candidate photo, and candidate info
  2. Automatically extract resume text + structured signals
  3. Score the candidate 0-100 against HR-defined requirements
  4. Show a fully explainable breakdown of the score
  5. Let an HR reviewer approve / reject (human-in-the-loop)
  6. Export a polished PDF report of the whole screening

Run with:  streamlit run app.py
"""

from datetime import datetime

import streamlit as st
import pandas as pd

from modules.parser import parse_resume
from modules.scorer import score_candidate
from modules.report import generate_report

st.set_page_config(
    page_title="AI Resume Screening Co-Pilot",
    page_icon="🧑‍💼",
    layout="wide",
)

# --------------------------------------------------------------------------
# Session state initialization
# --------------------------------------------------------------------------
DEFAULTS = {
    "resume_data": None,
    "score_breakdown": None,
    "candidate_info": {},
    "photo_bytes": None,
    "hr_decision": {"decision": "Pending", "reviewer": "", "comments": "", "timestamp": ""},
    "analyzed": False,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


def reset_screening():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val


# --------------------------------------------------------------------------
# Sidebar: Job requirements (what the candidate is scored against)
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("🧑‍💼 Co-Pilot Settings")
    st.caption("Define the role requirements used to score every candidate.")

    job_title = st.text_input("Job Title", value=st.session_state.get("job_title", "Software Engineer"))
    required_skills_raw = st.text_area(
        "Required Skills (comma-separated)",
        value=st.session_state.get(
            "required_skills_raw",
            "python, sql, aws, react, machine learning, communication",
        ),
        height=100,
    )
    min_years = st.slider("Minimum Years of Experience", 0, 15, 3)
    required_degree = st.selectbox(
        "Minimum Education Level",
        ["none", "associate", "bachelor", "master", "phd"],
        index=2,
    )

    st.session_state["job_title"] = job_title
    st.session_state["required_skills_raw"] = required_skills_raw

    st.divider()
    if st.button("🔄 Start New Screening", use_container_width=True):
        reset_screening()
        st.rerun()

    st.divider()
    st.caption(
        "Scoring is fully rule-based and transparent: every point is traced "
        "to specific evidence in the resume (see 'Explainable AI Insights')."
    )

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.title("AI Resume Screening Co-Pilot")
st.caption("Upload a resume, score it against your role requirements, review, and export a report.")

tab_intake, tab_results, tab_hitl, tab_report = st.tabs(
    ["📥 Candidate Intake", "📊 Screening Results", "✅ HR Review", "📄 Report"]
)

# --------------------------------------------------------------------------
# TAB 1: Candidate Intake
# --------------------------------------------------------------------------
with tab_intake:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Candidate Information")
        name = st.text_input("Full Name", value=st.session_state["candidate_info"].get("name", ""))
        email = st.text_input("Email", value=st.session_state["candidate_info"].get("email", ""))
        phone = st.text_input("Phone", value=st.session_state["candidate_info"].get("phone", ""))
        position = st.text_input(
            "Position Applied For",
            value=st.session_state["candidate_info"].get("position", job_title),
        )

        st.subheader("Resume Upload")
        resume_file = st.file_uploader("Upload Resume (PDF only)", type=["pdf"])

    with col2:
        st.subheader("Candidate Photo")
        photo_file = st.file_uploader("Upload Photo", type=["png", "jpg", "jpeg"])
        if photo_file:
            st.session_state["photo_bytes"] = photo_file.read()
            st.image(st.session_state["photo_bytes"], caption=name or "Candidate", width=200)
        elif st.session_state["photo_bytes"]:
            st.image(st.session_state["photo_bytes"], caption=name or "Candidate", width=200)
        else:
            st.info("No photo uploaded yet.")

    st.divider()
    analyze_clicked = st.button("🔍 Analyze Candidate", type="primary", use_container_width=True)

    if analyze_clicked:
        if not resume_file:
            st.error("Please upload a resume PDF before analyzing.")
        elif not name:
            st.error("Please enter the candidate's name.")
        else:
            with st.spinner("Extracting resume content and scoring candidate..."):
                resume_bytes = resume_file.read()
                resume_data = parse_resume(resume_bytes)

                required_skills = [s.strip() for s in required_skills_raw.split(",") if s.strip()]
                breakdown = score_candidate(
                    resume=resume_data,
                    required_skills=required_skills,
                    min_years_experience=min_years,
                    required_degree=required_degree,
                )

                st.session_state["resume_data"] = resume_data
                st.session_state["score_breakdown"] = breakdown
                st.session_state["candidate_info"] = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "position": position,
                }
                st.session_state["analyzed"] = True
                # Reset any prior HR decision for a fresh analysis
                st.session_state["hr_decision"] = {
                    "decision": "Pending", "reviewer": "", "comments": "", "timestamp": ""
                }

            st.success("Analysis complete! Head to the 'Screening Results' tab.")

# --------------------------------------------------------------------------
# TAB 2: Screening Results
# --------------------------------------------------------------------------
with tab_results:
    if not st.session_state["analyzed"]:
        st.info("Upload and analyze a candidate in the 'Candidate Intake' tab first.")
    else:
        bd = st.session_state["score_breakdown"]
        info = st.session_state["candidate_info"]
        resume_data = st.session_state["resume_data"]

        tone_emoji = {"success": "🟢", "warning": "🟡", "error": "🔴"}.get(bd.recommendation_tone, "⚪")

        top_l, top_r = st.columns([1, 3])
        with top_l:
            if st.session_state["photo_bytes"]:
                st.image(st.session_state["photo_bytes"], width=140)
        with top_r:
            st.subheader(info.get("name", ""))
            st.write(f"**Position:** {info.get('position','-')}  |  **Email:** {info.get('email','-')}  |  **Phone:** {info.get('phone','-')}")
            st.metric("Overall Score", f"{bd.overall_score:.1f} / 100")
            st.markdown(f"### {tone_emoji} Recommendation: **{bd.recommendation}**")

        st.divider()
        st.subheader("Score Breakdown")

        breakdown_df = pd.DataFrame(
            {
                "Component": ["Skill Match", "Experience", "Education", "Resume Completeness"],
                "Raw Score": [bd.skill_score, bd.experience_score, bd.education_score, bd.completeness_score],
                "Weight": ["50%", "25%", "15%", "10%"],
                "Contribution to Final Score": [
                    bd.component_contributions.get("skills", 0),
                    bd.component_contributions.get("experience", 0),
                    bd.component_contributions.get("education", 0),
                    bd.component_contributions.get("completeness", 0),
                ],
            }
        )
        c1, c2 = st.columns([3, 2])
        with c1:
            st.dataframe(breakdown_df, hide_index=True, use_container_width=True)
        with c2:
            st.bar_chart(breakdown_df.set_index("Component")["Raw Score"])

        st.divider()
        st.subheader("🔎 Explainable AI Insights")
        for line in bd.reasoning:
            st.markdown(f"- {line}")

        sk1, sk2, sk3 = st.columns(3)
        with sk1:
            st.markdown("**✅ Matched Required Skills**")
            st.write(", ".join(bd.matched_skills) if bd.matched_skills else "_None_")
        with sk2:
            st.markdown("**❌ Missing Required Skills**")
            st.write(", ".join(bd.missing_skills) if bd.missing_skills else "_None_")
        with sk3:
            st.markdown("**➕ Other Skills Detected**")
            st.write(", ".join(bd.bonus_skills) if bd.bonus_skills else "_None_")

        st.divider()
        with st.expander("📄 View Extracted Resume Text"):
            st.text_area("Raw extracted text", resume_data.raw_text, height=300)

        with st.expander("🧾 Parsed Resume Signals"):
            st.write(
                {
                    "Emails found": resume_data.emails,
                    "Phones found": resume_data.phones,
                    "Years of experience detected": resume_data.years_experience,
                    "Highest degree detected": resume_data.highest_degree,
                    "Sections found": resume_data.sections_found,
                    "Word count": resume_data.word_count,
                    "Page count": resume_data.page_count,
                }
            )

# --------------------------------------------------------------------------
# TAB 3: HR Review (Human-in-the-Loop)
# --------------------------------------------------------------------------
with tab_hitl:
    if not st.session_state["analyzed"]:
        st.info("Analyze a candidate first to enable HR review.")
    else:
        bd = st.session_state["score_breakdown"]
        st.subheader("Human-in-the-Loop Review")
        st.write(
            f"The AI recommends **{bd.recommendation}** with a score of **{bd.overall_score:.1f}/100**. "
            "Final hiring decisions always require HR sign-off below."
        )

        reviewer = st.text_input("Reviewer Name", value=st.session_state["hr_decision"].get("reviewer", ""))
        comments = st.text_area(
            "Review Comments",
            value=st.session_state["hr_decision"].get("comments", ""),
            placeholder="Add notes on why you're approving/rejecting, follow-up questions for the interview, etc.",
        )

        b1, b2, b3 = st.columns(3)
        approve = b1.button("✅ Approve Candidate", use_container_width=True, type="primary")
        reject = b2.button("❌ Reject Candidate", use_container_width=True)
        hold = b3.button("⏸️ Mark as Pending", use_container_width=True)

        if approve or reject or hold:
            decision = "Approved" if approve else ("Rejected" if reject else "Pending")
            st.session_state["hr_decision"] = {
                "decision": decision,
                "reviewer": reviewer or "Unspecified",
                "comments": comments,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            st.rerun()

        current = st.session_state["hr_decision"]
        if current["decision"] != "Pending" or current["reviewer"]:
            tone = {"Approved": "success", "Rejected": "error", "Pending": "warning"}[current["decision"]]
            getattr(st, tone)(
                f"Current decision: **{current['decision']}** by {current['reviewer'] or '-'} "
                f"on {current['timestamp'] or '-'}"
            )
            if current["comments"]:
                st.caption(f"Comments: {current['comments']}")

# --------------------------------------------------------------------------
# TAB 4: Report
# --------------------------------------------------------------------------
with tab_report:
    if not st.session_state["analyzed"]:
        st.info("Analyze a candidate first to generate a report.")
    else:
        st.subheader("Downloadable Candidate Report")
        st.write(
            "Generates a single PDF with candidate info, photo, score breakdown, "
            "explainability notes, and the current HR decision."
        )

        if st.button("🧾 Generate PDF Report", type="primary"):
            with st.spinner("Building PDF report..."):
                pdf_bytes = generate_report(
                    candidate_info=st.session_state["candidate_info"],
                    resume_data=st.session_state["resume_data"],
                    score_breakdown=st.session_state["score_breakdown"],
                    hr_decision=st.session_state["hr_decision"],
                    photo_bytes=st.session_state["photo_bytes"],
                )
            st.session_state["report_bytes"] = pdf_bytes
            st.success("Report generated!")

        if st.session_state.get("report_bytes"):
            fname = f"{st.session_state['candidate_info'].get('name','candidate').replace(' ','_')}_screening_report.pdf"
            st.download_button(
                "⬇️ Download PDF Report",
                data=st.session_state["report_bytes"],
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
            )
