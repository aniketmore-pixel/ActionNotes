# # db_utils.py
# import sqlite3

# DB_PATH = "meetings.db"

# def get_db_connection():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row  # so we can access columns by name
#     return conn


import sqlitecloud

DB_URL = "sqlitecloud://cekbo8acnk.g2.sqlite.cloud:8860/actionnotes.sqlite3?apikey=YPrFryodsBthblXh4RpZhyHeuRoCcVBiIjnRUCVUmaQ"

def get_db_connection():
    conn = sqlitecloud.connect(DB_URL)
    return conn
