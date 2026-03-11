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

# Only teachers and admins can access this page
if not (is_admin or is_teacher):
    print("<script>alert('Access Denied: This page is for teachers only');window.location.href = 'studrec.py';</script>")
    sys.exit()

# Get teacher ID from username
import re
teacher_id_match = re.search(r'^(\d{4})', username)
teacher_id = int(teacher_id_match.group(1)) if teacher_id_match else None

# Grade to numeric conversion
def letter_to_numeric(letter_grade):
    """Convert letter grade to numeric value"""
    grade_map = {
        'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D': 1.0, 'F': 0.0,
        'INC': 0.0, 'NG': 0.0
    }
    return grade_map.get(letter_grade, 0.0)

def numeric_to_letter(numeric_grade):
    """Convert numeric grade back to letter grade"""
    if numeric_grade >= 3.85: return 'A'
    elif numeric_grade >= 3.5: return 'A-'
    elif numeric_grade >= 3.15: return 'B+'
    elif numeric_grade >= 2.85: return 'B'
    elif numeric_grade >= 2.5: return 'B-'
    elif numeric_grade >= 2.15: return 'C+'
    elif numeric_grade >= 1.85: return 'C'
    elif numeric_grade >= 1.5: return 'C-'
    elif numeric_grade >= 0.5: return 'D'
    else: return 'F'

# Handle Calculate Final Grades action
calculate_action = form.getvalue("calculate_grades", "")
if calculate_action == "1":
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database=database_name
        )
        cursor = conn.cursor(buffered=True)
        
        # Get all grades that have all 4 components
        cursor.execute("""
            SELECT enroll_eid, prelim, midterm, prefinal, final
            FROM grades
            WHERE prelim IS NOT NULL AND prelim != 'NG'
            AND midterm IS NOT NULL AND midterm != 'NG'
            AND prefinal IS NOT NULL AND prefinal != 'NG'
            AND final IS NOT NULL AND final != 'NG'
        """)
        
        grades_to_calculate = cursor.fetchall()
        calculated_count = 0
        
        for grade_row in grades_to_calculate:
            eid, prelim, midterm, prefinal, final = grade_row
            
            # Convert to numeric
            prelim_num = letter_to_numeric(prelim)
            midterm_num = letter_to_numeric(midterm)
            prefinal_num = letter_to_numeric(prefinal)
            final_num = letter_to_numeric(final)
            
            # Calculate average
            average = (prelim_num + midterm_num + prefinal_num + final_num) / 4.0
            
            # Convert back to letter grade
            final_letter = numeric_to_letter(average)
            
            # Update the final grade
            cursor.execute("UPDATE grades SET final = %s WHERE enroll_eid = %s", (final_letter, eid))
            calculated_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"<script>alert('Final grades calculated for {calculated_count} students!');window.location.href = 'encodegrades.py';</script>")
        sys.exit()
        
    except Exception as e:
        print(f"<script>alert('Error calculating grades: {html.escape(str(e))}');window.location.href = 'encodegrades.py';</script>")
        sys.exit()

# Handle grade saving
save_action = form.getvalue("save_grades", "")
if save_action == "1":
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database=database_name
        )
        cursor = conn.cursor()

        for key in form.keys():
            if key.startswith("prelim_") or key.startswith("midterm_") or key.startswith("prefinal_") or key.startswith("final_"):
                parts = key.split("_")
                grade_type = parts[0]
                eid = parts[1]
                grade_value = form.getvalue(key, "")

                if grade_value and grade_value != "NG":
                    if grade_type == "prelim":
                        cursor.execute("UPDATE grades SET prelim = %s WHERE enroll_eid = %s", (grade_value, eid))
                    elif grade_type == "midterm":
                        cursor.execute("UPDATE grades SET midterm = %s WHERE enroll_eid = %s", (grade_value, eid))
                    elif grade_type == "prefinal":
                        cursor.execute("UPDATE grades SET prefinal = %s WHERE enroll_eid = %s", (grade_value, eid))
                    elif grade_type == "final":
                        cursor.execute("UPDATE grades SET final = %s WHERE enroll_eid = %s", (grade_value, eid))
                else:
                    if grade_type == "prelim":
                        cursor.execute("UPDATE grades SET prelim = %s WHERE enroll_eid = %s", (grade_value if grade_value else None, eid))
                    elif grade_type == "midterm":
                        cursor.execute("UPDATE grades SET midterm = %s WHERE enroll_eid = %s", (grade_value if grade_value else None, eid))
                    elif grade_type == "prefinal":
                        cursor.execute("UPDATE grades SET prefinal = %s WHERE enroll_eid = %s", (grade_value if grade_value else None, eid))
                    elif grade_type == "final":
                        cursor.execute("UPDATE grades SET final = %s WHERE enroll_eid = %s", (grade_value if grade_value else None, eid))

        conn.commit()
        cursor.close()
        conn.close()

        print("<script>alert('Grades saved successfully!');window.location.href = 'encodegrades.py';</script>")
        sys.exit()

    except Exception as e:
        print(f"<script>alert('Error saving grades: {html.escape(str(e))}');window.location.href = 'encodegrades.py';</script>")
        sys.exit()

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
        cursor.close()
        conn.close()
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database=database_name
        )
        cursor = conn.cursor()

    # Get subjects assigned to this teacher (if teacher)
    if is_teacher and teacher_id:
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched,
                   COUNT(DISTINCT e.studid) as num_students
            FROM subjects s
            INNER JOIN teacher_subjects ts ON s.subjid = ts.subjid
            LEFT JOIN enroll e ON s.subjid = e.subjid
            WHERE ts.tid = %s
            GROUP BY s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched
            ORDER BY s.subjid
        """, (teacher_id,))
    else:
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched,
                   COUNT(DISTINCT e.studid) as num_students
            FROM subjects s
            LEFT JOIN enroll e ON s.subjid = e.subjid
            GROUP BY s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched
            ORDER BY s.subjid
        """)

    assigned_subjects = cursor.fetchall()

    # Get enrolled students for each subject with their grades
    enrolled_students_by_subject = {}
    for subject in assigned_subjects:
        subjid = subject[0]
        cursor.execute("""
            SELECT e.eid, e.studid, st.studname,
                   g.prelim, g.midterm, g.prefinal, g.final
            FROM enroll e
            INNER JOIN students st ON e.studid = st.studid
            LEFT JOIN grades g ON e.eid = g.enroll_eid
            WHERE e.subjid = %s
            ORDER BY st.studname
        """, (subjid,))
        enrolled_students_by_subject[subjid] = cursor.fetchall()

    # Get SHOW GRANTS
    user_grants = []
    if not is_admin:
        try:
            cursor.execute(f"SHOW GRANTS FOR '{username}'@'localhost'")
            user_grants = [row[0] for row in cursor.fetchall()]
        except:
            pass
    else:
        try:
            cursor.execute("SHOW GRANTS FOR 'root'@'localhost'")
            user_grants = [row[0] for row in cursor.fetchall()]
        except:
            pass

    grade_options = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F', 'INC', 'NG']

    print(f"""
    <html>
    <head>
        <title>Encode Grades - Sumeru Akademiya</title>
        <style>
            @import url('https://fonts.cdnfonts.com/css/hywenhei');
            * {{ font-family: HYWenHei, sans-serif !important; }}
            body {{ font-family: HYWenHei, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
            .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 15px 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: space-between; }}
            .university-name {{ font-size: 24px; font-weight: bold; letter-spacing: 1px; line-height: 1.2; }}
            .subtitle {{ font-size: 14px; opacity: 0.9; margin-top: 3px; }}
            .main-container {{ max-width: 1400px; margin: 30px auto; padding: 20px; }}
            .logout-button {{ background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%); padding: 10px 20px; font-size: 14px; border-radius: 5px; color: white; cursor: pointer; transition: all 0.3s ease; border: none; }}
            .logout-button:hover {{ background: linear-gradient(135deg, #5a6268 0%, #4e555b 100%); transform: translateY(-2px); box-shadow: 0 6px 12px rgba(108,117,125,0.2); }}
            .section {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); margin-bottom: 30px; }}
            .section h2 {{ color: #1e3c72; margin-top: 0; border-bottom: 2px solid #1e3c72; padding-bottom: 10px; }}
            .section h3 {{ color: #2a5298; margin-top: 20px; }}
            table {{ border-collapse: collapse; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; margin-top: 15px; }}
            th {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 12px 10px; text-align: center; font-weight: bold; font-size: 14px; }}
            td {{ padding: 10px; border-bottom: 1px solid #e0e0e0; text-align: center; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            select {{ padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }}
            select:focus {{ outline: none; border-color: #2a5298; box-shadow: 0 0 0 2px rgba(42,82,152,0.2); }}
            .save-button {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; margin-top: 20px; margin-right: 10px; transition: all 0.3s ease; }}
            .save-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 12px rgba(40,167,69,0.3); }}
            .calculate-button {{ background: linear-gradient(135deg, #ff9800 0%, #ff5722 100%); color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; margin-top: 20px; transition: all 0.3s ease; }}
            .calculate-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 12px rgba(255,152,0,0.3); }}
            .info-text {{ color: #666; font-size: 14px; margin-bottom: 15px; }}
            .grants-box {{ background: #f0f8ff; border-left: 4px solid #1e3c72; padding: 15px; margin-top: 15px; border-radius: 4px; font-size: 13px; font-family: monospace !important; word-break: break-all; }}
            .grants-box p {{ margin: 4px 0; }}
            .students-section {{ display: none; }}
            .students-section.open {{ display: block; }}
            .button-group {{ display: flex; justify-content: center; gap: 10px; }}
        </style>
        <script>
            function logout() {{
                if (confirm('Are you sure you want to logout?')) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'encodegrades.py';
                    let logoutInput = document.createElement('input');
                    logoutInput.type = 'hidden';
                    logoutInput.name = 'logout_action';
                    logoutInput.value = '1';
                    form.appendChild(logoutInput);
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}

            function showStudents(subjid) {{
                document.querySelectorAll('.students-section').forEach(function(el) {{
                    el.classList.remove('open');
                }});
                var section = document.getElementById('students_' + subjid);
                if (section) {{
                    section.classList.add('open');
                    section.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }}
            
            function calculateFinalGrades() {{
                if (confirm('Calculate final grades for all students with complete grades (Prelim, Midterm, Prefinal)?\\n\\nFormula: (Prelim + Midterm + Prefinal + Final) / 4')) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'encodegrades.py';
                    let input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'calculate_grades';
                    input.value = '1';
                    form.appendChild(input);
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}
        </script>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="university-name">Sumeru Akademiya</div>
                <div class="subtitle">Grade Encoding System</div>
                <div class="subtitle">Database: {html.escape(database_name)} | User: {html.escape(username)} ({'Administrator' if is_admin else 'Teacher'})</div>
            </div>
            <button onclick="logout()" class="logout-button">Logout</button>
        </div>

        <div class="main-container">
    """)

    # Show GRANTS section
    if user_grants:
        print("""
        <div class="section">
            <h2>User Privileges (SHOW GRANTS)</h2>
            <div class="grants-box">
        """)
        for grant in user_grants:
            print(f"<p>{html.escape(str(grant))}</p>")
        print("""
            </div>
        </div>
        """)

    print("""
        <form method="POST" action="encodegrades.py">
            <input type="hidden" name="save_grades" value="1">
    """)

    if not assigned_subjects:
        print("""
            <div class="section">
                <h2>No Assigned Subjects</h2>
                <p class="info-text">You are not assigned to any subjects yet. Please contact an administrator.</p>
            </div>
        """)
    else:
        # Assigned Subjects summary table
        print("""
            <div class="section">
                <h2>Assigned Subjects</h2>
                <p class="info-text">Click a Subject ID to view and encode grades for that subject.</p>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                            <th>#Stud</th>
                            <th>StudEval</th>
                        </tr>
                    </thead>
                    <tbody>
        """)
        for subject in assigned_subjects:
            subjid, subjcode, subjdesc, subjunits, subjsched, num_students = subject
            print(f"""
                        <tr>
                            <td><a href="javascript:void(0)" onclick="showStudents('{subjid}')" style="color: #1a0dab; text-decoration: underline; cursor: pointer; font-weight: bold;">{subjid}</a></td>
                            <td>{html.escape(str(subjcode))}</td>
                            <td>{html.escape(str(subjdesc))}</td>
                            <td>{subjunits}</td>
                            <td>{html.escape(str(subjsched))}</td>
                            <td>{num_students}</td>
                            <td><a href="sentiment.py?subjid={subjid}" style="color: #0066cc; text-decoration: underline; cursor: pointer;">Open</a></td>
                        </tr>
            """)
        print("""
                    </tbody>
                </table>
            </div>
        """)

        # Enrolled Students per subject - all rendered but hidden by default
        for subject in assigned_subjects:
            subjid, subjcode, subjdesc, subjunits, subjsched, num_students = subject
            enrolled_students = enrolled_students_by_subject.get(subjid, [])

            print(f"""
            <div class="section students-section" id="students_{subjid}">
                <h2>Enrolled Students - {html.escape(str(subjcode))}: {html.escape(str(subjdesc))}</h2>
                <p class="info-text">Edit grades below. Click "Calculate Final Grades" to automatically compute final grades based on all four periods.</p>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Prelim</th>
                            <th>Midterm</th>
                            <th>Prefinal</th>
                            <th>Final</th>
                        </tr>
                    </thead>
                    <tbody>
            """)

            if not enrolled_students:
                print("<tr><td colspan='6' style='text-align: center; padding: 20px; color: #666;'>No students enrolled</td></tr>")
            else:
                for student in enrolled_students:
                    eid, studid, studname, prelim, midterm, prefinal, final = student

                    prelim_val   = prelim   if prelim   else "NG"
                    midterm_val  = midterm  if midterm  else "NG"
                    prefinal_val = prefinal if prefinal else "NG"
                    final_val    = final    if final    else "NG"

                    print(f"""
                    <tr>
                        <td>{studid}</td>
                        <td>{html.escape(str(studname))}</td>
                        <td>
                            <select name="prelim_{eid}">
                    """)
                    for grade in grade_options:
                        selected = "selected" if grade == prelim_val else ""
                        print(f"<option value='{grade}' {selected}>{grade}</option>")
                    print(f"""
                            </select>
                        </td>
                        <td>
                            <select name="midterm_{eid}">
                    """)
                    for grade in grade_options:
                        selected = "selected" if grade == midterm_val else ""
                        print(f"<option value='{grade}' {selected}>{grade}</option>")
                    print(f"""
                            </select>
                        </td>
                        <td>
                            <select name="prefinal_{eid}">
                    """)
                    for grade in grade_options:
                        selected = "selected" if grade == prefinal_val else ""
                        print(f"<option value='{grade}' {selected}>{grade}</option>")
                    print(f"""
                            </select>
                        </td>
                        <td>
                            <select name="final_{eid}">
                    """)
                    for grade in grade_options:
                        selected = "selected" if grade == final_val else ""
                        print(f"<option value='{grade}' {selected}>{grade}</option>")
                    print("""
                            </select>
                        </td>
                    </tr>
                    """)

            print("""
                    </tbody>
                </table>
            </div>
            """)

    print("""
                <div class="button-group">
                    <button type="submit" class="save-button">Save Grades</button>
                    <button type="button" onclick="calculateFinalGrades()" class="calculate-button">Calculate Final Grades</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """)

    cursor.close()
    conn.close()

except Exception as e:
    print(f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>")