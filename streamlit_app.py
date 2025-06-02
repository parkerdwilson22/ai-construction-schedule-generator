import streamlit as st
from datetime import datetime, timedelta
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
import os

st.set_page_config(page_title="AI Construction Scheduler", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date"],
    template="""
Generate a week-by-week construction schedule for a project called 
"{project_name}" in {location}, lasting {weeks} weeks, starting on 
{start_date}. 
Make the schedule very detailed. Each week's task must include specific 
work, dependencies if any, and realistic sequencing.
Also include the corresponding calendar dates for each week.
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

st.markdown("""
# 🏗️ AI Construction Schedule Generator

Enter your project details below to generate a smart, week-by-week construction timeline.
You’ll get a downloadable CSV, a Gantt chart, and the schedule via email.
""")

st.subheader("📋 Project Information")
project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
weeks = st.number_input("Project Duration (in weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Start Date", min_value=datetime.today())
email_address = st.text_input("Email to send the schedule")

if st.button("Generate Schedule"):
    if not project_name or not location or not email_address:
        st.warning("⚠️ Please fill in all fields before generating.")
    else:
        with st.spinner("Generating schedule..."):
            output = chain.run({
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d")
            })

        st.success("✅ Schedule generated!")

        st.subheader("📅 Weekly Construction Schedule")
        st.text_area("Detailed Timeline", output, height=400)

        def parse_schedule_to_df(output_text):
            data = []
            lines = output_text.split("\n")
            for line in lines:
                if line.strip().startswith("Week"):
                    parts = line.split(":")[0].split()
                    week_num = parts[1]
                    date_range = line.split("(")[-1].replace(")", "")
                    task = line.split(":")[1].strip() if ":" in line else ""
                    data.append({"Week": week_num, "Task": task, "Date Range": date_range})
            df = pd.DataFrame(data)
            return df

        df = parse_schedule_to_df(output)

        def create_gantt(df):
            df[['Start', 'End']] = df["Date Range"].str.split(" to ", expand=True)
            df['Start'] = pd.to_datetime(df['Start'])
            df['End'] = pd.to_datetime(df['End'])
            fig = px.timeline(df, x_start="Start", x_end="End", y="Task", color="Week")
            fig.update_yaxes(autorange="reversed")
            return fig

        gantt = create_gantt(df)

        with st.expander("📊 View Gantt Chart and Download CSV"):
            st.plotly_chart(gantt, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "schedule.csv", "text/csv")

        try:
            email_content = f"Here is your AI-generated construction schedule for {project_name}:\n\n{output}"
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
