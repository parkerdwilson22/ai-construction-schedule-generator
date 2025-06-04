import streamlit as st
from datetime import datetime, timedelta
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import json
import os
from fpdf import FPDF
import tempfile

st.set_page_config(page_title="AI Construction Scheduler", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date", "project_type"],
    template="""
Generate a detailed construction schedule for a {project_type} project called "{project_name}" in {location}, lasting {weeks} weeks, starting on {start_date}.
Include pre-construction tasks like permitting, inspections, and utility setup in the first week. 
Do not repeat them later. Return the schedule in strict JSON format like this:
[
  {{
    "week": 1,
    "date_range": "2025-06-01 to 2025-06-07",
    "tasks": ["Excavate site", "Set up perimeter fencing"]
  }},
  ...
]
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

st.title("🏗️ AI Construction Schedule Generator")
st.markdown("Generate, preview, and email editable construction schedules tailored by project type.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
project_type = st.selectbox("Project Type", ["Residential", "Commercial", "Renovation", "Infrastructure"])
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())
email_address = st.text_input("Recipient Email (Optional – used only when sending email)")

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None

if st.button("Generate Schedule"):
    if not project_name or not location:
        st.warning("⚠️ Please fill in all required fields.")
    else:
        with st.spinner("Generating schedule..."):
            prompt_input = {
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "project_type": project_type
            }

            output = chain.run(prompt_input)

        try:
            schedule = json.loads(output)

            df = pd.DataFrame([
                {
                    "week": item["week"],
                    "start_date": item["date_range"].split(" to ")[0],
                    "end_date": item["date_range"].split(" to ")[1],
                    "tasks": "; ".join(item["tasks"])
                }
                for item in schedule
            ])

            df["week"] = list(range(1, len(df) + 1))
            st.session_state.schedule_data = df

        except Exception as e:
            st.error(f"❌ Failed to parse or display schedule: {e}")

if st.session_state.schedule_data is not None:
    st.success("✅ Schedule successfully generated!")

    st.subheader("✏️ Preview & Edit Schedule")
    edited_df = st.data_editor(st.session_state.schedule_data.copy(), num_rows="dynamic", use_container_width=True, key="editable_table")

    st.subheader("📊 Gantt Chart")
    try:
        edited_df['Start'] = pd.to_datetime(edited_df['start_date'], errors='coerce')
        edited_df['End'] = pd.to_datetime(edited_df['end_date'], errors='coerce')
        gantt_fig = px.timeline(
            edited_df, 
            x_start="Start", 
            x_end="End", 
            y="tasks", 
            color="week", 
            height=600
        )
        gantt_fig.update_yaxes(autorange="reversed", title=None)
        gantt_fig.update_layout(margin=dict(l=50, r=50, t=30, b=30))
        st.plotly_chart(gantt_fig, use_container_width=True)
    except Exception as e:
        st.warning("⚠️ Could not generate Gantt chart. Check date formatting.")

    csv_data = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", csv_data, "schedule.csv", "text/csv")

    def create_pdf(df, project_name):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, f"Project Schedule for {project_name}", ln=True, align="C")
        pdf.set_font("Arial", size=10)
        pdf.ln(5)

        col_widths = [15, 30, 30, 110]
        headers = ["Week", "Start", "End", "Tasks"]

        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, border=1)
        pdf.ln()

        for _, row in df.iterrows():
            pdf.cell(col_widths[0], 8, str(row["week"]), border=1)
            pdf.cell(col_widths[1], 8, str(row["start_date"]), border=1)
            pdf.cell(col_widths[2], 8, str(row["end_date"]), border=1)
            pdf.multi_cell(col_widths[3], 8, str(row["tasks"]), border=1)
            pdf.ln(0)

        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp_path.name)
        return temp_path.name

    pdf_file_path = create_pdf(edited_df, project_name)
    with open(pdf_file_path, "rb") as f:
        st.download_button("🧾 Download PDF", f.read(), file_name="schedule.pdf", mime="application/pdf")

    st.subheader("📧 Send Schedule by Email")
    if st.button("Send Email"):
        if not email_address:
            st.warning("⚠️ Please enter an email address above.")
        else:
            email_body = f"Hi,\n\nAttached is your PDF schedule for '{project_name}'. Let me know if you need any changes.\n\nBest,\nAI Scheduler"

            pdf_file_path = create_pdf(edited_df, project_name)

            msg = MIMEMultipart()
            msg["Subject"] = f"Construction Schedule for {project_name}"
            msg["From"] = st.secrets["EMAIL_ADDRESS"]
            msg["To"] = email_address
            msg.attach(MIMEText(email_body))

            with open(pdf_file_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename="schedule.pdf")
                msg.attach(part)

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)

            st.success("📨 PDF schedule emailed successfully!")




