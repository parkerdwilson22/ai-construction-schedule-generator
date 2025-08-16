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

# Prompt Templates
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
If any task doesn't require materials, return "materials": ["[Add materials]"]
"""
)

chain = LLMChain(llm=llm, prompt=prompt)
materials_chain = LLMChain(llm=llm, prompt=materials_prompt)

# App Title
st.title("AI Construction Schedule Generator")
st.markdown("Generate, preview, and download editable construction schedules tailored by project type.")

# Layout Columns
col1, col2 = st.columns(2)
with col1:
    project_name = st.text_input("Project Name")
    square_footage = st.number_input("Square Footage", min_value=0, step=100)
    project_type = st.selectbox("Project Type", ["Residential", "Renovation"])
with col2:
    location = st.text_input("Project Location")
    stories = st.number_input("Number of Stories", min_value=1, max_value=10, step=1)
    start_date = st.date_input("Project Start Date", min_value=datetime.today())

email = st.text_input("Recipient Email", placeholder="example@email.com")

# Session states
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None
if "materials_data" not in st.session_state:
    st.session_state.materials_data = None
if "estimated_cost" not in st.session_state:
    st.session_state.estimated_cost = None

# Auto duration
DEFAULT_WEEKS = 16 if project_type == "Renovation" else 25

# Generate Schedule Button
if st.button("Generate Schedule"):
    if not project_name or not location or square_footage == 0:
        st.warning("Please fill in all required fields.")
    else:
        progress = st.progress(0)
        progress.text("Initializing...")

        with st.spinner("Generating schedule and materials..."):
            prompt_input = {
                "project_name": project_name,
                "weeks": DEFAULT_WEEKS,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "project_type": project_type
            }
            output = chain.run(prompt_input)
            progress.progress(40)

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

            task_list = [task for item in schedule for task in item["tasks"]]
            materials_output = materials_chain.run({"tasks": "\n".join(task_list)})
            progress.progress(70)

            materials_json = json.loads(materials_output)
            materials_df = pd.DataFrame([
                {"task": item["task"], "materials": "; ".join(item["materials"])}
                for item in materials_json
            ])
            st.session_state.materials_data = materials_df

            cost_per_sqft = 85 if project_type == "Renovation" else 117.5
            total_sqft = square_footage * stories
            estimated_cost = cost_per_sqft * total_sqft
            st.session_state.estimated_cost = estimated_cost

            progress.progress(100)
            st.success("✅ Schedule & Cost estimate generated!")

            st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:10px; border-radius:6px; margin-top:10px;">
                <b>Estimated Build Cost:</b> <span style="font-size:20px;">${estimated_cost:,.2f}</span><br>
                <small><i>(AI generated estimate based on average per sqft. Confirm with a GC.)</i></small>
                </div>
            """, unsafe_allow_html=True)

# Display & Export
if st.session_state.schedule_data is not None:
    st.subheader("📅 Preview & Edit Schedule")
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
        fig = px.timeline(
            edited_df,
            x_start="Start",
            x_end="End",
            y="tasks",
            color="week",
            height=600
        )
        fig.update_yaxes(autorange="reversed", title=None)
        fig.update_layout(margin=dict(l=50, r=50, t=30, b=30))
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("Gantt chart could not be displayed.")

    # Materials Table
    if st.session_state.materials_data is not None:
        st.subheader("🧱 Materials List")
        edited_materials_df = st.data_editor(
            st.session_state.materials_data.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="editable_materials"
        )

        st.download_button(
            "⬇️ Download Materials (CSV)",
            edited_materials_df.to_csv(index=False).encode("utf-8"),
            "materials.csv",
            "text/csv"
        )

    # Schedule Export
    csv = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Schedule (CSV)",
        csv,
        "schedule.csv",
        "text/csv"
    )

    def create_pdf(dataframe, cost_estimate):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)

        # Fix: Only include 1 set of dates
        table_data = [["Week", "Start Date", "End Date", "Tasks"]] + dataframe[["week", "start_date", "end_date", "tasks"]].values.tolist()
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
        cost_paragraph = Paragraph(
            f"<b>Estimated Build Cost:</b> ${cost_estimate:,.2f}<br/><i>(AI generated. Confirm with your GC or estimator.)</i>",
            styles["Normal"]
        )

        elements = [
            Paragraph("<b>AI Construction Schedule (Beta)</b>", styles["Title"]),
            Spacer(1, 12),
            table,
            Spacer(1, 12),
            cost_paragraph
        ]
        doc.build(elements)
        buffer.seek(0)
        return buffer

    pdf_buffer = create_pdf(edited_df, st.session_state.estimated_cost)
    st.download_button(
        "⬇️ Download PDF",
        pdf_buffer,
        file_name="schedule.pdf",
        mime="application/pdf"
    )

    # Send Email Button
    if st.button("📧 Send Email"):
        if not email:
            st.warning("Please enter recipient email.")
        else:
            try:
                msg = EmailMessage()
                msg["Subject"] = "Your AI Construction Schedule"
                msg["From"] = st.secrets["EMAIL_ADDRESS"]
                msg["To"] = email
                msg.set_content("Attached is your AI-generated construction schedule.")
                msg.add_attachment(pdf_buffer.read(), maintype='application', subtype='pdf', filename='schedule.pdf')

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                    smtp.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
                    smtp.send_message(msg)

                st.success("✅ Email sent successfully.")
            except Exception as e:
                st.error(f"❌ Failed to send email: {e}")























