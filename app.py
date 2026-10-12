import os
import difflib
import html
import json
from io import BytesIO
import streamlit.components.v1 as components
import streamlit as st
from docx import Document
from pypdf import PdfReader
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TexLexer
from dotenv import load_dotenv
from chain import build_chain, ResumeAnalysis

# ── Load Settings from .env ──────────────────────────────────────────────────
load_dotenv()

AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]

RESUME_LATEX_PATH = os.environ.get("RESUME_LATEX_PATH", "resume.tex")
RESUME_UPLOAD_PATH = os.environ.get("RESUME_UPLOAD_PATH", ".uploaded_resume.tex")

st.set_page_config(page_title="Resume Tailor", layout="wide")


def themed_code_frame(
    content: str, height: int = 620, is_diff: bool = False,
    language: str = "text", modal: bool = False, viewport_height: float | None = None,
) -> None:
    def format_code(text: str) -> str:
        if language == "latex":
            return highlight(
                text, TexLexer(stripnl=False, ensurenl=False), HtmlFormatter(nowrap=True),
            ).rstrip("\n")
        return html.escape(text)

    clipboard_content = json.dumps(content).replace("<", r"\u003c")
    wrap_button = (
        '<button id="wordwrap" aria-pressed="false" title="Toggle word wrapping">Word wrap</button>'
        if language == "latex" else ""
    )
    if is_diff:
        rows = []
        for line in content.splitlines():
            if line.startswith(("+++", "---", "@@")):
                kind, marker, text = "meta", "", line
            elif line.startswith("+"):
                kind, marker, text = "added", "+", line[1:]
            elif line.startswith("-"):
                kind, marker, text = "removed", "−", line[1:]
            else:
                kind, marker, text = "context", " ", line[1:] if line.startswith(" ") else line
            rows.append(
                f'<div class="diff-line {kind}"><span class="marker">{marker}</span>'
                f'<span class="diff-text">{format_code(text) if text else "&nbsp;"}</span></div>'
            )
        code_markup = "".join(rows) or '<div class="diff-line">No changes.</div>'
        content_markup = f'<div class="code-panel diff-panel" id="content">{code_markup}</div>'
    else:
        content_markup = (
            f'<pre class="code-panel" id="content" style="height:{height}px;">'
            f'<code>{format_code(content)}</code></pre>'
        )

    components.html(
        f"""
        <style>
          * {{ box-sizing:border-box; }}
          html, body {{ margin:0; height:100%; overflow:hidden; }}
          body {{ font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace; }}
          .code-shell {{ position:relative; width:100%; height:{height}px; }}
          .code-actions {{ position:absolute; top:12px; right:20px; z-index:2; display:flex; gap:8px; }}
          .code-actions button {{ padding:6px 12px; cursor:pointer; border:1px solid; border-radius:6px;
                    font:13px system-ui,sans-serif; }}
          .code-actions button[aria-pressed="true"] {{ outline:2px solid #ff4b4b; outline-offset:1px; }}
          .code-panel {{ display:block; width:100%; margin:0; padding:52px 16px 16px; overflow:auto;
                         border:1px solid; border-radius:8px; white-space:pre; }}
          .diff-panel {{ height:{height}px; padding:52px 0 8px; }}
          .diff-line {{ display:flex; min-height:1.55em; min-width:max-content; padding:0 12px; white-space:pre; }}
          .diff-line .marker {{ flex:0 0 2ch; user-select:none; }}
          .code-panel.wrap-enabled {{ white-space:pre-wrap; overflow-wrap:anywhere; }}
          .code-panel.wrap-enabled .diff-line {{ white-space:pre-wrap; min-width:0; }}
          .code-panel.wrap-enabled .diff-text {{ flex:1; min-width:0; overflow-wrap:anywhere; }}
          body.dark .code-panel {{ background:#282c34; color:#abb2bf; border-color:#3e4451; }}
          body.dark button {{ background:#282c34; color:#abb2bf; border-color:#3e4451; }}
          body.dark .added {{ background:#2d3b32; color:#98c379; }}
          body.dark .removed {{ background:#3b2e32; color:#e06c75; }}
          body.dark .meta {{ color:#c678dd; font-weight:600; }}
          body.dark .context {{ color:#abb2bf; }}
          body.dark {{ --comment:#7f848e; --command:#c678dd; --name:#61afef; --string:#98c379; --number:#d19a66; --argument:#e5c07b; }}
          body.light .code-panel {{ background:#fafafa; color:#383a42; border-color:#e5e5e6; }}
          body.light button {{ background:#fafafa; color:#383a42; border-color:#e5e5e6; }}
          body.light .added {{ background:#edf7ed; color:#50a14f; }}
          body.light .removed {{ background:#fcedeb; color:#e45649; }}
          body.light .meta {{ color:#a626a4; font-weight:600; }}
          body.light .context {{ color:#383a42; }}
          body.light {{ --comment:#a0a1a7; --command:#a626a4; --name:#4078f2; --string:#50a14f; --number:#986801; --argument:#c18401; }}
          .code-panel .c, .code-panel .c1, .code-panel .cm {{ color:var(--comment); font-style:italic; }}
          .code-panel .k, .code-panel .kn, .code-panel .nb {{ color:var(--command); }}
          .code-panel .nf, .code-panel .nt, .code-panel .n {{ color:var(--name); }}
          .code-panel .s, .code-panel .s1, .code-panel .s2, .code-panel .sb {{ color:var(--string); }}
          .code-panel .m, .code-panel .mi, .code-panel .mf {{ color:var(--number); }}
          .code-panel .na, .code-panel .nv {{ color:var(--argument); }}
        </style>
        <div class="code-shell"><div class="code-actions">{wrap_button}<button id="copy">Copy</button></div>{content_markup}</div>
        <script>
          const wrapKey = 'resume-tailor-word-wrap';
          function updateWordWrap() {{
            const wrapButton = document.getElementById('wordwrap');
            if (!wrapButton) return;
            const enabled = window.parent.sessionStorage.getItem(wrapKey) === 'true';
            document.getElementById('content').classList.toggle('wrap-enabled', enabled);
            wrapButton.setAttribute('aria-pressed', String(enabled));
          }}
          const wrapButton = document.getElementById('wordwrap');
          if (wrapButton) wrapButton.onclick = () => {{
            const enabled = window.parent.sessionStorage.getItem(wrapKey) !== 'true';
            window.parent.sessionStorage.setItem(wrapKey, String(enabled));
            updateWordWrap();
          }};
          updateWordWrap();
          function resizePanel() {{
            let frameHeight = {height};
            if ({str(modal).lower()}) {{
              // The modal surface has a fixed viewport size, so its content
              // boundary stays stable when the iframe height changes.
              const dialog = window.frameElement.closest('[role="dialog"]');
              const contentBody = dialog && dialog.querySelector(':scope > div:last-child');
              if (contentBody) {{
                const padding = parseFloat(window.parent.getComputedStyle(contentBody).paddingBottom) || 0;
                frameHeight = Math.max(80, Math.floor(contentBody.getBoundingClientRect().bottom - window.frameElement.getBoundingClientRect().top - padding));
              }}
            }} else if ({json.dumps(viewport_height)} !== null) {{
              frameHeight = Math.max(360, Math.floor(window.parent.innerHeight * {json.dumps(viewport_height)}));
            }}
            const nextHeight = frameHeight + 'px';
            if (window.frameElement.style.height !== nextHeight) window.frameElement.style.height = nextHeight;
            const elementContainer = window.frameElement.closest('[data-testid="stElementContainer"]');
            if (elementContainer) elementContainer.style.height = nextHeight;
            document.querySelector('.code-shell').style.height = nextHeight;
            document.getElementById('content').style.height = nextHeight;
          }}
          function updateTheme() {{
            try {{
              const parentDoc = window.parent.document;
              let node = parentDoc.querySelector('[data-testid="stAppViewContainer"]')
                      || parentDoc.querySelector('[data-testid="stApp"]')
                      || parentDoc.body;
              let rgb = null;
              while (node) {{
                const color = getComputedStyle(node).backgroundColor;
                const values = color.match(/[\\d.]+/g);
                if (values && values.length >= 3 && (values.length < 4 || Number(values[3]) > 0)) {{
                  rgb = values;
                  break;
                }}
                node = node.parentElement;
              }}
              if (!rgb || rgb.length < 3) return;
              const brightness = Number(rgb[0]) * 0.299 + Number(rgb[1]) * 0.587 + Number(rgb[2]) * 0.114;
              document.body.classList.toggle('dark', brightness < 128);
              document.body.classList.toggle('light', brightness >= 128);
            }} catch (error) {{
              const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
              document.body.classList.toggle('dark', prefersDark);
              document.body.classList.toggle('light', !prefersDark);
            }}
          }}
          updateTheme();
          resizePanel();
          requestAnimationFrame(resizePanel);
          setTimeout(resizePanel, 100);
          window.parent.addEventListener('resize', resizePanel);
          window.addEventListener('unload', () => {{
            window.parent.removeEventListener('resize', resizePanel);
            clearInterval(window.themePoll);
          }});
          if (window.themePoll) clearInterval(window.themePoll);
          window.themePoll = setInterval(() => {{ updateTheme(); updateWordWrap(); }}, 500);
          document.getElementById('copy').onclick = async () => {{
            await navigator.clipboard.writeText({clipboard_content});
            document.getElementById('copy').textContent = 'Copied';
          }};
        </script>
        """,
        height=height,
        scrolling=False,
    )


@st.dialog("Resume", width="large")
def show_resume_modal():
    st.html(
        """
        <style>
        [data-testid="stDialog"] {
            position:fixed !important; inset:0 !important;
            display:flex !important; align-items:center !important; justify-content:center !important;
            overflow:hidden !important;
        }
        [data-testid="stDialog"] > div {
            position:relative !important; box-sizing:border-box !important;
            width:90vw !important; max-width:90vw !important;
            height:90vh !important; height:90dvh !important; max-height:90dvh !important;
            margin:0 !important; transform:none !important; overflow:hidden !important;
        }
        [data-testid="stDialog"] [role="dialog"] {
            display:flex !important; flex-direction:column !important;
            width:100% !important; height:100% !important; min-height:0 !important;
            overflow:hidden !important;
        }
        [data-testid="stDialog"] [role="dialog"] > h2 { flex-shrink:0 !important; }
        [data-testid="stDialog"] [role="dialog"] > div {
            flex:1 !important; min-height:0 !important; overflow:hidden !important;
        }
        </style>
        """,
    )
    view = st.radio(
        "Pop-out view", ["Updated Resume", "Diff"], horizontal=True,
        label_visibility="collapsed", key="modal_resume_view",
    )
    themed_code_frame(resume_view_content(view), height=620, is_diff=view == "Diff", language="latex", modal=True)


def resume_view_content(view: str) -> str:
    updated = st.session_state.get("updated_latex", "")
    if view == "Diff":
        return "\n".join(difflib.unified_diff(
            st.session_state.get("original_latex", RESUME_LATEX).splitlines(),
            updated.splitlines(), fromfile="Original", tofile="Tailored", lineterm="",
        ))
    return updated

# ── Main UI ──────────────────────────────────────────────────────────────────
st.title("Resume Tailor")
st.caption("Upload or paste a target job description, then hit **Run** to tailor your resume.")

uploaded_resume = st.file_uploader(
    "Upload resume (.tex)",
    type=["tex"],
    help="The uploaded resume is saved locally and reused in future sessions.",
    key="resume_upload",
)
if uploaded_resume is not None:
    resume_bytes = uploaded_resume.getvalue()
    if not resume_bytes.strip():
        st.error("The uploaded resume file is empty.")
        st.stop()
    saved_bytes = None
    if os.path.exists(RESUME_UPLOAD_PATH):
        with open(RESUME_UPLOAD_PATH, "rb") as f:
            saved_bytes = f.read()
    if resume_bytes != saved_bytes:
        with open(RESUME_UPLOAD_PATH, "wb") as f:
            f.write(resume_bytes)
        st.success("Resume uploaded and saved for future sessions.")

resume_path = RESUME_UPLOAD_PATH if os.path.exists(RESUME_UPLOAD_PATH) else RESUME_LATEX_PATH
with open(resume_path, "r", encoding="utf-8") as f:
    RESUME_LATEX = f.read()
st.caption(f"Using resume: {os.path.basename(resume_path)}")

input_mode = st.radio(
    "Job description source",
    ["Upload File", "Paste Text"],
    horizontal=True,
    label_visibility="collapsed",
)
jd_file = None
pasted_job_description = ""
if input_mode == "Upload File":
    jd_file = st.file_uploader(
        "Job description file",
        type=["txt", "md", "pdf", "docx"],
        help="Supported formats: TXT, Markdown, PDF, and DOCX.",
    )
else:
    pasted_job_description = st.text_area(
        "Job Description",
        height=300,
        placeholder="Paste the full job description here…",
    )

run = st.button("Run", type="primary", use_container_width=True)

# ── Execution ────────────────────────────────────────────────────────────────
if run:
    job_description = ""
    if input_mode == "Upload File" and jd_file is not None:
        extension = jd_file.name.rsplit(".", 1)[-1].lower()
        try:
            file_bytes = jd_file.getvalue()
            if extension in {"txt", "md"}:
                job_description = file_bytes.decode("utf-8-sig")
            elif extension == "pdf":
                reader = PdfReader(BytesIO(file_bytes))
                job_description = "\n".join(page.extract_text() or "" for page in reader.pages)
            elif extension == "docx":
                document = Document(BytesIO(file_bytes))
                job_description = "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:
            st.error(f"Could not read the uploaded file: {exc}")
            st.stop()
    elif input_mode == "Paste Text":
        job_description = pasted_job_description

    if not job_description.strip():
        st.error("Upload a job description file or paste the job description text.")
        st.stop()

    st.session_state.pop("stage_one_report", None)
    st.session_state.pop("stage_two_report", None)
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
        st.session_state["stage_one_report"] = {
            "job_title": analysis.recent_job_title,
            "changes": analysis.changes,
        }
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
        stage_two_report = "Generated the tailored LaTeX resume using the job title and changes from Stage 1."
        st.write(stage_two_report)
        st.session_state["stage_two_report"] = stage_two_report
        s2.update(label="Stage 2 complete", state="complete")

    st.session_state["resume_analysis"] = analysis
    st.session_state["updated_latex"] = updated_latex
    st.session_state["original_latex"] = RESUME_LATEX

if "stage_one_report" not in st.session_state and "resume_analysis" in st.session_state:
    saved_analysis = st.session_state["resume_analysis"]
    st.session_state["stage_one_report"] = {
        "job_title": saved_analysis.recent_job_title,
        "changes": saved_analysis.changes,
    }
if "stage_two_report" not in st.session_state and "updated_latex" in st.session_state:
    st.session_state["stage_two_report"] = (
        "Generated the tailored LaTeX resume using the job title and changes from Stage 1."
    )

if not run:
    if "stage_one_report" in st.session_state:
        report = st.session_state["stage_one_report"]
        with st.status("Stage 1 complete", state="complete", expanded=True):
            st.write(f"**Suggested job title:** {report['job_title']}")
            st.write("**Planned changes:**")
            st.markdown(report["changes"])
    if "stage_two_report" in st.session_state:
        with st.status("Stage 2 complete", state="complete", expanded=True):
            st.write(st.session_state["stage_two_report"])

if "resume_analysis" in st.session_state and "updated_latex" in st.session_state:
    analysis = st.session_state["resume_analysis"]
    updated_latex = st.session_state["updated_latex"]
    # ── Results ──────────────────────────────────────────────────────────────
    st.divider()
    tab_resume, tab_portal, tab_skills = st.tabs(["Resume", "Portal Descriptions", "Skills for Portal"])

    with tab_resume:
        with st.container(border=True):
            resume_view = st.radio(
                "Resume view",
                ["Updated Resume", "Diff"],
                horizontal=True,
                label_visibility="collapsed",
                key="resume_view",
            )
            is_diff = resume_view == "Diff"
            display_content = resume_view_content(resume_view)
            download_col, popout_col = st.columns([19, 1])
            with download_col:
                st.download_button(
                    "Download .tex",
                    data=updated_latex,
                    file_name="tailored_resume.tex",
                    mime="application/x-tex",
                    type="primary",
                    use_container_width=True,
                )
            with popout_col:
                if st.button(
                    "Pop out",
                    key="popout_resume",
                    help="Open this view in a scrollable window",
                    use_container_width=True,
                ):
                    st.session_state["modal_resume_view"] = resume_view
                    show_resume_modal()
            themed_code_frame(display_content, height=620, is_diff=is_diff, language="latex", viewport_height=0.6)

    with tab_portal:
        for exp in analysis.experience_descriptions:
            st.subheader(f"{exp.role} @ {exp.company}")
            themed_code_frame(exp.description, height=220)
            st.divider()

    with tab_skills:
        st.subheader("Extracted Skills (Portal-Ready)")
        st.info("Use the copy button on each block to copy a skill.")
        skills_list = [s.strip() for s in analysis.skills.split(",") if s.strip()]
        cols = st.columns(4)
        for i, skill in enumerate(skills_list):
            with cols[i % 4]:
                themed_code_frame(skill, height=110)
