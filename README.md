# Resume Tailor

A Streamlit app that takes your LaTeX resume and a target job description, then uses a two-stage LangChain pipeline to tailor the resume.

## Setup

```bash
cd resume-editor
pip install -r requirements.txt
```

Add a resume.tex file containing you resume latex code.
Add a .env with the required Azure OpenAI env vars.

## Run

```bash
streamlit run app.py
```

Paste the target JD, then click **Run**.

## How it works

| Stage | What it does |
|-------|-------------|
| **LLM 1 – Analyst** | Produces structured output: suggested job title, change instructions, and portal-ready experience descriptions. |
| **LLM 2 – Editor** | Applies the changes to the LaTeX source, keeping format intact and the PDF to one page. |

### Output

- **Updated LaTeX** – download as `.tex` and compile. (or copy/paste in overleaf and compile)
- **Diff** - a git like diff screen
- **Portal Descriptions** – copy-paste into company application portals.
- **Skills** - relevant skills for the company portal
