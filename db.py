import sqlite3

def init_db():
    conn = sqlite3.connect("meetings.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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
        name TEXT NOT NULL,
        user_id INTEGER,
        UNIQUE(name, user_id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # ---------- Meetings table ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        date TEXT,
        transcript TEXT,
        summary TEXT,
        user_id INTEGER,
        collection_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(collection_id) REFERENCES collections(id)
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

    # ---------- Add user_id to meetings if missing ----------
    cursor.execute("PRAGMA table_info(meetings)")
    meeting_columns = [col[1] for col in cursor.fetchall()]
    if "user_id" not in meeting_columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN user_id INTEGER")
    if "collection_id" not in meeting_columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN collection_id INTEGER REFERENCES collections(id)")

    # ---------- Add user_id to collections if missing ----------
    cursor.execute("PRAGMA table_info(collections)")
    collection_columns = [col[1] for col in cursor.fetchall()]
    if "user_id" not in collection_columns:
        cursor.execute("ALTER TABLE collections ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()
