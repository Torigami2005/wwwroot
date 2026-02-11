#!/usr/bin/env python3
import cgi
import mysql.connector
import html
import sys
import os
import http.cookies
from datetime import datetime

print("Content-Type: text/html")

form = cgi.FieldStorage()

# Handle logout first
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

# Session check with RBAC
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

# SECURITY FUNCTION: Redirect students attempting CRUD
def redirect_student_crud_security(action_type, is_student):
    """Redirect student to index.py if attempting CRUD actions"""
    if is_student and action_type in ["insert", "update", "delete"]:
        return True
    return False

# Create new semester database - ADMIN ONLY
create_db_action = form.getvalue("create_db_action", "")
semester_selection = form.getvalue("semester_selection", "")

if create_db_action == "1":
    if not is_admin:
        print("<script>alert('Access Denied: Admin privileges required');window.location.href = 'subjects.py';</script>")
        sys.exit()
    
    if semester_selection:
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            cursor = conn.cursor()

            current_year = datetime.now().year
            next_year = current_year + 1

            if semester_selection == "1st":
                new_db_name = f"1stsem_{current_year}_{next_year}"
            elif semester_selection == "2nd":
                new_db_name = f"2ndsem_{current_year}_{next_year}"
            elif semester_selection == "summer":
                new_db_name = f"summer_{current_year}_{next_year}"
            else:
                new_db_name = "enrollmentsystem"

            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {new_db_name}")
            cursor.execute(f"USE {new_db_name}")

            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    studid INT PRIMARY KEY,
                    studname VARCHAR(100) NOT NULL,
                    studadd VARCHAR(200),
                    studcrs VARCHAR(50),
                    studgender VARCHAR(10),
                    yrlvl VARCHAR(10)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    subjid INT PRIMARY KEY,
                    subjcode VARCHAR(20) NOT NULL,
                    subjdesc VARCHAR(100),
                    subjunits INT,
                    subjsched VARCHAR(50)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enroll (
                    eid INT AUTO_INCREMENT PRIMARY KEY,
                    studid INT,
                    subjid INT,
                    FOREIGN KEY (studid) REFERENCES students(studid),
                    FOREIGN KEY (subjid) REFERENCES subjects(subjid)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grades (
                    gradeid INT AUTO_INCREMENT PRIMARY KEY,
                    enroll_eid INT,
                    grade DECIMAL(5,2),
                    FOREIGN KEY (enroll_eid) REFERENCES enroll(eid)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    tid INT PRIMARY KEY,
                    tname VARCHAR(100) NOT NULL,
                    tdept VARCHAR(50),
                    tadd VARCHAR(200),
                    tcontact VARCHAR(50),
                    tstatus VARCHAR(20)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teacher_subjects (
                    tsid INT AUTO_INCREMENT PRIMARY KEY,
                    tid INT,
                    subjid INT,
                    FOREIGN KEY (tid) REFERENCES teachers(tid),
                    FOREIGN KEY (subjid) REFERENCES subjects(subjid)
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()

            session_id = cookies.get('session_id').value if cookies.get('session_id') else ""
            print(f"Set-Cookie: session_id={session_id}; path=/; HttpOnly; SameSite=Lax")
            print(f"Set-Cookie: username={username}; path=/; SameSite=Lax")
            print(f"Set-Cookie: database={new_db_name}; path=/; SameSite=Lax")
            print(f"Set-Cookie: user_role={user_role}; path=/; SameSite=Lax")
            print()

            print(f"<script>alert('New database \"{new_db_name}\" created successfully!');window.location.href = 'subjects.py?created=1';</script>")
            sys.exit()

        except Exception as e:
            error_msg = f"Database creation failed: {str(e)}"
            print()
            print(f"<script>alert('{error_msg}');window.location.href = 'subjects.py';</script>")
            sys.exit()

# Form values
action_type = form.getvalue("action_type", "")
subjid = form.getvalue("subjid", "")
subjcode = html.escape(form.getvalue("subjcode", ""))
subjdesc = html.escape(form.getvalue("subjdesc", ""))
subjunits = form.getvalue("subjunits", "")
subjsched = html.escape(form.getvalue("subjsched", ""))

# For enrollment by teachers
selected_studid = form.getvalue("selected_studid", "")
selected_subjid = form.getvalue("selected_subjid", "")
subject_action = form.getvalue("subject_action", "")

# URL parameters
url_subjid = form.getvalue("subjid", "")

# SECURITY CHECK: Redirect students attempting CRUD actions
if redirect_student_crud_security(action_type, is_student):
    print()
    print("<script>alert('Security Alert: Students cannot modify subject records. Redirecting to login.');window.location.href = 'index.py';</script>")
    sys.exit()

# RBAC Check for subject CRUD operations - ADMIN OR TEACHER
if action_type in ["insert", "update", "delete"] and not (is_admin or is_teacher):
    print("<script>alert('Access Denied: Only administrators or teachers can modify subject records');window.location.href = 'subjects.py';</script>")
    sys.exit()

# RBAC Check for enrollment operations - ADMIN OR TEACHER
if subject_action in ["enroll", "drop"] and not (is_admin or is_teacher):
    print("<script>alert('Access Denied: Only administrators or teachers can enroll/drop students');window.location.href = 'subjects.py';</script>")
    sys.exit()

def parse_time(time_str):
    """Parse time string (HHMM or HH:MM) to minutes"""
    try:
        # Remove colons if present
        time_str = time_str.replace(':', '')
        
        if len(time_str) == 3:  # Handle HMM format
            hours = int(time_str[0])
            minutes = int(time_str[1:3])
        elif len(time_str) == 4:  # Handle HHMM format
            hours = int(time_str[0:2])
            minutes = int(time_str[2:4])
        else:
            return None
            
        return hours * 60 + minutes
    except:
        return None

def check_schedule_conflict(cursor, student_id, subject_id):
    """Check if enrolling a student in a subject would create a schedule conflict"""
    try:
        # Get the schedule of the new subject
        cursor.execute("SELECT subjsched FROM subjects WHERE subjid = %s", (subject_id,))
        new_subject = cursor.fetchone()
        if not new_subject or not new_subject[0]:
            return None  # No schedule to check
            
        new_sched = new_subject[0].strip()
        if not new_sched or len(new_sched) < 3:
            return None
            
        # Parse new schedule (format: "MWF 0830-1000" or "MWF 08:30-10:00")
        new_days = new_sched[:3].upper()
        
        # Find time part
        time_part_start = 3
        while time_part_start < len(new_sched) and new_sched[time_part_start] == ' ':
            time_part_start += 1
            
        time_part = new_sched[time_part_start:].strip()
        if '-' not in time_part:
            return None
            
        new_stime_str, new_etime_str = time_part.split('-')
        new_stime_str = new_stime_str.strip()
        new_etime_str = new_etime_str.strip()
        
        new_start_minutes = parse_time(new_stime_str)
        new_end_minutes = parse_time(new_etime_str)
        
        if new_start_minutes is None or new_end_minutes is None:
            return None  # Invalid time format
            
        # Get other subjects enrolled by this student
        cursor.execute("""
            SELECT s.subjcode, s.subjsched 
            FROM subjects s 
            INNER JOIN enroll e ON s.subjid = e.subjid 
            WHERE e.studid = %s 
            AND s.subjsched IS NOT NULL 
            AND s.subjsched != ''
        """, (student_id,))
        enrolled_subjects = cursor.fetchall()
        
        # Check each enrolled subject
        for enrolled_code, enrolled_sched in enrolled_subjects:
            if enrolled_sched and len(enrolled_sched.strip()) >= 3:
                old_sched = enrolled_sched.strip()
                old_days = old_sched[:3].upper()
                
                # Only check if same days
                if old_days == new_days:
                    # Parse old schedule
                    old_time_part_start = 3
                    while old_time_part_start < len(old_sched) and old_sched[old_time_part_start] == ' ':
                        old_time_part_start += 1
                    
                    old_time_part = old_sched[old_time_part_start:].strip()
                    if '-' not in old_time_part:
                        continue
                    
                    old_stime_str, old_etime_str = old_time_part.split('-')
                    old_stime_str = old_stime_str.strip()
                    old_etime_str = old_etime_str.strip()
                    
                    old_start_minutes = parse_time(old_stime_str)
                    old_end_minutes = parse_time(old_etime_str)
                    
                    if old_start_minutes is None or old_end_minutes is None:
                        continue  # Skip invalid time format
                    
                    # Check for time overlap
                    if not (new_end_minutes <= old_start_minutes or new_start_minutes >= old_end_minutes):
                        return f"Schedule conflict with {enrolled_code} ({old_sched})"
    except Exception as e:
        return f"Error checking schedule: {str(e)}"
    
    return None  # No conflict

def get_teacher_id_from_username(cursor, username):
    """Get teacher ID from username"""
    try:
        import re
        numbers = re.findall(r'\d+', username)
        if numbers:
            teacher_id = int(numbers[0])
            cursor.execute("SELECT tid FROM teachers WHERE tid = %s", (teacher_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
        
        cursor.execute("SELECT tid FROM teachers WHERE tname LIKE %s", (f"%{username}%",))
        result = cursor.fetchone()
        if result:
            return result[0]
        
        cursor.execute("SELECT tid FROM teachers WHERE tname = %s", (username,))
        result = cursor.fetchone()
        if result:
            return result[0]
            
        return None
    except:
        return None

def get_student_id_from_username(cursor, username):
    """Get student ID from username"""
    try:
        import re
        numbers = re.findall(r'\d+', username)
        if numbers:
            student_id = int(numbers[0])
            cursor.execute("SELECT studid FROM students WHERE studid = %s", (student_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
        
        cursor.execute("SELECT studid FROM students WHERE studname LIKE %s", (f"%{username}%",))
        result = cursor.fetchone()
        if result:
            return result[0]
        
        cursor.execute("SELECT studid FROM students WHERE studname = %s", (username,))
        result = cursor.fetchone()
        if result:
            return result[0]
            
        return None
    except:
        return None

try:
    # Connect to MySQL database
    if is_admin:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database=database_name
        )
    else:
        # For teachers and students
        name_only = ''.join([c for c in username if not c.isdigit()])
        mysql_password = f"AdDU{name_only}"
        
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user=username,
                password=mysql_password,
                database=database_name
            )
        except mysql.connector.Error as e:
            print(f"<script>alert('Access Denied: Cannot connect to database');window.location.href = 'index.py';</script>")
            sys.exit()
    
    cursor = conn.cursor()

    # Check required tables
    cursor.execute("SHOW TABLES LIKE 'subjects'")
    subjects_table_exists = cursor.fetchone() is not None

    cursor.execute("SHOW TABLES LIKE 'enroll'")
    enroll_table_exists = cursor.fetchone() is not None

    cursor.execute("SHOW TABLES LIKE 'students'")
    students_table_exists = cursor.fetchone() is not None

    cursor.execute("SHOW TABLES LIKE 'teachers'")
    teachers_table_exists = cursor.fetchone() is not None

    cursor.execute("SHOW TABLES LIKE 'teacher_subjects'")
    teacher_subjects_table_exists = cursor.fetchone() is not None

    if not subjects_table_exists:
        print(f"<html><body><h1>Error</h1><p>Table 'subjects' doesn't exist in database '{database_name}'.</p></body></html>")
        cursor.close()
        conn.close()
        sys.exit()

    # Handle subject CRUD (ADMIN OR TEACHER)
    if action_type == "insert" and subjcode:
        try:
            cursor.execute("SELECT MAX(subjid) FROM subjects")
            result = cursor.fetchone()
            max_subjid = result[0]
            if max_subjid is None:
                next_subjid = 2000
            else:
                next_subjid = max(max_subjid + 1, 2000)

            cursor.execute(
                "INSERT INTO subjects (subjid, subjcode, subjdesc, subjunits, subjsched) VALUES (%s, %s, %s, %s, %s)",
                (next_subjid, subjcode, subjdesc, int(subjunits) if subjunits else 0, subjsched)
            )
            conn.commit()
            print(f"<script>window.location.href='subjects.py?subjid={next_subjid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='subjects.py?error={html.escape(str(e))}';</script>")

    elif action_type == "update" and subjid and subjcode:
        try:
            cursor.execute(
                "UPDATE subjects SET subjcode=%s, subjdesc=%s, subjunits=%s, subjsched=%s WHERE subjid=%s",
                (subjcode, subjdesc, int(subjunits) if subjunits else 0, subjsched, subjid)
            )
            conn.commit()
            print(f"<script>window.location.href='subjects.py?subjid={subjid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='subjects.py?subjid={subjid}&error={html.escape(str(e))}';</script>")

    elif action_type == "delete" and subjid:
        try:
            # Delete from related tables first
            cursor.execute("DELETE FROM enroll WHERE subjid=%s", (subjid,))
            cursor.execute("DELETE FROM teacher_subjects WHERE subjid=%s", (subjid,))
            cursor.execute("DELETE FROM subjects WHERE subjid=%s", (subjid,))
            conn.commit()
            print("<script>window.location.href='subjects.py';</script>")
        except Exception as e:
            print(f"<script>window.location.href='subjects.py?subjid={subjid}&error={html.escape(str(e))}';</script>")

    # Handle enrollment by teachers (ADMIN OR TEACHER)
    if subject_action == "enroll" and selected_studid and selected_subjid:
        try:
            cursor.execute("SELECT COUNT(*) FROM students WHERE studid = %s", (selected_studid,))
            student_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM subjects WHERE subjid = %s", (selected_subjid,))
            subject_count = cursor.fetchone()[0]
            if student_count == 0 or subject_count == 0:
                error_msg = "Student or Subject not found"
                redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid))
            count = cursor.fetchone()[0]
            if count > 0:
                error_msg = "Student is already enrolled in this subject"
                redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()

            # Check for schedule conflicts
            conflict_msg = check_schedule_conflict(cursor, selected_studid, selected_subjid)
            if conflict_msg:
                redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(conflict_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()

            cursor.execute("INSERT INTO enroll (studid, subjid) VALUES (%s, %s)", (selected_studid, selected_subjid))
            conn.commit()
            cursor.execute("SELECT eid FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid))
            result = cursor.fetchone()
            if result:
                eid = result[0]
                cursor.execute("INSERT INTO grades (enroll_eid) VALUES (%s)", (eid,))
                conn.commit()
            
            redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&success=Student enrolled successfully'
            print(f"<script>window.location.href='{redirect_url}';</script>")
        except Exception as e:
            error_msg = f"Enrollment failed: {str(e)}"
            redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
    elif subject_action == "drop" and selected_studid and selected_subjid:
        try:
            cursor.execute("SELECT eid FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid))
            result = cursor.fetchone()
            if result:
                eid = result[0]
                cursor.execute("DELETE FROM grades WHERE enroll_eid = %s", (eid,))
                cursor.execute("DELETE FROM enroll WHERE eid = %s", (eid,))
                conn.commit()
                redirect_url = f'subjects.py?studid={selected_studid}&success=Subject dropped successfully'
                if selected_subjid:
                    redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&success=Subject dropped successfully'
                print(f"<script>window.location.href='{redirect_url}';</script>")
            else:
                redirect_url = f'subjects.py?studid={selected_studid}&error=Student is not enrolled in this subject'
                if selected_subjid:
                    redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}&error=Student is not enrolled in this subject'
                print(f"<script>window.location.href='{redirect_url}';</script>")
        except Exception as e:
            redirect_url = f'subjects.py?studid={selected_studid}'
            if selected_subjid:
                redirect_url = f'subjects.py?studid={selected_studid}&subjid={selected_subjid}'
            print(f"<script>window.location.href='{redirect_url}';</script>")

    # Get subjects based on user role
    subjects = []
    teacher_assigned_subjects = []
    student_enrolled_subjects = []
    
    if is_admin:
        # Admin can see all subjects
        cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects ORDER BY subjid")
        subjects = cursor.fetchall()
    
    elif is_teacher:
        # Teachers can see all subjects (for enrollment)
        cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects ORDER BY subjid")
        subjects = cursor.fetchall()
        
        # Get assigned subjects for teacher
        teacher_id = get_teacher_id_from_username(cursor, username)
        if teacher_id and teacher_subjects_table_exists:
            cursor.execute("""
                SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
                FROM subjects s 
                INNER JOIN teacher_subjects ts ON s.subjid = ts.subjid 
                WHERE ts.tid = %s 
                ORDER BY s.subjid
            """, (teacher_id,))
            teacher_assigned_subjects = cursor.fetchall()
    
    elif is_student:
        # Students can only see subjects they are enrolled in
        student_id = get_student_id_from_username(cursor, username)
        if student_id and enroll_table_exists:
            cursor.execute("""
                SELECT DISTINCT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
                FROM subjects s 
                INNER JOIN enroll e ON s.subjid = e.subjid 
                WHERE e.studid = %s 
                ORDER BY s.subjid
            """, (student_id,))
            subjects = cursor.fetchall()
            student_enrolled_subjects = subjects
        else:
            subjects = []
    else:
        cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects ORDER BY subjid")
        subjects = cursor.fetchall()

    # Get enrolled students for selected subject
    enrolled_students = []
    teacher_of_subject = None
    if url_subjid and enroll_table_exists and students_table_exists:
        # Get enrolled students
        cursor.execute("""
            SELECT s.studid, s.studname, s.studcrs, s.yrlvl
            FROM enroll e
            JOIN students s ON e.studid = s.studid
            WHERE e.subjid = %s
            ORDER BY s.studid
        """, (url_subjid,))
        enrolled_students = cursor.fetchall()
        
        # Get teacher assigned to this subject
        if teacher_subjects_table_exists and teachers_table_exists:
            cursor.execute("""
                SELECT t.tid, t.tname, t.tdept
                FROM teachers t
                INNER JOIN teacher_subjects ts ON t.tid = ts.tid
                WHERE ts.subjid = %s
            """, (url_subjid,))
            teacher_result = cursor.fetchone()
            if teacher_result:
                teacher_of_subject = {
                    'tid': teacher_result[0],
                    'tname': teacher_result[1],
                    'tdept': teacher_result[2]
                }

    # URL parameters
    error_msg = form.getvalue("error", "")
    success_msg = form.getvalue("success", "")
    created_msg = form.getvalue("created", "")

    # Pre-fill form
    prefill_data = {}
    if url_subjid:
        cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects WHERE subjid = %s", (url_subjid,))
        row = cursor.fetchone()
        if row:
            prefill_data = {
                'subjid': str(row[0]) if row[0] else '',
                'subjcode': row[1] or '',
                'subjdesc': row[2] or '',
                'subjunits': str(row[3]) if row[3] is not None else '',
                'subjsched': row[4] or ''
            }

    # Determine role display
    role_display = ""
    if is_admin:
        role_display = "Administrator"
    elif is_teacher:
        role_display = "Teacher"
    elif is_student:
        role_display = "Student"

    # HTML output starts here
    print(f"""
    <html>
    <head>
        <title>Sumeru Akademiya - Subject Management System</title>
        <style>
            * {{
                font-family: HYWenHei, sans-serif !important;
            }}
            
            body {{
                font-family: HYWenHei, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            
            .header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 15px 30px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            
            .header-left {{
                display: flex;
                align-items: center;
            }}
            
            .logo {{
                height: 70px;
                width: 70px;
                margin-right: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            
            .university-info {{
                display: flex;
                flex-direction: column;
            }}
            
            .university-name {{
                font-size: 28px;
                font-weight: bold;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                letter-spacing: 1px;
                line-height: 1.2;
            }}
            
            .subtitle {{
                font-size: 16px;
                opacity: 0.9;
                margin-top: 3px;
            }}
            
            .nav-link {{
                color: white;
                text-decoration: none;
                background-color: rgba(255, 255, 255, 0.2);
                padding: 8px 20px;
                border-radius: 20px;
                transition: all 0.3s ease;
                font-size: 14px;
            }}
            
            .nav-link:hover {{
                background-color: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }}
            
            .main-container {{
                max-width: 1400px;
                margin: 30px auto;
                padding: 20px;
            }}
            
            button {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                font-family: HYWenHei;
            }}
            
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }}
            
            button:disabled {{
                background: #cccccc;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
                opacity: 0.6;
            }}
            
            .logout-button {{
                background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
                color: white;
                cursor: pointer;
                transition: all 0.3s ease;
                border: none;
            }}
            
            .logout-button:hover {{
                background: linear-gradient(135deg, #5a6268 0%, #4e555b 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(108, 117, 125, 0.2);
            }}
            
            .semester-selection {{
                display: flex;
                gap: 10px;
                margin-top: 10px;
                justify-content: center;
            }}
            
            .semester-btn {{ 
                padding: 10px 20px; 
                background: linear-gradient(135deg, #6f42c1 0%, #6610f2 100%); 
                color: white; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                font-family: HYWenHei;
                font-size: 14px;
            }}
            .semester-btn:hover:not(:disabled) {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(111, 66, 193, 0.3); }}
            
            input, select {{
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }}
            
            input:focus, select:focus {{
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
            }}
            
            input:disabled, select:disabled {{
                background-color: #f5f5f5;
                cursor: not-allowed;
            }}
            
            .error-message {{
                background-color: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #f5c6cb;
                text-align: center;
                font-weight: bold;
            }}
            
            .success-message {{
                background-color: #d4edda;
                color: #155724;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #c3e6cb;
                text-align: center;
                font-weight: bold;
            }}
            
            .warning-message {{
                background-color: #fff3cd;
                color: #856404;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #ffeaa7;
                text-align: center;
                font-weight: bold;
            }}
            
            .info-message {{
                background-color: #d1ecf1;
                color: #0c5460;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #bee5eb;
                text-align: center;
                font-weight: bold;
            }}
            
            table {{
                border-collapse: collapse;
                width: 100%;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                overflow: hidden;
            }}
            
            th {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 12px 15px;
                text-align: center;
                font-weight: bold;
                font-size: 16px;
            }}
            
            td {{
                padding: 12px 15px;
                border-bottom: 1px solid #e0e0e0;
                text-align: center;
                transition: background-color 0.2s ease;
            }}
            
            tr:hover {{
                background-color: rgba(42, 82, 152, 0.05);
                cursor: pointer;
            }}
            
            .selected-row {{
                background-color: rgba(42, 82, 152, 0.15) !important;
                font-weight: bold;
            }}
            
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            
            tr:nth-child(even):hover {{
                background-color: rgba(42, 82, 152, 0.08);
            }}
            
            .form-container {{
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                margin-bottom: 30px;
            }}
            
            .form-container h2 {{
                color: #1e3c72;
                margin-top: 0;
                border-bottom: 2px solid #1e3c72;
                padding-bottom: 10px;
            }}
            
            .two-column-layout {{
                display: grid;
                grid-template-columns: 1fr 1.5fr;
                gap: 30px;
            }}
            
            .enroll-buttons-container {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
                margin-top: 15px;
            }}
            
            .create-db-section {{ 
                background: white; 
                padding: 25px; 
                border-radius: 10px; 
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); 
                margin-bottom: 30px; 
                text-align: center;
                border: 2px dashed #1e3c72;
            }}
            .create-db-section h3 {{ 
                color: #1e3c72; 
                margin-top: 0; 
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }}
            .create-db-section h3::before {{
                content: "folder";
                font-size: 24px;
            }}
            .db-create-select {{ 
                padding: 12px 20px;
                border: 2px solid #1e3c72;
                border-radius: 8px;
                font-size: 16px;
                background: white;
                color: #1e3c72;
                cursor: pointer;
                min-width: 200px;
                font-family: HYWenHei;
                margin: 0 10px;
                display: inline-block;
                appearance: none;
                -webkit-appearance: none;
                -moz-appearance: none;
                background-image: url('data:image/svg+xml;utf8,<svg fill="%231e3c72" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5z"/><path d="M0 0h24v24H0z" fill="none"/></svg>');
                background-repeat: no-repeat;
                background-position: right 10px center;
                padding-right: 40px;
            }}
            .db-create-select:focus {{
                outline: none;
                box-shadow: 0 0 0 3px rgba(30, 60, 114, 0.2);
            }}
            .db-create-action {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 12px 24px;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-family: HYWenHei;
                font-size: 16px;
                font-weight: bold;
                text-decoration: none;
                margin-left: 15px;
            }}
            .db-create-action:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(30, 60, 114, 0.3);
            }}
            .db-create-action::before {{
                content: "+";
                font-size: 18px;
            }}
            
            .form-table {{
                width: 100%;
            }}
            
            .form-table td {{
                padding: 10px 0;
                text-align: left;
            }}
            
            .form-table td:first-child {{
                width: 120px;
                font-weight: bold;
            }}
            
            .button-container {{
                text-align: center;
                padding-top: 20px;
            }}
            
            .action-button {{
                width: 80px;
                margin: 0 5px;
            }}
            
            .assign-button {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                width: 300px;
                margin: 5px;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-family: HYWenHei;
                font-size: 16px;
                font-weight: bold;
            }}
            
            .assign-button:hover:not(:disabled) {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }}
            
            .assign-button:disabled {{
                background: #cccccc;
                cursor: not-allowed;
                opacity: 0.6;
            }}
            
            .unassign-button {{
                background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                width: 100%;
                padding: 12px;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-family: HYWenHei;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
            }}
            
            .unassign-button:hover:not(:disabled) {{
                background: linear-gradient(135deg, #c82333 0%, #bd2130 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(220, 53, 69, 0.2);
            }}
            
            .role-badge {{
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                margin-left: 10px;
            }}
            
            .admin-badge {{
                background-color: #dc3545;
                color: white;
            }}
            
            .teacher-badge {{
                background-color: #007bff;
                color: white;
            }}
            
            .student-badge {{
                background-color: #28a745;
                color: white;
            }}
            
            @media (max-width: 1024px) {{
                .two-column-layout {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        <script>
            let selectedSubjectId = null;
            let isAdmin = {str(is_admin).lower()};
            let isTeacher = {str(is_teacher).lower()};
            let isStudent = {str(is_student).lower()};

            function selectSubject(subjid, subjcode, subjdesc, subjunits, subjsched) {{
                if (isStudent) {{
                    selectedSubjectId = subjid;
                    window.location.href = 'subjects.py?subjid=' + subjid;
                    return;
                }}
                
                selectedSubjectId = subjid;

                document.getElementById('subjid').value = subjid;
                document.getElementById('subjcode').value = subjcode;
                document.getElementById('subjdesc').value = subjdesc;
                document.getElementById('subjunits').value = subjunits;
                document.getElementById('subjsched').value = subjsched;

                window.location.href = 'subjects.py?subjid=' + subjid;
            }}

            function submitForm(action) {{
                if (isStudent) {{
                    alert('Security Alert: Students cannot modify subject records.');
                    window.location.href = 'index.py';
                    return false;
                }}
                if (!isAdmin && !isTeacher) {{
                    alert('Access Denied: Only administrators or teachers can modify subject records');
                    return false;
                }}
                
                let form = document.getElementById('subjectForm');
                let actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'action_type';
                actionInput.value = action;
                form.appendChild(actionInput);
                
                form.submit();
            }}

            function enrollStudent(studid, subjid) {{
                if (isStudent) {{
                    alert('Security Alert: Students cannot enroll students.');
                    window.location.href = 'index.py';
                    return false;
                }}
                if (!isAdmin && !isTeacher) {{
                    alert('Access Denied: Only administrators or teachers can enroll students');
                    return false;
                }}
                
                if (studid && subjid) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'subjects.py';
                    
                    let studidInput = document.createElement('input');
                    studidInput.type = 'hidden';
                    studidInput.name = 'selected_studid';
                    studidInput.value = studid;
                    form.appendChild(studidInput);
                    
                    let subjidInput = document.createElement('input');
                    subjidInput.type = 'hidden';
                    subjidInput.name = 'selected_subjid';
                    subjidInput.value = subjid;
                    form.appendChild(subjidInput);
                    
                    let actionInput = document.createElement('input');
                    actionInput.type = 'hidden';
                    actionInput.name = 'subject_action';
                    actionInput.value = 'enroll';
                    form.appendChild(actionInput);
                    
                    let urlSubjId = document.createElement('input');
                    urlSubjId.type = 'hidden';
                    urlSubjId.name = 'subjid';
                    urlSubjId.value = subjid;
                    form.appendChild(urlSubjId);
                    
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}

            function dropStudent(studid, subjid) {{
                if (isStudent) {{
                    alert('Security Alert: Students cannot drop students.');
                    window.location.href = 'index.py';
                    return false;
                }}
                if (!isAdmin && !isTeacher) {{
                    alert('Access Denied: Only administrators or teachers can drop students');
                    return false;
                }}
                
                if (studid && subjid) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'subjects.py';
                    
                    let studidInput = document.createElement('input');
                    studidInput.type = 'hidden';
                    studidInput.name = 'selected_studid';
                    studidInput.value = studid;
                    form.appendChild(studidInput);
                    
                    let subjidInput = document.createElement('input');
                    subjidInput.type = 'hidden';
                    subjidInput.name = 'selected_subjid';
                    subjidInput.value = subjid;
                    form.appendChild(subjidInput);
                    
                    let actionInput = document.createElement('input');
                    actionInput.type = 'hidden';
                    actionInput.name = 'subject_action';
                    actionInput.value = 'drop';
                    form.appendChild(actionInput);
                    
                    let urlSubjId = document.createElement('input');
                    urlSubjId.type = 'hidden';
                    urlSubjId.name = 'subjid';
                    urlSubjId.value = subjid;
                    form.appendChild(urlSubjId);
                    
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}

            function createDatabase() {{
                if (!isAdmin) {{
                    alert('Access Denied: Only administrators can create databases');
                    return false;
                }}
                let semester = document.getElementById('semesterSelect').value;
                if (!semester) {{
                    alert('Please select a semester first');
                    return;
                }}
                if (confirm('Are you sure you want to create a new ' + semester + ' semester database? This will create a fresh database with all necessary tables.')) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'subjects.py';
                    
                    let createDbInput = document.createElement('input');
                    createDbInput.type = 'hidden';
                    createDbInput.name = 'create_db_action';
                    createDbInput.value = '1';
                    form.appendChild(createDbInput);
                    
                    let semesterInput = document.createElement('input');
                    semesterInput.type = 'hidden';
                    semesterInput.name = 'semester_selection';
                    semesterInput.value = semester;
                    form.appendChild(semesterInput);
                    
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}

            function logout() {{
                if (confirm('Are you sure you want to logout?')) {{
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'subjects.py';
                    
                    let logoutInput = document.createElement('input');
                    logoutInput.type = 'hidden';
                    logoutInput.name = 'logout_action';
                    logoutInput.value = '1';
                    form.appendChild(logoutInput);
                    
                    document.body.appendChild(form);
                    form.submit();
                }}
            }}

            window.onload = function() {{
                const urlParams = new URLSearchParams(window.location.search);
                const subjid = urlParams.get('subjid');
                
                if (subjid) {{
                    selectedSubjectId = subjid;
                    let rows = document.querySelectorAll('#subjectsTable tr');
                    for (let row of rows) {{
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === subjid) {{
                            row.classList.add('selected-row');
                            break;
                        }}
                    }}
                }}
            }};
        </script>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Genshin_Impact_logo.svg/2560px-Genshin_Impact_logo.svg.png" alt="Genshin Impact Logo" class="logo">
                <div class="university-info">
                    <div class="university-name">Sumeru Akademiya</div>
                    <div class="subtitle">Subject Management System</div>
                    <div class="subtitle">Database: {html.escape(database_name)} | User: {html.escape(username)} <span class="role-badge { 'admin-badge' if is_admin else 'teacher-badge' if is_teacher else 'student-badge' }">{role_display}</span></div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
    """)

    # Generate navigation links
    students_link = "students.py"
    teachers_link = "teachers.py"
    
    if url_subjid:
        students_link = f"students.py?subjid={url_subjid}"
        teachers_link = f"teachers.py?subjid={url_subjid}"

    print(f"""
                <a href="{students_link}" class="nav-link">Students</a>
                <a href="{teachers_link}" class="nav-link">Teachers</a>
                <button onclick="logout()" class="logout-button">Logout</button>
            </div>
        </div>

        <div class="main-container">
    """)

    if created_msg == "1":
        print(f"""
        <div class="success-message">
            New semester database created successfully!<br>
            Current database: <strong>{database_name}</strong>
        </div>
        """)

    # Show role info message
    if is_student:
        print(f"""
        <div class="info-message">
            You are logged in as <strong>{role_display}</strong>. You can only view subjects you are enrolled in.
        </div>
        """)
    elif is_teacher:
        print(f"""
        <div class="info-message">
            You are logged in as <strong>{role_display}</strong>. You can modify subjects and enroll/drop students.
        </div>
        """)

    if error_msg:
        error_display = html.unescape(error_msg)
        print(f"""
        <div class="error-message">
            {error_display}
        </div>
        """)
    
    if success_msg:
        print(f"""
        <div class="success-message">
            {html.unescape(success_msg)}
        </div>
        """)

    # Create Database Section - Show only for admins
    if is_admin:
        print(f"""
        <div class="create-db-section">
            <h3>Create New Semester Database</h3>
            <p>Create a fresh database for a new semester. This will create all necessary tables.</p>
            <div class="semester-selection">
                <select id="semesterSelect" class="db-create-select">
                    <option value="">-- Select Semester --</option>
                    <option value="1st">1st Semester</option>
                    <option value="2nd">2nd Semester</option>
                    <option value="summer">Summer</option>
                </select>
                <a href="#" onclick="createDatabase()" class="db-create-action">Create Database</a>
            </div>
            <p style="margin-top: 15px; color: #666; font-size: 14px;">
                Current Database: <strong>{database_name}</strong>
            </p>
        </div>
        """)

    # Disable form inputs for students
    disabled_attr = "" if (is_admin or is_teacher) else "disabled"
    
    print(f"""
    <div class="two-column-layout">
        <div>
            <div class="form-container">
                <h2>Subject Form</h2>
                <form method="POST" action="subjects.py" id="subjectForm">
                    <table class="form-table">
                        <tr>
                            <td>Subject ID:</td>
                            <td><input type="text" name="subjid" id="subjid" style="width: 100px" readonly value=""" + f"'{prefill_data.get('subjid', '')}'" + """></td>
                        </tr>
                        <tr>
                            <td>Code:</td>
                            <td><input type="text" name="subjcode" id="subjcode" style="width: 150px" value=""" + f"'{html.escape(prefill_data.get('subjcode', ''))}'" + """ {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Description:</td>
                            <td><input type="text" name="subjdesc" id="subjdesc" style="width: 200px" value=""" + f"'{html.escape(prefill_data.get('subjdesc', ''))}'" + """ {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Units:</td>
                            <td><input type="text" name="subjunits" id="subjunits" style="width: 80px" value=""" + f"'{prefill_data.get('subjunits', '')}'" + """ {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Schedule:</td>
                            <td><input type="text" name="subjsched" id="subjsched" style="width: 150px" value=""" + f"'{html.escape(prefill_data.get('subjsched', ''))}'" + """ {disabled_attr}></td>
                        </tr>
                    </table>
                    <div class="button-container">
                        <button type="button" onclick="submitForm('insert')" class="action-button" {disabled_attr}>Insert</button>
                        <button type="button" onclick="submitForm('update')" class="action-button" {disabled_attr}>Update</button>
                        <button type="button" onclick="submitForm('delete')" class="action-button" {disabled_attr}>Delete</button>
                    </div>
                </form>
            </div>

            <div class="form-container">
                <h3>Subject Information</h3>
    """)

    if url_subjid and prefill_data.get('subjid'):
        print(f"""<div style="text-align: center; margin-bottom: 15px;">
            <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Selected Subject: {url_subjid}</p>
            <p><strong>Code:</strong> {html.escape(prefill_data.get('subjcode', ''))}</p>
            <p><strong>Description:</strong> {html.escape(prefill_data.get('subjdesc', ''))}</p>
            <p><strong>Units:</strong> {prefill_data.get('subjunits', '')}</p>
            <p><strong>Schedule:</strong> {html.escape(prefill_data.get('subjsched', ''))}</p>
        </div>""")
        
        if teacher_of_subject:
            print(f"""<div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; border-left: 4px solid #007bff;">
                <p style="font-weight: bold; color: #007bff; margin-bottom: 5px;">Assigned Teacher:</p>
                <p><strong>Name:</strong> {html.escape(teacher_of_subject['tname'])}</p>
                <p><strong>Department:</strong> {html.escape(teacher_of_subject['tdept'])}</p>
            </div>""")
        
        # Enrollment form for teachers
        if is_teacher or is_admin:
            print(f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #f0f8ff; border-radius: 5px; border: 1px solid #d0e7ff;">
                <p style="font-weight: bold; color: #1e3c72; margin-bottom: 10px;">Enroll Student in This Subject:</p>
                <form method="POST" action="subjects.py" style="display: flex; gap: 10px; align-items: center;">
                    <input type="hidden" name="subjid" value="{url_subjid}">
                    <input type="text" name="selected_studid" placeholder="Student ID" style="flex: 1; padding: 8px;">
                    <input type="hidden" name="selected_subjid" value="{url_subjid}">
                    <button type="submit" name="subject_action" value="enroll" class="assign-button" style="padding: 8px 15px;">Enroll Student</button>
                </form>
            </div>
            """)
    else:
        print("""<div style="text-align: center; padding: 20px;">
            <p style="color: #666;">
                Select a subject from the table to view details
            </p>
        </div>""")

    print("""
            </div>
        </div>

        <div>
            <div class="form-container">
                <h2>Subjects Table for: """ + database_name + """</h2>
    """)
    
    if is_admin:
        print("<p>All subjects in the database (Administrator View)</p>")
    elif is_teacher:
        print("<p>All subjects (Teacher View - Can modify)</p>")
    elif is_student:
        print("<p>Subjects you are enrolled in (Student View)</p>")
    else:
        print("<p>Subjects in the database</p>")
    
    print("""
                <table border="1" id="subjectsTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                        </tr>
                    </thead>
                    <tbody>
    """)

    if subjects:
        for subject in subjects:
            subjid_val = str(subject[0])
            subjcode_val = html.escape(str(subject[1]))
            subjdesc_val = html.escape(str(subject[2]))
            subjunits_val = str(subject[3])
            subjsched_val = html.escape(str(subject[4]))
            
            print(f"""<tr onclick="selectSubject('{subjid_val}', '{subjcode_val}', '{subjdesc_val}', '{subjunits_val}', '{subjsched_val}')">""")
            print("<td>" + subjid_val + "</td>")
            print("<td>" + subjcode_val + "</td>")
            print("<td>" + subjdesc_val + "</td>")
            print("<td>" + subjunits_val + "</td>")
            print("<td>" + subjsched_val + "</td>")
            print("</tr>")
    else:
        if is_student:
            print("""<tr><td colspan="5" style="text-align: center; padding: 30px; color: #666;">
                You are not enrolled in any subjects.
            </td></tr>""")
        else:
            print("""<tr><td colspan="5" style="text-align: center; padding: 30px; color: #666;">
                No subjects found in the database
            </td></tr>""")

    print("""
                    </tbody>
                </table>
            </div>

            <div class="form-container" style="margin-top: 30px;">
                <h2>Enrolled Students in Subject ID: """ + (url_subjid if url_subjid else "None") + """</h2>
    """)
    
    if is_teacher or is_admin:
        print("<p>Students enrolled in this subject (Click to drop)</p>")
    elif is_student:
        print("<p>Other students enrolled in this subject</p>")
    
    print("""
                <table border="1" id="enrolledStudentsTable">
                    <thead>
                        <tr>
                            <th>Student ID</th>
                            <th>Name</th>
                            <th>Course</th>
                            <th>Year Level</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
    """)

    if url_subjid and enrolled_students:
        for student in enrolled_students:
            print("<tr>")
            print("<td>" + str(student[0]) + "</td>")
            print("<td>" + html.escape(str(student[1])) + "</td>")
            print("<td>" + html.escape(str(student[2])) + "</td>")
            print("<td>" + html.escape(str(student[3])) + "</td>")
            if is_admin or is_teacher:
                print(f"""<td><button onclick="dropStudent('{student[0]}', '{url_subjid}')" style="padding: 5px 10px; background: #dc3545; color: white; border: none; border-radius: 3px; cursor: pointer;">Drop</button></td>""")
            else:
                print("<td>--</td>")
            print("</tr>")
    elif url_subjid and not enrolled_students:
        print("""<tr><td colspan="5" style="text-align: center; padding: 20px; color: #666;">
            No students enrolled in this subject
        </td></tr>""")
    else:
        print("""<tr><td colspan="5" style="text-align: center; padding: 20px; color: #666;">
            Select a subject from the table to view enrolled students
        </td></tr>""")

    print("""
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    </div>
    </body>
    </html>
    """)

    cursor.close()
    conn.close()

except mysql.connector.Error as e:
    print(f"<html><body><h1>Database Connection Error</h1><p>{html.escape(str(e))}</p><p>Database: {database_name}</p></body></html>")
except Exception as e:
    print(f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>")