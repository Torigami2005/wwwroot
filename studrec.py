#!/usr/bin/env python3
import cgi
import mysql.connector
import html
import sys
import os
import http.cookies

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
import re
student_id_match = re.search(r'^(\d{4})', username)
student_id = int(student_id_match.group(1)) if student_id_match else None

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database=database_name
    )
    cursor = conn.cursor()

    # Check which grade columns exist and add any that are missing
    grade_cols = ['prelim', 'midterm', 'prefinal', 'final']
    cursor.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'grades'
    """, (database_name,))
    existing_cols = [row[0].lower() for row in cursor.fetchall()]

    schema_changed = False
    for col in grade_cols:
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE grades ADD COLUMN {col} VARCHAR(5)")
                schema_changed = True
            except:
                pass

    if schema_changed:
        conn.commit()
        # Close and reconnect so MySQL reflects the new schema
        cursor.close()
        conn.close()
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database=database_name
        )
        cursor = conn.cursor()

    # Get student information
    cursor.execute("""
        SELECT studid, studname, studcrs, yrlvl
        FROM students
        WHERE studid = %s
    """, (student_id,))
    student_info = cursor.fetchone()

    if not student_info:
        print("<script>alert('Student record not found');window.location.href = 'index.py';</script>")
        sys.exit()

    studid, studname, studcrs, yrlvl = student_info

    # Get enrolled subjects with grades
    cursor.execute("""
        SELECT s.subjid, s.subjcode, g.prelim, g.midterm, g.prefinal, g.final
        FROM enroll e
        INNER JOIN subjects s ON e.subjid = s.subjid
        LEFT JOIN grades g ON e.eid = g.enroll_eid
        WHERE e.studid = %s
        ORDER BY s.subjid
    """, (student_id,))
    enrolled_subjects = cursor.fetchall()

    # Get SHOW GRANTS for the logged-in student user
    user_grants = []
    try:
        cursor.execute(f"SHOW GRANTS FOR '{username}'@'localhost'")
        user_grants = [row[0] for row in cursor.fetchall()]
    except:
        pass

    # HTML output
    print(f"""
    <html>
    <head>
        <title>Student Grade Sheet - Sumeru Akademiya</title>
        <style>
            @import url('https://fonts.cdnfonts.com/css/hywenhei');
            * {{ font-family: HYWenHei, sans-serif !important; }}
            body {{
                font-family: HYWenHei, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #ffffff;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background: white;
                padding: 40px;
            }}
            .header-section {{
                text-align: center;
                margin-bottom: 40px;
                border-bottom: 2px solid #000;
                padding-bottom: 20px;
            }}
            .university-name {{
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
                text-transform: uppercase;
            }}
            .office-name {{
                font-size: 18px;
                margin: 5px 0;
            }}
            .sheet-title {{
                font-size: 22px;
                font-weight: bold;
                margin-top: 30px;
            }}
            .student-info {{
                margin: 30px 0;
                line-height: 2;
            }}
            .info-row {{
                display: flex;
                margin: 10px 0;
            }}
            .info-label {{
                font-weight: bold;
                min-width: 180px;
            }}
            .info-value {{
                flex: 1;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 30px 0;
            }}
            th, td {{
                border: 2px solid #000;
                padding: 12px;
                text-align: center;
            }}
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .subjects-count {{
                font-weight: bold;
                margin-top: 20px;
                font-size: 16px;
            }}
            .logout-button {{
                position: fixed;
                top: 20px;
                right: 20px;
                background: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            }}
            .logout-button:hover {{
                background: #c82333;
            }}
            .grants-section {{
                margin-top: 40px;
                border-top: 2px solid #000;
                padding-top: 20px;
            }}
            .grants-section h3 {{
                font-size: 18px;
                margin-bottom: 10px;
            }}
            .grants-box {{
                background: #f0f8ff;
                border-left: 4px solid #1e3c72;
                padding: 15px;
                border-radius: 4px;
                font-size: 13px;
                font-family: monospace !important;
                word-break: break-all;
            }}
            .grants-box p {{
                margin: 4px 0;
            }}
            @media print {{
                .logout-button {{ display: none; }}
            }}
        </style>
        <script>
            function logout() {{
                if (confirm('Are you sure you want to logout?')) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'studrec.py';

                    let logoutInput = document.createElement('input');
                    logoutInput.type = 'hidden';
                    logoutInput.name = 'logout_action';
                    logoutInput.value = '1';
                    form.appendChild(logoutInput);

                    document.body.appendChild(form);
                    form.submit();
                }}
            }}
        </script>
    </head>
    <body>
        <button onclick="logout()" class="logout-button">Logout</button>

        <div class="container">
            <div class="header-section">
                <div class="university-name">UNIVERSITY NAME</div>
                <div class="office-name">Registrars Office</div>
                <div class="sheet-title">Student Grade Sheet</div>
            </div>

            <div class="student-info">
                <div class="info-row">
                    <div class="info-label">Student ID</div>
                    <div class="info-value">{studid}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">School Year</div>
                    <div class="info-value">{html.escape(database_name)}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Student Name</div>
                    <div class="info-value">{html.escape(str(studname))}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Student Course</div>
                    <div class="info-value">{html.escape(str(studcrs))}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Student Year</div>
                    <div class="info-value">{html.escape(str(yrlvl))}</div>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>SubjID</th>
                        <th>Subj Code</th>
                        <th>Prelim</th>
                        <th>Midterm</th>
                        <th>Prefinal</th>
                        <th>Final</th>
                    </tr>
                </thead>
                <tbody>
    """)

    if not enrolled_subjects:
        print("<tr><td colspan='6' style='padding: 30px;'>No subjects enrolled</td></tr>")
    else:
        for subject in enrolled_subjects:
            subjid, subjcode, prelim, midterm, prefinal, final = subject

            prelim_display = prelim if prelim else ""
            midterm_display = midterm if midterm else ""
            prefinal_display = prefinal if prefinal else ""
            final_display = final if final else ""

            print(f"""
                <tr>
                    <td>{subjid}</td>
                    <td>{html.escape(str(subjcode))}</td>
                    <td>{html.escape(str(prelim_display))}</td>
                    <td>{html.escape(str(midterm_display))}</td>
                    <td>{html.escape(str(prefinal_display))}</td>
                    <td>{html.escape(str(final_display))}</td>
                </tr>
            """)

    num_subjects = len(enrolled_subjects)

    print(f"""
                </tbody>
            </table>

            <div class="subjects-count">
                Number of Subjects Listed: {num_subjects}
            </div>
    """)

    # Show GRANTS section
    if user_grants:
        print("""
            <div class="grants-section">
                <h3>User Privileges (SHOW GRANTS)</h3>
                <div class="grants-box">
        """)
        for grant in user_grants:
            print(f"<p>{html.escape(str(grant))}</p>")
        print("""
                </div>
            </div>
        """)

    print("""
        </div>
    </body>
    </html>
    """)

    cursor.close()
    conn.close()

except Exception as e:
    print(f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>")