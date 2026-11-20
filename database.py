import os
import sqlite3
from werkzeug.security import generate_password_hash

# Absolute path, so the database is always created next to this file
# (needed on hosting such as PythonAnywhere, where the working folder differs)
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.db")
FORM_VERSION = "2"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL,
            text TEXT NOT NULL,
            q_type TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            instructor_name TEXT,
            batch TEXT,
            course_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            avg_rating REAL,
            sentiment TEXT,
            sentiment_reason TEXT,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT,
            FOREIGN KEY (submission_id) REFERENCES submissions(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Older databases had a registration number column: remove it
    columns = [row["name"] for row in cur.execute("PRAGMA table_info(submissions)")]

    if "reg_no" in columns:
        cur.execute("ALTER TABLE submissions DROP COLUMN reg_no")

    if "instructor_name" not in columns:
        cur.execute("ALTER TABLE submissions ADD COLUMN instructor_name TEXT")

    if "batch" not in columns:
        cur.execute("ALTER TABLE submissions ADD COLUMN batch TEXT")

    conn.commit()
    conn.close()


def seed_data():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM admins")

    if cur.fetchone()[0] == 0:
        password_hash = generate_password_hash("admin123")

        cur.execute(
            """
            INSERT INTO admins
            (username, password_hash)
            VALUES (?, ?)
            """,
            ("admin", password_hash)
        )

    questions = [
        ("Instructor", "Lectures were well organized.", "rating"),
        ("Instructor", "Command over the subject was sound.", "rating"),
        ("Instructor", "Lecture pace was right for understanding.", "rating"),
        ("Instructor", "Instructor was fair and unbiased.", "rating"),
        ("Instructor", "Relationship with students was congenial.", "rating"),
        ("Instructor", "Class discipline during lecture was good.", "rating"),
        ("Instructor", "Class discussion and questions were encouraged.", "rating"),
        ("Instructor", "Satisfactory answers were given to class questions.", "rating"),
        ("Instructor", "Instructor was helpful outside the class.", "rating"),
        ("Courses", "Lab availability.", "rating"),
        ("Courses", "Course coverage was in time.", "rating"),
        ("Courses", "Course outline was provided and followed.", "rating"),
        ("Courses", "Hands-on experience was given.", "rating"),
        ("Courses", "Course proceeded as per schedule.", "rating"),
        ("Overall Facilities", "Administration / Management.", "rating"),
        ("Overall Facilities", "Staff interaction.", "rating"),
        ("Overall Facilities", "General environment.", "rating"),
        ("Specific Weakness / Complaints", "Please write any specific weakness or complaints.", "text"),
        ("Suggestions for Improvement of Institution", "Please write your suggestions for improving the institute.", "text")
    ]

    # The question set is loaded only once (form version 2: 4-point scale).
    # After that, questions are managed from the admin panel, so they are
    # never re-added automatically.
    cur.execute("SELECT value FROM meta WHERE key = 'form_version'")
    row = cur.fetchone()

    if row is None or row[0] != FORM_VERSION:
        # Replace the old question set (old answers used a different scale)
        cur.execute("DELETE FROM answers")
        cur.execute("DELETE FROM submissions")
        cur.execute("DELETE FROM questions")
        cur.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('answers', 'submissions', 'questions')"
        )

        for section, text, q_type in questions:
            cur.execute(
                """
                INSERT INTO questions
                (section, text, q_type, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (section, text, q_type)
            )

        cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('form_version', ?)",
            (FORM_VERSION,)
        )

    courses = [
        "CCNA",
        "CCNP",
        "Cyber Security",
        "Cloud Computing",
        "Artificial Intelligence",
        "Data Science",
        "Project Management",
        "Other IT Courses"
    ]

    # Remove old courses that nobody has submitted feedback for
    placeholders = ",".join("?" for _ in courses)

    cur.execute(
        f"""
        DELETE FROM courses
        WHERE name NOT IN ({placeholders})
        AND id NOT IN (SELECT DISTINCT course_id FROM submissions)
        """,
        courses
    )

    for course_name in courses:
        cur.execute(
            """
            INSERT OR IGNORE INTO courses (name)
            VALUES (?)
            """,
            (course_name,)
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    seed_data()
    print("Database created and updated successfully.")