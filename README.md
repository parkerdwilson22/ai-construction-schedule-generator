# 🏗️ AI Construction Schedule Generator

This is a no-code-friendly AI-powered web app that lets users generate detailed, week-by-week construction schedules using OpenAI. It includes a downloadable CSV file, an interactive Gantt chart, and automatic email delivery — all from a simple user interface.

> ✅ Built by someone with no prior tech experience using GenAI tools like OpenAI, LangChain, and Streamlit.

---

## 🚀 Features

- Collects project name, location, start date, and duration
- Uses GPT-3.5 via LangChain to generate a structured JSON construction schedule
- Parses and visualizes the output as an interactive Gantt chart using Plotly
- Lets users download the schedule as a CSV file
- Sends the full schedule to any email via Gmail SMTP
- Hosted live on Streamlit Cloud

---

## 🧠 Tech Stack & Tools

| Tool               | Purpose                                           |
|--------------------|---------------------------------------------------|
| **Streamlit**      | For building and hosting the UI                   |
| **OpenAI GPT-3.5** | For generating the schedule                       |
| **LangChain**      | For structured prompting and response parsing     |
| **Pandas**         | For data processing                               |
| **Plotly**         | For Gantt chart visualization                     |
| **SMTP (Gmail)**   | For sending the schedule via email                |
| **Git & GitHub**   | For version control and cloud deployment          |
| **VS Code**        | For local development                             |
| **Streamlit Secrets** | For securely storing keys and passwords      |

---

## 📦 Setup Instructions

1. **Clone this repo**
git clone https://github.com/parkerdwilson22/ai-construction-schedule-generator.git
cd ai-construction-schedule-generator


2. **Install dependencies**


3. **Set up secrets**

Create a file at `.streamlit/secrets.toml` and add:

OPENAI_API_KEY = "your-openai-api-key"
EMAIL_ADDRESS = "your-gmail-address"
EMAIL_PASSWORD = "your-app-password"


(Use an [App Password](https://myaccount.google.com/apppasswords) for Gmail.)

4. **Run locally**

treamlit run streamlit_app.py

5. **Deploy to Streamlit Cloud**
- Push to GitHub
- Go to [https://streamlit.io/cloud](https://streamlit.io/cloud)
- Connect your repo and deploy

---

## 🎯 How It Works

1. You enter the project details in the app.
2. LangChain formats a prompt using your input and sends it to OpenAI.
3. OpenAI responds with structured JSON for a week-by-week construction timeline.
4. The app parses the JSON into a DataFrame, shows a Gantt chart, and offers a CSV download.
5. Your construction schedule is also emailed to you automatically.

---

## ✅ Live Links

- 🔗 **Live App**: [ai-construction-schedule-generator.streamlit.app](https://ai-construction-schedule-generator.streamlit.app)
- 💻 **GitHub Repo**: [github.com/parkerdwilson22/ai-construction-schedule-generator](https://github.com/parkerdwilson22/ai-construction-schedule-generator)
- 📹 **Demo Video**: [Loom link coming soon]
- 🧠 **Portfolio Page**: [Notion link coming soon]

---

## 🙌 A Note From the Creator

I built this without any formal coding background — just GenAI tools, a laptop, and curiosity. If you're a recruiter or hiring manager looking for someone who can solve problems, create products, and move fast using AI, I’d love to connect.

---

## 📫 Contact

**Parker Wilson**  
[LinkedIn] https://www.linkedin.com/in/parkerdwilson/

[Email](mailto:parkerdwilson@gmail.com)

