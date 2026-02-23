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

# SECURITY FUNCTION: Redirect students attempting unauthorized actions
def redirect_student_security_action(action_type, assignment_action, enrollment_action, is_student):
    """Redirect student to index.py if attempting unauthorized actions"""
    if is_student:
        # Check for CRUD actions
        if action_type in ["insert", "update", "delete"]:
            return True
        # Check for teacher-subject assignment actions
        if assignment_action in ["assign", "unassign"]:
            return True
        # Check for enrollment/drop actions
        if enrollment_action in ["enroll", "drop"]:
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
        print("<script>alert('Access Denied: Admin privileges required');window.location.href = 'teachers.py';</script>")
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

            print(f"<script>alert('New database \"{new_db_name}\" created successfully!');window.location.href = 'teachers.py?created=1';</script>")
            sys.exit()

        except Exception as e:
            error_msg = f"Database creation failed: {str(e)}"
            print()
            print(f"<script>alert('{error_msg}');window.location.href = 'teachers.py';</script>")
            sys.exit()

# Form values
action_type = form.getvalue("action_type", "")
tid = form.getvalue("tid", "")
tname = html.escape(form.getvalue("tname", ""))
tdept = html.escape(form.getvalue("tdept", ""))
tadd = html.escape(form.getvalue("tadd", ""))
tcontact = html.escape(form.getvalue("tcontact", ""))
tstatus = html.escape(form.getvalue("tstatus", ""))

# For teacher-subject assignment
selected_tid = form.getvalue("selected_tid", "")
selected_subjid = form.getvalue("selected_subjid", "")
assignment_action = form.getvalue("assignment_action", "")

# For enrollment operations (ENROLL/DROP STUDENTS)
selected_studid = form.getvalue("selected_studid", "")
selected_subjid_enroll = form.getvalue("selected_subjid_enroll", "")
enrollment_action = form.getvalue("enrollment_action", "")

# URL parameters
url_tid = form.getvalue("tid", "")
url_subjid = form.getvalue("subjid", "")
url_studid = form.getvalue("studid", "")
error_msg = form.getvalue("error", "")
success_msg = form.getvalue("success", "")
created_msg = form.getvalue("created", "")

# SECURITY CHECK: Redirect students attempting unauthorized actions
if redirect_student_security_action(action_type, assignment_action, enrollment_action, is_student):
    print()
    print("<script>alert('Security Alert: Unauthorized action attempted. Redirecting to login.');window.location.href = 'index.py';</script>")
    sys.exit()

# RBAC Check for teacher CRUD operations - ADMIN ONLY
if action_type in ["insert", "update", "delete"] and not is_admin:
    print("<script>alert('Access Denied: Only administrators can modify teacher records');window.location.href = 'teachers.py';</script>")
    sys.exit()

# RBAC Check for assignment operations - ADMIN OR TEACHER
if assignment_action in ["assign", "unassign"] and not (is_admin or is_teacher):
    print("<script>alert('Access Denied: Only administrators or teachers can assign/unassign subjects');window.location.href = 'teachers.py';</script>")
    sys.exit()

# RBAC Check for enrollment operations - ADMIN OR TEACHER
if enrollment_action in ["enroll", "drop"] and not (is_admin or is_teacher):
    print("<script>alert('Access Denied: Only administrators or teachers can enroll/drop students');window.location.href = 'teachers.py';</script>")
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

def check_teacher_schedule_conflict(cursor, teacher_id, subject_id):
    """Check if assigning a teacher to a subject would create a schedule conflict with their other subjects"""
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
            
        # Get other subjects assigned to this teacher
        cursor.execute("""
            SELECT s.subjcode, s.subjsched 
            FROM subjects s 
            INNER JOIN teacher_subjects ts ON s.subjid = ts.subjid 
            WHERE ts.tid = %s 
            AND s.subjsched IS NOT NULL 
            AND s.subjsched != ''
        """, (teacher_id,))
        assigned_subjects = cursor.fetchall()
        
        # Check each assigned subject
        for assigned_code, assigned_sched in assigned_subjects:
            if assigned_sched and len(assigned_sched.strip()) >= 3:
                old_sched = assigned_sched.strip()
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
                        return f"Teacher schedule conflict with {assigned_code} ({old_sched})"
                        
    except Exception as e:
        return f"Error checking teacher schedule: {str(e)}"
    
    return None  # No conflict

def check_teacher_already_assigned(cursor, teacher_id, subject_id):
    """Check if teacher is already assigned to this subject"""
    try:
        cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE tid = %s AND subjid = %s", (teacher_id, subject_id))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        return False

def check_subject_already_assigned(cursor, subject_id):
    """Check if subject already has a teacher assigned"""
    try:
        cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE subjid = %s", (subject_id,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        return False

def check_teacher_teaches_subject(cursor, teacher_id, subject_id):
    """Check if teacher is assigned to teach this subject"""
    try:
        cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE tid = %s AND subjid = %s", (teacher_id, subject_id))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        return False

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

def create_mysql_user_for_teacher(tid, tname, database_name):
    """Create MySQL user for teacher with appropriate access to specific database"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        # Create username from tid + tname (remove spaces and special chars)
        safe_name = ''.join(c for c in tname if c.isalnum() or c.isspace()).replace(' ', '').lower()
        mysql_username = f"{tid}{safe_name}"
        
        # Password format: AdDU + name only (without ID)
        mysql_password = f"AdDU{safe_name}"
        
        # Check if user already exists
        cursor.execute("SELECT User FROM mysql.user WHERE User = %s", (mysql_username,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            # Create MySQL user with password AdDU + name
            cursor.execute(f"CREATE USER '{mysql_username}'@'localhost' IDENTIFIED BY '{mysql_password}'")
            
        # Grant full privileges for teachers on all tables
        # Teachers can: modify subjects, enroll/drop students, view everything
        cursor.execute(f"CREATE USER IF NOT EXISTS '{mysql_username}'@'localhost' IDENTIFIED BY '{mysql_password}'")
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON `{database_name}`.* TO '{mysql_username}'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, mysql_username, mysql_password
    except Exception as e:
        return False, None, None

def delete_mysql_user_for_teacher(tid, tname):
    """Delete MySQL user for teacher"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        # Create username from tid + tname (remove spaces and special chars)
        safe_name = ''.join(c for c in tname if c.isalnum() or c.isspace()).replace(' ', '').lower()
        mysql_username = f"{tid}{safe_name}"
        
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
    
def revoke_database_permissions(database_name):
    """Revoke permissions for users on a specific database (don't delete users)"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        # Get all users that have grants on this database
        cursor.execute("SELECT User FROM mysql.user")
        all_users = cursor.fetchall()
        
        revoked_count = 0
        for user_tuple in all_users:
            username = user_tuple[0]
            
            # Skip system users (root, mysql.sys, etc.)
            if username in ['root', 'mysql.sys', 'mysql.session', 'mysql.infoschema']:
                continue
            
            # Skip users that don't look like students or teachers
            if len(username) < 4:
                continue
                
            try:
                # Check if user has grants on this database
                cursor.execute(f"SHOW GRANTS FOR '{username}'@'localhost'")
                grants = cursor.fetchall()
                
                # Check if any grant is for our database
                has_grant_on_db = False
                for grant_tuple in grants:
                    grant_str = grant_tuple[0]
                    if f"`{database_name}`" in grant_str or database_name in grant_str:
                        has_grant_on_db = True
                        break
                
                # If user has grant on this database, REVOKE (not DROP)
                if has_grant_on_db:
                    # Revoke all privileges on this specific database
                    cursor.execute(f"REVOKE ALL PRIVILEGES ON `{database_name}`.* FROM '{username}'@'localhost'")
                    revoked_count += 1
                    print(f"<!-- Revoked permissions for user: {username} on database: {database_name} -->", file=sys.stderr)
                    
            except mysql.connector.Error as e:
                print(f"<!-- Error checking user {username}: {str(e)} -->", file=sys.stderr)
                continue
        
        cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, revoked_count
        
    except Exception as e:
        print(f"<!-- Error revoking database permissions: {str(e)} -->", file=sys.stderr)
        return False, 0
    
try:
    # Connect to MySQL database
    # For non-admin users, extract name from username for password
    if is_admin:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database=database_name
        )
    else:
        # Extract name from username (remove digits)
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

    # Handle teacher actions (ADMIN ONLY - already checked above)
    if action_type == "insert" and tname:
        try:
            cursor.execute("SELECT MAX(tid) FROM teachers")
            result = cursor.fetchone()
            max_tid = result[0]
            if max_tid is None:
                next_tid = 3000
            else:
                next_tid = max(max_tid + 1, 3000)
            
            cursor.execute(
                "INSERT INTO teachers (tid, tname, tdept, tadd, tcontact, tstatus) VALUES (%s, %s, %s, %s, %s, %s)",
                (next_tid, tname, tdept, tadd, tcontact, tstatus)
            )
            conn.commit()
            
            # Create MySQL user for this teacher
            success, mysql_username, mysql_password = create_mysql_user_for_teacher(next_tid, tname, database_name)
            
            if success:
                print(f"<script>alert('Teacher added successfully!\\nMySQL User Created:\\nUsername: {mysql_username}\\nPassword: {mysql_password}');window.location.href='teachers.py?tid={next_tid}';</script>")
            else:
                print(f"<script>alert('Teacher added but MySQL user creation failed');window.location.href='teachers.py?tid={next_tid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='teachers.py';</script>")
    elif action_type == "update" and tid and tname:
        try:
            cursor.execute(
                "UPDATE teachers SET tname=%s, tdept=%s, tadd=%s, tcontact=%s, tstatus=%s WHERE tid=%s",
                (tname, tdept, tadd, tcontact, tstatus, tid)
            )
            conn.commit()
            print(f"<script>window.location.href='teachers.py?tid={tid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='teachers.py?tid={tid}';</script>")
    elif action_type == "delete" and tid:
        try:
            # Get teacher name before deletion
            cursor.execute("SELECT tname FROM teachers WHERE tid=%s", (tid,))
            teacher_data = cursor.fetchone()
            tname_for_deletion = teacher_data[0] if teacher_data else ""
            
            # Delete from teacher_subjects first
            cursor.execute("DELETE FROM teacher_subjects WHERE tid=%s", (tid,))
            # Delete teacher
            cursor.execute("DELETE FROM teachers WHERE tid=%s", (tid,))
            conn.commit()
            
            # REVOKE MySQL permissions for this database (don't delete user)
            if tname_for_deletion:
                safe_name = ''.join(c for c in tname_for_deletion if c.isalnum() or c.isspace()).replace(' ', '').lower()
                mysql_username = f"{tid}{safe_name}"
                
                # Revoke permissions on THIS database only
                try:
                    revoke_conn = mysql.connector.connect(
                        host="localhost",
                        user="root",
                        password="root"
                    )
                    revoke_cursor = revoke_conn.cursor()
                    revoke_cursor.execute(f"REVOKE ALL PRIVILEGES ON `{database_name}`.* FROM '{mysql_username}'@'localhost'")
                    revoke_cursor.execute("FLUSH PRIVILEGES")
                    revoke_conn.commit()
                    revoke_cursor.close()
                    revoke_conn.close()
                except:
                    pass  # User might not exist or already revoked
            
            print(f"<script>window.location.href='teachers.py';</script>")
        except Exception as e:
            print(f"<script>window.location.href='teachers.py?tid={tid}';</script>")

        # Handle teacher-subject assignment (ADMIN ONLY - already checked above)
    if assignment_action == "assign" and selected_tid and selected_subjid:
        try:
            cursor.execute("SELECT COUNT(*) FROM teachers WHERE tid = %s", (selected_tid,))
            teacher_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM subjects WHERE subjid = %s", (selected_subjid,))
            subject_count = cursor.fetchone()[0]
            
            if teacher_count == 0 or subject_count == 0:
                error_msg = "Teacher or Subject not found"
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            if is_teacher:
                current_teacher_id = get_teacher_id_from_username(cursor, username)
                if str(current_teacher_id) == str(selected_tid):
                    error_msg = "Access Denied: Teachers can only assign themselves to subjects"
                    redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                    print(f"<script>window.location.href='{redirect_url}';</script>")
                    conn.close()
                    sys.exit()
            
            already_assigned = check_teacher_already_assigned(cursor, selected_tid, selected_subjid)
            if already_assigned:
                error_msg = "You are already assigned to this subject" if is_teacher else "Teacher is already assigned to this subject"
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            conflict_msg = check_teacher_schedule_conflict(cursor, selected_tid, selected_subjid)
            if conflict_msg:
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(conflict_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            cursor.execute("INSERT INTO teacher_subjects (tid, subjid) VALUES (%s, %s)", (selected_tid, selected_subjid))
            conn.commit()
            
            success_msg = "You have been assigned to this subject successfully" if is_teacher else "Teacher assigned to subject successfully"
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&success={html.escape(success_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
            
        except Exception as e:
            error_msg = f"Assignment failed: {str(e)}"
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
    
    elif assignment_action == "unassign" and selected_tid and selected_subjid:
        try:
            # Teachers can unassign ANY teacher (no restriction)
            # Admins can also unassign any teacher
            
            # Check if teacher is assigned to this subject
            cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE tid = %s AND subjid = %s", (selected_tid, selected_subjid))
            count = cursor.fetchone()[0]
            
            if count == 0:
                error_msg = "Teacher is not assigned to this subject"
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>alert('{error_msg}');window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            # Unassign the teacher from the subject
            cursor.execute("DELETE FROM teacher_subjects WHERE tid = %s AND subjid = %s", (selected_tid, selected_subjid))
            conn.commit()
            
            # Redirect with success message
            success_msg = "Teacher unassigned from subject successfully"
            redirect_url = f'teachers.py?tid={selected_tid}&success={html.escape(success_msg)}'
            print(f"<script>alert('{success_msg}');window.location.href='{redirect_url}';</script>")
            conn.close()
            sys.exit()
            
        except Exception as e:
            error_msg = f"Unassign failed: {str(e)}"
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
            print(f"<script>alert('{error_msg}');window.location.href='{redirect_url}';</script>")
            conn.close()
            sys.exit()
            
            # Check if teacher is assigned to this subject
            cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE tid = %s AND subjid = %s", (selected_tid, selected_subjid))
            count = cursor.fetchone()[0]
            
            if count == 0:
                error_msg = "Teacher is not assigned to this subject"
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            # Unassign the teacher from the subject
            cursor.execute("DELETE FROM teacher_subjects WHERE tid = %s AND subjid = %s", (selected_tid, selected_subjid))
            conn.commit()
            
            # Redirect with success message
            success_msg = "You have been unassigned from this subject successfully" if is_teacher else "Teacher unassigned from subject successfully"
            redirect_url = f'teachers.py?tid={selected_tid}&success={html.escape(success_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
            conn.close()
            sys.exit()
            
        except Exception as e:
            error_msg = f"Unassign failed: {str(e)}"
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
            conn.close()
            sys.exit()
        
    # Handle enrollment actions (ENROLL/DROP STUDENTS) - ADMIN OR TEACHER
    if enrollment_action == "enroll" and selected_studid and selected_subjid_enroll:
        try:
            cursor.execute("SELECT COUNT(*) FROM students WHERE studid = %s", (selected_studid,))
            student_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM subjects WHERE subjid = %s", (selected_subjid_enroll,))
            subject_count = cursor.fetchone()[0]
            
            if student_count == 0 or subject_count == 0:
                error_msg = "Student or Subject not found"
                redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            # Check if student is already enrolled
            cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid_enroll))
            count = cursor.fetchone()[0]
            if count > 0:
                error_msg = "Student is already enrolled in this subject"
                redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            # Check for schedule conflicts
            conflict_msg = check_schedule_conflict(cursor, selected_studid, selected_subjid_enroll)
            if conflict_msg:
                redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(conflict_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                sys.exit()
            
            # Enroll the student
            cursor.execute("INSERT INTO enroll (studid, subjid) VALUES (%s, %s)", (selected_studid, selected_subjid_enroll))
            conn.commit()
            
            # Create grade record
            cursor.execute("SELECT eid FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid_enroll))
            result = cursor.fetchone()
            if result:
                eid = result[0]
                cursor.execute("INSERT INTO grades (enroll_eid) VALUES (%s)", (eid,))
                conn.commit()
            
            redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&success=Student enrolled successfully'
            print(f"<script>window.location.href='{redirect_url}';</script>")
            
        except Exception as e:
            error_msg = f"Enrollment failed: {str(e)}"
            redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
    
    elif enrollment_action == "drop" and selected_studid and selected_subjid_enroll:
        try:
            # Check if teacher is authorized to drop from this subject
            if is_teacher:
                # Get current teacher ID
                teacher_id = get_teacher_id_from_username(cursor, username)
                if not teacher_id:
                    error_msg = "Teacher ID not found"
                    redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(error_msg)}'
                    print(f"<script>window.location.href='{redirect_url}';</script>")
                    conn.close()
                    sys.exit()
                
                # Check if teacher teaches this subject
                if not check_teacher_teaches_subject(cursor, teacher_id, selected_subjid_enroll):
                    error_msg = "Access Denied: You can only drop students from subjects you teach"
                    redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(error_msg)}'
                    print(f"<script>window.location.href='{redirect_url}';</script>")
                    conn.close()
                    sys.exit()
            
            # Check if enrollment exists
            cursor.execute("SELECT eid FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid_enroll))
            result = cursor.fetchone()
            
            if result:
                eid = result[0]
                # Delete from grades first
                cursor.execute("DELETE FROM grades WHERE enroll_eid = %s", (eid,))
                # Delete from enroll
                cursor.execute("DELETE FROM enroll WHERE eid = %s", (eid,))
                conn.commit()
                
                redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&success=Student dropped successfully'
                print(f"<script>window.location.href='{redirect_url}';</script>")
            else:
                error_msg = "Student is not enrolled in this subject"
                redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                
        except Exception as e:
            error_msg = f"Drop failed: {str(e)}"
            redirect_url = f'teachers.py?tid={url_tid}&subjid={url_subjid}&studid={selected_studid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")

    # Get all teachers
    cursor.execute("SELECT tid, tname, tdept, tadd, tcontact, tstatus FROM teachers ORDER BY tid")
    teachers = cursor.fetchall()

    # Get assigned subjects for selected teacher
    assigned_subjects = []
    if url_tid:
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
            FROM teacher_subjects ts 
            JOIN subjects s ON ts.subjid = s.subjid 
            WHERE ts.tid = %s 
            ORDER BY s.subjid
        """, (url_tid,))
        assigned_subjects = cursor.fetchall()

    # Get enrolled students for selected subject (if any)
    enrolled_students = []
    teacher_teaches_subject = False
    
    if url_subjid:
        cursor.execute("""
            SELECT s.studid, s.studname, s.studcrs, s.yrlvl
            FROM enroll e
            JOIN students s ON e.studid = s.studid
            WHERE e.subjid = %s
            ORDER BY s.studid
        """, (url_subjid,))
        enrolled_students = cursor.fetchall()
        
        # Check if current teacher teaches this subject
        if is_teacher and url_tid:
            teacher_teaches_subject = check_teacher_teaches_subject(cursor, url_tid, url_subjid)

    # Get all available subjects for assignment
    cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits FROM subjects ORDER BY subjid")
    all_subjects = cursor.fetchall()

    # Check for schedule conflicts and assignment status - FOR DISPLAY
    teacher_schedule_conflict = ""
    teacher_already_assigned = False
    subject_already_assigned = False
    
    if url_subjid and url_tid:
        teacher_already_assigned = check_teacher_already_assigned(cursor, url_tid, url_subjid)
        subject_already_assigned = check_subject_already_assigned(cursor, url_subjid)
        if not teacher_already_assigned and not subject_already_assigned:
            teacher_schedule_conflict = check_teacher_schedule_conflict(cursor, url_tid, url_subjid)

    # Pre-fill form
    prefill_data = {}
    if url_tid:
        cursor.execute("SELECT tid, tname, tdept, tadd, tcontact, tstatus FROM teachers WHERE tid = %s", (url_tid,))
        teacher_data = cursor.fetchone()
        if teacher_data:
            prefill_data = {
                'tid': teacher_data[0],
                'tname': teacher_data[1],
                'tdept': teacher_data[2],
                'tadd': teacher_data[3],
                'tcontact': teacher_data[4],
                'tstatus': teacher_data[5]
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
    <title>Sumeru Akademiya - Teacher Management System</title>
    <style>
    @import url('https://fonts.cdnfonts.com/css/hywenhei');
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
    .assign-green-button {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 8px; color: white; cursor: pointer; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; min-width: 300px; border: none; margin: 5px; }}
    .assign-green-button:hover:not(:disabled) {{ transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); }}
    .unassign-button {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); padding: 12px 25px; font-size: 16px; font-weight: bold; border-radius: 8px; color: white; cursor: pointer; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; min-width: 300px; border: none; margin: 5px; }}
    .unassign-button:hover:not(:disabled) {{ background: linear-gradient(135deg, #c82333 0%, #bd2130 100%); transform: translateY(-2px); box-shadow: 0 6px 12px rgba(220, 53, 69, 0.2); }}
    .enroll-button {{ background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 8px 15px; font-size: 14px; font-weight: bold; border-radius: 5px; color: white; cursor: pointer; transition: all 0.3s ease; border: none; margin: 2px; }}
    .enroll-button:hover:not(:disabled) {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3); }}
    .drop-button {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); padding: 8px 15px; font-size: 14px; font-weight: bold; border-radius: 5px; color: white; cursor: pointer; transition: all 0.3s ease; border: none; margin: 2px; }}
    .drop-button:hover:not(:disabled) {{ background: linear-gradient(135deg, #c82333 0%, #bd2130 100%); transform: translateY(-2px); box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3); }}
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
    .three-column-layout {{ display: grid; grid-template-columns: 1fr 1fr 1.5fr; gap: 30px; }}
    .enroll-buttons-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 15px; }}
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
    
    .teacher-tag {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        margin-left: 5px;
        background-color: #007bff;
        color: white;
    }}
    
    @media (max-width: 1024px) {{
        .three-column-layout {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>
    <script>
    let selectedTeacherId = null;
    let selectedAssignedSubjectId = null;
    let isAdmin = {str(is_admin).lower()};
    let isTeacher = {str(is_teacher).lower()};
    let isStudent = {str(is_student).lower()};
    
    function selectTeacher(tid, tname, tdept, tadd, tcontact, tstatus) {{
        selectedTeacherId = tid;
        selectedAssignedSubjectId = null;
        document.getElementById('tid').value = tid;
        document.getElementById('tname').value = tname;
        document.getElementById('tdept').value = tdept;
        document.getElementById('tadd').value = tadd;
        document.getElementById('tcontact').value = tcontact;
        document.getElementById('tstatus').value = tstatus;
        
        const urlParams = new URLSearchParams(window.location.search);
        const currentSubjid = urlParams.get('subjid');
        let newUrl = 'teachers.py?tid=' + tid;
        if (currentSubjid) {{
            newUrl += '&subjid=' + currentSubjid;
        }}
        window.location.href = newUrl;
    }}
    
function selectAssignedSubject(subjid, subjcode) {{
    selectedAssignedSubjectId = subjid;
    let rows = document.querySelectorAll('#assignedSubjectsTable tr');
    rows.forEach(row => row.classList.remove('selected-row'));
    let rowsArray = Array.from(rows);
    for (let row of rowsArray) {{
        let firstCell = row.querySelector('td:first-child');
        if (firstCell && firstCell.textContent === subjid) {{
            row.classList.add('selected-row');
            break;
        }}
    }}
    
    let unassignButton = document.getElementById('unassignButton');
    if (unassignButton && selectedTeacherId && selectedAssignedSubjectId) {{
        unassignButton.style.display = 'block';
        unassignButton.innerHTML = 'Unassign Teacher ID: ' + selectedTeacherId + ' from Subject ID: ' + selectedAssignedSubjectId;
        unassignButton.disabled = !(isAdmin || isTeacher);  //  Enable for admins AND teachers
    }}
}}
        
        let unassignButton = document.getElementById('unassignButton');
        if (unassignButton && selectedTeacherId && selectedAssignedSubjectId) {{
            unassignButton.style.display = 'block';
            unassignButton.innerHTML = 'Unassign Teacher ID: ' + selectedTeacherId + ' from Subject ID: ' + selectedAssignedSubjectId;
            unassignButton.disabled = !isAdmin;
        }}

    
    function submitForm(action) {{
        if (isStudent) {{
            alert('Security Alert: Students cannot modify teacher records.');
            window.location.href = 'index.py';
            return false;
        }}
        if (!isAdmin) {{
            alert('Access Denied: Only administrators can modify teacher records');
            return false;
        }}
        let form = document.getElementById('teacherForm');
        let actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action_type';
        actionInput.value = action;
        form.appendChild(actionInput);
        
        form.submit();
    }}
    
    function assignTeacher(subjid) {{
        if (isStudent) {{
            alert('Security Alert: Students cannot assign subjects to teachers.');
            window.location.href = 'index.py';
            return false;
        }}
        if (!isAdmin && !isTeacher) {{
            alert('Access Denied: Only administrators or teachers can assign subjects');
            return false;
        }}
        let tid = document.getElementById('tid').value;
        if (tid && subjid) {{
            let form = document.createElement('form');
            form.method = 'POST';
            form.action = 'teachers.py';
            
            let tidInput = document.createElement('input');
            tidInput.type = 'hidden';
            tidInput.name = 'selected_tid';
            tidInput.value = tid;
            form.appendChild(tidInput);
            
            let subjidInput = document.createElement('input');
            subjidInput.type = 'hidden';
            subjidInput.name = 'selected_subjid';
            subjidInput.value = subjid;
            form.appendChild(subjidInput);
            
            let actionInput = document.createElement('input');
            actionInput.type = 'hidden';
            actionInput.name = 'assignment_action';
            actionInput.value = 'assign';
            form.appendChild(actionInput);
            
            // Preserve URL parameters
            let urlTid = document.createElement('input');
            urlTid.type = 'hidden';
            urlTid.name = 'tid';
            urlTid.value = tid;
            form.appendChild(urlTid);
            
            let urlSubjid = document.createElement('input');
            urlSubjid.type = 'hidden';
            urlSubjid.name = 'subjid';
            urlSubjid.value = subjid;
            form.appendChild(urlSubjid);
            
            document.body.appendChild(form);
            form.submit();
        }}
    }}
    
function unassignSubject() {{
    if (isStudent) {{
        alert('Security Alert: Students cannot unassign teachers from subjects.');
        window.location.href = 'index.py';
        return false;
    }}
    if (!isAdmin && !isTeacher) {{
        alert('Access Denied: Only administrators or teachers can unassign teachers from subjects');
        return false;
    }}
    if (selectedTeacherId && selectedAssignedSubjectId) {{
        let form = document.createElement('form');
        form.method = 'POST';
        form.action = 'teachers.py';
        
        let tidInput = document.createElement('input');
        tidInput.type = 'hidden';
        tidInput.name = 'selected_tid';
        tidInput.value = selectedTeacherId;
        form.appendChild(tidInput);
        
        let subjidInput = document.createElement('input');
        subjidInput.type = 'hidden';
        subjidInput.name = 'selected_subjid';
        subjidInput.value = selectedAssignedSubjectId;
        form.appendChild(subjidInput);
        
        let actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'assignment_action';
        actionInput.value = 'unassign';
        form.appendChild(actionInput);
        
        let urlTid = document.createElement('input');
        urlTid.type = 'hidden';
        urlTid.name = 'tid';
        urlTid.value = selectedTeacherId;
        form.appendChild(urlTid);
        
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
            form.action = 'teachers.py';
            
            let studidInput = document.createElement('input');
            studidInput.type = 'hidden';
            studidInput.name = 'selected_studid';
            studidInput.value = studid;
            form.appendChild(studidInput);
            
            let subjidInput = document.createElement('input');
            subjidInput.type = 'hidden';
            subjidInput.name = 'selected_subjid_enroll';
            subjidInput.value = subjid;
            form.appendChild(subjidInput);
            
            let actionInput = document.createElement('input');
            actionInput.type = 'hidden';
            actionInput.name = 'enrollment_action';
            actionInput.value = 'enroll';
            form.appendChild(actionInput);
            
            const urlParams = new URLSearchParams(window.location.search);
            const currentTid = urlParams.get('tid');
            const currentSubjid = urlParams.get('subjid');
            
            if (currentTid) {{
                let urlTid = document.createElement('input');
                urlTid.type = 'hidden';
                urlTid.name = 'tid';
                urlTid.value = currentTid;
                form.appendChild(urlTid);
            }}
            
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
            if (confirm('Are you sure you want to drop this student from the subject?')) {{
                let form = document.createElement('form');
                form.method = 'POST';
                form.action = 'teachers.py';
                
                let studidInput = document.createElement('input');
                studidInput.type = 'hidden';
                studidInput.name = 'selected_studid';
                studidInput.value = studid;
                form.appendChild(studidInput);
                
                let subjidInput = document.createElement('input');
                subjidInput.type = 'hidden';
                subjidInput.name = 'selected_subjid_enroll';
                subjidInput.value = subjid;
                form.appendChild(subjidInput);
                
                let actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'enrollment_action';
                actionInput.value = 'drop';
                form.appendChild(actionInput);
                
                const urlParams = new URLSearchParams(window.location.search);
                const currentTid = urlParams.get('tid');
                const currentSubjid = urlParams.get('subjid');
                
                if (currentTid) {{
                    let urlTid = document.createElement('input');
                    urlTid.type = 'hidden';
                    urlTid.name = 'tid';
                    urlTid.value = currentTid;
                    form.appendChild(urlTid);
                }}
                
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
            form.action = 'teachers.py';
            
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
            form.action = 'teachers.py';
            
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
    const tid = urlParams.get('tid');
    const subjid = urlParams.get('subjid');
    
    if (tid) {{
        selectedTeacherId = tid;
        let rows = document.querySelectorAll('#teachersTable tr');
        for (let row of rows) {{
            let firstCell = row.querySelector('td:first-child');
            if (firstCell && firstCell.textContent === tid) {{
                row.classList.add('selected-row');
                break;
            }}
        }}
    }}
    
    if (subjid && tid) {{
        let subjectRows = document.querySelectorAll('#assignedSubjectsTable tr');
        for (let row of subjectRows) {{
            let firstCell = row.querySelector('td:first-child');
            if (firstCell && firstCell.textContent === subjid) {{
                row.classList.add('selected-row');
                selectedAssignedSubjectId = subjid;
                let unassignButton = document.getElementById('unassignButton');
                if (unassignButton) {{
                    unassignButton.style.display = 'block';
                    unassignButton.innerHTML = 'Unassign Teacher ID: ' + selectedTeacherId + ' from Subject ID: ' + selectedAssignedSubjectId;
                    unassignButton.disabled = !(isAdmin || isTeacher);  // Enable for admins AND teachers
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
            <img src="sumeru.jpg" alt="Genshin Impact Logo" class="logo">
            <div class="university-info">
                <div class="university-name">Sumeru Akademiya</div>
                <div class="subtitle">Teacher Management System</div>
                <div class="subtitle">Database: {html.escape(database_name)} | User: {html.escape(username)} <span class="role-badge { 'admin-badge' if is_admin else 'teacher-badge' if is_teacher else 'student-badge' }">{role_display}</span></div>
            </div>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
    """)

    # Generate navigation links with URL preservation
    students_link = "students.py"
    subjects_link = "subjects.py"
    teachers_link = "teachers.py"
    
    if url_subjid:
        students_link = f"students.py?subjid={url_subjid}"
        subjects_link = f"subjects.py?subjid={url_subjid}"
        teachers_link = f"teachers.py?subjid={url_subjid}"

    print(f"""
            <a href="{students_link}" class="nav-link">Students</a>
            <a href="{subjects_link}" class="nav-link">Subjects</a>
            <a href="{teachers_link}" class="nav-link">Teachers</a>
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
    if not is_admin and not is_teacher:
        print(f"""
        <div class="info-message">
            You are logged in as {role_display}. You have read-only access to this page.
        </div>
        """)
    elif is_teacher:
        print(f"""
        <div class="info-message">
            You are logged in as <strong>Teacher</strong>. You can enroll/drop students in subjects you teach.
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

    # Use three-column layout when a subject is selected
    if url_subjid:
        print("""
    <div class="three-column-layout">
        <div>
        """)
    else:
        print("""
    <div class="two-column-layout">
        <div>
        """)

    # Teacher Form Section
    print(f"""
            <div class="form-container">
                <h2>Teacher Form</h2>
                <form method="POST" action="teachers.py" id="teacherForm">
    """)
    
    if url_subjid:
        print(f"<input type='hidden' name='subjid' value='{url_subjid}'>")
    
    # Disable form inputs for non-admins
    disabled_attr = "" if is_admin else "disabled"
    
    print(f"""
                    <table style="width: 100%;">
                        <tr>
                            <td>Teacher ID:</td>
                            <td><input type="text" name="tid" id="tid" style="width: 100px" readonly value='{prefill_data.get("tid", "")}'></td>
                        </tr>
                        <tr>
                            <td>Name:</td>
                            <td><input type="text" name="tname" id="tname" style="width: 200px" value='{html.escape(prefill_data.get("tname", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Department:</td>
                            <td><input type="text" name="tdept" id="tdept" style="width: 150px" value='{html.escape(prefill_data.get("tdept", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Address:</td>
                            <td><input type="text" name="tadd" id="tadd" style="width: 200px" value='{html.escape(prefill_data.get("tadd", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Contact:</td>
                            <td><input type="text" name="tcontact" id="tcontact" style="width: 150px" value='{html.escape(prefill_data.get("tcontact", ""))}' {disabled_attr}></td>
                        </tr>
                        <tr>
                            <td>Status:</td>
                            <td><input type="text" name="tstatus" id="tstatus" style="width: 100px" value='{html.escape(prefill_data.get("tstatus", ""))}' {disabled_attr}></td>
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
    """)

    # Assignment Section - For admins OR teachers when subject is selected
    if url_subjid and (is_admin or is_teacher):
        print("""
            <div class="enroll-section">
                <h3>Assign Teacher to Subject</h3>
        """)
        
        if url_tid and prefill_data.get('tid'):
            tid = prefill_data.get('tid')
            
            # Check if this teacher is the currently logged in teacher
            is_current_teacher = False
            if is_teacher:
                current_teacher_id = get_teacher_id_from_username(cursor, username)
                is_current_teacher = (str(current_teacher_id) == str(tid))
            
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Assign Teacher to Subject:</p>
            </div>""")
            
            # Check if subject already has a teacher
            subject_assigned = check_subject_already_assigned(cursor, url_subjid)
            
            if subject_assigned:
                # Get the currently assigned teacher info
                cursor.execute("""
                    SELECT t.tid, t.tname 
                    FROM teachers t 
                    INNER JOIN teacher_subjects ts ON t.tid = ts.tid 
                    WHERE ts.subjid = %s
                """, (url_subjid,))
                current_teacher = cursor.fetchone()
                
                if current_teacher:
                    if is_teacher and str(current_teacher[0]) == str(tid):
                        # Teacher is already assigned to this subject
                        print(f"""
                        <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                            <div class="info-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                                <strong>You are already assigned to Subject ID: {url_subjid}</strong><br>
                                You are currently teaching this subject.
                            </div>
                            <button type="button" onclick="assignTeacher('{url_subjid}')" class="assign-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                                You are already assigned to Subject ID: {url_subjid}
                            </button>
                        </div>
                        """)
                    else:
                        # Subject has a different teacher assigned
                        print(f"""
                        <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                            <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                                <strong>Subject already has a teacher assigned</strong><br>
                                Teacher ID: {current_teacher[0]} - {current_teacher[1]}
                            </div>
                            <button type="button" onclick="assignTeacher('{url_subjid}')" class="assign-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                                Subject already has Teacher ID: {current_teacher[0]} assigned
                            </button>
                        </div>
                        """)
                else:
                    # Subject has a teacher but couldn't fetch details
                    print(f"""
                    <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                        <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                            Subject ID: {url_subjid} already has a teacher assigned
                        </div>
                        <button type="button" onclick="assignTeacher('{url_subjid}')" class="assign-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                            Subject already has a teacher assigned
                        </button>
                    </div>
                    """)
            
            elif teacher_already_assigned:
                # Teacher is already assigned to this subject
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                    <div class="info-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                        {'You are' if is_current_teacher else 'Teacher ID: ' + str(tid)} already assigned to Subject ID: {url_subjid}
                    </div>
                    <button type="button" onclick="assignTeacher('{url_subjid}')" class="assign-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                        {'You are' if is_current_teacher else 'Teacher ID: ' + str(tid)} already assigned
                    </button>
                </div>
                """)
            
            elif teacher_schedule_conflict:
                # Schedule conflict
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                    <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                        <div style="text-align: center; color: #dc3545; font-weight: bold;">
                            {teacher_schedule_conflict}
                        </div>
                    </div>
                    <button type="button" onclick="assignTeacher('{url_subjid}')" class="assign-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                        Schedule conflict - cannot assign
                    </button>
                </div>
                """)
            
            else:
                # Teacher can be assigned
                button_text = f"Assign {'Yourself' if is_current_teacher else 'Teacher ID: ' + str(tid)} to Subject ID: {url_subjid}"
                button_disabled = "" if (is_admin or is_teacher) else "disabled"
                
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center;">
                    <button type="button" onclick="assignTeacher('{url_subjid}')" class="assign-green-button" {button_disabled}>
                        {button_text}
                    </button>
                </div>
                """)
        
        elif not url_tid:
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Assign Teacher to Subject:</p>
            </div>""")
            print("""<div class="enroll-buttons-container" style="justify-content: center;">""")
            
            if is_teacher and not is_admin:
                # Get current teacher ID for teacher users
                current_teacher_id = get_teacher_id_from_username(cursor, username)
                if current_teacher_id:
                    print(f"""<p style="text-align: center; color: #666; padding: 20px; width: 100%;">
                        To assign yourself to Subject ID: {url_subjid}, please select your teacher profile from the table first.
                    </p>""")
                else:
                    print(f"""<p style="text-align: center; color: #666; padding: 20px; width: 100%;">
                        Select a teacher from the table to assign to Subject ID: {url_subjid}
                    </p>""")
            else:
                print(f"""<p style="text-align: center; color: #666; padding: 20px; width: 100%;">
                    Select a teacher from the table to assign to Subject ID: {url_subjid}
                </p>""")
            
            print("</div>")
        
        print("""
            </div>
        """)

    # Close first column
    print("""
        </div>
    """)

    # Teachers Table Section (TOP RIGHT when subject is selected)
    if url_subjid:
        print("""
        <div style="display: flex; flex-direction: column; gap: 30px;">
        """)
    else:
        print("""
        <div>
        """)

    print(f"""
            <div class="form-container">
                <h2>Teachers Table for: {database_name}</h2>
                <table border="1" id="teachersTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Department</th>
                            <th>Address</th>
                            <th>Contact</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
    """)
    
    for teacher in teachers:
        print("<tr onclick='selectTeacher(" + str(teacher[0]) + ", \"" + html.escape(str(teacher[1])) + "\", \"" + html.escape(str(teacher[2])) + "\", \"" + html.escape(str(teacher[3])) + "\", \"" + html.escape(str(teacher[4])) + "\", \"" + html.escape(str(teacher[5])) + "\")'>")
        print("<td>" + str(teacher[0]) + "</td>")
        print("<td>" + html.escape(str(teacher[1])) + "</td>")
        print("<td>" + html.escape(str(teacher[2])) + "</td>")
        print("<td>" + html.escape(str(teacher[3])) + "</td>")
        print("<td>" + html.escape(str(teacher[4])) + "</td>")
        print("<td>" + html.escape(str(teacher[5])) + "</td>")
        print("</tr>")
    
    print("""
                    </tbody>
                </table>
            </div>
    """)

    # Assigned Subjects Section (RIGHT COLUMN, DIRECTLY UNDER TEACHERS TABLE)
    if url_subjid:
        print(f"""
            <div class="form-container">
                <h2>Assigned Subjects for Teacher ID: {url_tid if url_tid else "None"}</h2>
                <table border="1" id="assignedSubjectsTable">
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
        
        if assigned_subjects:
            for subject in assigned_subjects:
                print("<tr onclick='selectAssignedSubject(" + str(subject[0]) + ", \"" + html.escape(str(subject[1])) + "\")'>")
                print("<td>" + str(subject[0]) + "</td>")
                print("<td>" + html.escape(str(subject[1])) + "</td>")
                print("<td>" + html.escape(str(subject[2])) + "</td>")
                print("<td>" + str(subject[3]) + "</td>")
                print("<td>" + html.escape(str(subject[4])) + "</td>")
                print("</tr>")
        else:
            print("<tr><td colspan='5' style='text-align: center; padding: 20px; color: #666;'>No assigned subjects</td></tr>")
        
        unassign_button_disabled = "" if (is_admin or is_teacher) else "disabled"  # Enable for admins AND teachers
        print(f"""
                                </tbody>
                            </table>
                            <div style="margin-top: 20px; text-align: center;">
                                <button id="unassignButton" type="button" onclick="unassignSubject()" class="unassign-button" style="width: 100%; padding: 12px; display: none;" {unassign_button_disabled}>
                                    Unassign Subject
                                </button>
                            </div>
                        </div>
                    </div>
                """)
    else:
        print("""
        </div>
        """)
        
    # # Enrolled Students Section - Only when subject is selected
    # if url_subjid:
    #     print(f"""
    #         <div class="form-container" style="margin-top: 30px;">
    #             <h2>Enrolled Students in Subject ID: {url_subjid}</h2>
    #             <p style="color: #666; margin-bottom: 15px;">
    #                 { "You can enroll/drop students in this subject (Teachers: only subjects you teach)" if (is_admin or is_teacher) else "Students enrolled in this subject" }
    #                 { "<span class='teacher-tag'>You teach this subject</span>" if teacher_teaches_subject else "" }
    #             </p>
    #             <table border="1" id="enrolledStudentsTable">
    #                 <thead>
    #                     <tr>
    #                         <th>Student ID</th>
    #                         <th>Name</th>
    #                         <th>Course</th>
    #                         <th>Year Level</th>
    #                         <th>Action</th>
    #                     </tr>
    #                 </thead>
    #                 <tbody>
    #     """)
        
    #     if enrolled_students:
    #         for student in enrolled_students:
    #             print("<tr>")
    #             print("<td>" + str(student[0]) + "</td>")
    #             print("<td>" + html.escape(str(student[1])) + "</td>")
    #             print("<td>" + html.escape(str(student[2])) + "</td>")
    #             print("<td>" + html.escape(str(student[3])) + "</td>")
    #             print("<td>")
                
    #             # Drop button - Show for admins OR teachers who teach this subject
    #             if is_admin or (is_teacher and teacher_teaches_subject):
    #                 print(f"""<button onclick="dropStudent('{student[0]}', '{url_subjid}')" class="drop-button" style="padding: 5px 10px; font-size: 12px;">Drop</button>""")
    #             else:
    #                 print("--")
                
    #             print("</td>")
    #             print("</tr>")
    #     else:
    #         print("""<tr><td colspan="5" style="text-align: center; padding: 20px; color: #666;">
    #             No students enrolled in this subject
    #         </td></tr>""")
        
    #     print("""
    #                 </tbody>
    #             </table>
                
    #             <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
    #                 <h3 style="color: #1e3c72; margin-top: 0; margin-bottom: 15px; font-size: 16px;">Enroll New Student</h3>
    #                 <form id="enrollForm" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
    #                     <input type="number" id="enroll_studid" placeholder="Enter Student ID" style="width: 120px;" required>
    #                     <input type="hidden" id="enroll_subjid" value="{url_subjid}">
    #                     <button type="button" onclick="enrollStudent(document.getElementById('enroll_studid').value, '{url_subjid}')" class="enroll-button" { '' if (is_admin or (is_teacher and teacher_teaches_subject)) else 'disabled' }>
    #                         Enroll Student
    #                     </button>
    #                 </form>
    #             </div>
    #         </div>
    #     """)

    # Close the last column and layout div
    print("""
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