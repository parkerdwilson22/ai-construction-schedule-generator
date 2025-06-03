 🏗️ AI Construction Schedule Generator

This is a Streamlit web application that uses OpenAI's GPT-3.5 Turbo to generate smart, week-by-week construction schedules based on project inputs. The app outputs a detailed construction timeline, displays a Gantt chart, allows CSV download, and sends the schedule via email.

---

## ✨ Features

- **AI-Powered Schedule Generation**: Uses OpenAI's GPT-3.5 Turbo via LangChain to generate detailed construction plans.
- **Streamlit UI**: Clean and responsive web interface for user inputs.
- **Gantt Chart Visualization**: Interactive task timeline with Plotly.
- **CSV Export**: Instantly download the construction schedule in a structured format.
- **Email Integration**: Automatically sends the schedule to a user’s email using Gmail SMTP and app passwords.

---

## 🚀 How It Works

1. **User enters** project name, location, duration (in weeks), and start date.
2. The app **sends this data to OpenAI** which returns a detailed schedule.
3. The output is:
   - Displayed in a readable format
   - Converted into a table using pandas
   - Used to generate a Gantt chart via Plotly
   - Downloadable as a CSV
   - Emailed to the provided address

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Streamlit | Web UI |
| OpenAI API | Schedule generation |
| LangChain | Prompt orchestration |
| Plotly | Gantt chart visualization |
| Pandas | Data handling and CSV export |
| smtplib + Gmail | Email delivery |
| GitHub | Version control |
| Streamlit Cloud | Deployment platform |

---

## 🔒 Secrets Configuration

Create a `.streamlit/secrets.toml` file or add secrets in Streamlit Cloud with:

```toml
OPENAI_API_KEY = "your-openai-key"
EMAIL_ADDRESS = "your-gmail-address"
EMAIL_PASSWORD = "your-app-password"
```

> Ensure you’re using an **App Password** from Gmail, not your actual Gmail password.

---

## 📦 Installation (For Local Development)

1. Clone the repository:
```bash
git clone https://github.com/your-username/ai-construction-schedule-generator.git
cd ai-construction-schedule-generator
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the app:
```bash
streamlit run streamlit_app.py
```

---

## 📍 Live Demo

Check out the live app here: [https://ai-construction-schedule-generator.streamlit.app](https://ai-construction-schedule-generator.streamlit.app)

---

## 📬 Contact

Built by Parker Wilson Connect with me on [LinkedIn]https://www.linkedin.com/in/parkerdwilson/
