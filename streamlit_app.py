import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests
from fpdf import FPDF
import io

# ----------------------------
# Constants
# ----------------------------
ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/23091746/u2h14yd/"

# ----------------------------
# PDF Export Utility
# ----------------------------
def generate_pdf(project_name, schedule_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, f"Construction Schedule: {project_name}", ln=True, align="C")
    pdf.set_font("Arial", size=12)

    for index, row in schedule_df.iterrows():
        pdf.cell(200, 10, f"Week {row['Week']}: {row['Start Date']} - {row['End Date']}", ln=True)
        pdf.multi_cell(200, 10, f"Tasks: {row['Tasks']}")

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    return pdf_output.getvalue()

# ----------------------------
# App UI
# ----------------------------
st.title("🚧 AI Construction Schedule Generator")
st.markdown("Generate your construction schedule based on your project inputs.")

with st.form("schedule_form"):
    project_name = st.text_input("Project Name", "New Construction Project")
    project_location = st.text_input("Location", "Charlotte, NC")
    project_type = st.selectbox("Project Type", ["Residential", "Commercial", "Infrastructure"])
    num_weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=52, value=6)
    start_date = st.date_input("Start Date", datetime.today())

    submitted = st.form_submit_button("Generate Schedule")

if submitted:
    schedule_data = []
    for week in range(num_weeks):
        week_start = start_date + timedelta(weeks=week)
        week_end = week_start + timedelta(days=6)
        tasks = f"Tasks for week {week + 1}"  # You can replace this with GPT-generated tasks later
        schedule_data.append({
            "Week": week + 1,
            "Start Date": week_start,
            "End Date": week_end,
            "Tasks": tasks
        })

    schedule_df = pd.DataFrame(schedule_data)

    st.success("✅ Schedule Generated!")
    st.dataframe(schedule_df)

    # Gantt chart
    fig = px.timeline(
        schedule_df,
        x_start="Start Date",
        x_end="End Date",
        y="Tasks",
        color="Week",
        title="Construction Schedule Timeline"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig)

    st.markdown("---")
    st.subheader("🚀 Finalize & Send")

    if st.button("🚀 Finalize & Send"):
        pdf_bytes = generate_pdf(project_name, schedule_df)
        csv_string = schedule_df.to_csv(index=False)

        zapier_payload = {
            "project_name": project_name,
            "location": project_location,
            "project_type": project_type,
            "weeks": num_weeks,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "schedule": [
                {
                    "week": row["Week"],
                    "start_date": row["Start Date"].strftime("%Y-%m-%d"),
                    "end_date": row["End Date"].strftime("%Y-%m-%d"),
                    "tasks": row["Tasks"]
                }
                for _, row in schedule_df.iterrows()
            ],
            "csv": csv_string,
            "pdf_base64": pdf_bytes.decode("latin1")  # Zapier receives PDF as string
        }

        try:
            response = requests.post(ZAPIER_WEBHOOK_URL, json=zapier_payload)
            if response.status_code == 200:
                st.success("✅ Schedule sent to Zapier!")
            else:
                st.error(f"❌ Error sending to Zapier: {response.text}")
        except Exception as e:
            st.error(f"❌ Exception: {e}")







