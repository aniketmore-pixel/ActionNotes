# db.py
import sqlitecloud

# Replace with your SQLite Cloud URL
DB_URL = "sqlitecloud://cekbo8acnk.g2.sqlite.cloud:8860/actionnotes.sqlite3?apikey=YPrFryodsBthblXh4RpZhyHeuRoCcVBiIjnRUCVUmaQ"

def get_conn():
    """
    Returns a connection to SQLite Cloud with dict-style row access.
    """
    conn = sqlitecloud.connect(DB_URL)
    # Dict-style rows for easy access in Flask
    conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    return conn


def init_db(drop_existing=False):
    """
    Initialize the database tables.
    Set drop_existing=True to completely reset the database.
    """
    conn = get_conn()
    cursor = conn.cursor()

    if drop_existing:
        # Drop all tables if you want a fresh start
        cursor.execute("DROP TABLE IF EXISTS upcoming_meetings")
        cursor.execute("DROP TABLE IF EXISTS tasks")
        cursor.execute("DROP TABLE IF EXISTS meetings")
        cursor.execute("DROP TABLE IF EXISTS collections")
        cursor.execute("DROP TABLE IF EXISTS users")

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

    # ---------- Upcoming Meetings table ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS upcoming_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully!")
