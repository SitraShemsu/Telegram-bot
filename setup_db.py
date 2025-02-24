 
import sqlite3

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

# Enable WAL mode for better concurrent writes
cursor.execute("PRAGMA journal_mode=WAL;")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE,
    name TEXT,
    department TEXT,
    phone TEXT
)
""")

conn.commit()
conn.close()

print("Database and table created successfully with WAL mode!")
