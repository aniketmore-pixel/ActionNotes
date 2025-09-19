from flask import Flask, request, flash, jsonify, render_template, session, redirect, url_for, make_response
import sqlitecloud
from sqlitecloud.exceptions import SQLiteCloudIntegrityError
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import sqlite3
from db import init_db
from ai_engine import process_transcript
from werkzeug.security import generate_password_hash, check_password_hash
from types import SimpleNamespace
import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# ---------------- App Setup ----------------
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")

load_dotenv()
ASSEMBLYAI_KEY = os.environ.get("ASSEMBLYAI_KEY")
DB_PATH = os.environ.get(
    "DB_PATH",
    "sqlitecloud://cekbo8acnk.g2.sqlite.cloud:8860/actionnotes.sqlite3?apikey=YPrFryodsBthblXh4RpZhyHeuRoCcVBiIjnRUCVUmaQ"
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------- Helper Functions ----------------
def get_conn():
    conn = sqlitecloud.connect(DB_PATH)
    # Custom row factory for sqlitecloud compatibility
    conn.row_factory = lambda cursor, row: {col[0]: row[i] for i, col in enumerate(cursor.description)}
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ---------------- Upload Audio ----------------
@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No file uploaded"}), 400

    headers = {"authorization": ASSEMBLYAI_KEY}
    response = requests.post("https://api.assemblyai.com/v2/upload", files={"file": audio_file}, headers=headers)
    audio_url = response.json()["upload_url"]

    transcript_request = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={"audio_url": audio_url},
        headers=headers
    )
    transcript_id = transcript_request.json()["id"]

    while True:
        check = requests.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers)
        status = check.json()["status"]
        if status == "completed":
            return jsonify({"transcript": check.json()["text"]})
        elif status == "failed":
            return jsonify({"error": "Transcription failed"}), 500

# ---------------- Home / Dashboard ----------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, date, summary, collection_id FROM meetings WHERE user_id = ?", 
        (session["user_id"],)
    )
    meetings = cursor.fetchall()
    cursor.execute("SELECT id, name FROM collections WHERE user_id = ?", (session["user_id"],))
    collections = cursor.fetchall()
    conn.close()
    return render_template("index.html", meetings=meetings, collections=collections)



# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#         username = request.form["username"]
#         password = generate_password_hash(request.form["password"])
#         conn = get_conn()
#         cursor = conn.cursor()
#         try:
#             cursor.execute(
#                 "INSERT INTO users (username, password) VALUES (?, ?)", 
#                 (username, password)
#             )
#             conn.commit()
#         except sqlite3.IntegrityError:
#             return "Username exists!"
#         finally:
#             conn.close()
#         return redirect(url_for("login"))
#     return render_template("register.html")
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)", 
                (username, password)
            )
            conn.commit()
            # For AJAX requests, return a success response instead of redirecting
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return '', 200  # Return empty 200 OK response
            else:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for("login"))
        except SQLiteCloudIntegrityError:  # Changed from sqlite3.IntegrityError
            # For AJAX requests, return an error response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return 'Username exists!', 409  # Return 409 Conflict status
            else:
                flash('Username already exists! Please try a different one.', 'error')
                return render_template("register.html")
        finally:
            conn.close()
    
    # For GET requests, render the template normally
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if not row:
            # User not found
            return redirect(url_for("login", error="User does not exist. Please register first."))
        
        if not check_password_hash(row["password"], password):
            # Wrong password
            return redirect(url_for("login", error="Incorrect password. Please try again."))

        # Success → create session
        session["user_id"] = row["id"]
        session["username"] = username
        return redirect(url_for("home"))

    # GET → render template
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("login"))

# ---------------- Upload Meeting ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form["title"]
    date = request.form["date"]
    transcript = request.form["transcript"]
    summary, tasks = process_transcript(transcript)

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO meetings (title, date, transcript, summary, user_id) VALUES (?, ?, ?, ?, ?)",
        (title, date, transcript, summary, session["user_id"])
    )
    meeting_id = cursor.lastrowid

    for person, person_tasks in tasks.items():
        for task in person_tasks:
            cursor.execute(
                "INSERT INTO tasks (meeting_id, person, task) VALUES (?, ?, ?)",
                (meeting_id, person, task)
            )

    conn.commit()
    conn.close()
    return redirect(url_for("meeting_details", id=meeting_id))



@app.route("/delete_meeting/<int:id>", methods=["POST"])
def delete_meeting(id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE meeting_id = ?", (id,))
        cursor.execute("DELETE FROM meetings WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("Error deleting meeting:", e)
        return jsonify({"error": "Database error"}), 500


# ---------------- Create Collection ----------------
@app.route("/create_collection", methods=["POST"])
def create_collection():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"error": "Name required"}), 400

    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO collections (name, user_id) VALUES (?, ?)", (name, session["user_id"]))
        conn.commit()
    except sqlitecloud.exceptions.SQLiteCloudIntegrityError:
        return jsonify({"error": "Collection name already exists"}), 400
    finally:
        conn.close()
    return jsonify({"success": True})

# ---------------- View Collection ----------------
@app.route("/collection/<int:collection_id>")
def view_collection(collection_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM collections WHERE id = ?", (collection_id,))
    collection_row = cursor.fetchone()
    if not collection_row:
        return "Collection not found", 404
    collection = dict(collection_row)

    cursor.execute("""
        SELECT id, title, date, summary, collection_id 
        FROM meetings 
        WHERE collection_id = ? AND user_id = ?
        ORDER BY date DESC
    """, (collection_id, session["user_id"]))
    meetings = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return render_template("collection.html", collection=collection, meetings=meetings)

# ---------------- Delete Collection ----------------
@app.route("/delete_collection/<collection_name>", methods=["POST"])
def delete_collection(collection_name):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE meetings SET collection_id = NULL WHERE collection_id = (SELECT id FROM collections WHERE name = ?)",
            (collection_name,)
        )
        cursor.execute("DELETE FROM collections WHERE name = ?", (collection_name,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(e)
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

# ---------------- Remove Multiple Meetings from Collection ----------------
@app.route("/remove_meetings_from_collection", methods=["POST"])
def remove_meetings_from_collection():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    meeting_ids = data.get("meeting_ids")
    if not meeting_ids or not isinstance(meeting_ids, list):
        return jsonify({"error": "No meeting IDs provided"}), 400

    try:
        conn = get_conn()
        cursor = conn.cursor()
        query = f"""
            UPDATE meetings 
            SET collection_id = NULL 
            WHERE id IN ({','.join(['?'] * len(meeting_ids))}) AND user_id = ?
        """
        cursor.execute(query, meeting_ids + [session["user_id"]])
        conn.commit()
        removed_count = cursor.rowcount
        conn.close()
        return jsonify({"success": True, "removed_count": removed_count})
    except Exception as e:
        print("Error removing meetings from collection:", e)
        return jsonify({"error": "Database error"}), 500


# ---------------- Move Meeting ----------------
@app.route("/move_meeting/<int:meeting_id>", methods=["POST"])
def move_meeting(meeting_id):
    data = request.get_json()
    if not data or "collection_id" not in data:
        return jsonify({"error": "No collection_id provided"}), 400

    collection_id = data["collection_id"]
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE meetings SET collection_id = ? WHERE id = ?", (collection_id, meeting_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(e)
        return jsonify({"error": "Database error"}), 500


# ---------------- Edit Meeting ----------------
@app.route("/edit_meeting/<int:id>", methods=["POST"])
def edit_meeting(id):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    title = data.get("title")
    date = data.get("date")
    transcript = data.get("transcript")
    summary = data.get("summary")
    if not title or not date or not transcript or not summary:
        return jsonify({"error": "All fields are required"}), 400

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE meetings 
            SET title = ?, date = ?, transcript = ?, summary = ? 
            WHERE id = ? AND user_id = ?
        """, (title, date, transcript, summary, id, session["user_id"]))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(e)
        return jsonify({"error": "Database error"}), 500


# ---------------- Meeting Details ----------------
@app.route("/meeting/<int:id>")
def meeting_details(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "Meeting not found", 404

    meeting = SimpleNamespace(**row)
    cursor.execute("SELECT person, task FROM tasks WHERE meeting_id = ?", (id,))
    tasks = cursor.fetchall()
    conn.close()
    return render_template("meeting_details.html", meeting=meeting, tasks=tasks)

# ---------------- Calendar Page ----------------
@app.route("/calendar")
def calendar_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("calendar.html")

# ---------------- Download PDF ----------------
@app.route("/download_pdf/<int:id>")
def download_pdf(id):
    conn = get_conn()
    meeting = conn.execute("SELECT * FROM meetings WHERE id = ?", (id,)).fetchone()
    tasks = conn.execute("SELECT person, task FROM tasks WHERE meeting_id = ?", (id,)).fetchall()
    conn.close()

    if meeting is None:
        return "Meeting not found", 404

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{meeting['title']}</b>", styles["Title"]))
    elements.append(Paragraph(f"Date: {meeting['date']}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Transcript:</b>", styles["Heading2"]))
    elements.append(Paragraph(meeting['transcript'], styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Summary / Action Items:</b>", styles["Heading2"]))
    elements.append(Paragraph(meeting['summary'], styles["Normal"]))
    elements.append(Spacer(1, 12))

    if tasks:
        elements.append(Paragraph("<b>Tasks:</b>", styles["Heading2"]))
        for task in tasks:
            elements.append(Paragraph(f"{task['person']}: {task['task']}", styles["Normal"]))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Disposition"] = f"attachment; filename=meeting_{id}.pdf"
    response.headers["Content-Type"] = "application/pdf"
    return response

# ---------------- Upcoming Meetings ----------------
@app.route("/add_upcoming_meeting", methods=["POST"])
def add_upcoming_meeting():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    title = data.get("title")
    date = data.get("date")
    description = data.get("description")
    if not title or not date:
        return jsonify({"error": "Title and Date are required"}), 400

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO upcoming_meetings (title, date, description, user_id) VALUES (?, ?, ?, ?)",
            (title, date, description, session["user_id"])
        )
        conn.commit()
        meeting_id = cursor.lastrowid
        conn.close()
        return jsonify({"success": True, "id": meeting_id})
    except Exception as e:
        print(e)
        return jsonify({"error": "Database error"}), 500


@app.route("/get_upcoming_meetings")
def get_upcoming_meetings():
    if "user_id" not in session:
        return jsonify([])

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, date, description FROM upcoming_meetings WHERE user_id=? ORDER BY date ASC",
        (session["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    events = [{"id": row["id"], "title": row["title"], "start": row["date"], "description": row.get("description") or ""} for row in rows]
    return jsonify(events)

@app.route("/get_meetings_by_date")
def get_meetings_by_date():
    if "user_id" not in session:
        return jsonify({"meetings": []}), 401

    date_str = request.args.get("date")  # format: YYYY-MM-DD
    if not date_str:
        return jsonify({"meetings": []})

    try:
        conn = get_conn()  # Use your existing SQLiteCloud connection
        cursor = conn.cursor()
        
        # Match all rows where date starts with "YYYY-MM-DD" for the current user
        cursor.execute(
            "SELECT id, title, date, description FROM upcoming_meetings WHERE user_id = ? AND date LIKE ?",
            (session["user_id"], f"{date_str}%")
        )
        rows = cursor.fetchall()
        conn.close()

        # Convert to list of dicts
        meetings = [dict(row) for row in rows]

        return jsonify({"meetings": meetings})
    except Exception as e:
        print(f"Error in get_meetings_by_date: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/delete_upcoming_meeting/<int:meeting_id>", methods=["DELETE"])
def delete_upcoming_meeting(meeting_id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM upcoming_meetings WHERE id = ?", (meeting_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- Next Meeting Helper ----------------
def get_next_meeting(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, date FROM meetings WHERE user_id=? AND date >= ? ORDER BY date ASC LIMIT 1",
        (user_id, datetime.now().strftime("%Y-%m-%d"))
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        row = dict(row)
        return f"Your next meeting is '{row['title']}' on {row['date']}."
    return "You don’t have any upcoming meetings."


# ---------------- Chatbot ----------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    if "user_id" not in session:
        return jsonify({"reply": "⚠️ Please log in to use the chatbot."}), 401

    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "⚠️ Please send a message."}), 400

    try:
        chat_model = genai.GenerativeModel("gemini-1.5-flash")
        context = """
        You are an assistant for ActionNotes:
        AI-powered meeting notes manager — Summarize meetings, extract action items, and organize everything in one place.

        Key points:
        - Flask + SQLiteCloud + Gemini AI + AssemblyAI
        - Upload audio or transcripts to get summaries
        - Extract action items grouped by person
        - Organize meetings into collections
        - Web dashboard with authentication
        - Focus on helping the user understand how to use the app
        """
        prompt = f"{context}\n\nAnswer this user query clearly and concisely: '{user_message}'"
        response = chat_model.generate_content(prompt)
        reply = response.text if response.text else "Sorry, I couldn't generate a response."
    except Exception as e:
        print("Chatbot error:", e)
        reply = "⚠️ Something went wrong. Please try again."

    return jsonify({"reply": reply})


# ---------------- Run App ----------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
