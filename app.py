import os
import difflib
import streamlit as st
from dotenv import load_dotenv
from chain import build_chain, ResumeAnalysis

# ── Load Settings from .env ──────────────────────────────────────────────────
load_dotenv()

AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]

RESUME_LATEX_PATH = os.environ.get("RESUME_LATEX_PATH", "resume.tex")
with open(RESUME_LATEX_PATH, "r") as f:
    RESUME_LATEX = f.read()

st.set_page_config(page_title="Resume Tailor", layout="wide")

# ── Main UI ──────────────────────────────────────────────────────────────────
st.title("Resume Tailor")
st.caption("Paste a target job description, then hit **Run** to tailor your hardcoded LaTeX resume.")

job_description = st.text_area(
    "Job Description",
    height=400,
    placeholder="Paste the full JD here…"
)

run = st.button("Run", type="primary", use_container_width=True)

# ── Execution ────────────────────────────────────────────────────────────────
if run:
    if not job_description.strip():
        st.error("The job description field is required.")
        st.stop()

    analysis_chain, rewrite_chain = build_chain(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    # Stage 1 – Analyse
    with st.status("Stage 1: Analysing resume against JD…", expanded=True) as s1:
        analysis: ResumeAnalysis = analysis_chain.invoke({
            "resume_latex": RESUME_LATEX,
            "job_description": job_description,
        })
        st.write(f"**Suggested job title:** {analysis.recent_job_title}")
        st.write("**Planned changes:**")
        st.markdown(analysis.changes)
        s1.update(label="Stage 1 complete", state="complete")

    # Stage 2 – Rewrite LaTeX
    with st.status("Stage 2: Rewriting LaTeX…", expanded=True) as s2:
        updated_latex: str = rewrite_chain.invoke({
            "resume_latex": RESUME_LATEX,
            "changes": (
                f"Most-recent job title should be: {analysis.recent_job_title}\n\n"
                f"{analysis.changes}"
            ),
        })
        s2.update(label="Stage 2 complete", state="complete")

    # ── Results ──────────────────────────────────────────────────────────────
    st.divider()
    tab_latex, tab_diff, tab_portal, tab_skills = st.tabs(["Updated LaTeX", "Diff", "Portal Descriptions", "Skills for Portal"])

    with tab_latex:
        st.code(updated_latex, language="latex")
        st.download_button(
            "Download .tex file",
            data=updated_latex,
            file_name="tailored_resume.tex",
            mime="application/x-tex",
        )

    with tab_diff:
        diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
            RESUME_LATEX.splitlines(),
            updated_latex.splitlines(),
            fromdesc="Original",
            todesc="Tailored",
            context=False,
        )
        diff_css = """<style>
        table.diff { width:100%; border-collapse:collapse; font-family:monospace; font-size:13px; }
        table.diff td { padding:2px 6px; white-space:pre-wrap; word-break:break-all; vertical-align:top; }
        table.diff th { padding:6px; text-align:left; background:#262730; color:#fafafa; }
        .diff_add { background-color: #1a3a1a; }
        .diff_chg { background-color: #3a3a1a; }
        .diff_sub { background-color: #3a1a1a; }
        .diff_header { background-color: #1a1a3a; color: #8888ff; }
        td.diff_header { font-weight: bold; }
        </style>"""
        st.html(diff_css + diff_html)

    with tab_portal:
        for exp in analysis.experience_descriptions:
            st.subheader(f"{exp.role} @ {exp.company}")
            st.code(exp.description, language=None)
            st.divider()

    with tab_skills:
        st.subheader("Extracted Skills (Portal-Ready)")
        st.info("Use the copy button on each block to copy a skill.")
        skills_list = [s.strip() for s in analysis.skills.split(",") if s.strip()]
        cols = st.columns(4)
        for i, skill in enumerate(skills_list):
            with cols[i % 4]:
                st.code(skill, language=None)