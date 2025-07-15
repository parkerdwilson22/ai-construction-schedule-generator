from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import openai
import requests
import plotly.express as px
from fpdf import FPDF
import os

# Streamlit secrets for security
openai.api_key = st.secrets["OPENAI_API_KEY"]
zapier_webhook_url = st.secrets["ZAPIER_WEBHOOK_URL"]

# Title
st.title("🏗️ AI Construction Schedule Generator")

# User input
project_name = st.text_input("Project Name")
start_date = st.date_input("Start Date", value=datetime.today())
num_weeks = st.slider("How many weeks is your schedule?", 1, 20, 10)

# Generate Schedule Button
if st.button("Generate Schedule"):
    with st.spinner("Generating construction schedule..."):
        prompt = f"""
        Create a construction schedule broken down by week for a project named '{project_name}' that lasts {num_weeks} weeks.
        Output the schedule as a JSON list with one entry per week using this format:
        [
          {{"week": 1, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "tasks": "Task A, Task B"}},
          ...
        ]
        Assume the project starts on {start_date.strftime("%Y-%m-%d")}.
        """
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{{"role": "user", "content": prompt}}],
            temperature=0.5,
        )
        text_output = response.choices[0].message.content.strip()
        try:
            schedule_data = eval(text_output)
        except:
            st.error("⚠️ Error parsing GPT response. Please try again.")
            st.stop()

        df = pd.DataFrame(schedule_data)

        # Show Gantt chart
        fig = px.timeline(
            df,
            x_start="start_date",
            x_end="end_date",
            y="tasks",
            color="week",
            title="📊 Gantt Chart",
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

        # Save CSV
        csv_path = "/tmp/schedule.csv"
        df.to_csv(csv_path, index=False)

        # Save PDF
        pdf_path = "/tmp/schedule.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"{project_name} Schedule", ln=True, align="C")
        for row in schedule_data:
            pdf.cell(200, 10, txt=f"Week {row['week']}: {row['tasks']}", ln=True)
        pdf.output(pdf_path)

        st.success("✅ Schedule generated!")

        if st.button("📤 Finalize & Send"):
            with open(csv_path, "rb") as f_csv, open(pdf_path, "rb") as f_pdf:
                response = requests.post(
                    zapier_webhook_url,
                    files={{
                        "csv_file": f_csv,
                        "pdf_file": f_pdf,
                    }},
                    data={{"project_name": project_name}},
                )
            if response.status_code == 200:
                st.success("✅ Sent to email & automation system!")
            else:
                st.error("❌ Failed to send. Check Zapier webhook URL.")






