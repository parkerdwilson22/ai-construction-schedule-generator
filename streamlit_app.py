import streamlit as st
from datetime import datetime, timedelta
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

# ----------------------------
# App Config & Keys
# ----------------------------
st.set_page_config(page_title="AI Construction Schedule Generator", layout="centered")
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# ----------------------------
# LLM Setup (LangChain)
# ----------------------------
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.4)

schedule_prompt = PromptTemplate(
    input_variables=[
        "project_name", "weeks", "location", "start_date",
        "project_type", "square_footage", "stories",
        "cost_low", "cost_high"
    ],
    template="""
You are scheduling a {project_type} construction project called "{project_name}" in {location}.
The project lasts exactly {weeks} weeks, starting on {start_date}.

Audience: younger residential developers and small renovation builders.
Scope focus: Residential + Renovation only. Avoid commercial/infrastructure scope and terms.

Constraints & style:
- Return STRICT JSON ONLY (no prose), shaped as:
[
  {{ "week": 1, "tasks": ["...","..."] }},
  {{ "week": 2, "tasks": ["...","..."] }},
  ...
  {{ "week": {weeks}, "tasks": ["...","..."] }}
]
- Must include ALL weeks from 1..{weeks} (no missing weeks).
- Keep tasks practical and descriptive for field use.
- Include pre-construction items (permits, utility setup) in week 1 only; do not repeat later.
- Balance trades (framing, MEP rough-ins, inspections, drywall, finishes, punch).
- Use budget-aware sequencing: assume estimated build cost range is ${cost_low}–${cost_high} total
  (based on ~{square_footage} sq ft × {stories} stories).
- Consider lead times in task names when relevant (e.g., "Order windows (6–8 week lead)").

Return ONLY the JSON array. Do not include date ranges (the app will compute dates).
"""
)

materials_prompt = PromptTemplate(
    input_variables=["tasks"],
    template="""
You will receive a list of residential/renovation construction tasks. For EACH task,
return a concise materials list suitable for a "materials order preview".

Return STRICT JSON ONLY, shaped as:
[
  {{ "task": "Task name here", "materials": ["Item A", "Item B", "Item C"] }},
  ...
]

Tasks:
{tasks}
"""
)

schedule_chain = LLMChain(llm=llm, prompt=schedule_prompt)
materials_chain = LLMChain(llm=llm, prompt=materials_prompt)

# ----------------------------
# Cost Estimation (no region multipliers)
# ----------------------------
def estimate_cost(square_footage, stories, project_type):
    multipliers = {
        "Residential": (140, 300),   # USD per sq ft (new build)
        "Renovation": (80, 150)      # USD per sq ft (mid-range flip/rehab)
    }
    low, high = multipliers[project_type]
    total_sq_ft = square_footage * stories
    return int(total_sq_ft * low), int(total_sq_ft * high)

# ----------------------------
# Materials Fallback Logic
# ----------------------------
def materials_fallback_from_tasks(task_list):
    """Rule-based mapping so preview never comes back empty."""
    rows = []
    for t in task_list:
        tl = (t or "").lower()
        if any(k in tl for k in ["excav", "grading", "site prep"]):
            mats = ["Excavator rental", "Dump fees", "Safety fencing"]
        elif any(k in tl for k in ["foundation", "footing", "slab", "concrete"]):
            mats = ["Concrete", "Rebar", "Vapor barrier", "Formwork"]
        elif "framing" in tl:
            mats = ["Lumber", "Joist hangers", "Nails"]
        elif any(k in tl for k in ["roof", "shingle"]):
            mats = ["Shingles", "Felt", "Flashing", "Drip edge"]
        elif any(k in tl for k in ["window", "door"]):
            mats = ["Windows/doors", "Shims", "Foam", "Flashing tape"]
        elif any(k in tl for k in ["plumb", "hvac", "electrical", "mech"]):
            mats = ["Rough-in fixtures", "Conduit/pipe", "Wire/duct"]
        elif "drywall" in tl:
            mats = ["Drywall sheets", "Joint compound", "Tape"]
        elif any(k in tl for k in ["tile", "floor"]):
            mats = ["Tile/wood/laminate", "Mortar/underlayment", "Trim pieces"]
        elif "paint" in tl:
            mats = ["Primer", "Interior paint", "Brushes/rollers"]
        elif any(k in tl for k in ["cabinet", "counter"]):
            mats = ["Cabinets", "Countertops", "Hardware"]
        elif any(k in tl for k in ["fixture", "finish"]):
            mats = ["Lighting fixtures", "Plumbing trim", "Switch/cover plates"]
        else:
            mats = ["General building materials"]
        rows.append({"task": t, "materials": "; ".join(mats)})
    return pd.DataFrame(rows)

# ----------------------------
# PDF Export
# ----------------------------
def create_pdf(schedule_df, project_name, location, project_type, sf, stories, est_cost_range):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    title = Paragraph(f"<b>Construction Schedule: {project_name}</b>", styles["Title"])
    meta = Paragraph(
        f"<b>Project Type:</b> {project_type} &nbsp; | &nbsp; "
        f"<b>Location:</b> {location} &nbsp; | &nbsp; "
        f"<b>Size:</b> {sf:,} sq ft × {stories} story(ies)",
        styles["Normal"]
    )

    elements = [title, Spacer(1, 8), meta, Spacer(1, 12)]

    # Estimated cost block
    if est_cost_range:
        low, high = est_cost_range
        cost_tbl = Table(
            [["Estimated Build Cost (AI rough range)", f"${low:,.0f} – ${high:,.0f}"]],
            style=[
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ],
            hAlign="CENTER"
        )
        elements += [cost_tbl, Spacer(1, 12)]

    # Schedule table
    sched_cols = ["week", "start_date", "end_date", "tasks"]
    tbl_data = [sched_cols] + schedule_df[sched_cols].astype(str).values.tolist()

    schedule_table = Table(tbl_data, repeatRows=1)
    schedule_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements += [schedule_table, Spacer(1, 12)]

    disclaimer = Paragraph(
        "<font color='red'><i>Disclaimer:</i> This schedule and cost range are AI-generated rough guidance. "
        "They do not constitute a bid or contract. Verify all dates, quantities, and costs with your team and vendors.</font>",
        styles["Italic"]
    )
    elements.append(disclaimer)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ----------------------------
# UI
# ----------------------------
st.title("🏗️ AI Construction Schedule Generator")
st.markdown("For **Residential** and **Renovation** projects. Generate a schedule, preview materials, and download CSV/PDF.")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
project_type = st.selectbox("Project Type", ["Residential", "Renovation"])
weeks = st.number_input("Project Duration (weeks)", min_value=1, max_value=100, step=1)
start_date = st.date_input("Project Start Date", min_value=datetime.today())

# Cost inputs
square_footage = st.number_input("Total Square Footage", min_value=100, max_value=20000, step=50)
stories = st.number_input("Number of Stories", min_value=1, max_value=5, step=1)

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = None
if "materials_data" not in st.session_state:
    st.session_state.materials_data = None

# ----------------------------
# Generate Schedule
# ----------------------------
if st.button("Generate Schedule"):
    if not project_name or not location:
        st.warning("⚠️ Please fill in all required fields.")
    else:
        cost_low, cost_high = estimate_cost(square_footage, stories, project_type)

        with st.spinner("Generating schedule..."):
            llm_input = {
                "project_name": project_name,
                "weeks": weeks,
                "location": location,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "project_type": project_type,
                "square_footage": square_footage,
                "stories": stories,
                "cost_low": cost_low,
                "cost_high": cost_high
            }
            raw = schedule_chain.run(llm_input)

        try:
            # Expect list of {"week": int, "tasks": [..]}
            weeks_json = json.loads(raw)

            # Build DataFrame with exact weeks + computed dates
            rows = []
            for i in range(1, int(weeks) + 1):
                wk_entry = next((w for w in weeks_json if int(w.get("week", -1)) == i), {"tasks": []})
                wk_start = start_date + timedelta(weeks=i - 1)
                wk_end = wk_start + timedelta(days=6)
                rows.append({
                    "week": i,
                    "start_date": wk_start.strftime("%Y-%m-%d"),
                    "end_date": wk_end.strftime("%Y-%m-%d"),
                    "tasks": "; ".join(wk_entry.get("tasks", []))
                })

            df = pd.DataFrame(rows)
            st.session_state.schedule_data = df

            # Materials preview (LLM first, then fallback)
            all_tasks = []
            for entry in weeks_json:
                all_tasks.extend(entry.get("tasks", []))

            materials_df = pd.DataFrame(columns=["task", "materials"])
            if all_tasks:
                try:
                    materials_raw = materials_chain.run({"tasks": "\n".join(all_tasks)})
                    materials_json = json.loads(materials_raw)
                    materials_df = pd.DataFrame([
                        {"task": item.get("task", ""), "materials": "; ".join(item.get("materials", []))}
                        for item in materials_json
                    ])
                except Exception:
                    materials_df = materials_fallback_from_tasks(all_tasks)
            else:
                # No tasks from LLM? Fallback from the schedule dataframe
                flat_tasks = []
                for t in df["tasks"].tolist():
                    flat_tasks.extend([s.strip() for s in (t or "").split(";") if s.strip()])
                materials_df = materials_fallback_from_tasks(flat_tasks)

            st.session_state.materials_data = materials_df

        except Exception as e:
            st.error(f"❌ Failed to parse or display schedule: {e}")

# ----------------------------
# After Generation: UI Sections
# ----------------------------
if st.session_state.schedule_data is not None:
    df = st.session_state.schedule_data

    st.success("✅ Schedule successfully generated!")

    # Show cost estimate + disclaimers
    c_low, c_high = estimate_cost(square_footage, stories, project_type)
    st.markdown(f"💰 **Estimated Build Cost:** ${c_low:,.0f} – ${c_high:,.0f} USD")
    st.caption("AI-generated rough estimate. Not a bid or contract. Verify with suppliers and subcontractors.")

    # Editable schedule table
    st.subheader("✏️ Preview & Edit Schedule")
    edited_df = st.data_editor(
        df.copy(),
        num_rows="dynamic",
        use_container_width=True,
        key="editable_table"
    )

    # Gantt Chart
    st.subheader("📊 Gantt Chart")
    try:
        gantt_df = edited_df.copy()
        gantt_df['Start'] = pd.to_datetime(gantt_df['start_date'], errors='coerce')
        gantt_df['End'] = pd.to_datetime(gantt_df['end_date'], errors='coerce')
        gantt_fig = px.timeline(
            gantt_df,
            x_start="Start",
            x_end="End",
            y="tasks",
            color="week",
            height=600
        )
        gantt_fig.update_yaxes(autorange="reversed", title=None)
        gantt_fig.update_layout(margin=dict(l=50, r=50, t=30, b=30))
        st.plotly_chart(gantt_fig, use_container_width=True)
    except Exception:
        st.warning("⚠️ Could not generate Gantt chart. Check date formatting.")

    # Materials Order Preview (guaranteed to show with fallback)
    st.subheader("🛠 Materials Order Preview")
    if st.session_state.materials_data is not None and not st.session_state.materials_data.empty:
        edited_materials_df = st.data_editor(
            st.session_state.materials_data.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="editable_materials"
        )
        # Materials CSV
        materials_csv = edited_materials_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Materials List (CSV)",
            materials_csv,
            "materials_list.csv",
            "text/csv"
        )
    else:
        st.info("No materials suggested yet. Add tasks above and regenerate to see a preview.")

    # Schedule CSV
    csv = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Schedule (CSV)",
        csv,
        "schedule.csv",
        "text/csv"
    )

    # PDF Download (with cost & disclaimer)
    pdf_buffer = create_pdf(
        edited_df,
        project_name=project_name,
        location=location,
        project_type=project_type,
        sf=square_footage,
        stories=stories,
        est_cost_range=(c_low, c_high)
    )
    st.download_button(
        "📄 Download Schedule (PDF)",
        pdf_buffer,
        file_name="schedule.pdf",
        mime="application/pdf"
    )














