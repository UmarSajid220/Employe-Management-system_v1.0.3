from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecret"

# ---------------- Gemini Configuration ----------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = "gemini-2.5-flash"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"Gemini API configured successfully: {GEMINI_API_KEY[:6]}...{GEMINI_API_KEY[-4:]}")
else:
    print("Warning: GEMINI_API_KEY not found. Chatbot will not work.")

# ---------------- Database Setup ----------------
def get_db_connection():
    conn = sqlite3.connect("Database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            role TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT,
            title TEXT,
            explanation TEXT,
            priority TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Pending',
            assigned_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            login_time TEXT,
            logout_time TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- Utility Functions ----------------
def is_admin():
    return "user" in session and session.get("role") == "admin"

def is_employee():
    return "user" in session and session.get("role") == "employee"

# ---------------- Routes ----------------

@app.route("/")
def home():
    if "user" in session:
        if session["role"] == "admin":
            return redirect(url_for("admin"))
        return redirect(url_for("employee"))
    return redirect(url_for("login"))

# -------- Signup ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    msg = ""
    if request.method == "POST":
        username = request.form["username"].strip()
        role = "employee"
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, role) VALUES (?, ?)", (username, role))
            conn.commit()
            msg = f"Employee {username} signed up successfully! Please log in."
        except sqlite3.IntegrityError:
            msg = "Username already exists. Please choose a different one."
        except Exception as e:
            msg = f"An error occurred: {e}"
        finally:
            conn.close()
        return render_template("signup.html", message=msg)
    return render_template("signup.html")

# -------- Admin Signup ----------
@app.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    admin_count = cur.fetchone()[0]
    conn.close()

    if admin_count > 0 and not is_admin():
        return redirect(url_for("login"))

    msg = "Create the first admin account." if admin_count == 0 else "Admin account creation."

    if request.method == "POST":
        username = request.form["username"].strip()
        role = "admin"
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, role) VALUES (?, ?)", (username, role))
            conn.commit()
            msg = f"Admin '{username}' created successfully! Please log in."
        except sqlite3.IntegrityError:
            msg = "Username already exists."
        finally:
            conn.close()
        return render_template("admin_signup.html", message=msg)
    return render_template("admin_signup.html", message=msg)

# -------- Login ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=?", (username,))
        data = cur.fetchone()
        conn.close()

        if data:
            role = data["role"]
            session["user"] = username
            session["role"] = role

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (username, login_time) VALUES (?, ?)",
                (username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()

            return redirect(url_for("admin") if role == "admin" else url_for("employee"))
        else:
            return render_template("login.html", message="User not found. Try signing up.")
    return render_template("login.html")

# -------- Logout ----------
@app.route("/logout")
def logout():
    if "user" in session:
        username = session["user"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM sessions
            WHERE username=? AND logout_time IS NULL
            ORDER BY login_time DESC LIMIT 1
        """, (username,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE sessions SET logout_time=? WHERE id=?",
                (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["id"]),
            )
            conn.commit()
        conn.close()
    session.clear()
    return redirect(url_for("login"))

# -------- Admin Dashboard ----------
@app.route("/admin")
def admin():
    if not is_admin():
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY status, deadline")
    tasks = cur.fetchall()
    cur.execute("SELECT username FROM users WHERE role='employee'")
    employees = [row["username"] for row in cur.fetchall()]
    cur.execute("SELECT * FROM sessions ORDER BY login_time DESC")
    logs = cur.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", tasks=tasks, logs=logs, employees=employees)

# -------- Assign Task ----------
@app.route("/assign_task", methods=["GET", "POST"])
def assign_task():
    if not is_admin():
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE role='employee'")
    employees = [row["username"] for row in cur.fetchall()]
    conn.close()

    if request.method == "POST":
        employee = request.form["employee"]
        title = request.form["title"]
        explanation = request.form["explanation"]
        priority = request.form["priority"]
        deadline = request.form["deadline"]
        assigned_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tasks (employee, title, explanation, priority, deadline, assigned_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee, title, explanation, priority, deadline, assigned_at))
        conn.commit()
        conn.close()

        return redirect(url_for("admin"))
    return render_template("assign_task.html", employees=employees)

# -------- Employee Dashboard ----------
@app.route("/employee")
def employee():
    if not is_employee():
        return redirect(url_for("login"))

    username = session["user"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE employee=? ORDER BY status DESC, priority DESC, deadline ASC", (username,))
    tasks = cur.fetchall()
    cur.execute("SELECT login_time, logout_time FROM sessions WHERE username=? ORDER BY login_time DESC", (username,))
    logs = cur.fetchall()
    conn.close()

    return render_template("employee_dashboard.html", user=username, tasks=tasks, logs=logs)

# -------- Complete Task ----------
@app.route("/complete_task/<int:task_id>")
def complete_task(task_id):
    if not is_employee():
        return redirect(url_for("login"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status='Completed' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("employee"))

# -------- Chatbot ----------
@app.route("/chat")
def chat_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html")

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message")

    if not GEMINI_API_KEY:
        return jsonify({"response": "Gemini API key is missing or invalid."})

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(user_input)
        reply = response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        reply = "Sorry, the chatbot is currently unavailable."
    return jsonify({"response": reply})

# -------- Admin Report Page ----------
@app.route("/report")
def report_page():
    """Direct access to the generate_report.html page from the dashboard"""
    if not is_admin():
        return redirect(url_for("login"))
    return render_template("generate_report.html")

# -------- Generate Employee Report (AI-based) ----------
@app.route("/generate-report/<username>")
def generate_report(username):
    if not is_admin():
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT role FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    if not user or user["role"] != "employee":
        conn.close()
        return "Invalid employee username."

    cur.execute("""
        SELECT title, explanation, priority, deadline, status, assigned_at
        FROM tasks
        WHERE employee=?
        ORDER BY assigned_at DESC
    """, (username,))
    tasks = cur.fetchall()
    conn.close()

    if not tasks:
        return f"No tasks found for employee '{username}'."

    formatted_tasks = "\n".join([
        f"• Title: {t['title']} | Priority: {t['priority']} | Status: {t['status']} | Deadline: {t['deadline']}"
        for t in tasks
    ])

    prompt = f"""
    You are an intelligent reporting assistant for a task management system.
    Generate a concise and professional progress report for the employee '{username}' based on the following task data:

    {formatted_tasks}

    Include:
    - Task performance summary
    - Completion rate
    - Strengths and possible improvement areas
    - Overall productivity rating (out of 10)
    """

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        report = response.text
    except Exception as e:
        print(f"Gemini API Error while generating report: {e}")
        report = "Error generating report. Please try again later."

    return render_template("report.html", username=username, report=report)

# ---------------- Run App ----------------
if __name__ == "__main__":
    print(f"Starting Flask app — Gemini API: {'Configured' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    app.run(debug=True)
