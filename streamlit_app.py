import streamlit as st
from datetime import datetime
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
import os
import json

st.set_page_config(page_title="AI Construction Scheduler", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.5)

prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date"],
    template="""
Generate a detailed construction schedule for a project called "{project_name}" located in {location}, lasting {weeks} weeks starting from {start_date}.

Return the output as valid JSON formatted like this:
[
  {{
    "week": 1,
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "tasks": ["Task 1", "Task 2"]
  }},
  ...
]

The output MUST be valid JSON. Do not include any notes or text outside the JSON block.
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

st.title("AI Construction Schedule Generator")
st.subheader("Project Information")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
weeks = st.number_input("Project Duration (in weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Start Date", min_value=datetime.today())
email_address = st.text_input("Email to send the schedule")

if st.button("Generate Schedule"):
    if not project_name or not location or not email_address:
        st.warning("Please fill in all fields before generating.")
    else:
        with st.spinner("Generating schedule..."):
            output = chain.run({
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d")
            })

        try:
            schedule_json = json.loads(output)
        except Exception as e:
            st.error(f"Failed to parse AI response as JSON: {e}")
            st.code(output)
            st.stop()

        df = pd.DataFrame(schedule_json)
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['end_date'] = pd.to_datetime(df['end_date'])
        df['Week'] = df['week']
        df['Task'] = df['tasks'].apply(lambda tasks: "; ".join(tasks))

        st.success("Schedule generated!")

        st.subheader("Schedule Preview")
        st.dataframe(df[["Week", "start_date", "end_date", "Task"]])

        st.subheader("Gantt Chart and CSV Export")
        fig = px.timeline(df, x_start="start_date", x_end="end_date", y="Task", color="Week")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "schedule.csv", "text/csv")

        try:
            email_content = f"Here is your AI-generated construction schedule for {project_name}:\n\n{df.to_string(index=False)}"
            msg = MIMEText(email_content)
            msg["Subject"] = f"Construction Schedule: {project_name}"
            msg["From"] = st.secrets["EMAIL_ADDRESS"]
            msg["To"] = email_address

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)

            st.success("Schedule sent via email!")
        except Exception as e:
            st.error(f"Email failed: {e}")
