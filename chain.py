from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

class ExperienceDescription(BaseModel):
    company: str = Field(description="Company name")
    role: str = Field(description="Role / job title at this company")
    description: str = Field(
        description="2-4 sentence description of work at this company, tailored to the target JD. "
        "Suitable for pasting into a company application portal."
    )

class ResumeAnalysis(BaseModel):
    recent_job_title: str = Field(
        description="The job title that should appear as the most recent experience, "
        "chosen to best align with the target job description."
    )
    changes: str = Field(
        description="Detailed, natural-language description of every change that should "
        "be made to the resume: which bullet points to rewrite, what keywords "
        "to weave in, how to adjust the summary section, etc."
    )
    experience_descriptions: List[ExperienceDescription] = Field(
        description="A list of concise descriptions for each experience entry in the resume, "
        "tailored to the target JD."
    )
    skills: str = Field(
        description="A comma-separated list of technical and soft skills extracted from the resume "
        "that are most relevant to the target job description. This is for pasting into portal 'Skills' fields."
    )

ANALYSIS_SYSTEM = """\
You are a senior human recruiter and resume editor with 15 years of experience.
Your job is to make subtle, targeted tweaks—not rewrite from scratch.
Your analysis is given to a rewriter agent, which modifies the resume (LaTeX code) accordingly.

Given a candidate's resume (in LaTeX source) and a target job description, produce a structured analysis:

1. recent_job_title – Pick a standard, widely-recognized industry title for the candidate's most recent role.
   Use titles that commonly appear on job boards (e.g. "Software Engineer", "Senior Software Engineer", "ML Engineer", "Data Scientist", "Backend Developer", "AI Engineer", "AI/ML Engineer", "AI Systems Engineer").
   Do NOT invent hyper-specific titles like "Software Engineer – Agentic AI Systems" or "ML Intern – Customer Analytics". Keep it simple and conventional.
2. changes – Write precise, minimal edit instructions. Focus on:
   - Swapping a few keywords to match the JD's language (do NOT stuff keywords).
   - Tightening wordy bullets into concise, metric-driven statements.
   - Adjusting the summary to naturally mirror the JD's priorities.
   - Keeping the candidate's authentic voice—do NOT use corporate buzzwords, filler phrases, or overly polished AI-sounding language.
   - The final resume MUST fit on ONE page. If edits risk exceeding one page, instruct the rewriter to trim or consolidate lower-priority bullets.
3. experience_descriptions – Write 2-4 sentence descriptions for each experience, in a natural conversational tone (as if the candidate wrote them), tailored to the JD.
4. skills – A comma-separated list of relevant skills from the resume that match the JD.

Rules:
- Be surgical: change only what genuinely improves JD alignment.
- Preserve the candidate's real accomplishments and numbers—never fabricate.
- Avoid generic filler like "leveraged", "spearheaded", "passionate about", "cutting-edge", "state-of-the-art".
- Write like a human, not a language model.
"""

REWRITE_SYSTEM = """\
You are a meticulous LaTeX resume editor who writes like a real person.

Apply the given change instructions and return the complete updated LaTeX.

Rules:
1. Only modify bullet text, the summary section, and the most recent job title. Leave everything else untouched.
2. The final resume MUST fit on ONE page. If content is too long, shorten or consolidate the least impactful bullets rather than shrinking fonts or margins.
3. Keep language natural, specific, and concise. Avoid generic AI-sounding phrases ("utilized", "leveraged", "spearheaded", "passionate", "cutting-edge"). Use plain, direct language a real engineer would write.
4. Job titles MUST be standard, widely-recognized industry titles (e.g. "Software Engineer", "Senior Software Engineer", "ML Engineer", "AI Engineer", "Machine Learning Intern"). Do NOT invent hyper-specific titles with dashes or qualifiers like "Software Engineer – Agentic AI Systems".
5. Preserve all LaTeX commands, structure, packages, and formatting exactly as-is.
6. Return ONLY the raw LaTeX source. No markdown fences, no commentary, not even the word "latex".
"""

def build_chain(api_key: str, azure_endpoint: str, deployment: str, api_version: str = "2024-12-01-preview"):
    """Build and return the two-stage LangChain chain using Azure OpenAI."""

    llm = AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version=api_version,
        model=deployment,
        temperature=0.3    )

    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYSIS_SYSTEM),
        ("human", "## Resume (LaTeX)\n\n{resume_latex}\n\n## Target Job Description\n\n{job_description}"),
    ])

    analysis_chain = analysis_prompt | llm.with_structured_output(ResumeAnalysis)

    rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", REWRITE_SYSTEM),
        ("human",
         "## Original Resume (LaTeX)\n\n{resume_latex}\n\n"
         "## Change Instructions\n\n{changes}\n\n"
         "Return the full updated LaTeX source below:"),
    ])

    rewrite_chain = rewrite_prompt | llm | StrOutputParser()

    return analysis_chain, rewrite_chain