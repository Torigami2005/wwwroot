#!/usr/bin/env python3
import cgi
import mysql.connector
import html
import sys
import os
import http.cookies
import re

print("Content-Type: text/html")

form = cgi.FieldStorage()

# Handle logout
logout_action = form.getvalue("logout_action", "")
if logout_action == "1":
    print("Set-Cookie: session_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; HttpOnly")
    print("Set-Cookie: username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: user_role=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print()
    print("<script>window.location.href = 'index.py';</script>")
    sys.exit()

# Load cookies
cookie_string = os.environ.get('HTTP_COOKIE', '')
cookies = http.cookies.SimpleCookie()
if cookie_string:
    cookies.load(cookie_string)

# Session check
is_logged_in = False
username = ""
database_name = ""
user_role = ""
is_admin = False
is_teacher = False
is_student = False

if 'session_id' in cookies and 'username' in cookies:
    session_id = cookies['session_id'].value
    username = cookies['username'].value
    database_name = cookies['database'].value if 'database' in cookies else ""
    user_role = cookies['user_role'].value if 'user_role' in cookies else ""

    if session_id:
        is_logged_in = True
        is_admin = (user_role == "admin")
        is_teacher = (user_role == "teacher")
        is_student = (user_role == "student")

print()

if not is_logged_in:
    print("<script>alert('Please login first');window.location.href = 'index.py';</script>")
    sys.exit()

if not database_name:
    print("<script>alert('Please select a database first');window.location.href = 'index.py';</script>")
    sys.exit()

# Only students can access this page
if not is_student:
    print("<script>alert('Access Denied: This page is for students only');window.location.href = 'encodegrades.py';</script>")
    sys.exit()

# Get student ID from username
student_id_match = re.search(r'^(\d+)', username)
student_id = int(student_id_match.group(1)) if student_id_match else None

if not student_id:
    print("<script>alert('Could not determine student ID from username');window.location.href = 'studrec.py';</script>")
    sys.exit()

# Get subject ID — handle list if key appears in both query string and POST body
raw_subjid = form.getvalue("subjid", "")
raw_subjid = (raw_subjid[0] if isinstance(raw_subjid, list) else raw_subjid).strip()

if not raw_subjid:
    print("<script>alert('No subject selected');window.location.href = 'studrec.py';</script>")
    sys.exit()

try:
    subjid = int(raw_subjid)
except ValueError:
    print("<script>alert('Invalid subject ID');window.location.href = 'studrec.py';</script>")
    sys.exit()

# Status message shown inline (replaces JS alert)
status_message = ""
status_type = ""  # "success" or "error"

# Handle comment submission
submit_comment = form.getvalue("submit_comment", "")
comment_text = form.getvalue("evaluation_comment", "")

if submit_comment == "1":
    if not comment_text or not comment_text.strip():
        status_message = "Comment cannot be empty."
        status_type = "error"
    else:
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database=database_name
            )
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    eval_id INT AUTO_INCREMENT PRIMARY KEY,
                    studid INT,
                    subjid INT,
                    evaluation_comment TEXT,
                    eval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (studid) REFERENCES students(studid),
                    FOREIGN KEY (subjid) REFERENCES subjects(subjid)
                )
            """)
            conn.commit()

            # Drop unique constraint if it still exists from old schema.
            # Must drop foreign keys that depend on it first, then re-add them.
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.statistics
                WHERE table_schema = %s
                AND table_name = 'evaluations'
                AND index_name = 'unique_student_subject'
            """, (database_name,))
            if cursor.fetchone()[0] > 0:
                # Find all foreign keys on the evaluations table
                cursor.execute("""
                    SELECT constraint_name FROM information_schema.table_constraints
                    WHERE table_schema = %s
                    AND table_name = 'evaluations'
                    AND constraint_type = 'FOREIGN KEY'
                """, (database_name,))
                fk_names = [row[0] for row in cursor.fetchall()]

                # Drop each foreign key
                for fk in fk_names:
                    cursor.execute(f"ALTER TABLE evaluations DROP FOREIGN KEY `{fk}`")
                conn.commit()

                # Now drop the unique index
                cursor.execute("ALTER TABLE evaluations DROP INDEX unique_student_subject")
                conn.commit()

                # Re-add the foreign keys
                cursor.execute("""
                    ALTER TABLE evaluations
                    ADD CONSTRAINT fk_eval_studid FOREIGN KEY (studid) REFERENCES students(studid),
                    ADD CONSTRAINT fk_eval_subjid FOREIGN KEY (subjid) REFERENCES subjects(subjid)
                """)
                conn.commit()

            # Always insert — students can comment as many times as they want
            cursor.execute(
                "INSERT INTO evaluations (studid, subjid, evaluation_comment) VALUES (%s, %s, %s)",
                (student_id, subjid, comment_text.strip())
            )
            conn.commit()
            cursor.close()
            conn.close()

            status_message = "Evaluation submitted successfully!"
            status_type = "success"

        except Exception as e:
            status_message = f"Error submitting evaluation: {html.escape(str(e))}"
            status_type = "error"

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database=database_name
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            eval_id INT AUTO_INCREMENT PRIMARY KEY,
            studid INT,
            subjid INT,
            evaluation_comment TEXT,
            eval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (studid) REFERENCES students(studid),
            FOREIGN KEY (subjid) REFERENCES subjects(subjid)
        )
    """)
    conn.commit()

    # Auto-migrate: drop unique constraint if it still exists from old schema
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE table_schema = %s
        AND table_name = 'evaluations'
        AND index_name = 'unique_student_subject'
    """, (database_name,))
    if cursor.fetchone()[0] > 0:
        cursor.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_schema = %s
            AND table_name = 'evaluations'
            AND constraint_type = 'FOREIGN KEY'
        """, (database_name,))
        fk_names = [row[0] for row in cursor.fetchall()]
        for fk in fk_names:
            cursor.execute(f"ALTER TABLE evaluations DROP FOREIGN KEY `{fk}`")
        conn.commit()
        cursor.execute("ALTER TABLE evaluations DROP INDEX unique_student_subject")
        conn.commit()
        cursor.execute("""
            ALTER TABLE evaluations
            ADD CONSTRAINT fk_eval_studid FOREIGN KEY (studid) REFERENCES students(studid),
            ADD CONSTRAINT fk_eval_subjid FOREIGN KEY (subjid) REFERENCES subjects(subjid)
        """)
        conn.commit()

    # Get student information
    cursor.execute("""
        SELECT studid, studname, studcrs, yrlvl
        FROM students
        WHERE studid = %s
    """, (student_id,))
    student_info = cursor.fetchone()

    if not student_info:
        print("<script>alert('Student record not found');window.location.href = 'studrec.py';</script>")
        sys.exit()

    studid, studname, studcrs, yrlvl = student_info

    # Get subject information
    cursor.execute("""
        SELECT subjid, subjcode, subjdesc, subjunits, subjsched
        FROM subjects
        WHERE subjid = %s
    """, (subjid,))
    subject_info = cursor.fetchone()

    if not subject_info:
        print("<script>alert('Subject not found');window.location.href = 'studrec.py';</script>")
        sys.exit()

    subj_id, subj_code, subj_desc, subj_units, subj_sched = subject_info

    # Check enrollment
    cursor.execute(
        "SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s",
        (student_id, subjid)
    )
    is_enrolled = cursor.fetchone()[0] > 0

    if not is_enrolled:
        print("<script>alert('You are not enrolled in this subject');window.location.href = 'studrec.py';</script>")
        sys.exit()

    # Fetch all previous comments by this student for this subject
    cursor.execute(
        "SELECT evaluation_comment, eval_date FROM evaluations WHERE studid = %s AND subjid = %s ORDER BY eval_date ASC",
        (student_id, subjid)
    )
    previous_comments = cursor.fetchall()

    cursor.close()
    conn.close()

    # Build previous comments HTML
    previous_comments_html = ""
    if previous_comments:
        previous_comments_html = '<div style="margin-bottom:15px;">'
        previous_comments_html += '<p style="font-weight:bold; color:#555; margin-bottom:8px;">Previous comments:</p>'
        for pc_text, pc_date in previous_comments:
            previous_comments_html += f"""
            <div style="background:#f8f9fa; border-left:4px solid #2a5298; padding:10px 15px; margin-bottom:8px; border-radius:4px;">
                <div style="font-size:12px; color:#888; margin-bottom:4px;">{pc_date}</div>
                <div>{html.escape(str(pc_text))}</div>
            </div>"""
        previous_comments_html += '</div>'

    # Build inline status banner
    status_banner = ""
    if status_message:
        if status_type == "success":
            banner_style = "background:#d4edda; color:#155724; border:1px solid #c3e6cb;"
            icon = "&#10003;"
        else:
            banner_style = "background:#f8d7da; color:#721c24; border:1px solid #f5c6cb;"
            icon = "&#10007;"
        status_banner = f"""
        <div style="{banner_style} padding:14px 20px; border-radius:8px; margin-bottom:24px;
                    font-size:15px; font-weight:bold; display:flex; align-items:center; gap:10px;">
            <span style="font-size:18px;">{icon}</span>
            {status_message}
        </div>"""

    print(f"""
    <html>
    <head>
        <title>Student Evaluation Portal</title>
        <style>
            @import url('https://fonts.cdnfonts.com/css/hywenhei');
            * {{ font-family: HYWenHei, sans-serif !important; }}
            body {{
                font-family: HYWenHei, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 20px 40px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            .header-content {{
                display: flex;
                align-items: center;
            }}
            .logo {{
                width: 60px;
                height: 60px;
                margin-right: 20px;
                background: white;
                border-radius: 5px;
            }}
            .header-text {{ flex: 1; }}
            .header-title {{
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }}
            .header-subtitle {{
                font-size: 14px;
                opacity: 0.9;
                margin-top: 5px;
            }}
            .container {{
                max-width: 1200px;
                margin: 30px auto;
                padding: 0 20px;
            }}
            .page-title {{
                font-size: 28px;
                font-weight: bold;
                margin: 30px 0;
                color: #333;
            }}
            .back-button {{
                background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                margin-bottom: 30px;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }}
            .back-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            .section {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                margin-bottom: 30px;
            }}
            .section-title {{
                font-size: 20px;
                font-weight: bold;
                margin: 0 0 20px 0;
                color: #333;
                padding-bottom: 10px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .info-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .info-table td {{
                padding: 12px;
                border: 1px solid #ddd;
            }}
            .info-table td:first-child {{
                font-weight: bold;
                background-color: #f8f9fa;
                width: 150px;
            }}
            textarea {{
                width: 100%;
                min-height: 200px;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                font-family: HYWenHei, sans-serif;
                resize: vertical;
                box-sizing: border-box;
            }}
            textarea:focus {{
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
            }}
            .submit-button {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                transition: all 0.3s ease;
            }}
            .submit-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(30, 60, 114, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo"></div>
                <div class="header-text">
                    <div class="header-title">STUDENT INFORMATION SYSTEM</div>
                    <div class="header-subtitle">UNIVERSITY NAME</div>
                </div>
            </div>
        </div>

        <div class="container">
            <h1 class="page-title">Student Evaluation Portal</h1>

            <a href="studrec.py" class="back-button">Back to Student Record</a>

            {status_banner}

            <div class="section">
                <h2 class="section-title">Student Information</h2>
                <table class="info-table">
                    <tr>
                        <td>ID</td>
                        <td>{studid}</td>
                        <td>Course</td>
                        <td>{html.escape(str(studcrs))}</td>
                    </tr>
                    <tr>
                        <td>Name</td>
                        <td>{html.escape(str(studname))}</td>
                        <td>Year Level</td>
                        <td>{html.escape(str(yrlvl))}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2 class="section-title">Subject Information</h2>
                <table class="info-table">
                    <tr>
                        <td>ID</td>
                        <td>{subj_id}</td>
                    </tr>
                    <tr>
                        <td>Code</td>
                        <td>{html.escape(str(subj_code))}</td>
                    </tr>
                    <tr>
                        <td>Description</td>
                        <td>{html.escape(str(subj_desc))}</td>
                    </tr>
                    <tr>
                        <td>Units</td>
                        <td>{subj_units}</td>
                    </tr>
                    <tr>
                        <td>Schedule</td>
                        <td>{html.escape(str(subj_sched))}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2 class="section-title">Your Evaluation/Comments:</h2>
                <form method="POST" action="evaluate.py">
                    <input type="hidden" name="submit_comment" value="1">
                    <input type="hidden" name="subjid" value="{subjid}">
                    {previous_comments_html}
                    <textarea name="evaluation_comment" placeholder="Enter your thoughts here..."></textarea>
                    <button type="submit" class="submit-button">Submit Comment</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """)

except Exception as e:
    print(f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>")