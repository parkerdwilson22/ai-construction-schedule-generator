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
    input_variables=["project_name", "weeks", "location", "start_date", "precon_instructions"],
    template="""
Generate a detailed construction schedule for a project called "{project_name}" in {location}, lasting {weeks} weeks, starting on {start_date}.
{precon_instructions}
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
st.markdown("Generate, preview, and email editable construction schedules with optional permitting steps.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())
include_precon = st.checkbox("✅ Include permitting/inspection tasks?")
email_address = st.text_input("Recipient Email (Optional – used only when sending email)")

if st.button("Generate Schedule"):
    if not project_name or not location:
        st.warning("⚠️ Please fill in all required fields.")
    else:
        with st.spinner("Generating schedule..."):
            precon_note = (
                "Include pre-construction steps such as permitting, inspections, and utility setup."
                if include_precon else ""
            )
            prompt_input = {
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "precon_instructions": precon_note
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

            if include_precon:
                precon_tasks = {
                    "week": 1,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": (start_date + timedelta(days=6)).strftime("%Y-%m-%d"),
                    "tasks": "Apply for permits; Schedule utility setup; Call city inspector"
                }
                df.loc[-1] = precon_tasks
                df.index = df.index + 1
                df.sort_index(inplace=True)

            df["week"] = list(range(1, len(df) + 1))

            st.success("✅ Schedule successfully generated!")

            st.subheader("✏️ Preview & Edit Schedule")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editable_table")

            st.subheader("📊 Gantt Chart")
            try:
                edited_df['Start'] = pd.to_datetime(edited_df['start_date'], errors='coerce')
                edited_df['End'] = pd.to_datetime(edited_df['end_date'], errors='coerce')
                gantt_fig = px.timeline(edited_df, x_start="Start", x_end="End", y="tasks", color="week")
                gantt_fig.update_yaxes(autorange="reversed")
                st.plotly_chart(gantt_fig, use_container_width=True)
            except Exception as e:
                st.warning("⚠️ Could not generate Gantt chart. Check date formatting.")

            csv_data = edited_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv_data, "schedule.csv", "text/csv")

            st.subheader("📧 Send Schedule by Email")
            if st.button("Send Email"):
                if not email_address:
                    st.warning("⚠️ Please enter an email address above.")
                else:
                    email_body = f"Here is your edited schedule for '{project_name}':\n\n{edited_df.to_string(index=False)}"
                    msg = MIMEText(email_body)
                    msg["Subject"] = f"Construction Schedule for {project_name}"
                    msg["From"] = st.secrets["EMAIL_ADDRESS"]
                    msg["To"] = email_address

                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                        server.send_message(msg)

                    st.success("📨 Email sent successfully!")

        except Exception as e:
            st.error(f"❌ Failed to parse or display schedule: {e}")
