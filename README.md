# Corvit Student Feedback System

A web-based course feedback system built for **Corvit Systems, Rawalpindi**. Students submit feedback about their course through an online form, replacing the paper feedback form. Administrators review submissions, manage the questions and generate reports from a dashboard.

Built with **Flask** and **SQLite**.

## Features

### Student portal
- Student login
- Feedback form with course selection and rating questions
- Four-level rating scale: **Excellent, Good, Average, Below Average**
- Duplicate submissions are blocked, so each student can submit only once for a course
- Confirmation after the feedback is saved

### Admin dashboard
- Admin login
- View all feedback submissions
- Charts that summarise the ratings
- Manage questions: add, edit and remove feedback questions
- AI-generated feedback result (summary report)
- Print-friendly report

### Courses covered
CCNA, CCNP, Cyber Security, Cloud Computing, Artificial Intelligence, Data Science, Project Management, Other IT Courses

## Tech stack

| Part | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript (Jinja2 templates) |

## Project structure

```
feedback-system/
├── app.py            # Flask application and routes
├── database.py       # Database setup
├── templates/        # HTML pages (student portal and admin dashboard)
├── static/
│   ├── style.css     # Styling
│   └── logo.jpeg     # Corvit logo
└── README.md
```

## Getting started

### Prerequisites
- Python 3.9 or later
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<repository-name>.git
cd <repository-name>

# 2. (Optional) create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install flask

# 4. Create the database
python database.py

# 5. Run the application
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## How it works

1. A student logs in and fills the feedback form for their course.
2. The responses are saved in the SQLite database.
3. An administrator logs in to the dashboard to see the submissions, charts and the AI-generated result.
4. Administrators can update the feedback questions at any time from the question management page.

## Security notes

- Change the default admin credentials before using the system with real students.
- Do not commit secrets or API keys to the repository.

<!--
## Screenshots
Add your screenshots to a `screenshots/` folder, then remove these comment markers.

![Student login](screenshots/student-login.png)
![Feedback form](screenshots/feedback-form.png)
![Admin dashboard](screenshots/admin-dashboard.png)
-->

## Author

**Rida Shahzadi**
BS Computer Science, Arid Agriculture University, Rawalpindi
Developed during an internship at Corvit Systems, Rawalpindi.

## License

This project was developed for educational and internship purposes.
