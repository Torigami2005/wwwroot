#!/usr/bin/env python3
import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()

# Get form values
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

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    cursor = conn.cursor()

    # Handle student actions
    if action_type == "insert" and studname:
        try:
            cursor.execute("SELECT MAX(studid) FROM students")
            result = cursor.fetchone()
            max_studid = result[0]
            
            if max_studid is None:
                next_studid = 1000
            else:
                next_studid = max(max_studid + 1, 1000)
            
            cursor.execute("INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s, %s)", 
                          (next_studid, studname, studadd, studcrs, studgender, yrlvl))
            conn.commit()
            print(f"<script>window.location.href='students.py?studid={next_studid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='students.py';</script>")
    
    elif action_type == "update" and studid and studname:
        try:
            cursor.execute("UPDATE students SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s WHERE studid=%s", 
                          (studname, studadd, studcrs, studgender, yrlvl, studid))
            conn.commit()
            print(f"<script>window.location.href='students.py?studid={studid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='students.py?studid={studid}';</script>")
    
    elif action_type == "delete" and studid:
        try:
            cursor.execute("SELECT eid FROM enroll WHERE studid=%s", (studid,))
            enrollments = cursor.fetchall()
            
            for enrollment in enrollments:
                eid = enrollment[0]
                cursor.execute("DELETE FROM grades WHERE enroll_eid = %s", (eid,))
            
            cursor.execute("DELETE FROM enroll WHERE studid=%s", (studid,))
            cursor.execute("DELETE FROM students WHERE studid=%s", (studid,))
            
            conn.commit()
            print("<script>window.location.href='students.py';</script>")
        except Exception as e:
            print("<script>window.location.href='students.py';</script>")

    # Handle subject enrollment
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
                exit()
            
            cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s", (selected_studid, selected_subjid))
            count = cursor.fetchone()[0]
            
            if count > 0:
                error_msg = "Student is already enrolled in this subject"
                redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                exit()
            
            # Check for schedule conflicts - DIRECT SQL
            cursor.execute("SELECT subjsched FROM subjects WHERE subjid = %s", (selected_subjid,))
            new_subject = cursor.fetchone()
            new_sched = new_subject[0] if new_subject else ""
            
            if new_sched and new_sched.strip():
                # Get enrolled subjects for the student
                cursor.execute("""
                    SELECT s.subjsched 
                    FROM subjects s
                    INNER JOIN enroll e ON s.subjid = e.subjid 
                    WHERE e.studid = %s AND s.subjsched IS NOT NULL AND s.subjsched != ''
                """, (selected_studid,))
                enrolled_schedules = cursor.fetchall()
                
                # Parse new schedule
                new_sched_clean = new_sched.strip()
                
                if len(new_sched_clean) >= 3:
                    new_days = new_sched_clean[:3]  # First 3 chars are days
                    
                    # Find dash position
                    dash_pos = new_sched_clean.find('-')
                    if dash_pos != -1:
                        # Get time part (after days)
                        time_part = new_sched_clean[3:].strip()
                        
                        # Handle multiple spaces
                        if ' ' in time_part:
                            # Remove extra spaces, keep just the time part
                            time_part = time_part.replace(' ', '')
                        
                        # Split start and end times
                        if '-' in time_part:
                            new_stime, new_etime = time_part.split('-')
                            new_stime = new_stime.strip()
                            new_etime = new_etime.strip()
                            
                            # Convert to minutes
                            new_start_hour = int(new_stime[:2])
                            new_start_min = int(new_stime[3:5])
                            new_end_hour = int(new_etime[:2])
                            new_end_min = int(new_etime[3:5])
                            new_start_minutes = (new_start_hour * 60) + new_start_min
                            new_end_minutes = (new_end_hour * 60) + new_end_min
                            
                            # Check each enrolled subject
                            for enrolled in enrolled_schedules:
                                old_sched = enrolled[0].strip() if enrolled[0] else ""
                                
                                if old_sched and len(old_sched) >= 3:
                                    old_days = old_sched[:3]
                                    
                                    # Only check if same days
                                    if old_days == new_days:
                                        old_dash_pos = old_sched.find('-')
                                        if old_dash_pos != -1:
                                            # Get time part for old schedule
                                            old_time_part = old_sched[3:].strip()
                                            
                                            # Handle multiple spaces
                                            if ' ' in old_time_part:
                                                old_time_part = old_time_part.replace(' ', '')
                                            
                                            if '-' in old_time_part:
                                                old_stime, old_etime = old_time_part.split('-')
                                                old_stime = old_stime.strip()
                                                old_etime = old_etime.strip()
                                                
                                                # Convert to minutes
                                                old_start_hour = int(old_stime[:2])
                                                old_start_min = int(old_stime[3:5])
                                                old_end_hour = int(old_etime[:2])
                                                old_end_min = int(old_etime[3:5])
                                                old_start_minutes = (old_start_hour * 60) + old_start_min
                                                old_end_minutes = (old_end_hour * 60) + old_end_min
                                                
                                                # Check for time overlap
                                                # NOT (new ends before old starts OR new starts after old ends)
                                                if not (new_end_minutes <= old_start_minutes or new_start_minutes >= old_end_minutes):
                                                    conflict_msg = f"Conflict with {old_sched}"
                                                    redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}&error={html.escape(conflict_msg)}'
                                                    print(f"<script>window.location.href='{redirect_url}';</script>")
                                                    conn.close()
                                                    exit()
            
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

    # Get URL parameters
    url_studid = form.getvalue("studid", "")
    url_subjid = form.getvalue("subjid", "")
    error_msg = form.getvalue("error", "")
    success_msg = form.getvalue("success", "")
    
    # Check for schedule conflicts - DIRECT SQL for display
    conflict_detected = False
    conflict_message = ""
    
    if url_studid and url_subjid:
        cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s", (url_studid, url_subjid))
        already_enrolled = cursor.fetchone()[0] > 0
        
        if not already_enrolled:
            # Get the schedule of the new subject
            cursor.execute("SELECT subjsched FROM subjects WHERE subjid = %s", (url_subjid,))
            new_subject = cursor.fetchone()
            new_sched = new_subject[0] if new_subject else ""
            
            if new_sched and new_sched.strip():
                # Get enrolled subjects for the student
                cursor.execute("""
                    SELECT s.subjsched 
                    FROM subjects s
                    INNER JOIN enroll e ON s.subjid = e.subjid 
                    WHERE e.studid = %s AND s.subjsched IS NOT NULL AND s.subjsched != ''
                """, (url_studid,))
                enrolled_schedules = cursor.fetchall()
                
                # Parse new schedule
                new_sched_clean = new_sched.strip()
                
                if len(new_sched_clean) >= 3:
                    new_days = new_sched_clean[:3]
                    
                    # Find dash position
                    dash_pos = new_sched_clean.find('-')
                    if dash_pos != -1:
                        # Get time part (after days)
                        time_part = new_sched_clean[3:].strip()
                        
                        # Handle multiple spaces
                        if ' ' in time_part:
                            time_part = time_part.replace(' ', '')
                        
                        # Split start and end times
                        if '-' in time_part:
                            new_stime, new_etime = time_part.split('-')
                            new_stime = new_stime.strip()
                            new_etime = new_etime.strip()
                            
                            # Convert to minutes
                            new_start_hour = int(new_stime[:2])
                            new_start_min = int(new_stime[3:5])
                            new_end_hour = int(new_etime[:2])
                            new_end_min = int(new_etime[3:5])
                            new_start_minutes = (new_start_hour * 60) + new_start_min
                            new_end_minutes = (new_end_hour * 60) + new_end_min
                            
                            # Check each enrolled subject
                            for enrolled in enrolled_schedules:
                                old_sched = enrolled[0].strip() if enrolled[0] else ""
                                
                                if old_sched and len(old_sched) >= 3:
                                    old_days = old_sched[:3]
                                    
                                    # Only check if same days
                                    if old_days == new_days:
                                        old_dash_pos = old_sched.find('-')
                                        if old_dash_pos != -1:
                                            # Get time part for old schedule
                                            old_time_part = old_sched[3:].strip()
                                            
                                            # Handle multiple spaces
                                            if ' ' in old_time_part:
                                                old_time_part = old_time_part.replace(' ', '')
                                            
                                            if '-' in old_time_part:
                                                old_stime, old_etime = old_time_part.split('-')
                                                old_stime = old_stime.strip()
                                                old_etime = old_etime.strip()
                                                
                                                # Convert to minutes
                                                old_start_hour = int(old_stime[:2])
                                                old_start_min = int(old_stime[3:5])
                                                old_end_hour = int(old_etime[:2])
                                                old_end_min = int(old_etime[3:5])
                                                old_start_minutes = (old_start_hour * 60) + old_start_min
                                                old_end_minutes = (old_end_hour * 60) + old_end_min
                                                
                                                # Check for time overlap
                                                if not (new_end_minutes <= old_start_minutes or new_start_minutes >= old_end_minutes):
                                                    conflict_detected = True
                                                    conflict_message = f"Conflict with {old_sched}"
                                                    break
        
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
            FROM enroll e 
            JOIN subjects s ON e.subjid = s.subjid 
            WHERE e.studid = %s
            ORDER BY s.subjid
        """, (url_studid,))
        enrolled_subjects = cursor.fetchall()
        
        enrolled_subject_ids = [subject[0] for subject in enrolled_subjects]
    elif url_studid:
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
            FROM enroll e 
            JOIN subjects s ON e.subjid = s.subjid 
            WHERE e.studid = %s
            ORDER BY s.subjid
        """, (url_studid,))
        enrolled_subjects = cursor.fetchall()
        enrolled_subject_ids = [subject[0] for subject in enrolled_subjects]
    else:
        enrolled_subjects = []
        enrolled_subject_ids = []

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

    print("""
    <html>
    <head>
        <title>Sumeru Akademiya - Student Enrollment System</title>
        <style>
            * {
                font-family: HYWenHei, sans-serif !important;
            }
            
            body {
                font-family: HYWenHei, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            
            .header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 15px 30px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .header-left {
                display: flex;
                align-items: center;
            }
            
            .logo {
                height: 70px;
                width: 70px;
                margin-right: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
            
            .university-info {
                display: flex;
                flex-direction: column;
            }
            
            .university-name {
                font-size: 28px;
                font-weight: bold;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                letter-spacing: 1px;
                line-height: 1.2;
            }
            
            .subtitle {
                font-size: 16px;
                opacity: 0.9;
                margin-top: 3px;
            }
            
            .nav-link {
                color: white;
                text-decoration: none;
                background-color: rgba(255, 255, 255, 0.2);
                padding: 8px 20px;
                border-radius: 20px;
                transition: all 0.3s ease;
                font-size: 14px;
            }
            
            .nav-link:hover {
                background-color: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
            
            .main-container {
                max-width: 1400px;
                margin: 30px auto;
                padding: 20px;
            }
            
            button {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                font-family: HYWenHei
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
            
            button:disabled {
                background: #cccccc;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            .enroll-green-button {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                color: white;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
                min-width: 300px;
                border: none;
                margin: 5px;
            }
            
            .enroll-green-button:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
            
            .drop-button {
                background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                color: white;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
                min-width: 300px;
                border: none;
                margin: 5px;
            }
            
            .drop-button:hover {
                background: linear-gradient(135deg, #c82333 0%, #bd2130 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(220, 53, 69, 0.2);
            }
            
            input, select {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            
            input:focus, select:focus {
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
            }
            
            .error-message {
                background-color: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #f5c6cb;
                text-align: center;
                font-weight: bold;
            }
            
            .success-message {
                background-color: #d4edda;
                color: #155724;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #c3e6cb;
                text-align: center;
                font-weight: bold;
            }
            
            .warning-message {
                background-color: #fff3cd;
                color: #856404;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border: 1px solid #ffeaa7;
                text-align: center;
                font-weight: bold;
            }
            
            table {
                border-collapse: collapse;
                width: 100%;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                overflow: hidden;
            }
            
            th {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 12px 15px;
                text-align: center;
                font-weight: bold;
                font-size: 16px;
            }
            
            td {
                padding: 12px 15px;
                border-bottom: 1px solid #e0e0e0;
                text-align: center;
                transition: background-color 0.2s ease;
            }
            
            tr:hover {
                background-color: rgba(42, 82, 152, 0.05);
                cursor: pointer;
            }
            
            .selected-row {
                background-color: rgba(42, 82, 152, 0.15) !important;
                font-weight: bold;
            }
            
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            
            tr:nth-child(even):hover {
                background-color: rgba(42, 82, 152, 0.08);
            }
            
            .form-container {
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                margin-bottom: 30px;
            }
            
            .form-container h2 {
                color: #1e3c72;
                margin-top: 0;
                border-bottom: 2px solid #1e3c72;
                padding-bottom: 10px;
            }
            
            .enroll-section {
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                margin-top: 20px;
            }
            
            .enroll-section h3 {
                color: #1e3c72;
                margin-top: 0;
            }
            
            .two-column-layout {
                display: grid;
                grid-template-columns: 1fr 1.5fr;
                gap: 30px;
            }
            
            .enroll-buttons-container {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
                margin-top: 15px;
            }
            
            @media (max-width: 1024px) {
                .two-column-layout {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        <script>
            let selectedStudentId = null;
            let selectedEnrolledSubjectId = null;
            
            function selectStudent(studid, studname, studadd, studcrs, studgender, yrlvl) {
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
                if (currentSubjid) {
                    newUrl += '&subjid=' + currentSubjid;
                }
                window.location.href = newUrl;
            }
            
            function selectEnrolledSubject(subjid, subjcode) {
                selectedEnrolledSubjectId = subjid;
                
                let rows = document.querySelectorAll('#enrolledSubjectsTable tr');
                rows.forEach(row => row.classList.remove('selected-row'));
                
                let rowsArray = Array.from(rows);
                for (let row of rowsArray) {
                    let firstCell = row.querySelector('td:first-child');
                    if (firstCell && firstCell.textContent === subjid) {
                        row.classList.add('selected-row');
                        break;
                    }
                }
                
                let dropButton = document.getElementById('dropButton');
                if (dropButton && selectedStudentId && selectedEnrolledSubjectId) {
                    dropButton.style.display = 'block';
                    dropButton.innerHTML = 'Drop Student ID: ' + selectedStudentId + ' from Subject ID: ' + selectedEnrolledSubjectId;
                    dropButton.disabled = false;
                }
            }
            
            function submitForm(action) {
                let form = document.getElementById('studentForm');
                let actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'action_type';
                actionInput.value = action;
                form.appendChild(actionInput);
                form.submit();
            }
            
            function enrollStudent(subjid) {
                let studid = document.getElementById('studid').value;
                
                if (studid && subjid) {
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
                    if (currentSubjid) {
                        let urlSubjId = document.createElement('input');
                        urlSubjId.type = 'hidden';
                        urlSubjId.name = 'subjid';
                        urlSubjId.value = currentSubjid;
                        form.appendChild(urlSubjId);
                    }
                    
                    document.body.appendChild(form);
                    form.submit();
                }
            }
            
            function dropSubject() {
                if (selectedStudentId && selectedEnrolledSubjectId) {
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
                    if (currentSubjid) {
                        let urlSubjId = document.createElement('input');
                        urlSubjId.type = 'hidden';
                        urlSubjId.name = 'subjid';
                        urlSubjId.value = currentSubjid;
                        form.appendChild(urlSubjId);
                    }
                    
                    document.body.appendChild(form);
                    form.submit();
                }
            }
            
            window.onload = function() {
                const urlParams = new URLSearchParams(window.location.search);
                const studid = urlParams.get('studid');
                const subjid = urlParams.get('subjid');
                
                if (studid) {
                    selectedStudentId = studid;
                    let rows = document.querySelectorAll('#studentsTable tr');
                    for (let row of rows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === studid) {
                            row.classList.add('selected-row');
                            break;
                        }
                    }
                }
                
                if (subjid && studid) {
                    let subjectRows = document.querySelectorAll('#enrolledSubjectsTable tr');
                    for (let row of subjectRows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === subjid) {
                            row.classList.add('selected-row');
                            selectedEnrolledSubjectId = subjid;
                            
                            let dropButton = document.getElementById('dropButton');
                            if (dropButton) {
                                dropButton.style.display = 'block';
                                dropButton.innerHTML = 'Drop Student ID: ' + selectedStudentId + ' from Subject ID: ' + selectedEnrolledSubjectId;
                                dropButton.disabled = false;
                            }
                            break;
                        }
                    }
                }
            };
        </script>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Genshin_Impact_logo.svg/2560px-Genshin_Impact_logo.svg.png" 
                     alt="Genshin Impact Logo" class="logo">
                <div class="university-info">
                    <div class="university-name">Sumeru Akademiya</div>
                    <div class="subtitle">Student Enrollment Management System</div>
                </div>
            </div>
            <a href="subjects.py""" + (f"?subjid={url_subjid}" if url_subjid else "") + """" class="nav-link">Go to Subjects</a>
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

    print("""
            <div class="two-column-layout">
                <div>
                    <div class="form-container">
                        <h2>Student Form</h2>
                        <form method="POST" action="students.py" id="studentForm">
    """)

    if url_subjid:
        print(f"<input type='hidden' name='subjid' value='{url_subjid}'>")

    print("""
                            <table style="width: 100%;">
                                <tr>
                                    <td>Student ID:</td>
                                    <td><input type="text" name="studid" id="studid" style="width: 100px" readonly value=""" + f"'{prefill_data.get('studid', '')}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Name:</td>
                                    <td><input type="text" name="studname" id="studname" style="width: 200px" value=""" + f"'{html.escape(prefill_data.get('studname', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Address:</td>
                                    <td><input type="text" name="studadd" id="studadd" style="width: 200px" value=""" + f"'{html.escape(prefill_data.get('studadd', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Gender:</td>
                                    <td><input type="text" name="studgender" id="studgender" style="width: 100px" value=""" + f"'{html.escape(prefill_data.get('studgender', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Course:</td>
                                    <td><input type="text" name="studcrs" id="studcrs" style="width: 150px" value=""" + f"'{html.escape(prefill_data.get('studcrs', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Year Level:</td>
                                    <td><input type="text" name="yrlvl" id="yrlvl" style="width: 100px" value=""" + f"'{html.escape(prefill_data.get('yrlvl', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td colspan="2" style="text-align: center; padding-top: 20px;">
                                        <button type="button" onclick="submitForm('insert')" style="width: 80px; margin: 0 5px;">Insert</button>
                                        <button type="button" onclick="submitForm('update')" style="width: 80px; margin: 0 5px;">Update</button>
                                        <button type="button" onclick="submitForm('delete')" style="width: 80px; margin: 0 5px;">Delete</button>
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
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center;">
                    <button type="button" onclick="enrollStudent('{url_subjid}')" class="enroll-green-button">
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
                        <h2>Students Table for: enrollmentsystem</h2>
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
        print("<tr onclick='selectStudent(" + str(student[0]) + ", \"" + 
               html.escape(str(student[1])) + "\", \"" + 
               html.escape(str(student[2])) + "\", \"" + 
               html.escape(str(student[4])) + "\", \"" + 
               html.escape(str(student[3])) + "\", \"" + 
               html.escape(str(student[5])) + "\")'>")
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

    print("""
                            </tbody>
                        </table>
                        <div style="margin-top: 20px; text-align: center;">
                            <button id="dropButton" type="button" onclick="dropSubject()" class="drop-button" style="width: 100%; padding: 12px; display: none;" disabled>
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
