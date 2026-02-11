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

# SECURITY FUNCTION: Auto-logout unauthorized students
def check_student_security_action(action_type, subject_action, is_student):
    """Check if student is attempting unauthorized actions and logout if true"""
    if is_student:
        # Check for CRUD actions in students.py
        if action_type in ["insert", "update", "delete"]:
            return True
        # Check for enrollment/drop actions
        if subject_action in ["enroll", "drop"]:
            return True
        # Check for database creation
        if create_db_action == "1":
            return True
    return False

# Create new semester database - ADMIN ONLY
create_db_action = form.getvalue("create_db_action", "")
semester_selection = form.getvalue("semester_selection", "")

if create_db_action == "1":
    if not is_admin:
        print("<script>alert('Access Denied: Admin privileges required');window.location.href = 'students.py';</script>")
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

            print(f"<script>alert('New database \"{new_db_name}\" created successfully!');window.location.href = 'students.py?created=1';</script>")
            sys.exit()

        except Exception as e:
            error_msg = f"Database creation failed: {str(e)}"
            print()
            print(f"<script>alert('{error_msg}');window.location.href = 'students.py';</script>")
            sys.exit()

# Form values
action_type = form.getvalue("action_type", "")
studid = form.getvalue("studid", "")
studname = html.escape(form.getvalue("studname", ""))
studadd = html.escape(form.getvalue("studadd", ""))
studcrs = html.escape(form.getvalue("studcrs", ""))
studgender = form.getvalue("studgender", "")
yrlvl = form.getvalue("yrlvl", "")

# For subject enrollment
selected_studid = form.getvalue("selected_studid", "")
selected_subjid = form.getvalue("selected_subjid", "")
subject_action = form.getvalue("subject_action", "")

# SECURITY CHECK: Auto-logout students attempting unauthorized actions
if check_student_security_action(action_type, subject_action, is_student):
    print("Set-Cookie: session_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; HttpOnly")
    print("Set-Cookie: username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: user_role=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print()
    print("<script>alert('Security Alert: Unauthorized action attempted. You have been logged out.');window.location.href = 'index.py';</script>")
    sys.exit()

# RBAC Check for student CRUD operations - ADMIN ONLY
if action_type in ["insert", "update", "delete"] and not is_admin:
    print("<script>alert('Access Denied: Only administrators can modify student records');window.location.href = 'students.py';</script>")
    sys.exit()

# RBAC Check for enrollment operations - ADMIN ONLY
if subject_action in ["enroll", "drop"] and not is_admin:
    print("<script>alert('Access Denied: Only administrators can enroll/drop students');window.location.href = 'students.py';</script>")
    sys.exit()

# URL parameters
url_studid = form.getvalue("studid", "")
url_subjid = form.getvalue("subjid", "")
error_msg = form.getvalue("error", "")
success_msg = form.getvalue("success", "")
created_msg = form.getvalue("created", "")

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

def create_mysql_user_for_student(studid, studname, database_name):
    """Create MySQL user for student with READ-ONLY access to specific database"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        # Create username from studid + studname (remove spaces and special chars)
        safe_name = ''.join(c for c in studname if c.isalnum() or c.isspace()).replace(' ', '').lower()
        mysql_username = f"{studid}{safe_name}"
        
        # Password format: AdDU + name only (without ID)
        mysql_password = f"AdDU{safe_name}"
        
        # Check if user already exists
        cursor.execute("SELECT User FROM mysql.user WHERE User = %s", (mysql_username,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            # Create MySQL user with password AdDU + name
            cursor.execute(f"CREATE USER '{mysql_username}'@'localhost' IDENTIFIED BY '{mysql_password}'")
            
        # Grant SELECT ONLY privileges on the specific database (READ-ONLY for students)
        cursor.execute(f"GRANT SELECT ON `{database_name}`.* TO '{mysql_username}'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, mysql_username, mysql_password
    except Exception as e:
        return False, None, None

def delete_mysql_user_for_student(studid, studname):
    """Delete MySQL user for student"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        # Create username from studid + studname (remove spaces and special chars)
        safe_name = ''.join(c for c in studname if c.isalnum() or c.isspace()).replace(' ', '').lower()
        mysql_username = f"{studid}{safe_name}"
        
        # Check if user exists
        cursor.execute("SELECT User FROM mysql.user WHERE User = %s", (mysql_username,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Drop user
            cursor.execute(f"DROP USER '{mysql_username}'@'localhost'")
            cursor.execute("FLUSH PRIVILEGES")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        return False

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database=database_name
    )
    cursor = conn.cursor()

    # Handle student actions (ADMIN ONLY - already checked above)
    if action_type == "insert" and studname:
        try:
            cursor.execute("SELECT MAX(studid) FROM students")
            result = cursor.fetchone()
            max_studid = result[0]
            if max_studid is None:
                next_studid = 1000
            else:
                next_studid = max(max_studid + 1, 1000)
            cursor.execute("INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s, %s)", (next_studid, studname, studadd, studcrs, studgender, yrlvl))
            conn.commit()
            
            # Create MySQL user for this student
            success, mysql_username, mysql_password = create_mysql_user_for_student(next_studid, studname, database_name)
            
            if success:
                print(f"<script>alert('Student added successfully!\\nMySQL User Created:\\nUsername: {mysql_username}\\nPassword: {mysql_password}');window.location.href='students.py?studid={next_studid}';</script>")
            else:
                print(f"<script>alert('Student added but MySQL user creation failed');window.location.href='students.py?studid={next_studid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='students.py';</script>")
    elif action_type == "update" and studid and studname:
        try:
            cursor.execute("UPDATE students SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s WHERE studid=%s", (studname, studadd, studcrs, studgender, yrlvl, studid))
            conn.commit()
            print(f"<script>window.location.href='students.py?studid={studid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='students.py?studid={studid}';</script>")
    elif action_type == "delete" and studid:
        try:
            # Get student name before deletion
            cursor.execute("SELECT studname FROM students WHERE studid=%s", (studid,))
            student_data = cursor.fetchone()
            studname_for_deletion = student_data[0] if student_data else ""
            
            cursor.execute("SELECT eid FROM enroll WHERE studid=%s", (studid,))
            enrollments = cursor.fetchall()
            for enrollment in enrollments:
                eid = enrollment[0]
                cursor.execute("DELETE FROM grades WHERE enroll_eid = %s", (eid,))
            cursor.execute("DELETE FROM enroll WHERE studid=%s", (studid,))
            cursor.execute("DELETE FROM students WHERE studid=%s", (studid,))
            conn.commit()
            
            # Delete MySQL user for this student
            if studname_for_deletion:
                delete_mysql_user_for_student(studid, studname_for_deletion)
            
            print(f"<script>window.location.href='students.py';</script>")
        except Exception as e:
            print(f"<script>window.location.href='students.py';</script>")

    # Handle subject enrollment (ADMIN ONLY - already checked above)
    if subject_action == "enroll" and selected_studid and selected_subjid:
        try:
            cursor.execute("SELECT COUNT(*) FROM students WHERE studid = %s", (selected_studid,))
            student_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM subjects WHERE subjid = %s", (selected_subjid,))
            subject_count = cursor.fetchone()[0]
            if student_count == 0 or subject_count == 0:
                error_msg = "Student or Subject not found"
                redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid))
            count = cursor.fetchone()[0]
            if count > 0:
                error_msg = "Student is already enrolled in this subject"
                redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()

            # Check for schedule conflicts
            conflict_msg = check_schedule_conflict(cursor, selected_studid, selected_subjid)
            if conflict_msg:
                redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(conflict_msg)}'
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
            url_subjid = form.getvalue("subjid", "")
            redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&success=Student enrolled successfully'
            if url_subjid and url_subjid != selected_subjid:
                redirect_url = f'students.py?studid={selected_studid}&subjid={url_subjid}&success=Student enrolled successfully'
            print(f"<script>window.location.href='{redirect_url}';</script>")
        except Exception as e:
            error_msg = f"Enrollment failed: {str(e)}"
            redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
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
                url_subjid = form.getvalue("subjid", "")
                redirect_url = f'students.py?studid={selected_studid}&success=Subject dropped successfully'
                if url_subjid:
                    redirect_url = f'students.py?studid={selected_studid}&subjid={url_subjid}&success=Subject dropped successfully'
                print(f"<script>window.location.href='{redirect_url}';</script>")
            else:
                url_subjid = form.getvalue("subjid", "")
                redirect_url = f'students.py?studid={selected_studid}&error=Student is not enrolled in this subject'
                if url_subjid:
                    redirect_url = f'students.py?studid={selected_studid}&subjid={url_subjid}&error=Student is not enrolled in this subject'
                print(f"<script>window.location.href='{redirect_url}';</script>")
        except Exception as e:
            url_subjid = form.getvalue("subjid", "")
            redirect_url = f'students.py?studid={selected_studid}'
            if url_subjid:
                redirect_url = f'students.py?studid={selected_studid}&subjid={url_subjid}'
            print(f"<script>window.location.href='{redirect_url}';</script>")

    # Get all students
    cursor.execute("""
        SELECT s.studid, s.studname, s.studadd, s.studgender, s.studcrs, s.yrlvl, 
               COALESCE(SUM(sub.subjunits), 0) as total_units 
        FROM students s 
        LEFT JOIN enroll e ON s.studid = e.studid 
        LEFT JOIN subjects sub ON e.subjid = sub.subjid 
        GROUP BY s.studid, s.studname, s.studadd, s.studgender, s.studcrs, s.yrlvl 
        ORDER BY s.studid
    """)
    students = cursor.fetchall()

    # Check for schedule conflicts - FOR DISPLAY
    conflict_detected = False
    conflict_message = ""
    if url_studid and url_subjid:
        cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s", (url_studid, url_subjid))
        already_enrolled = cursor.fetchone()[0] > 0
        if not already_enrolled:
            conflict_message = check_schedule_conflict(cursor, url_studid, url_subjid)
            if conflict_message:
                conflict_detected = True

    cursor.execute("""
        SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
        FROM enroll e 
        JOIN subjects s ON e.subjid = s.subjid 
        WHERE e.studid = %s 
        ORDER BY s.subjid
    """, (url_studid,))
    enrolled_subjects = cursor.fetchall()
    enrolled_subject_ids = [subject[0] for subject in enrolled_subjects]

    # Pre-fill form
    prefill_data = {}
    if url_studid:
        cursor.execute("SELECT studid, studname, studadd, studcrs, studgender, yrlvl FROM students WHERE studid = %s", (url_studid,))
        student_data = cursor.fetchone()
        if student_data:
            prefill_data = {
                'studid': student_data[0],
                'studname': student_data[1],
                'studadd': student_data[2],
                'studcrs': student_data[3],
                'studgender': student_data[4],
                'yrlvl': student_data[5]
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
    <title>Sumeru Akademiya - Student Enrollment System</title>
    <style>
    * {{ font-family: HYWenHei, sans-serif !important; }}
    body {{ font-family: HYWenHei, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
    .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 15px 30px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); display: flex; align-items: center; justify-content: space-between; }}
    .header-left {{ display: flex; align-items: center; }}
    .logo {{ height: 70px; width: 70px; margin-right: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }}
    .university-info {{ display: flex; flex-direction: column; }}
    .university-name {{ font-size: 28px; font-weight: bold; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3); letter-spacing: 1px; line-height: 1.2; }}
    .subtitle {{ font-size: 16px; opacity: 0.9; margin-top: 3px; }}
    .nav-link {{ color: white; text-decoration: none; background-color: rgba(255, 255, 255, 0.2); padding: 8px 20px; border-radius: 20px; transition: all 0.3s ease; font-size: 14px; }}
    .nav-link:hover {{ background-color: rgba(255, 255, 255, 0.3); transform: translateY(-2px); }}
    .main-container {{ max-width: 1400px; margin: 30px auto; padding: 20px; }}
    button {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); font-family: HYWenHei }}
    button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); }}
    button:disabled {{ background: #cccccc; cursor: not-allowed; transform: none; box-shadow: none; opacity: 0.6; }}
    .enroll-green-button {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 8px; color: white; cursor: pointer; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; min-width: 300px; border: none; margin: 5px; }}
    .enroll-green-button:hover:not(:disabled) {{ transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); }}
    .drop-button {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 8px; color: white; cursor: pointer; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; min-width: 300px; border: none; margin: 5px; }}
    .drop-button:hover:not(:disabled) {{ background: linear-gradient(135deg, #c82333 0%, #bd2130 100%); transform: translateY(-2px); box-shadow: 0 6px 12px rgba(220, 53, 69, 0.2); }}
    .logout-button {{ background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%); padding: 10px 20px; font-size: 14px; border-radius: 5px; color: white; cursor: pointer; transition: all 0.3s ease; border: none; }}
    .logout-button:hover {{ background: linear-gradient(135deg, #5a6268 0%, #4e555b 100%); transform: translateY(-2px); box-shadow: 0 6px 12px rgba(108, 117, 125, 0.2); }}
    .semester-selection {{ display: flex; gap: 10px; margin-top: 10px; justify-content: center; }}
    .semester-btn {{ padding: 10px 20px; background: linear-gradient(135deg, #6f42c1 0%, #6610f2 100%); color: white; border: none; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; }}
    .semester-btn:hover:not(:disabled) {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(111, 66, 193, 0.3); }}
    input, select {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }}
    input:focus, select:focus {{ outline: none; border-color: #2a5298; box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2); }}
    input:disabled, select:disabled {{ background-color: #f5f5f5; cursor: not-allowed; }}
    .error-message {{ background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #f5c6cb; text-align: center; font-weight: bold; }}
    .success-message {{ background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #c3e6cb; text-align: center; font-weight: bold; }}
    .warning-message {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #ffeaa7; text-align: center; font-weight: bold; }}
    .info-message {{ background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #bee5eb; text-align: center; font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); border-radius: 8px; overflow: hidden; }}
    th {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 12px 15px; text-align: center; font-weight: bold; font-size: 16px; }}
    td {{ padding: 12px 15px; border-bottom: 1px solid #e0e0e0; text-align: center; transition: background-color 0.2s ease; }}
    tr:hover {{ background-color: rgba(42, 82, 152, 0.05); cursor: pointer; }}
    .selected-row {{ background-color: rgba(42, 82, 152, 0.15) !important; font-weight: bold; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    tr:nth-child(even):hover {{ background-color: rgba(42, 82, 152, 0.08); }}
    .form-container {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); margin-bottom: 30px; }}
    .form-container h2 {{ color: #1e3c72; margin-top: 0; border-bottom: 2px solid #1e3c72; padding-bottom: 10px; }}
    .enroll-section {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); margin-top: 20px; }}
    .enroll-section h3 {{ color: #1e3c72; margin-top: 0; }}
    .two-column-layout {{ display: grid; grid-template-columns: 1fr 1.5fr; gap: 30px; }}
    .enroll-buttons-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 15px; }}
    .create-db-section {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); margin-bottom: 30px; text-align: center; }}
    .create-db-section h3 {{ color: #1e3c72; margin-top: 0; }}
    
    /* Status Indicator Styles */
    .status-indicator {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .status-active {{
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }}
    
    .status-inactive {{
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }}
    
    .status-pending {{
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }}
    
    .status-enrolled {{
        background-color: #cce5ff;
        color: #004085;
        border: 1px solid #b8daff;
    }}
    
    /* Role Badge Styles */
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
    
    /* Student Level Indicators */
    .level-freshman {{
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }}
    
    .level-sophomore {{
        background-color: #e8f5e9;
        color: #1b5e20;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }}
    
    .level-junior {{
        background-color: #fff3e0;
        color: #e65100;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }}
    
    .level-senior {{
        background-color: #f3e5f5;
        color: #4a148c;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }}
    
    /* Course Badges */
    .course-badge {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        margin: 2px;
    }}
    
    .course-bs-it {{
        background-color: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }}
    
    .course-bs-cs {{
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }}
    
    .course-bs-is {{
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }}
    
    .course-bs-ece {{
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }}
    
    /* Units Indicator */
    .units-indicator {{
        font-weight: bold;
        color: #1e3c72;
        padding: 4px 8px;
        border-radius: 4px;
        background-color: #f0f8ff;
        border: 1px solid #d0e7ff;
    }}
    
    .units-full {{
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }}
    
    .units-warning {{
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }}
    
    @media (max-width: 1024px) {{ .two-column-layout {{ grid-template-columns: 1fr; }} }}
    </style>
    <script>
    let selectedStudentId = null;
    let selectedEnrolledSubjectId = null;
    let isAdmin = {str(is_admin).lower()};
    let isTeacher = {str(is_teacher).lower()};
    let isStudent = {str(is_student).lower()};
    
    function selectStudent(studid, studname, studadd, studcrs, studgender, yrlvl) {{
        selectedStudentId = studid;
        selectedEnrolledSubjectId = null;
        document.getElementById('studid').value = studid;
        document.getElementById('studname').value = studname;
        document.getElementById('studadd').value = studadd;
        document.getElementById('studcrs').value = studcrs;
        document.getElementById('studgender').value = studgender;
        document.getElementById('yrlvl').value = yrlvl;
        
        const urlParams = new URLSearchParams(window.location.search);
        const currentSubjid = urlParams.get('subjid');
        let newUrl = 'students.py?studid=' + studid;
        if (currentSubjid) {{
            newUrl += '&subjid=' + currentSubjid;
        }}
        window.location.href = newUrl;
    }}
    
    function selectEnrolledSubject(subjid, subjcode) {{
        selectedEnrolledSubjectId = subjid;
        let rows = document.querySelectorAll('#enrolledSubjectsTable tr');
        rows.forEach(row => row.classList.remove('selected-row'));
        let rowsArray = Array.from(rows);
        for (let row of rowsArray) {{
            let firstCell = row.querySelector('td:first-child');
            if (firstCell && firstCell.textContent === subjid) {{
                row.classList.add('selected-row');
                break;
            }}
        }}
        
        let dropButton = document.getElementById('dropButton');
        if (dropButton && selectedStudentId && selectedEnrolledSubjectId) {{
            dropButton.style.display = 'block';
            dropButton.innerHTML = 'Drop Student ID: ' + selectedStudentId + ' from Subject ID: ' + selectedEnrolledSubjectId;
            dropButton.disabled = !isAdmin;
        }}
    }}
    
    function submitForm(action) {{
        if (!isAdmin) {{
            alert('Access Denied: Only administrators can modify student records');
            return false;
        }}
        let form = document.getElementById('studentForm');
        let actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action_type';
        actionInput.value = action;
        form.appendChild(actionInput);
        
        form.submit();
    }}
    
    function enrollStudent(subjid) {{
        if (!isAdmin) {{
            alert('Access Denied: Only administrators can enroll students');
            return false;
        }}
        let studid = document.getElementById('studid').value;
        if (studid && subjid) {{
            let form = document.createElement('form');
            form.method = 'POST';
            form.action = 'students.py';
            
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
            
            let urlStudId = document.createElement('input');
            urlStudId.type = 'hidden';
            urlStudId.name = 'studid';
            urlStudId.value = studid;
            form.appendChild(urlStudId);
            
            const urlParams = new URLSearchParams(window.location.search);
            const currentSubjid = urlParams.get('subjid');
            if (currentSubjid) {{
                let urlSubjId = document.createElement('input');
                urlSubjId.type = 'hidden';
                urlSubjId.name = 'subjid';
                urlSubjId.value = currentSubjid;
                form.appendChild(urlSubjId);
            }}
            
            document.body.appendChild(form);
            form.submit();
        }}
    }}
    
    function dropSubject() {{
        if (!isAdmin) {{
            alert('Access Denied: Only administrators can drop students from subjects');
            return false;
        }}
        if (selectedStudentId && selectedEnrolledSubjectId) {{
            let form = document.createElement('form');
            form.method = 'POST';
            form.action = 'students.py';
            
            let studidInput = document.createElement('input');
            studidInput.type = 'hidden';
            studidInput.name = 'selected_studid';
            studidInput.value = selectedStudentId;
            form.appendChild(studidInput);
            
            let subjidInput = document.createElement('input');
            subjidInput.type = 'hidden';
            subjidInput.name = 'selected_subjid';
            subjidInput.value = selectedEnrolledSubjectId;
            form.appendChild(subjidInput);
            
            let actionInput = document.createElement('input');
            actionInput.type = 'hidden';
            actionInput.name = 'subject_action';
            actionInput.value = 'drop';
            form.appendChild(actionInput);
            
            let urlStudId = document.createElement('input');
            urlStudId.type = 'hidden';
            urlStudId.name = 'studid';
            urlStudId.value = selectedStudentId;
            form.appendChild(urlStudId);
            
            const urlParams = new URLSearchParams(window.location.search);
            const currentSubjid = urlParams.get('subjid');
            if (currentSubjid) {{
                let urlSubjId = document.createElement('input');
                urlSubjId.type = 'hidden';
                urlSubjId.name = 'subjid';
                urlSubjId.value = currentSubjid;
                form.appendChild(urlSubjId);
            }}
            
            document.body.appendChild(form);
            form.submit();
        }}
    }}
    
    function createDatabase(semester) {{
        if (!isAdmin) {{
            alert('Access Denied: Only administrators can create databases');
            return false;
        }}
        if (confirm('Are you sure you want to create a new ' + semester + ' semester database? This will create a fresh database with all necessary tables.')) {{
            let form = document.createElement('form');
            form.method = 'POST';
            form.action = 'students.py';
            
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
            form.action = 'students.py';
            
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
        const studid = urlParams.get('studid');
        const subjid = urlParams.get('subjid');
        
        if (studid) {{
            selectedStudentId = studid;
            let rows = document.querySelectorAll('#studentsTable tr');
            for (let row of rows) {{
                let firstCell = row.querySelector('td:first-child');
                if (firstCell && firstCell.textContent === studid) {{
                    row.classList.add('selected-row');
                    break;
                }}
            }}
        }}
        
        if (subjid && studid) {{
            let subjectRows = document.querySelectorAll('#enrolledSubjectsTable tr');
            for (let row of subjectRows) {{
                let firstCell = row.querySelector('td:first-child');
                if (firstCell && firstCell.textContent === subjid) {{
                    row.classList.add('selected-row');
                    selectedEnrolledSubjectId = subjid;
                    let dropButton = document.getElementById('dropButton');
                    if (dropButton) {{
                        dropButton.style.display = 'block';
                        dropButton.innerHTML = 'Drop Student ID: ' + selectedStudentId + ' from Subject ID: ' + selectedEnrolledSubjectId;
                        dropButton.disabled = !isAdmin;
                    }}
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
                <div class="subtitle">Student Enrollment Management System</div>
                <div class="subtitle">Database: {html.escape(database_name)} | User: {html.escape(username)} <span class="role-badge {'admin-badge' if is_admin else 'teacher-badge' if is_teacher else 'student-badge'}">{role_display}</span></div>
            </div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <a href="subjects.py{f"?subjid={url_subjid}" if url_subjid else ""}" class="nav-link">Go to Subjects</a>
            <a href="teachers.py" class="nav-link">Go to Teachers</a>
            <button onclick="logout()" class="logout-button">Logout</button>
        </div>
    </div>
    <div class="main-container">
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
    if created_msg:
        print(f"""
        <div class="success-message">
            Database created successfully! You are now using the new database.
        </div>
        """)

    # Show role info message for non-admins
    if not is_admin:
        print(f"""
        <div class="info-message">
            You are logged in as {role_display}. You have read-only access to this page.
        </div>
        """)

    # Create Database Section - Show only for admins
    if is_admin:
        print("""
        <div class="create-db-section">
            <h3>Create New Semester Database</h3>
            <p>Create a fresh database for a new semester. This will create all necessary tables.</p>
            <div class="semester-selection">
                <button class="semester-btn" onclick="createDatabase('1st')">Create 1st Semester Database</button>
                <button class="semester-btn" onclick="createDatabase('2nd')">Create 2nd Semester Database</button>
                <button class="semester-btn" onclick="createDatabase('summer')">Create Summer Database</button>
            </div>
        </div>
        """)

    print("""
    <div class="two-column-layout">
        <div>
            <div class="form-container">
                <h2>Student Form</h2>
                <form method="POST" action="students.py" id="studentForm">
    """)
    if url_subjid:
        print(f"<input type='hidden' name='subjid' value='{url_subjid}'>")
    
    # Disable form inputs for non-admins
    disabled_attr = "" if is_admin else "disabled"
    
    print(f"""
                    <table style="width: 100%;">
                        <tr>
                            <td>Student ID:</td>
                            <td><input type="text" name="studid" id="studid" style="width: 100px" readonly value='{prefill_data.get("studid", "")}'></td>
                        </tr>
                        <tr>
                            <td>Name:</td>
                            <td><input type="text" name="studname" id="studname" style="width: 200px" value='{html.escape(prefill_data.get("studname", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Address:</td>
                            <td><input type="text" name="studadd" id="studadd" style="width: 200px" value='{html.escape(prefill_data.get("studadd", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Gender:</td>
                            <td><input type="text" name="studgender" id="studgender" style="width: 100px" value='{html.escape(prefill_data.get("studgender", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Course:</td>
                            <td><input type="text" name="studcrs" id="studcrs" style="width: 150px" value='{html.escape(prefill_data.get("studcrs", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Year Level:</td>
                            <td><input type="text" name="yrlvl" id="yrlvl" style="width: 100px" value='{html.escape(prefill_data.get("yrlvl", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td colspan="2" style="text-align: center; padding-top: 20px;">
                                <button type="button" onclick="submitForm('insert')" style="width: 80px; margin: 0 5px;" {disabled_attr}>Insert</button>
                                <button type="button" onclick="submitForm('update')" style="width: 80px; margin: 0 5px;" {disabled_attr}>Update</button>
                                <button type="button" onclick="submitForm('delete')" style="width: 80px; margin: 0 5px;" {disabled_attr}>Delete</button>
                            </td>
                        </tr>
                    </table>
                </form>
            </div>
            
            <div class="enroll-section">
                <h3>Enroll Student to Subject</h3>
    """)
    if url_subjid:
        if url_studid and prefill_data.get('studid'):
            studid = prefill_data.get('studid')
            try:
                is_already_enrolled = int(url_subjid) in enrolled_subject_ids
            except:
                is_already_enrolled = False
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Enroll Student to Subject:</p>
            </div>""")
            if conflict_detected:
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                    <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                        <div style="text-align: center; color: #dc3545; font-weight: bold;">
                            {conflict_message}
                        </div>
                    </div>
                    <button type="button" onclick="enrollStudent('{url_subjid}')" class="enroll-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                        Enroll Student ID: {studid} to Subject ID: {url_subjid}
                    </button>
                </div>
                """)
            elif is_already_enrolled:
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                    <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                        Student ID: {studid} is already enrolled in Subject ID: {url_subjid}
                    </div>
                    <button type="button" onclick="enrollStudent('{url_subjid}')" class="enroll-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                        Enroll Student ID: {studid} to Subject ID: {url_subjid}
                    </button>
                </div>
                """)
            else:
                button_disabled = "" if is_admin else "disabled"
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center;">
                    <button type="button" onclick="enrollStudent('{url_subjid}')" class="enroll-green-button" {button_disabled}>
                        Enroll Student ID: {studid} to Subject ID: {url_subjid}
                    </button>
                </div>
                """)
        elif not url_studid:
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Enroll Student to Subject:</p>
            </div>""")
            print("""<div class="enroll-buttons-container" style="justify-content: center;">""")
            print(f"""<p style="text-align: center; color: #666; padding: 20px; width: 100%;">
                Select a student from the table to enroll in Subject ID: {url_subjid}
            </p>""")
            print("</div>")
    else:
        print("""<div style="text-align: center; padding: 20px;">
            <p style="color: #666;">
                To enroll students in subjects, go to Subjects page and select a subject first
            </p>
        </div>""")
    print("""
            </div>
        </div>
        
        <div>
            <div class="form-container">
                <h2>Students Table for: """ + database_name + """</h2>
                <table border="1" id="studentsTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Address</th>
                            <th>Gender</th>
                            <th>Course</th>
                            <th>Year</th>
                            <th>Total Units</th>
                        </tr>
                    </thead>
                    <tbody>
    """)
    for student in students:
        print("<tr onclick='selectStudent(" + str(student[0]) + ", \"" + html.escape(str(student[1])) + "\", \"" + html.escape(str(student[2])) + "\", \"" + html.escape(str(student[4])) + "\", \"" + html.escape(str(student[3])) + "\", \"" + html.escape(str(student[5])) + "\")'>")
        print("<td>" + str(student[0]) + "</td>")
        print("<td>" + html.escape(str(student[1])) + "</td>")
        print("<td>" + html.escape(str(student[2])) + "</td>")
        print("<td>" + html.escape(str(student[3])) + "</td>")
        print("<td>" + html.escape(str(student[4])) + "</td>")
        print("<td>" + html.escape(str(student[5])) + "</td>")
        print("<td>" + str(student[6]) + "</td>")
        print("</tr>")
    print("""
                    </tbody>
                </table>
            </div>
            
            <div class="form-container" style="margin-top: 30px;">
                <h2>Enrolled Subjects</h2>
                <table border="1" id="enrolledSubjectsTable">
                    <thead>
                        <tr>
                            <th>Subject ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                        </tr>
                    </thead>
                    <tbody>
    """)
    if enrolled_subjects:
        for subject in enrolled_subjects:
            print("<tr onclick='selectEnrolledSubject(" + str(subject[0]) + ", \"" + html.escape(str(subject[1])) + "\")'>")
            print("<td>" + str(subject[0]) + "</td>")
            print("<td>" + html.escape(str(subject[1])) + "</td>")
            print("<td>" + html.escape(str(subject[2])) + "</td>")
            print("<td>" + str(subject[3]) + "</td>")
            print("<td>" + html.escape(str(subject[4])) + "</td>")
            print("</tr>")
    else:
        print("<tr><td colspan='5' style='text-align: center; padding: 20px; color: #666;'>No enrolled subjects</td></tr>")
    
    drop_button_disabled = "" if is_admin else "disabled"
    print(f"""
                    </tbody>
                </table>
                <div style="margin-top: 20px; text-align: center;">
                    <button id="dropButton" type="button" onclick="dropSubject()" class="drop-button" style="width: 100%; padding: 12px; display: none;" {drop_button_disabled}>
                        Drop Subject
                    </button>
                </div>
            </div>
        </div>
    </div>
    </div>
    </body>
    </html>
    """)
    cursor.close()
    conn.close()
except Exception as e:
    print(f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>")