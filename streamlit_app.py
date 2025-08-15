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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="AI Construction Scheduler (Beta)", layout="wide")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# Inject light styling
def set_styles():
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stDownloadButton button {
            background-color: #2E86AB;
            color: white;
            font-weight: 500;
        }
        .stButton button {
            background-color: #2E86AB;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)

set_styles()

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date", "project_type", "square_footage", "stories"],
    template="""
Generate a detailed construction schedule for a {project_type} project called "{project_name}" in {location}, lasting {weeks} weeks, starting on {start_date}. This project is {square_footage} sqft with {stories} stories.

Assume typical construction workflows for {project_type.lower()} developers. Include pre-construction tasks like permitting and inspections early. Return JSON format like:
[
  {{
    "week": 1,
    "date_range": "2025-06-01 to 2025-06-07",
    "tasks": ["Excavate site", "Stake layout"]
  }},
  ...
]

Also provide a rough build cost estimate using ${"70" if project_type == "Renovation" else "140"}–${"70" if project_type == "Renovation" else "300"} per sqft range.
Return only JSON.
"""
)

materials_prompt = PromptTemplate(
    input_variables=["tasks"],
    template="""
For the following construction tasks:
{tasks}
Generate a materials list in JSON format:
[
  {{
    "task": "Excavate site",
    "materials": ["Excavator rental", "Safety fencing"]
  }},
  ...
] — leave materials as '[Add materials]' if unclear.
"""
)

chain = LLMChain(llm=llm, prompt=prompt)
materials_chain = LLMChain(llm=llm, prompt=materials_prompt)

st.title("AI Construction Scheduler (Beta)")
st.markdown("Designed for residential and renovation developers. Quickly generate build schedules, cost estimates, and material previews.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
project_type = st.selectbox("Project Type", ["Residential", "Renovation"])
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=52)
square_footage = st.number_input("Estimated Square Footage", min_value=200)
stories = st.number_input("Number of Stories", min_value=1, max_value=4)
start_date = st.date_input("Start Date", min_value=datetime.today())

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None
if "materials_data" not in st.session_state:
    st.session_state.materials_data = None

if st.button("Generate Schedule"):
    if not project_name or not location:
        st.warning("Please fill in all required fields.")
    else:
        with st.spinner("Generating schedule and cost estimate..."):
            inputs = {
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "project_type": project_type,
                "square_footage": square_footage,
                "stories": stories
            }
            output = chain.run(inputs)

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

            # Materials
            task_list = [task for item in schedule for task in item["tasks"]]
            materials_output = materials_chain.run({"tasks": "\n".join(task_list)})
            materials_json = json.loads(materials_output)

            materials_df = pd.DataFrame([
                {
                    "task": item["task"],
                    "materials": "; ".join(item.get("materials") or ["[Add materials]"])
                }
                for item in materials_json
            ])
            st.session_state.materials_data = materials_df

        except Exception as e:
            st.error(f"Failed to parse: {e}")

if st.session_state.schedule_data is not None:
    st.subheader("Schedule Preview")
    edited_df = st.data_editor(st.session_state.schedule_data, num_rows="dynamic")

    st.subheader("Gantt Chart")
    try:
        edited_df["Start"] = pd.to_datetime(edited_df["start_date"], errors="coerce")
        edited_df["End"] = pd.to_datetime(edited_df["end_date"], errors="coerce")
        fig = px.timeline(edited_df, x_start="Start", x_end="End", y="tasks", color="week")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("Couldn't render chart.")

    # Materials
    if st.session_state.materials_data is not None:
        st.subheader("Materials Order Preview")
        st.data_editor(st.session_state.materials_data, num_rows="dynamic")
        mat_csv = st.session_state.materials_data.to_csv(index=False).encode("utf-8")
        st.download_button("Download Materials CSV", mat_csv, "materials_list.csv")

    # Download schedule CSV
    csv = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Schedule CSV", csv, "schedule.csv")

    # PDF Export
    def create_pdf(dataframe):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        table_data = [list(dataframe.columns)] + dataframe.values.tolist()
        table = Table(table_data)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("\u2B1B AI-generated schedule. Please confirm with your contractor.", styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    pdf_buffer = create_pdf(edited_df)
    st.download_button("Download PDF", pdf_buffer, "schedule.pdf", mime="application/pdf")

















