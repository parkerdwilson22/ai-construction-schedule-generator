import streamlit as st
from datetime import datetime
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import plotly.express as px
import os
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

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

materials_prompt = PromptTemplate(
    input_variables=["tasks"],
    template="""
For the following construction tasks:
{tasks}
Generate a short materials list for each task in JSON format like this:
[
  {{
    "task": "Excavate site",
    "materials": ["Excavator rental", "Safety barriers", "Dump truck service"]
  }},
  ...
]
"""
)

chain = LLMChain(llm=llm, prompt=prompt)
materials_chain = LLMChain(llm=llm, prompt=materials_prompt)

st.title("\U0001F3D7️ AI Construction Schedule Generator")
st.markdown("Generate, preview, and download editable construction schedules tailored by project type.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
project_type = st.selectbox("Project Type", ["Residential", "Commercial", "Renovation", "Infrastructure"])
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None
if "materials_data" not in st.session_state:
    st.session_state.materials_data = None

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

            # Generate Materials List
            task_list = [task for item in schedule for task in item["tasks"]]
            materials_output = materials_chain.run({"tasks": "\n".join(task_list)})
            materials_json = json.loads(materials_output)

            materials_df = pd.DataFrame([
                {"task": item["task"], "materials": "; ".join(item["materials"])}
                for item in materials_json
            ])
            st.session_state.materials_data = materials_df

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

    # Materials Order Preview Feature
    if st.session_state.materials_data is not None:
        st.subheader("🛠 Materials Order Preview")
        edited_materials_df = st.data_editor(
            st.session_state.materials_data.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="editable_materials"
        )

        # Download Materials CSV
        materials_csv = edited_materials_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Materials List (CSV)",
            materials_csv,
            "materials_list.csv",
            "text/csv"
        )

    # Download CSV
    csv = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Schedule (CSV)",
        csv,
        "schedule.csv",
        "text/csv"
    )

    # Download PDF
    def create_pdf(dataframe):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        table_data = [list(dataframe.columns)] + dataframe.values.tolist()
        table = Table(table_data)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)
        doc.build([table])
        buffer.seek(0)
        return buffer

    pdf_buffer = create_pdf(edited_df)
    st.download_button(
        "📄 Download Schedule (PDF)",
        pdf_buffer,
        file_name="schedule.pdf",
        mime="application/pdf"
    )













