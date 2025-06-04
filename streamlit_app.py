import streamlit as st
from datetime import datetime, timedelta
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
import json
import os

st.set_page_config(page_title="AI Construction Scheduler", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date", "include_precon"],
    template="""
Generate a detailed construction schedule for a project called "{project_name}" in {location}, lasting {weeks} weeks, starting on {start_date}.
{include_precon} 
Respond in strict JSON format as a list of weekly objects like this:
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
st.markdown("Create a detailed Gantt chart & CSV from a prompt-based construction schedule.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())
include_precon = st.checkbox("✅ Include permitting, inspections, and pre-construction tasks")
email_address = st.text_input("Recipient Email")

if st.button("Generate Schedule"):
    if not project_name or not location or not email_address:
        st.warning("⚠️ Please fill in all fields.")
    else:
        with st.spinner("Generating schedule..."):
            prompt_input = {
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "include_precon": "Include permitting, inspections, and other common pre-construction tasks." if include_precon else ""
            }
            output = chain.run(prompt_input)

        try:
            schedule = json.loads(output)
            df = pd.DataFrame([
                {
                    "Week": item["week"],
                    "Date Range": item["date_range"],
                    "Task": "; ".join(item["tasks"])
                }
                for item in schedule
            ])

            st.success("✅ Schedule successfully parsed!")

            st.subheader("✏️ Preview & Edit Schedule")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

            def create_gantt(df):
                df[['Start', 'End']] = df['Date Range'].str.split(" to ", expand=True)
                df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
                df['End'] = pd.to_datetime(df['End'], errors='coerce')
                df.dropna(subset=['Start', 'End'], inplace=True)
                fig = px.timeline(df, x_start="Start", x_end="End", y="Task", color="Week")
                fig.update_yaxes(autorange="reversed")
                return fig

            st.subheader("📊 Gantt Chart & Export Options")
            gantt_chart = create_gantt(edited_df)
            st.plotly_chart(gantt_chart, use_container_width=True)

            csv = edited_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "schedule.csv", "text/csv")

            if st.button("📧 Send Email with Schedule"):
                email_content = f"Your schedule for '{project_name}' is below:\n\n{edited_df.to_string(index=False)}"
                msg = MIMEText(email_content)
                msg["Subject"] = f"Construction Schedule for {project_name}"
                msg["From"] = st.secrets["EMAIL_ADDRESS"]
                msg["To"] = email_address

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                    server.send_message(msg)

                st.success("📧 Email sent successfully!")

        except Exception as e:
            st.error(f"❌ Error parsing or processing schedule: {e}")

