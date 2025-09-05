from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response
import sqlite3
import wave
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from db import init_db
from ai_engine import process_transcript
from werkzeug.security import generate_password_hash, check_password_hash
from types import SimpleNamespace
import json
import subprocess
import os
import requests

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

app.secret_key = "supersecretkey123" 
# model = Model("models/vosk-model-small-en-us-0.15")
# ASSEMBLYAI_KEY = "aea5633912134b76a53c80c5bf615b6d"

# app.secret_key = os.environ.get("SECRET_KEY")
ASSEMBLYAI_KEY = os.environ.get("ASSEMBLYAI_KEY")
DB_PATH = os.environ.get("DB_PATH", "meetings.db")  # fallback to local DB



# DB_PATH = "meetings.db"






# ---------------- Helper Functions ----------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # <--- Important! Returns dict-like rows
    return conn


@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No file uploaded"}), 400

    # Upload to AssemblyAI
    headers = {"authorization": ASSEMBLYAI_KEY}
    response = requests.post("https://api.assemblyai.com/v2/upload", files={"file": audio_file}, headers=headers)
    audio_url = response.json()["upload_url"]

    # Request transcription
    transcript_request = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={"audio_url": audio_url},
        headers=headers
    )
    transcript_id = transcript_request.json()["id"]

    # Poll until transcription is done
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

    # Fetch meetings for the user
    cursor.execute(
        "SELECT id, title, date, summary, collection_id FROM meetings WHERE user_id = ?", 
        (session["user_id"],)
    )
    meetings = [dict(row) for row in cursor.fetchall()]

    # Fetch collections
    cursor.execute("SELECT id, name FROM collections WHERE user_id = ?", (session["user_id"],))

    collections = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return render_template("index.html", meetings=meetings, collections=collections)

# ---------------- User Registration/Login ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username exists!"
        finally:
            conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = username
            return redirect(url_for("home"))
        return "Invalid credentials"
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

    # Save tasks
    for person, person_tasks in tasks.items():
        for task in person_tasks:
            cursor.execute(
                "INSERT INTO tasks (meeting_id, person, task) VALUES (?, ?, ?)",
                (meeting_id, person, task)
            )

    conn.commit()
    conn.close()

    return redirect(url_for("meeting_details", id=meeting_id))

# ---------------- Delete Meeting ----------------
@app.route("/delete_meeting/<int:id>", methods=["POST"])
def delete_meeting(id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meetings WHERE id = ?", (id,))
    cursor.execute("DELETE FROM tasks WHERE meeting_id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

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
        cursor.execute("INSERT INTO collections (name, user_id) VALUES (?, ?)",(name, session["user_id"]))

        conn.commit()
    except sqlite3.IntegrityError:
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

    # Get collection info
    cursor.execute("SELECT name FROM collections WHERE id = ?", (collection_id,))
    collection_row = cursor.fetchone()
    if not collection_row:
        return "Collection not found", 404
    collection = dict(collection_row)

    # Get meetings inside this collection for this user
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
        cursor.execute("UPDATE meetings SET collection_id = NULL WHERE collection_id = (SELECT id FROM collections WHERE name = ?)", (collection_name,))
        cursor.execute("DELETE FROM collections WHERE name = ?", (collection_name,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(e)
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

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
        return "Meeting not found", 404

    # Convert sqlite3.Row -> dict -> SimpleNamespace
    meeting = SimpleNamespace(**{key: row[key] for key in row.keys()})

    # Fetch tasks
    cursor.execute("SELECT person, task FROM tasks WHERE meeting_id = ?", (id,))
    tasks = [dict(task) for task in cursor.fetchall()]

    conn.close()
    return render_template("meeting_details.html", meeting=meeting, tasks=tasks)

@app.route("/calendar")
def calendar_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("calendar.html")


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

# ---------------- Add Upcoming Meeting ----------------
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
        return jsonify([])  # no events if not logged in

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, date, description FROM upcoming_meetings WHERE user_id = ?",
        (session["user_id"],)
    )
    rows = cursor.fetchall()
    conn.close()

    # Convert DB rows -> FullCalendar event objects
    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "title": row["title"],
            "start": row["date"],   # must be ISO 8601 format string
            "description": row["description"]
        })

    return jsonify(events)

@app.route("/get_meetings_by_date")
def get_meetings_by_date():
    date_str = request.args.get("date")  # comes from JS, format: YYYY-MM-DD
    if not date_str:
        return jsonify({"meetings": []})

    try:
        conn = sqlite3.connect("meetings.db")
        conn.row_factory = sqlite3.Row  # rows as dict-like objects
        cursor = conn.cursor()

        # Match all rows where date starts with "YYYY-MM-DD"
        cursor.execute(
            "SELECT id, title, date, description FROM upcoming_meetings WHERE date LIKE ?",
            (f"{date_str}%",)
        )
        rows = cursor.fetchall()
        conn.close()

        # Convert to list of dicts
        meetings = [dict(row) for row in rows]

        return jsonify({"meetings": meetings})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_upcoming_meeting/<int:meeting_id>", methods=["DELETE"])
def delete_upcoming_meeting(meeting_id):
    try:
        conn = sqlite3.connect("meetings.db")
        cursor = conn.cursor()

        cursor.execute("DELETE FROM upcoming_meetings WHERE id = ?", (meeting_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- Run App ----------------
if __name__ == "__main__":
    import os
    init_db()
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT env variable if available
    app.run(host="0.0.0.0", port=port, debug=True)
