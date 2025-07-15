import streamlit as st
from datetime import datetime
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import plotly.express as px
import os
import json
import requests  # For Zapier webhook

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

st.title("\U0001F3D7️ AI Construction Schedule Generator")
st.markdown("Generate, preview, and send editable construction schedules tailored by project type.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
project_type = st.selectbox("Project Type", ["Residential", "Commercial", "Renovation", "Infrastructure"])
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())

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
    edited_df = st.data_editor(
        st.session_state.schedule_data.copy(),
        num_rows="dynamic",
        use_container_width=True,
        key="editable_table"
    )

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

    st.subheader("\U0001F680 Finalize & Send")
    if st.button("\U0001F680 Finalize & Send"):
        try:
            df_for_zapier = edited_df.copy()
            for col in ["start_date", "end_date", "Start", "End"]:
                if col in df_for_zapier.columns:
                    df_for_zapier[col] = df_for_zapier[col].astype(str)

            schedule_payload = df_for_zapier.to_dict(orient="records")

            requests.post(
                st.secrets["ZAPIER_WEBHOOK_URL"],
                json={
                    "project_name": project_name,
                    "location": location,
                    "project_type": project_type,
                    "weeks": weeks,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "schedule": schedule_payload  # ✅ <== KEY FIX
                }
            )
            st.success("✅ Schedule sent to Zapier!")

        except Exception as e:
            st.error(f"❌ Error sending to Zapier: {e}")











