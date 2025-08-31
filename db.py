import sqlite3

def init_db():
    conn = sqlite3.connect("meetings.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ---------- Meetings table ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        date TEXT,
        transcript TEXT,
        summary TEXT
    )
    ''')

    # ---------- Tasks table ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        person TEXT,
        task TEXT,
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    )
    ''')

    # ---------- Users table ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    # ---------- Collections table ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    ''')

    # ---------- Add user_id column to meetings if missing ----------
    cursor.execute("PRAGMA table_info(meetings)")
    columns = [col[1] for col in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN user_id INTEGER")

    # ---------- Refresh columns before checking collection_id ----------
    cursor.execute("PRAGMA table_info(meetings)")
    columns = [col[1] for col in cursor.fetchall()]
    if "collection_id" not in columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN collection_id INTEGER REFERENCES collections(id)")

    conn.commit()
    conn.close()
