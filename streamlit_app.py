import streamlit as st
import pandas as pd
import datetime
import requests
import plotly.express as px
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="AI Construction Schedule Generator")

st.title("🏗️ AI Construction Schedule Generator")
st.markdown("Generate a week-by-week schedule and send it via Zapier!")

# User inputs
project_name = st.text_input("Project Name")
location = st.text_input("Location")
project_type = st.selectbox("Project Type", ["Residential", "Commercial", "Infrastructure"])
start_date = st.date_input("Start Date", datetime.date.today())
weeks = st.slider("How many weeks is your schedule?", 1, 20, 6)

# Task input
task_inputs = []
st.subheader("📅 Weekly Tasks")
for i in range(weeks):
    week_tasks = st.text_area(f"Week {i+1} Tasks", "")
    task_inputs.append(week_tasks)

# Generate Schedule Data
schedule = []
for i in range(weeks):
    week_start = start_date + datetime.timedelta(weeks=i)
    week_end = week_start + datetime.timedelta(days=6)
    schedule.append({
        "week": i + 1,
        "start_date": week_start.strftime("%Y-%m-%d"),
        "end_date": week_end.strftime("%Y-%m-%d"),
        "tasks": task_inputs[i]
    })

# Display Gantt Chart
df = pd.DataFrame(schedule)
fig = px.timeline(df, x_start="start_date", x_end="end_date", y="tasks", color="week")
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig)

# PDF Export
def generate_pdf(schedule):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"{project_name} – Construction Schedule", ln=True, align="C")

    for week in schedule:
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Week {week['week']}: {week['start_date']} to {week['end_date']}", ln=True)
        pdf.multi_cell(0, 10, txt=f"Tasks: {week['tasks']}")

    output = BytesIO()
    pdf.output(output)
    return output

# Finalize & Send
st.subheader("🚀 Finalize & Send")
webhook_url = st.secrets.get("zapier_webhook_url")

send_to_zapier = st.button("🚀 Finalize & Send")
if send_to_zapier:
    # JSON-serializable payload
    zapier_payload = {
        "project_name": project_name,
        "location": location,
        "project_type": project_type,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "weeks": weeks,
        "schedule": schedule  # clean array of dicts
    }

    if webhook_url:
        try:
            res = requests.post(webhook_url, json=zapier_payload)
            if res.status_code == 200:
                st.success("✅ Sent to Zapier!")
            else:
                st.error(f"❌ Zapier Error: {res.text}")
        except Exception as e:
            st.error(f"❌ Exception: {str(e)}")
    else:
        st.warning("Webhook URL is missing from Streamlit secrets.")




