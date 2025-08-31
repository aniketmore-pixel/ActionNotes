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
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collections'")
    if cursor.fetchone():
        # Check if UNIQUE(name, user_id) exists by trying to create temp table
        cursor.execute("PRAGMA index_list(collections)")
        indexes = [row["name"] for row in cursor.fetchall()]
        if "idx_col_name_user" not in indexes:
            # Migrate: rename old table, create new, copy data
            cursor.execute("ALTER TABLE collections RENAME TO collections_old")
            cursor.execute('''
            CREATE TABLE collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER,
                UNIQUE(name, user_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            ''')
            cursor.execute('''
            INSERT INTO collections (id, name, user_id)
            SELECT id, name, user_id FROM collections_old
            ''')
            cursor.execute("DROP TABLE collections_old")
    else:
        cursor.execute('''
        CREATE TABLE collections (
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

    # Ensure user_id & collection_id exist (for older tables)
    cursor.execute("PRAGMA table_info(meetings)")
    meeting_columns = [col[1] for col in cursor.fetchall()]
    if "user_id" not in meeting_columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN user_id INTEGER")
    if "collection_id" not in meeting_columns:
        cursor.execute("ALTER TABLE meetings ADD COLUMN collection_id INTEGER REFERENCES collections(id)")

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

    conn.commit()
    conn.close()
