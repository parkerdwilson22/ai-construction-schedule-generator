import streamlit as st
import pandas as pd
import io
from email.message import EmailMessage
import smtplib
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ----- PAGE CONFIG -----
st.set_page_config(page_title="AI Construction Schedule Generator", layout="wide")

# ----- HEADER -----
st.title("AI Construction Schedule Generator (Beta)")
st.markdown("Easily generate construction schedules and cost estimates using AI. Finalize and share with your team.")

# ----- INPUT FORM -----
with st.form("input_form"):
    project_name = st.text_input("Project Name")
    location = st.text_input("Location")
    square_feet = st.number_input("Project Size (sq. ft.)", min_value=0, step=100)
    schedule_data = st.text_area("Schedule Tasks (one per line)")
    submit = st.form_submit_button("Generate Schedule")

# ----- HELPER FUNCTIONS -----
def calculate_estimated_cost(sq_ft):
    if sq_ft < 500:
        return 0
    new_construction = sq_ft * 120
    return new_construction

def generate_dataframe(raw_text):
    lines = raw_text.strip().split("\n")
    tasks = [line.strip() for line in lines if line.strip()]
    df = pd.DataFrame({"Task": tasks})
    return df

def create_pdf(dataframe, estimated_cost):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI Construction Schedule (Beta)", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Disclaimer: This schedule and cost estimate are AI-generated. Please review and finalize with your team.", styles["Normal"]))
    elements.append(Spacer(1, 12))
    
    if estimated_cost:
        cost_text = f"Estimated Project Cost: ${estimated_cost:,.2f} (Based on $110–$125/sq ft for new builds, $85/sq ft for renovations)"
        elements.append(Paragraph(cost_text, styles["Normal"]))
        elements.append(Spacer(1, 12))

    table_data = [["Task"]]
    for _, row in dataframe.iterrows():
        table_data.append([row["Task"]])
    table = Table(table_data)
    table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,0),12),
        ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ])
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_email_with_pdf(to_email, pdf_buffer):
    msg = EmailMessage()
    msg["Subject"] = "Your AI Construction Schedule (Beta)"
    msg["From"] = st.secrets["EMAIL_ADDRESS"]
    msg["To"] = to_email
    msg.set_content("Attached is your AI-generated construction schedule.")

    msg.add_attachment(pdf_buffer.getvalue(), maintype="application", subtype="pdf", filename="schedule.pdf")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
        smtp.send_message(msg)

# ----- MAIN LOGIC -----
if submit:
    if project_name and square_feet > 0 and schedule_data.strip():
        st.session_state.schedule_data = schedule_data
        st.session_state.estimated_cost = calculate_estimated_cost(square_feet)
        st.session_state.df = generate_dataframe(schedule_data)
    else:
        st.warning("Please fill out all fields to generate your schedule.")

# ----- OUTPUT -----
if st.session_state.get("schedule_data"):
    st.subheader("Schedule Preview")
    edited_df = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic")

    pdf_buffer = create_pdf(edited_df, st.session_state.estimated_cost)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download Schedule (CSV)", edited_df.to_csv(index=False), file_name="schedule.csv", mime="text/csv")
    with col2:
        st.download_button("Download Schedule (PDF)", pdf_buffer, file_name="schedule.pdf", mime="application/pdf")

    if st.session_state.estimated_cost:
        st.markdown(f"### Estimated Cost:\n**${st.session_state.estimated_cost:,.2f}**")
        st.markdown("#### Notes:")
        st.markdown("- **New Construction**: $110–$125 per sq. ft.")
        st.markdown("- **Renovation**: $85 per sq. ft.")
        st.markdown("_Estimates are for informational purposes only and subject to real-world conditions._")

    # Send Email Button (simplified)
    if st.button("Send Schedule to My Email"):
        try:
            send_email_with_pdf(
                to_email=st.secrets["EMAIL_TO"],
                pdf_buffer=pdf_buffer
            )
            st.success("Schedule sent to your email successfully.")
        except Exception as e:
            st.error(f"Failed to send email: {e}")



















