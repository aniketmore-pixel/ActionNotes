Perfect 🙂 Now I have a full picture of **ActionNotes**:

* **ai\_engine.py** → Uses **Gemini AI** to summarize meetings & extract action items.
* **app.py** → Flask-based dashboard + **AssemblyAI** for transcription + CRUD operations for meetings, tasks, and collections.
* **db.py** → SQLite-based schema for users, meetings, tasks, and collections.

With this, I can now create a **professional, polished, and SEO-friendly** `README.md` optimized for GitHub.

---

# **Final README.md for ActionNotes**

```markdown
# 📝 ActionNotes
> AI-powered meeting notes manager — **Summarize meetings**, **extract action items**, and **organize everything** in one place.

[![Flask](https://img.shields.io/badge/Flask-2.3+-blue.svg)](https://flask.palletsprojects.com/)
[![Gemini AI](https://img.shields.io/badge/Google%20Gemini-1.5%20Flash-orange.svg)](https://ai.google/)
[![AssemblyAI](https://img.shields.io/badge/AssemblyAI-Speech%20to%20Text-brightgreen.svg)](https://www.assemblyai.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Overview
**ActionNotes** is an AI-powered **meeting management app** built with **Flask**.  
It allows you to **upload meeting recordings or transcripts** and automatically:

- 🎙️ Converts **audio to text** using **AssemblyAI**.
- 🤖 Generates **concise summaries** with **Google Gemini 1.5 Flash**.
- ✅ Extracts **action items grouped by person**.
- 📂 Organizes everything into **collections** and dashboards.

---

## ✨ Features
- 🔐 **User Authentication** — Register, log in, and manage private meetings.
- 🎙️ **Audio Upload & Transcription** — Upload meeting recordings and get transcripts instantly.
- 🤖 **AI Summaries** — Get **5-point concise summaries** of meetings.
- ✅ **Task Extraction** — Action items are grouped **by person** automatically.
- 📂 **Collections** — Organize meetings into collections for easy navigation.
- 🗄️ **Database-Backed** — Uses **SQLite** for users, meetings, tasks, and collections.
- 🖥️ **Web Dashboard** — Intuitive and responsive interface.

---

## 🛠️ Tech Stack

| **Component**       | **Technology**       |
|---------------------|-----------------------|
| **Backend**        | Flask (Python)        |
| **Frontend**       | HTML, CSS, Jinja2     |
| **Database**       | SQLite               |
| **AI Engine**      | Google Gemini 1.5 Flash |
| **Speech-to-Text** | AssemblyAI            |
| **Authentication** | Werkzeug Password Hashing |
| **Environment**    | Python 3.10+          |

---

## 📂 Project Structure

```

ActionNotes/
│── app.py              # Main Flask app & routes
│── ai\_engine.py        # AI integration with Gemini API
│── db.py               # SQLite schema & DB initialization
│── db\_utils.py         # DB helper functions (optional)
│── templates/          # Jinja2 HTML templates
│── static/             # CSS, JS, and assets
│── models/             # Pre-trained models (if any)
│── meetings.db         # SQLite database (auto-generated)
│── requirements.txt    # Python dependencies
│── .env                # API keys & secrets
└── README.md           # Project documentation

````

---

## ⚡ Installation & Setup

### **1. Clone the Repository**
```bash
git clone https://github.com/aniketmore-pixel/ActionNotes.git
cd ActionNotes
````

### **2. Create a Virtual Environment**

```bash
python -m venv venv
```

Activate it:

* **Windows:** `venv\Scripts\activate`
* **Linux/Mac:** `source venv/bin/activate`

### **3. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **4. Configure Environment Variables**

Create a `.env` file in the root folder:

```env
GEMINI_API_KEY=your_google_gemini_api_key
ASSEMBLYAI_KEY=your_assemblyai_api_key
DB_PATH=meetings.db
SECRET_KEY=your_flask_secret_key
```

### **5. Initialize the Database**

```bash
python -c "from db import init_db; init_db()"
```

### **6. Run the Application**

```bash
python app.py
```

> The app will start on: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 💻 Usage

1. **Sign up / Log in** to create a personal workspace.
2. **Upload audio files** or **paste transcripts**.
3. Wait for:

   * 🎙️ Transcription (**AssemblyAI**)
   * 🧠 AI summaries & tasks (**Gemini**)
4. Organize meetings into **collections**.
5. View, edit, or delete meetings anytime.

---

## 🔑 API Integrations

### **Google Gemini AI**

* Model: **gemini-1.5-flash**
* Task: Generates **summaries** and **action items**.

### **AssemblyAI**

* Task: Transcribes **uploaded meeting recordings**.

---

## 📜 License

This project is licensed under the **MIT License**.
You are free to use, modify, and distribute it.

---

## 🤝 Contributing

Contributions are welcome! 🚀

1. **Fork** the repo.
2. Create a new branch (`feature/my-feature`).
3. Commit changes.
4. Submit a **pull request**.

---

## 📧 Contact

**Author:** Aniket More
🔗 GitHub: [@aniketmore-pixel](https://github.com/aniketmore-pixel)
📩 Email: \[[your-email@example.com](mailto:your-email@example.com)]

---

## 🌟 Screenshots (Optional)

*Add screenshots of the dashboard, upload page, and meeting details here for better presentation.*

---

## ✅ Next Steps for You

* Add a `requirements.txt` file.
* Include a `.env.example` for contributors.
* Add screenshots or a **demo GIF**.
* Deploy on **Render**, **Railway**, or **Vercel** for public access.

---

Do you also want me to **generate a complete `requirements.txt`** for this project based on your code?
It’ll make installation seamless. Should I?
