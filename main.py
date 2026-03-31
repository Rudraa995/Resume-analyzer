import streamlit as st
from groq import Groq
import os
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import re
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# Load API Key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

st.set_page_config(page_title="AI Resume System", page_icon="📄", layout="wide")


menu = st.sidebar.selectbox(
    "Choose Feature",
    ["Resume Analyzer", "Job Description Matcher"]
)

if menu == "Resume Analyzer":

    st.title("📄 AI Resume Analyzer")
    st.write("Upload your resume and get **AI analysis, skills, suggestions and score**.")

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

    if uploaded_file:

        resume_name = uploaded_file.name
        analysis_date = datetime.now().strftime("%d %B %Y")

        pdf = PdfReader(uploaded_file)
        text = ""

        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        text_clean = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Resume Preview")
            st.text_area("Resume Text", text_clean, height=400)

        with col2:
            st.subheader("AI Analysis")

            if st.button("Analyze Resume"):

                with st.spinner("Analyzing resume..."):

                    prompt = f"""
You are a professional HR resume reviewer.

Analyze the resume and provide:

1. Resume summary
2. Extracted skills (list)
3. Suggestions for improvement
4. ATS compatibility score out of 100

Also provide scoring out of 100 based on:
Skills match (30)
Experience and achievements (30)
Clarity and formatting (20)
Overall impression (20)

Return JSON exactly like this:

Score JSON:
{{
"Skills": number,
"Experience": number,
"Clarity": number,
"Overall": number,
"ATS": number,
"SkillsList": ["skill1","skill2","skill3"]
}}

Resume:
{text_clean}
"""

                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}]
                    )

                    result = response.choices[0].message.content

                    parts = result.split("Score JSON:")
                    analysis_text = parts[0]

                    st.write(analysis_text)

                    if len(parts) > 1:

                        try:

                            json_text = parts[1]
                            match = re.search(r"\{.*\}", json_text, re.DOTALL)

                            if match:

                                score_data = json.loads(match.group())

                                score_data["Skills"] = min(score_data.get("Skills", 0), 30)
                                score_data["Experience"] = min(score_data.get("Experience", 0), 30)
                                score_data["Clarity"] = min(score_data.get("Clarity", 0), 20)
                                score_data["Overall"] = min(score_data.get("Overall", 0), 20)

                                ats_score = score_data.get("ATS", 0)
                                skills_list = score_data.get("SkillsList", [])

                                st.subheader("📊 Score Breakdown")

                                df = pd.DataFrame({
                                    "Category": ["Skills", "Experience", "Clarity", "Overall"],
                                    "Score": [
                                        score_data["Skills"],
                                        score_data["Experience"],
                                        score_data["Clarity"],
                                        score_data["Overall"]
                                    ]
                                })

                                st.bar_chart(df.set_index("Category"))

                                total_score = sum([
                                    score_data["Skills"],
                                    score_data["Experience"],
                                    score_data["Clarity"],
                                    score_data["Overall"]
                                ])

                                st.subheader("Overall Score")
                                st.progress(total_score/100)
                                st.success(f"Total Score: {total_score}/100")

                                st.subheader("ATS Compatibility")
                                st.info(f"ATS Score: {ats_score}/100")

                                st.subheader("Extracted Skills")
                                st.write(", ".join(skills_list))

                                plt.figure()
                                plt.bar(df["Category"], df["Score"])
                                chart_path = "score_chart.png"
                                plt.savefig(chart_path)
                                plt.close()

                                pdf_path = "resume_analysis_report.pdf"

                                styles = getSampleStyleSheet()
                                elements = []

                                elements.append(Paragraph("Candidate Resume Report", styles["Title"]))
                                elements.append(Spacer(1, 20))

                                elements.append(Paragraph(f"<b>Resume Name:</b> {resume_name}", styles["Normal"]))
                                elements.append(Paragraph(f"<b>Date of Analysis:</b> {analysis_date}", styles["Normal"]))
                                elements.append(Spacer(1, 20))

                                elements.append(Paragraph("<b>AI Analysis</b>", styles["Heading2"]))
                                elements.append(Paragraph(analysis_text.replace("\n", "<br/>"), styles["Normal"]))
                                elements.append(Spacer(1, 20))

                                elements.append(Paragraph("<b>Extracted Skills</b>", styles["Heading2"]))
                                elements.append(Paragraph(", ".join(skills_list), styles["Normal"]))
                                elements.append(Spacer(1, 20))

                                elements.append(Paragraph("<b>Score Breakdown</b>", styles["Heading2"]))
                                elements.append(Paragraph(
                                    f"Skills: {score_data['Skills']}/30<br/>"
                                    f"Experience: {score_data['Experience']}/30<br/>"
                                    f"Clarity: {score_data['Clarity']}/20<br/>"
                                    f"Overall Impression: {score_data['Overall']}/20<br/><br/>"
                                    f"<b>Total Score:</b> {total_score}/100",
                                    styles["Normal"]
                                ))

                                elements.append(Spacer(1, 20))
                                elements.append(Paragraph(f"<b>ATS Compatibility Score:</b> {ats_score}/100", styles["Normal"]))
                                elements.append(Spacer(1, 20))

                                elements.append(Paragraph("<b>Score Chart</b>", styles["Heading2"]))
                                elements.append(Image(chart_path, width=400, height=250))

                                pdf = SimpleDocTemplate(pdf_path)
                                pdf.build(elements)

                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        "📥 Download Full PDF Report",
                                        f,
                                        file_name="resume_analysis_report.pdf",
                                        mime="application/pdf"
                                    )

                        except Exception as e:
                            st.warning(f"Could not parse score JSON: {e}")

elif menu == "Job Description Matcher":

    st.title("Job Description Matcher")

    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

    job_description = st.text_area(
        "Enter Job Description",
        height=250
    )

    if st.button("Analyze Match"):

        if resume_file and job_description:

            pdf = PdfReader(resume_file)
            resume_text = ""

            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    resume_text += page_text + "\n"

            with st.spinner("Analyzing job match..."):

                prompt = f"""
You are an ATS resume expert.

Compare the following resume with the job description.

Return:

Match Score (0-100)

Missing Skills (bullet list)

Suggested Keywords to add (bullet list)

Short improvement suggestion.

Resume:
{resume_text}

Job Description:
{job_description}
"""

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )

                result = response.choices[0].message.content

                st.subheader("Match Analysis")

                st.write(result)

        else:
            st.warning("Upload resume and paste job description.")