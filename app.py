from flask import Flask, render_template, request, redirect, url_for, session, Response
from database import get_db, create_tables, seed_data
from werkzeug.security import check_password_hash
from textblob import TextBlob
import re
import csv
import io
from datetime import datetime
from collections import Counter, defaultdict


# ---------------------------------------------------------------
# Word lists (module level so both functions can use them)
# ---------------------------------------------------------------
POSITIVE_WORDS = [
    "good", "great", "excellent", "best", "amazing",
    "helpful", "useful", "nice", "perfect", "love",
    "like", "better", "clear", "friendly", "professional",
    "acha", "achi", "achay", "bohat acha", "zabardast",
    "behtareen", "mashallah", "pasand"
]

NEGATIVE_WORDS = [
    "bad", "poor", "worst", "slow", "problem", "problems",
    "issue", "issues", "difficult", "weak", "worse",
    "not good", "hate", "lack", "missing", "unavailable",
    "kharaab", "kharab", "masla", "maslay",
    "acha nahi", "achi nahi", "problem hai"
]

NO_COMPLAINT_WORDS = [
    "nothing", "none", "no problem", "no problems",
    "no issue", "no issues", "nothing to improve",
    "kuch nahi", "koi masla nahi", "koi problem nahi",
    "sab theek", "sab acha"
]

TOPIC_KEYWORDS = {
    "Teaching Quality": [
        "teacher", "teachers", "instructor", "sir",
        "madam", "maam", "teaching", "teach",
        "lecture", "explain", "explains", "explaining", "explained",
        "samjha", "samjh", "ustad"
    ],
    "Learning Environment": [
        "environment", "atmosphere", "classroom", "desk", "desks",
        "chair", "chairs", "furniture", "seating",
        "comfortable", "friendly environment",
        "mahol", "mahaul"
    ],
    "Internet": [
        "internet", "wifi", "wi-fi", "net",
        "connection", "connectivity"
    ],
    "Lab Facilities": [
        "lab", "labs", "laboratory", "computer", "computers",
        "pc", "system", "software", "equipment"
    ],
    "Course Content": [
        "course", "content", "syllabus", "topic",
        "topics", "curriculum", "subject"
    ],
    "Practical Work": [
        "practical", "project", "projects",
        "assignment", "assignments",
        "practice", "hands-on"
    ],
    "Administration": [
        "admin", "administration", "management",
        "staff", "admission", "fee", "fees",
        "schedule", "timing"
    ],
    "Career Support": [
        "career", "job", "jobs", "internship",
        "internships", "freelance",
        "employment", "placement"
    ]
}

SUGGESTION_MAP = {
    "Internet":
        "Improve internet speed and connection reliability.",
    "Lab Facilities":
        "Regularly check lab computers, software and equipment.",
    "Teaching Quality":
        "Continue improving clear teaching and student participation.",
    "Learning Environment":
        "Maintain a comfortable, friendly and positive learning environment.",
    "Course Content":
        "Regularly review course content according to current industry requirements.",
    "Practical Work":
        "Increase practical activities, projects and hands-on learning.",
    "Administration":
        "Improve communication and timely support from administration.",
    "Career Support":
        "Provide more guidance about internships, jobs and career opportunities."
}


# ---------------------------------------------------------------
# Text analysis helpers
# ---------------------------------------------------------------
def clean_text(text):
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def contains_word(text, word):
    """Whole-word match, so 'lab' does not match 'available'."""
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None


def is_complaint_answer(answer):
    """True if the answer belongs to a weakness / complaint question."""
    label = (str(answer["section"]) + " " + str(answer["question"])).lower()
    return any(key in label for key in ("weakness", "complaint", "problem"))


def analyze_comment(text, is_complaint=False):
    text = clean_text(text)

    if any(contains_word(text, phrase) for phrase in NO_COMPLAINT_WORDS):
        return "Neutral"

    # Anything written under "Specific Weakness / Complaints" is a complaint
    if is_complaint:
        return "Negative"

    positive_score = sum(1 for word in POSITIVE_WORDS if contains_word(text, word))
    negative_score = sum(1 for word in NEGATIVE_WORDS if contains_word(text, word))

    if positive_score > negative_score:
        return "Positive"

    if negative_score > positive_score:
        return "Negative"

    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.15:
        return "Positive"

    if polarity < -0.15:
        return "Negative"

    if text in ["environment", "atmosphere", "mahol", "mahaul"]:
        return "Positive"

    return "Neutral"


def detect_topics(text):
    text = clean_text(text)
    detected = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if contains_word(text, keyword):
                detected.append(topic)
                break

    return detected


def percent(part, total):
    return round(part / total * 100, 1) if total else 0


def generate_ai_report(text_answers):
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    strengths = []
    complaints = []

    topic_counter = Counter()

    topic_sentiments = defaultdict(
        lambda: {"Positive": 0, "Negative": 0, "Neutral": 0}
    )

    course_sentiments = defaultdict(
        lambda: {"Positive": 0, "Negative": 0, "Neutral": 0, "comments": 0}
    )

    course_topics = defaultdict(Counter)

    for answer in text_answers:
        text = clean_text(answer["answer"])

        if not text:
            continue

        sentiment = analyze_comment(text, is_complaint_answer(answer))
        topics = detect_topics(text)
        course_name = answer["course_name"]

        if sentiment == "Positive":
            positive_count += 1
        elif sentiment == "Negative":
            negative_count += 1
        else:
            neutral_count += 1

        course_sentiments[course_name][sentiment] += 1
        course_sentiments[course_name]["comments"] += 1

        for topic in topics:
            topic_counter[topic] += 1
            topic_sentiments[topic][sentiment] += 1
            course_topics[course_name][topic] += 1

        if any(contains_word(text, phrase) for phrase in NO_COMPLAINT_WORDS):
            continue

        if sentiment == "Positive":
            if topics:
                for topic in topics:
                    strengths.append(f"Students appreciate {topic.lower()}.")
            else:
                strengths.append(f"Positive feedback: {answer['answer']}")

        elif sentiment == "Negative":
            if topics:
                for topic in topics:
                    complaints.append(
                        f"Students reported concerns about {topic.lower()}."
                    )
            else:
                complaints.append(f"Negative feedback: {answer['answer']}")

    total_comments = positive_count + negative_count + neutral_count

    positive_percentage = percent(positive_count, total_comments)
    negative_percentage = percent(negative_count, total_comments)
    neutral_percentage = percent(neutral_count, total_comments)

    if positive_count > negative_count and positive_count >= neutral_count:
        overall_sentiment = "Mostly Positive"
    elif negative_count > positive_count and negative_count >= neutral_count:
        overall_sentiment = "Mostly Negative"
    elif positive_count > 0 and negative_count > 0:
        overall_sentiment = "Mixed"
    else:
        overall_sentiment = "Mostly Neutral"

    if topic_counter:
        most_mentioned_topic, most_topic_count = topic_counter.most_common(1)[0]
    else:
        most_mentioned_topic = "No specific topic detected"
        most_topic_count = 0

    topic_analysis = []

    for topic, count in topic_counter.most_common():
        positive = topic_sentiments[topic]["Positive"]
        negative = topic_sentiments[topic]["Negative"]
        neutral = topic_sentiments[topic]["Neutral"]
        total = positive + negative + neutral

        if negative > positive:
            insight = f"{topic} needs attention based on student feedback."
        elif positive > negative:
            insight = f"Students are generally satisfied with {topic.lower()}."
        else:
            insight = f"Feedback about {topic.lower()} is mostly neutral."

        topic_analysis.append({
            "topic": topic,
            "count": count,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_percentage": percent(positive, total),
            "negative_percentage": percent(negative, total),
            "neutral_percentage": percent(neutral, total),
            "insight": insight
        })

    if total_comments == 0:
        priority = "Low"
    elif negative_percentage >= 40:
        priority = "High"
    elif negative_percentage >= 20:
        priority = "Medium"
    else:
        priority = "Low"

    suggestions = []

    for topic, count in topic_counter.most_common():
        if topic in SUGGESTION_MAP:
            suggestions.append(SUGGESTION_MAP[topic])

    if not suggestions:
        suggestions.append(
            "Encourage students to provide more detailed feedback for better AI analysis."
        )

    course_analysis = []

    for course, data in course_sentiments.items():
        total = data["comments"]
        positive = data["Positive"]
        negative = data["Negative"]
        neutral = data["Neutral"]

        if negative > positive:
            insight = "This course may require improvement based on student feedback."
        elif positive > negative:
            insight = "Students are generally satisfied with this course."
        else:
            insight = "Student feedback for this course is mostly neutral."

        mentioned_topics = course_topics[course].most_common()

        if mentioned_topics:
            topic_names = [f"{t} ({c})" for t, c in mentioned_topics[:3]]
            insight += " Main topics: " + ", ".join(topic_names) + "."

        course_analysis.append({
            "course": course,
            "total": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_percentage": percent(positive, total),
            "negative_percentage": percent(negative, total),
            "neutral_percentage": percent(neutral, total),
            "insight": insight
        })

    return {
        "overall_sentiment": overall_sentiment,
        "total_comments": total_comments,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "positive_percentage": positive_percentage,
        "negative_percentage": negative_percentage,
        "neutral_percentage": neutral_percentage,
        "most_mentioned_topic": most_mentioned_topic,
        "most_topic_count": most_topic_count,
        "priority": priority,
        "strengths": list(dict.fromkeys(strengths)),
        "complaints": list(dict.fromkeys(complaints)),
        "suggestions": list(dict.fromkeys(suggestions)),
        "topics": topic_counter.most_common(),
        "topic_analysis": topic_analysis,
        "course_analysis": course_analysis
    }


# ---------------------------------------------------------------
# App setup
# ---------------------------------------------------------------
app = Flask(__name__)

# Make sure the database exists and is up to date every time the app starts
create_tables()
seed_data()
app.secret_key = "corvit_feedback_secret_key"


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def already_submitted(conn, student_name, course_id):
    """True if a student with this name already gave feedback for this course."""
    row = conn.execute(
        """
        SELECT id
        FROM submissions
        WHERE LOWER(TRIM(student_name)) = LOWER(TRIM(?))
        AND course_id = ?
        LIMIT 1
        """,
        (student_name, course_id)
    ).fetchone()

    return row is not None


def render_student_login(conn, error=None, student_name="", course_id="", instructor_name="", batch=""):
    courses = conn.execute(
        """
        SELECT *
        FROM courses
        ORDER BY (name = 'Other IT Courses'), name
        """
    ).fetchall()

    return render_template(
        "student_login.html",
        courses=courses,
        error=error,
        student_name=student_name,
        instructor_name=instructor_name,
        batch=batch,
        selected_course=str(course_id)
    )


# ---------------------------------------------------------------
# Student side
# ---------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/student")
def student_login():
    conn = get_db()
    page = render_student_login(conn)
    conn.close()
    return page


@app.route("/feedback", methods=["POST"])
def feedback():
    student_name = request.form.get("student_name", "").strip()
    course_id = request.form.get("course_id", "").strip()
    instructor_name = request.form.get("instructor_name", "").strip()
    batch = request.form.get("batch", "").strip()

    if not student_name or not course_id or not instructor_name or not batch:
        return redirect(url_for("student_login"))

    conn = get_db()

    course = conn.execute(
        """
        SELECT *
        FROM courses
        WHERE id = ?
        """,
        (course_id,)
    ).fetchone()

    questions = conn.execute(
        """
        SELECT *
        FROM questions
        WHERE is_active = 1
        ORDER BY id
        """
    ).fetchall()

    if course is None:
        conn.close()
        return redirect(url_for("student_login"))

    if already_submitted(conn, student_name, course["id"]):
        page = render_student_login(
            conn,
            error=(
                f"Feedback for {course['name']} has already been submitted "
                f"by {student_name}. "
                "Each student can submit only one feedback per course."
            ),
            student_name=student_name,
            instructor_name=instructor_name,
            batch=batch,
            course_id=course["id"]
        )
        conn.close()
        return page

    conn.close()

    if not questions:
        return "No feedback questions are available."

    return render_template(
        "feedback_form.html",
        student_name=student_name,
        instructor_name=instructor_name,
        batch=batch,
        course=course,
        questions=questions
    )


@app.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    student_name = request.form.get("student_name", "").strip()
    course_id = request.form.get("course_id", "").strip()
    instructor_name = request.form.get("instructor_name", "").strip()
    batch = request.form.get("batch", "").strip()

    if not student_name or not course_id or not instructor_name or not batch:
        return redirect(url_for("student_login"))

    conn = get_db()

    questions = conn.execute(
        """
        SELECT *
        FROM questions
        WHERE is_active = 1
        ORDER BY id
        """
    ).fetchall()

    if not questions:
        conn.close()
        return "No feedback questions are available."

    if already_submitted(conn, student_name, course_id):
        page = render_student_login(
            conn,
            error="Feedback has already been submitted for this course by this student.",
            student_name=student_name,
            instructor_name=instructor_name,
            batch=batch,
            course_id=course_id
        )
        conn.close()
        return page

    for question in questions:
        answer = request.form.get(f"question_{question['id']}", "").strip()

        if not answer and question["q_type"] != "text":
            conn.close()
            return "Please answer all questions before submitting the feedback."

    ratings = []

    for question in questions:
        if question["q_type"] == "rating":
            answer = request.form.get(f"question_{question['id']}", "").strip()

            try:
                rating = float(answer)

                if 1 <= rating <= 4:
                    ratings.append(rating)

            except ValueError:
                pass

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    cursor = conn.execute(
        """
        INSERT INTO submissions (student_name, instructor_name, batch, course_id, avg_rating)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_name, instructor_name, batch, course_id, avg_rating)
    )

    submission_id = cursor.lastrowid

    for question in questions:
        answer = request.form.get(f"question_{question['id']}", "").strip()

        conn.execute(
            """
            INSERT INTO answers (submission_id, question_id, answer)
            VALUES (?, ?, ?)
            """,
            (submission_id, question["id"], answer)
        )

    conn.commit()
    conn.close()

    return redirect(url_for("thank_you"))


@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


# ---------------------------------------------------------------
# Admin login / logout
# ---------------------------------------------------------------
@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")


@app.route("/admin/login", methods=["POST"])
def admin_login_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return render_template(
            "admin_login.html",
            error="Please enter username and password."
        )

    conn = get_db()

    admin = conn.execute(
        """
        SELECT *
        FROM admins
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if admin is None:
        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )

    if not check_password_hash(admin["password_hash"], password):
        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )

    session["admin_logged_in"] = True
    session["admin_username"] = admin["username"]

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    total_feedbacks = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM submissions
        """
    ).fetchone()["total"]

    average_rating = conn.execute(
        """
        SELECT AVG(avg_rating) AS average
        FROM submissions
        WHERE avg_rating IS NOT NULL
        """
    ).fetchone()["average"]

    positive_feedback = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM submissions
        WHERE avg_rating >= 2.5
        """
    ).fetchone()["total"]

    negative_feedback = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM submissions
        WHERE avg_rating < 2.5
        """
    ).fetchone()["total"]

    course_stats = conn.execute(
        """
        SELECT
            courses.name,
            COUNT(submissions.id) AS total,
            ROUND(AVG(submissions.avg_rating), 2) AS average
        FROM courses
        LEFT JOIN submissions
        ON courses.id = submissions.course_id
        GROUP BY courses.id
        ORDER BY (courses.name = 'Other IT Courses'), courses.name
        """
    ).fetchall()

    section_stats = conn.execute(
        """
        SELECT
            questions.section,
            ROUND(AVG(CAST(answers.answer AS REAL)), 2) AS average
        FROM answers
        JOIN questions
        ON answers.question_id = questions.id
        WHERE questions.q_type = 'rating'
        GROUP BY questions.section
        ORDER BY MIN(questions.id)
        """
    ).fetchall()

    recent_submissions = conn.execute(
        """
        SELECT
            submissions.id,
            submissions.student_name,
            submissions.instructor_name,
            submissions.batch,
            courses.name AS course_name,
            submissions.avg_rating,
            submissions.created_at
        FROM submissions
        JOIN courses
        ON submissions.course_id = courses.id
        ORDER BY submissions.id DESC
        LIMIT 10
        """
    ).fetchall()

    conn.close()

    average_rating = average_rating if average_rating is not None else 0

    return render_template(
        "admin_dashboard.html",
        total_feedbacks=total_feedbacks,
        average_rating=round(average_rating, 2),
        positive_feedback=positive_feedback,
        negative_feedback=negative_feedback,
        course_stats=course_stats,
        section_stats=section_stats,
        recent_submissions=recent_submissions
    )


# ---------------------------------------------------------------
# Manage questions
# ---------------------------------------------------------------
@app.route("/admin/questions")
def manage_questions():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    questions = conn.execute(
        """
        SELECT *
        FROM questions
        ORDER BY id
        """
    ).fetchall()

    sections = conn.execute(
        """
        SELECT DISTINCT section
        FROM questions
        ORDER BY section
        """
    ).fetchall()

    conn.close()

    return render_template(
        "manage_questions.html",
        questions=questions,
        sections=sections
    )


@app.route("/admin/questions/add", methods=["POST"])
def add_question():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    section = request.form.get("section", "").strip()
    text = request.form.get("text", "").strip()
    q_type = request.form.get("q_type", "").strip()

    if not section or not text:
        return redirect(url_for("manage_questions"))

    if q_type not in ["rating", "yesno", "text"]:
        return redirect(url_for("manage_questions"))

    conn = get_db()

    conn.execute(
        """
        INSERT INTO questions (section, text, q_type, is_active)
        VALUES (?, ?, ?, 1)
        """,
        (section, text, q_type)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("manage_questions"))


@app.route("/admin/questions/edit/<int:question_id>", methods=["POST"])
def edit_question(question_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    section = request.form.get("section", "").strip()
    text = request.form.get("text", "").strip()
    q_type = request.form.get("q_type", "").strip()

    if not section or not text:
        return redirect(url_for("manage_questions"))

    if q_type not in ["rating", "yesno", "text"]:
        return redirect(url_for("manage_questions"))

    conn = get_db()

    conn.execute(
        """
        UPDATE questions
        SET section = ?, text = ?, q_type = ?
        WHERE id = ?
        """,
        (section, text, q_type, question_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("manage_questions"))


@app.route("/admin/questions/delete/<int:question_id>", methods=["POST"])
def delete_question(question_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM answers
        WHERE question_id = ?
        """,
        (question_id,)
    )

    conn.execute(
        """
        DELETE FROM questions
        WHERE id = ?
        """,
        (question_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("manage_questions"))


# ---------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------
@app.route("/admin/submissions")
def student_submissions():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    submissions = conn.execute(
        """
        SELECT
            submissions.id,
            submissions.student_name,
            submissions.instructor_name,
            submissions.batch,
            courses.name AS course_name,
            submissions.avg_rating,
            submissions.created_at
        FROM submissions
        JOIN courses
        ON submissions.course_id = courses.id
        ORDER BY submissions.id DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "student_submissions.html",
        submissions=submissions
    )


@app.route("/admin/submission/<int:submission_id>")
def submission_detail(submission_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    submission = conn.execute(
        """
        SELECT
            submissions.id,
            submissions.student_name,
            submissions.instructor_name,
            submissions.batch,
            submissions.avg_rating,
            submissions.created_at,
            courses.name AS course_name
        FROM submissions
        JOIN courses
        ON submissions.course_id = courses.id
        WHERE submissions.id = ?
        """,
        (submission_id,)
    ).fetchone()

    if submission is None:
        conn.close()
        return redirect(url_for("student_submissions"))

    answers = conn.execute(
        """
        SELECT
            questions.section,
            questions.text,
            questions.q_type,
            answers.answer
        FROM answers
        JOIN questions
        ON answers.question_id = questions.id
        WHERE answers.submission_id = ?
        ORDER BY answers.id
        """,
        (submission_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "submission_detail.html",
        submission=submission,
        answers=answers
    )


@app.route("/admin/submission/<int:submission_id>/delete", methods=["POST"])
def delete_submission(submission_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM answers
        WHERE submission_id = ?
        """,
        (submission_id,)
    )

    conn.execute(
        """
        DELETE FROM submissions
        WHERE id = ?
        """,
        (submission_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("student_submissions"))


# ---------------------------------------------------------------
# Export (Excel / CSV)
# ---------------------------------------------------------------
@app.route("/admin/export/submissions.csv")
def export_submissions():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    questions = conn.execute(
        """
        SELECT id, section, text
        FROM questions
        ORDER BY id
        """
    ).fetchall()

    submissions = conn.execute(
        """
        SELECT
            submissions.id,
            submissions.student_name,
            submissions.instructor_name,
            submissions.batch,
            courses.name AS course_name,
            submissions.avg_rating,
            submissions.created_at
        FROM submissions
        JOIN courses
        ON submissions.course_id = courses.id
        ORDER BY submissions.id
        """
    ).fetchall()

    answer_rows = conn.execute(
        """
        SELECT submission_id, question_id, answer
        FROM answers
        """
    ).fetchall()

    conn.close()

    answer_map = {}

    for row in answer_rows:
        answer_map[(row["submission_id"], row["question_id"])] = row["answer"]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        ["Student Name", "Instructor", "Batch", "Course", "Average Rating (out of 4)", "Date & Time"]
        + [q["text"] for q in questions]
    )

    for sub in submissions:
        writer.writerow(
            [
                sub["student_name"],
                sub["instructor_name"] or "",
                sub["batch"] or "",
                sub["course_name"],
                sub["avg_rating"] if sub["avg_rating"] is not None else "",
                sub["created_at"]
            ]
            + [answer_map.get((sub["id"], q["id"]), "") for q in questions]
        )

    filename = f"corvit_feedback_{datetime.now().strftime('%Y-%m-%d')}.csv"

    # utf-8-sig so Excel shows Urdu / special characters correctly
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ---------------------------------------------------------------
# AI report
# ---------------------------------------------------------------
@app.route("/admin/ai-report")
def ai_report():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    submissions = conn.execute(
        """
        SELECT
            submissions.id,
            submissions.avg_rating,
            courses.name AS course_name
        FROM submissions
        JOIN courses
        ON submissions.course_id = courses.id
        ORDER BY submissions.id DESC
        """
    ).fetchall()

    text_answers = conn.execute(
        """
        SELECT
            answers.answer,
            questions.text AS question,
            questions.section,
            submissions.id AS submission_id,
            courses.name AS course_name
        FROM answers
        JOIN questions
        ON answers.question_id = questions.id
        JOIN submissions
        ON answers.submission_id = submissions.id
        JOIN courses
        ON submissions.course_id = courses.id
        WHERE questions.q_type = 'text'
        AND TRIM(answers.answer) != ''
        ORDER BY submissions.id DESC
        """
    ).fetchall()

    total_feedbacks = len(submissions)

    average_rating = conn.execute(
        """
        SELECT AVG(avg_rating) AS average
        FROM submissions
        WHERE avg_rating IS NOT NULL
        """
    ).fetchone()["average"]

    positive_feedback = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM submissions
        WHERE avg_rating >= 2.5
        """
    ).fetchone()["total"]

    negative_feedback = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM submissions
        WHERE avg_rating < 2.5
        """
    ).fetchone()["total"]

    conn.close()

    average_rating = average_rating if average_rating is not None else 0

    ai_result = generate_ai_report(text_answers)

    summary = (
        f"AI analyzed {ai_result['total_comments']} written feedback comments. "
        f"The overall sentiment is {ai_result['overall_sentiment'].lower()}. "
        f"{ai_result['positive_percentage']}% of comments are positive, "
        f"{ai_result['negative_percentage']}% are negative, and "
        f"{ai_result['neutral_percentage']}% are neutral. "
        f"The most mentioned topic is {ai_result['most_mentioned_topic']}."
    )

    return render_template(
        "ai_report.html",
        total_feedbacks=total_feedbacks,
        average_rating=round(average_rating, 2),
        positive_feedback=positive_feedback,
        negative_feedback=negative_feedback,
        overall_sentiment=ai_result["overall_sentiment"],
        sentiment=ai_result["overall_sentiment"],
        positive_count=ai_result["positive_count"],
        negative_count=ai_result["negative_count"],
        neutral_count=ai_result["neutral_count"],
        total_comments=ai_result["total_comments"],
        positive_percentage=ai_result["positive_percentage"],
        negative_percentage=ai_result["negative_percentage"],
        neutral_percentage=ai_result["neutral_percentage"],
        most_mentioned_topic=ai_result["most_mentioned_topic"],
        most_topic_count=ai_result["most_topic_count"],
        priority=ai_result["priority"],
        summary=summary,
        strengths=ai_result["strengths"],
        complaints=ai_result["complaints"],
        suggestions=ai_result["suggestions"],
        topics=ai_result["topics"],
        topic_analysis=ai_result["topic_analysis"],
        course_analysis=ai_result["course_analysis"],
        text_answers=text_answers
    )


if __name__ == "__main__":
    app.run(debug=True)