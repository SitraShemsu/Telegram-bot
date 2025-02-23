import sqlite3

try:
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # Enable WAL mode for better concurrent writes
    cursor.execute("PRAGMA journal_mode=WAL;")

    # Create the table if it does not exist
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

    print("Database and table created successfully with WAL mode!")

except sqlite3.Error as e:
    print(f"Error occurred: {e}")

finally:
    conn.close()
