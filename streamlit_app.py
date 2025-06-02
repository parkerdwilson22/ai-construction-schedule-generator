import streamlit as st
from datetime import datetime
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os

# Your API key
import streamlit as st
import os

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]


llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)

# Prompt template
prompt = PromptTemplate(
    input_variables=["project_name", "weeks", "location", "start_date"],
    template="""
Generate a week-by-week construction schedule for a project called 
"{project_name}" in {location}, lasting {weeks} weeks, starting on 
{start_date}. 
Make the schedule very detailed. Each week's task must include specific 
work, dependencies if any, and realistic sequencing.
Also include the corresponding calendar dates for each week.
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

# Streamlit UI
st.title("Construction Schedule Generator")

project_name = st.text_input("Project Name")
location = st.text_input("Project Location")
weeks = st.number_input("Project Duration (in weeks)", min_value=1, 
max_value=100, step=1)
start_date = st.date_input("Project Start Date", 
min_value=datetime.today())

if st.button("Generate Schedule"):
    if not project_name or not location or not start_date:
        st.warning("Please fill in all fields.")
    else:
        output = chain.run({
            "project_name": project_name,
            "weeks": weeks,
            "location": location,
            "start_date": start_date.strftime("%Y-%m-%d")
        })
        st.text_area("Generated Construction Schedule", output, 
height=400)
