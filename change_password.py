"""Change the admin password.

Usage (inside the project folder):
    python change_password.py
"""
import getpass

from werkzeug.security import generate_password_hash

from database import get_db, create_tables, seed_data


def main():
    create_tables()
    seed_data()

    username = input("Admin username [admin]: ").strip() or "admin"
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm new password: ")

    if len(password) < 6:
        print("Password must be at least 6 characters.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    conn = get_db()
    cur = conn.execute(
        "UPDATE admins SET password_hash = ? WHERE username = ?",
        (generate_password_hash(password), username)
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        print("No admin found with that username.")
    else:
        print("Password changed successfully.")


if __name__ == "__main__":
    main()
