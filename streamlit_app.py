import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import requests
import json

st.set_page_config(layout="wide")

st.title("🏗️ AI Construction Schedule Generator")
st.markdown("Generate and send a construction schedule with one click.")

# ---- Project Info ----
st.sidebar.header("Project Info")
project_name = st.sidebar.text_input("Project Name")
location = st.sidebar.text_input("Location")
project_type = st.sidebar.selectbox("Project Type", ["Residential", "Commercial"])
num_weeks = st.sidebar.number_input("Number of Weeks", min_value=1, max_value=52, value=4)
start_date = st.sidebar.date_input("Start Date", value=datetime.today())

# ---- Schedule Generation ----
generate = st.sidebar.button("Generate Schedule")

if generate:
    schedule = []
    for week in range(num_weeks):
        week_start = start_date + timedelta(weeks=week)
        week_end = week_start + timedelta(days=6)
        schedule.append({
            "Schedule Week": f"{week + 1}",
            "Schedule Start Date": week_start.strftime("%Y-%m-%d"),
            "Schedule End Date": week_end.strftime("%Y-%m-%d"),
            "Schedule Tasks": ""
        })

    st.session_state["generated_schedule"] = schedule

# ---- Editable Schedule Table ----
if "generated_schedule" in st.session_state:
    st.subheader("✏️ Edit Your Schedule Tasks")
    edited_schedule = []

    for i, week in enumerate(st.session_state["generated_schedule"]):
        with st.expander(f"Week {i + 1}: {week['Schedule Start Date']} to {week['Schedule End Date']}"):
            task_input = st.text_area("Tasks for the week", value=week["Schedule Tasks"], key=f"tasks_{i}")
            edited_schedule.append({
                "Schedule Week": week["Schedule Week"],
                "Schedule Start Date": week["Schedule Start Date"],
                "Schedule End Date": week["Schedule End Date"],
                "Schedule Tasks": task_input
            })

    # ---- Preview Schedule ----
    df = pd.DataFrame(edited_schedule)
    st.subheader("📋 Final Schedule Preview")
    st.dataframe(df, use_container_width=True)

    # ---- Gantt Chart ----
    st.subheader("📅 Gantt Chart")
    gantt_df = df.rename(columns={
        "Schedule Start Date": "Start",
        "Schedule End Date": "Finish",
        "Schedule Tasks": "Task"
    })
    gantt_df["Start"] = pd.to_datetime(gantt_df["Start"])
    gantt_df["Finish"] = pd.to_datetime(gantt_df["Finish"])
    gantt_df["Resource"] = gantt_df["Schedule Week"]

    fig = px.timeline(gantt_df, x_start="Start", x_end="Finish", y="Task", color="Resource", title="Project Schedule")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

    # ---- Finalize & Send ----
    st.subheader("🚀 Finalize & Send to Zapier")
    submit_final = st.button("Finalize & Send")

    if submit_final:
        # Final JSON payload
        payload = {
            "project_name": project_name,
            "location": location,
            "project_type": project_type,
            "weeks": num_weeks,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "schedule": edited_schedule  # ✅ clean key for Zapier loop
        }

        st.success("✅ Schedule finalized and ready to send!")

        # 🔍 Preview payload for debugging
        st.subheader("Webhook Payload Preview (debug)")
        st.json(payload)

        # 🚀 Send to Zapier
        zapier_webhook_url = st.secrets["zapier_webhook"]
        response = requests.post(zapier_webhook_url, json=payload)

        if response.status_code == 200:
            st.success("✅ Webhook sent to Zapier successfully!")
        else:
            st.error(f"❌ Failed to send to Zapier. Status code: {response.status_code}")










