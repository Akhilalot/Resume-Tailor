# Resume Tailor

A Streamlit app that takes your LaTeX resume and a target job description, then uses a two-stage LangChain pipeline to tailor the resume.

## Setup

```bash
cd Resume-Tailor
pip install -r requirements.txt
```

Add a `resume.tex` file containing your resume LaTeX. You can also upload a `.tex` resume in the app; uploaded resumes are saved locally as `.uploaded_resume.tex` and take precedence over `resume.tex` in future sessions.
Add a .env with the required Azure OpenAI env vars.

`RESUME_LATEX_PATH` sets the fallback resume path (default: `resume.tex`). `RESUME_UPLOAD_PATH` sets the saved upload path (default: `.uploaded_resume.tex`). Local resumes and environment files are ignored by Git.

## Run

```bash
streamlit run app.py
```

Choose **Upload File** to load a TXT, Markdown, text-based PDF, or DOCX job description, or choose **Paste Text**, then click **Run**. Scanned PDFs need text extraction before uploading.

Completed stage details and generated results remain available when switching views, downloading, or opening the pop-out within the same browser session. Uploaded resumes also persist across app restarts.

## How it works

| Stage | What it does |
|-------|-------------|
| **LLM 1 – Analyst** | Produces structured output: suggested job title, change instructions, and portal-ready experience descriptions. |
| **LLM 2 – Editor** | Applies the changes to the LaTeX source, keeping format intact and the PDF to one page. |

### Output

- **Resume** – switch between the tailored LaTeX and an inline diff in one scrollable panel. Download always saves the tailored `.tex` file.
- **Pop out** – open a viewport-sized modal with its own Updated Resume/Diff selector; scrolling stays inside the code panel.
- **Code controls** – copy the original text or toggle word wrap inside the panel. TeX syntax uses One Dark/One Light colors that follow the Streamlit theme; wrap preferences carry across views and the modal.
- **Portal Descriptions** – copy-paste into company application portals.
- **Skills** – copy relevant skills into the company portal.
