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
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="AI Construction Scheduler", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# PROMPTS
prompt = PromptTemplate(
    input_variables=["project_name", "location", "start_date", "project_type", "square_footage", "stories"],
    template="""
Generate a detailed weekly construction schedule for a {project_type} project called "{project_name}" in {location}, 
starting on {start_date}. The building is {stories} story/stories and approximately {square_footage} square feet.
Include pre-construction tasks like permitting, inspections, and utility setup in the first week only. 
Estimate the number of weeks based on a realistic home building timeline. 
Return the output in this strict JSON format:
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
If any task doesn't require materials, return "materials": ["[Add materials]"]
"""
)

chain = LLMChain(llm=llm, prompt=prompt)
materials_chain = LLMChain(llm=llm, prompt=materials_prompt)

# UI LAYOUT
st.title("AI Construction Schedule Generator")
st.markdown("Generate, preview, and email editable construction schedules tailored by project type.")

col1, col2 = st.columns(2)
with col1:
    project_name = st.text_input("Project Name")
    location = st.text_input("Project Location")
    start_date = st.date_input("Start Date", min_value=datetime.today())

with col2:
    project_type = st.selectbox("Project Type", ["Residential", "Renovation"])
    square_footage = st.number_input("Square Footage", min_value=100, step=100)
    stories = st.number_input("Number of Stories", min_value=1, max_value=5, step=1)

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None
if "materials_data" not in st.session_state:
    st.session_state.materials_data = None
if "estimated_cost" not in st.session_state:
    st.session_state.estimated_cost = None

if st.button("Generate Schedule"):
    if not project_name or not location or square_footage == 0:
        st.warning("Please fill in all required fields.")
    else:
        progress = st.progress(0, text="Generating schedule...")

        prompt_input = {
            "project_name": project_name,
            "location": location,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "project_type": project_type,
            "square_footage": square_footage,
            "stories": stories
        }

        output = chain.run(prompt_input)
        progress.progress(33, text="Parsing schedule...")

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
            progress.progress(66, text="Generating materials...")

            task_list = [task for item in schedule for task in item["tasks"]]
            materials_output = materials_chain.run({"tasks": "\n".join(task_list)})
            materials_json = json.loads(materials_output)
            materials_df = pd.DataFrame([
                {"task": item["task"], "materials": "; ".join(item["materials"])}
                for item in materials_json
            ])
            st.session_state.materials_data = materials_df

            cost_per_sqft = 85 if project_type == "Renovation" else 117
            total_sqft = square_footage * stories
            estimated_cost = total_sqft * cost_per_sqft
            st.session_state.estimated_cost = estimated_cost

            progress.progress(100, text="Done!")
        except Exception as e:
            st.error(f"❌ Failed to parse or display schedule: {e}")

if st.session_state.schedule_data is not None:
    st.success("✅ Schedule generated!")

    st.subheader("📋 Preview & Edit Schedule")
    edited_df = st.data_editor(
        st.session_state.schedule_data.copy(),
        num_rows="dynamic",
        use_container_width=True,
        key="schedule_editor"
    )

    st.subheader("📈 Gantt Chart")
    try:
        edited_df["Start"] = pd.to_datetime(edited_df["start_date"])
        edited_df["End"] = pd.to_datetime(edited_df["end_date"])
        fig = px.timeline(edited_df, x_start="Start", x_end="End", y="tasks", color="week", height=600)
        fig.update_yaxes(autorange="reversed", title=None)
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("Could not generate Gantt chart.")

    if st.session_state.materials_data is not None:
        st.subheader("🧱 Materials List")
        edited_materials_df = st.data_editor(
            st.session_state.materials_data.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="materials_editor"
        )
        st.download_button("Download Materials List (CSV)", edited_materials_df.to_csv(index=False), "materials.csv", "text/csv")

    # CSV
    st.download_button("Download Schedule (CSV)", edited_df.to_csv(index=False), "schedule.csv", "text/csv")

    # PDF Export
    def create_pdf(df, cost_estimate):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        table_data = [["Week", "Start Date", "End Date", "Tasks"]] + df[["week", "start_date", "end_date", "tasks"]].values.tolist()
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

        styles = getSampleStyleSheet()
        elements = [
            Paragraph("<b>AI Construction Schedule (Beta)</b>", styles["Title"]),
            Spacer(1, 12),
            table,
            Spacer(1, 12),
            Paragraph(f"<b>Estimated Build Cost:</b> ${cost_estimate:,.2f}<br/><i>(AI generated. Confirm with your GC or estimator.)</i>", styles["Normal"])
        ]
        doc.build(elements)
        buffer.seek(0)
        return buffer

    pdf_buffer = create_pdf(edited_df, st.session_state.estimated_cost)
    st.download_button("Download Schedule (PDF)", pdf_buffer, "schedule.pdf", "application/pdf")

    # Email Section
    st.subheader("📤 Email PDF")
    email = st.text_input("Recipient Email")
    subject = st.text_input("Subject", "Your AI Construction Schedule")
    message = st.text_area("Message", "Attached is your AI-generated construction schedule.")
    if st.button("Send Email"):
        try:
            def send_email_with_pdf(to_email, subject, body, pdf_buffer):
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = st.secrets["EMAIL_ADDRESS"]
                msg["To"] = to_email
                msg.set_content(body)
                msg.add_attachment(pdf_buffer.read(), maintype="application", subtype="pdf", filename="schedule.pdf")
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                    smtp.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                    smtp.send_message(msg)
            send_email_with_pdf(email, subject, message, pdf_buffer)
            st.success("✅ Email sent successfully.")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")






















