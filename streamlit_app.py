import smtplib
from email.message import EmailMessage
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

# Basic config
st.set_page_config(page_title="AI Construction Scheduler", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# Prompt for Schedule
schedule_prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date", "project_type", "square_feet", "num_stories"],
    template="""
You're an assistant helping a small-scale residential or renovation developer. Generate a detailed schedule for a {project_type} project called "{project_name}" in {location}, lasting {weeks} weeks, starting on {start_date}.

The project is approximately {square_feet} sq ft and has {num_stories} stories.

Only generate {weeks} weeks worth of schedule.

Include:
- Pre-construction in Week 1 (permitting, utility setup, inspections).
- Clearly organized weekly tasks.
- Don't repeat tasks across weeks.

Return strict JSON format:
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

# Prompt for Materials
materials_prompt = PromptTemplate(
    input_variables=["tasks"],
    template="""
For the following residential or renovation construction tasks:
{tasks}
Generate a materials list for each task. Return strict JSON:
[
  {{
    "task": "Excavate site",
    "materials": ["Excavator rental", "Safety barriers", "Dump truck service"]
  }},
  ...
]
"""
)

schedule_chain = LLMChain(llm=llm, prompt=schedule_prompt)
materials_chain = LLMChain(llm=llm, prompt=materials_prompt)

# UI Input
st.title("AI Construction Schedule Generator")
st.markdown("Generate and preview residential or renovation construction schedules.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
project_type = st.selectbox("Project Type", ["Residential", "Renovation"])
square_feet = st.number_input("Square Footage", min_value=100)
num_stories = st.number_input("Number of Stories", min_value=1)
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None
if "materials_data" not in st.session_state:
    st.session_state.materials_data = None

# Trigger Generator
if st.button("Generate Schedule"):
    if not project_name or not location:
        st.warning("Please fill in all required fields.")
    else:
        with st.spinner("Generating schedule..."):
            inputs = {
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "project_type": project_type,
                "square_feet": square_feet,
                "num_stories": num_stories,
            }
            output = schedule_chain.run(inputs)

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

            # Estimate cost
            if project_type == "Residential":
                cost_estimate = square_feet * 175
            else:  # Renovation
                cost_estimate = square_feet * 120

            st.session_state.estimated_cost = cost_estimate

            # Materials
            task_list = [task for item in schedule for task in item["tasks"]]
            materials_output = materials_chain.run({"tasks": "\n".join(task_list)})
            materials_json = json.loads(materials_output)

            materials_df = pd.DataFrame([
                {"task": item["task"], "materials": "; ".join(item["materials"]) if item["materials"] else "[Add materials]"}
                for item in materials_json
            ])
            st.session_state.materials_data = materials_df

        except Exception as e:
            st.error(f"Failed to parse schedule: {e}")

# Display
if st.session_state.schedule_data is not None:
    st.success("Schedule successfully generated!")

    st.subheader("Preview & Edit Schedule")
    edited_df = st.data_editor(
        st.session_state.schedule_data.copy(),
        num_rows="dynamic",
        use_container_width=True,
        key="editable_table"
    )

    st.subheader("Gantt Chart")
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
        st.warning("Could not generate Gantt chart.")

    st.subheader("Materials Order Preview")
    if st.session_state.materials_data is not None:
        edited_materials_df = st.data_editor(
            st.session_state.materials_data.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="editable_materials"
        )
        materials_csv = edited_materials_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Materials List (CSV)", materials_csv, "materials_list.csv", "text/csv")

    st.subheader("Estimated Build Cost")
    st.write(f"**Estimated Cost:** ${st.session_state.estimated_cost:,.2f}")
    st.caption("This is an AI-generated rough estimate. Please confirm with your contractor.")

    # CSV Export
    csv = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Schedule (CSV)", csv, "schedule.csv", "text/csv")

    # PDF Export
    def create_pdf(dataframe, cost_estimate):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph("AI Construction Schedule (Beta)", styles['Title']))
        elements.append(Spacer(1, 12))

        # Table
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
        elements.append(table)

        # Estimated Cost
        elements.append(Spacer(1, 12))
        cost_paragraph = Paragraph(
            f"Estimated Build Cost: ${cost_estimate:,.2f} <br/><i>(AI generated. Confirm with your GC or estimator.)</i>",
            styles["Normal"]
        )
        elements.append(cost_paragraph)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    pdf_buffer = create_pdf(edited_df, st.session_state.estimated_cost)
    st.download_button("Download Schedule (PDF)", pdf_buffer, file_name="schedule.pdf", mime="application/pdf")

      with st.form("email_form"):
        email = st.text_input("Recipient Email")
        subject = st.text_input("Subject", value="Your AI Construction Schedule")
        message = st.text_area("Message", value="Attached is your AI-generated construction schedule.")
        send = st.form_submit_button("Send Email")

        if send:
            try:
                send_email(email, subject, message, pdf_buffer)
                st.success("✅ Email sent successfully.")
            except Exception as e:
                st.error(f"❌ Failed to send email: {e}")




def send_email_with_pdf(to_email, pdf_buffer):
    msg = EmailMessage()
    msg["Subject"] = "Your AI Construction Schedule (Beta)"
    msg["From"] = st.secrets["EMAIL_ADDRESS"]
    msg["To"] = to_email
    msg.set_content("Attached is your AI-generated construction schedule.\n\nThis is a beta feature. Please verify with your team before use.")

    # Attach PDF
    msg.add_attachment(pdf_buffer.read(), maintype="application", subtype="pdf", filename="schedule.pdf")

    # Send
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
        smtp.send_message(msg)

















