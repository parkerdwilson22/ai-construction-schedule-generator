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
Create a construction schedule in JSON format. It should include:
- Week number
- Start and end date for the week (YYYY-MM-DD)
- List of tasks for the week

Project Name: {project_name}
Location: {location}
Duration: {weeks} weeks
Start Date: {start_date}

Return ONLY valid JSON formatted like this:

[
  {{
    "week": 1,
    "start_date": "2025-06-01",
    "end_date": "2025-06-07",
    "tasks": ["Site prep", "Demo work"]
  }},
  ...
]
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

st.title("🛠️ AI Construction Schedule Generator")
st.write("Generate a detailed construction schedule with a Gantt chart, CSV download, and email delivery.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
weeks = st.number_input("Project Duration (in weeks)", min_value=1, max_value=52, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())
email_address = st.text_input("Email to send the schedule")

if st.button("Generate Schedule"):
    if not project_name or not location or not email_address:
        st.warning("Please fill in all fields.")
    else:
        with st.spinner("Generating schedule..."):
            output = chain.run({
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d")
            })

        try:
            data = json.loads(output)
            df = pd.DataFrame(data)

            df['Start'] = pd.to_datetime(df['start_date'])
            df['End'] = pd.to_datetime(df['end_date'])
            df['Task'] = df['tasks'].apply(lambda x: "; ".join(x))

            st.success("✅ Schedule generated!")

            st.subheader("📋 Project Schedule")
            st.dataframe(df[['week', 'start_date', 'end_date', 'Task']])

            with st.expander("📊 View Gantt Chart and Download CSV"):
                fig = px.timeline(df, x_start="Start", x_end="End", y="Task", color="week")
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "schedule.csv", "text/csv")

            try:
                email_content = f"Here is your AI-generated construction schedule for {project_name}:\n\n{df.to_string(index=False)}"
                msg = MIMEText(email_content)
                msg["Subject"] = f"Construction Schedule: {project_name}"
                msg["From"] = st.secrets["EMAIL_ADDRESS"]
                msg["To"] = email_address

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                    server.send_message(msg)

                st.success("📧 Schedule sent via email!")
            except Exception as e:
                st.error(f"Email failed: {e}")

        except Exception as e:
            st.error(f"❌ Failed to parse schedule. Error: {e}")
