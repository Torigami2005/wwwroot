#!/usr/bin/env python3
import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()

# Get form values
action_type = form.getvalue("action_type", "")
tid = form.getvalue("tid", "")
tname = html.escape(form.getvalue("tname", ""))
tdept = html.escape(form.getvalue("tdept", ""))
tadd = html.escape(form.getvalue("tadd", ""))
tcontact = html.escape(form.getvalue("tcontact", ""))
tstatus = html.escape(form.getvalue("tstatus", ""))

# For subject assignment
selected_tid = form.getvalue("selected_tid", "")
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

    # Handle teacher actions
    if action_type == "insert" and tname:
        try:
            cursor.execute("SELECT MAX(tid) FROM teachers")
            result = cursor.fetchone()
            max_tid = result[0]
            
            if max_tid is None:
                next_tid = 3000
            else:
                next_tid = max(max_tid + 1, 3000)
            
            cursor.execute("INSERT INTO teachers (tid, tname, tdept, tadd, tcontact, tstatus) VALUES (%s, %s, %s, %s, %s, %s)", 
                          (next_tid, tname, tdept, tadd, tcontact, tstatus))
            conn.commit()
            print(f"<script>window.location.href='teachers.py?tid={next_tid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='teachers.py';</script>")
    
    elif action_type == "update" and tid and tname:
        try:
            cursor.execute("UPDATE teachers SET tname=%s, tdept=%s, tadd=%s, tcontact=%s, tstatus=%s WHERE tid=%s", 
                          (tname, tdept, tadd, tcontact, tstatus, tid))
            conn.commit()
            print(f"<script>window.location.href='teachers.py?tid={tid}';</script>")
        except Exception as e:
            print(f"<script>window.location.href='teachers.py?tid={tid}';</script>")
    
    elif action_type == "delete" and tid:
        try:
            # First check if teacher has any assigned subjects
            cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE tid=%s", (tid,))
            assigned_count = cursor.fetchone()[0]
            
            if assigned_count > 0:
                # Delete from teacher_subjects first
                cursor.execute("DELETE FROM teacher_subjects WHERE tid=%s", (tid,))
            
            # Then delete teacher
            cursor.execute("DELETE FROM teachers WHERE tid=%s", (tid,))
            conn.commit()
            print("<script>window.location.href='teachers.py';</script>")
        except Exception as e:
            print("<script>window.location.href='teachers.py';</script>")

    # Handle subject assignment
    if subject_action == "assign" and selected_tid and selected_subjid:
        try:
            # Check if teacher exists
            cursor.execute("SELECT COUNT(*) FROM teachers WHERE tid = %s", (selected_tid,))
            teacher_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM subjects WHERE subjid = %s", (selected_subjid,))
            subject_count = cursor.fetchone()[0]
            
            if teacher_count == 0 or subject_count == 0:
                error_msg = "Teacher or Subject not found"
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                exit()
            
            # Check if subject already assigned to another teacher
            cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE subjid = %s", (selected_subjid,))
            already_assigned = cursor.fetchone()[0]
            
            if already_assigned > 0:
                error_msg = "Subject already assigned to another teacher"
                redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
                print(f"<script>window.location.href='{redirect_url}';</script>")
                conn.close()
                exit()
            
            # Check for schedule conflicts
            cursor.execute("SELECT subjsched FROM subjects WHERE subjid = %s", (selected_subjid,))
            new_subject = cursor.fetchone()
            new_sched = new_subject[0] if new_subject else ""
            
            if new_sched and new_sched.strip():
                # Get assigned subjects for the teacher
                cursor.execute("""
                    SELECT s.subjsched 
                    FROM subjects s
                    INNER JOIN teacher_subjects ts ON s.subjid = ts.subjid 
                    WHERE ts.tid = %s AND s.subjsched IS NOT NULL AND s.subjsched != ''
                """, (selected_tid,))
                assigned_schedules = cursor.fetchall()
                
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
                            
                            # Check each assigned subject
                            for assigned in assigned_schedules:
                                old_sched = assigned[0].strip() if assigned[0] else ""
                                
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
                                                    conflict_msg = f"Schedule conflict with {old_sched}"
                                                    redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(conflict_msg)}'
                                                    print(f"<script>window.location.href='{redirect_url}';</script>")
                                                    conn.close()
                                                    exit()
            
            # Assign subject to teacher
            cursor.execute("INSERT INTO teacher_subjects (tid, subjid) VALUES (%s, %s)", (selected_tid, selected_subjid))
            conn.commit()
            
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&success=Subject assigned successfully'
            print(f"<script>window.location.href='{redirect_url}';</script>")
        except Exception as e:
            error_msg = f"Assignment failed: {str(e)}"
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")
    
    elif subject_action == "unassign" and selected_tid and selected_subjid:
        try:
            cursor.execute("DELETE FROM teacher_subjects WHERE tid = %s AND subjid = %s", (selected_tid, selected_subjid))
            conn.commit()
            
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&success=Subject unassigned successfully'
            print(f"<script>window.location.href='{redirect_url}';</script>")
        except Exception as e:
            error_msg = f"Unassignment failed: {str(e)}"
            redirect_url = f'teachers.py?tid={selected_tid}&subjid={selected_subjid}&error={html.escape(error_msg)}'
            print(f"<script>window.location.href='{redirect_url}';</script>")

    # Get all teachers with subject count and total units
    cursor.execute("""
        SELECT t.tid, t.tname, t.tdept, t.tcontact, t.tstatus, 
               COUNT(ts.subjid) as subject_count,
               COALESCE(SUM(s.subjunits), 0) as total_units
        FROM teachers t
        LEFT JOIN teacher_subjects ts ON t.tid = ts.tid
        LEFT JOIN subjects s ON ts.subjid = s.subjid
        GROUP BY t.tid, t.tname, t.tdept, t.tcontact, t.tstatus
        ORDER BY t.tid
    """)
    teachers = cursor.fetchall()

    # Get URL parameters
    url_tid = form.getvalue("tid", "")
    url_subjid = form.getvalue("subjid", "")
    error_msg = form.getvalue("error", "")
    success_msg = form.getvalue("success", "")
    
    # Check for schedule conflicts - for display
    conflict_detected = False
    conflict_message = ""
    
    if url_tid and url_subjid:
        # Check if subject already assigned to this teacher
        cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE tid = %s AND subjid = %s", (url_tid, url_subjid))
        already_assigned = cursor.fetchone()[0] > 0
        
        # Check if subject assigned to another teacher
        cursor.execute("SELECT COUNT(*) FROM teacher_subjects WHERE subjid = %s AND tid != %s", (url_subjid, url_tid))
        assigned_to_other = cursor.fetchone()[0] > 0
        
        if assigned_to_other:
            conflict_detected = True
            conflict_message = "Subject already assigned to another teacher"
        elif not already_assigned:
            # Check for schedule conflicts
            cursor.execute("SELECT subjsched FROM subjects WHERE subjid = %s", (url_subjid,))
            new_subject = cursor.fetchone()
            new_sched = new_subject[0] if new_subject else ""
            
            if new_sched and new_sched.strip():
                # Get assigned subjects for the teacher
                cursor.execute("""
                    SELECT s.subjsched 
                    FROM subjects s
                    INNER JOIN teacher_subjects ts ON s.subjid = ts.subjid 
                    WHERE ts.tid = %s AND s.subjsched IS NOT NULL AND s.subjsched != ''
                """, (url_tid,))
                assigned_schedules = cursor.fetchall()
                
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
                            
                            # Check each assigned subject
                            for assigned in assigned_schedules:
                                old_sched = assigned[0].strip() if assigned[0] else ""
                                
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
                                                    conflict_message = f"Schedule conflict with {old_sched}"
                                                    break
        
        # Get assigned subjects for this teacher
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
            FROM teacher_subjects ts 
            JOIN subjects s ON ts.subjid = s.subjid 
            WHERE ts.tid = %s
            ORDER BY s.subjid
        """, (url_tid,))
        assigned_subjects = cursor.fetchall()
        assigned_subject_ids = [subject[0] for subject in assigned_subjects]
    elif url_tid:
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
            FROM teacher_subjects ts 
            JOIN subjects s ON ts.subjid = s.subjid 
            WHERE ts.tid = %s
            ORDER BY s.subjid
        """, (url_tid,))
        assigned_subjects = cursor.fetchall()
        assigned_subject_ids = [subject[0] for subject in assigned_subjects]
    else:
        assigned_subjects = []
        assigned_subject_ids = []

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

    print("""
    <html>
    <head>
        <title>Sumeru Akademiya - Teacher Management System</title>
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
            let selectedTeacherId = null;
            let selectedAssignedSubjectId = null;
            
            function selectTeacher(tid, tname, tdept, tadd, tcontact, tstatus) {
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
                if (currentSubjid) {
                    newUrl += '&subjid=' + currentSubjid;
                }
                window.location.href = newUrl;
            }
            
            function selectAssignedSubject(subjid, subjcode) {
                selectedAssignedSubjectId = subjid;
                
                let rows = document.querySelectorAll('#assignedSubjectsTable tr');
                rows.forEach(row => row.classList.remove('selected-row'));
                
                let rowsArray = Array.from(rows);
                for (let row of rowsArray) {
                    let firstCell = row.querySelector('td:first-child');
                    if (firstCell && firstCell.textContent === subjid) {
                        row.classList.add('selected-row');
                        break;
                    }
                }
                
                let unassignButton = document.getElementById('unassignButton');
                if (unassignButton && selectedTeacherId && selectedAssignedSubjectId) {
                    unassignButton.style.display = 'block';
                    unassignButton.innerHTML = 'Unassign Teacher ID: ' + selectedTeacherId + ' from Subject ID: ' + selectedAssignedSubjectId;
                    unassignButton.disabled = false;
                }
            }
            
            function submitForm(action) {
                let form = document.getElementById('teacherForm');
                let actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'action_type';
                actionInput.value = action;
                form.appendChild(actionInput);
                form.submit();
            }
            
            function assignSubject(subjid) {
                let tid = document.getElementById('tid').value;
                
                if (tid && subjid) {
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
                    actionInput.name = 'subject_action';
                    actionInput.value = 'assign';
                    form.appendChild(actionInput);
                    
                    let urlTid = document.createElement('input');
                    urlTid.type = 'hidden';
                    urlTid.name = 'tid';
                    urlTid.value = tid;
                    form.appendChild(urlTid);
                    
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
            
            function unassignSubject() {
                if (selectedTeacherId && selectedAssignedSubjectId) {
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
                    actionInput.name = 'subject_action';
                    actionInput.value = 'unassign';
                    form.appendChild(actionInput);
                    
                    let urlTid = document.createElement('input');
                    urlTid.type = 'hidden';
                    urlTid.name = 'tid';
                    urlTid.value = selectedTeacherId;
                    form.appendChild(urlTid);
                    
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
                const tid = urlParams.get('tid');
                const subjid = urlParams.get('subjid');
                
                if (tid) {
                    selectedTeacherId = tid;
                    let rows = document.querySelectorAll('#teachersTable tr');
                    for (let row of rows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === tid) {
                            row.classList.add('selected-row');
                            break;
                        }
                    }
                }
                
                if (subjid && tid) {
                    let subjectRows = document.querySelectorAll('#assignedSubjectsTable tr');
                    for (let row of subjectRows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === subjid) {
                            row.classList.add('selected-row');
                            selectedAssignedSubjectId = subjid;
                            
                            let unassignButton = document.getElementById('unassignButton');
                            if (unassignButton) {
                                unassignButton.style.display = 'block';
                                unassignButton.innerHTML = 'Unassign Teacher ID: ' + selectedTeacherId + ' from Subject ID: ' + selectedAssignedSubjectId;
                                unassignButton.disabled = false;
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
                    <div class="subtitle">Teacher Management System</div>
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
                        <h2>Teacher Form</h2>
                        <form method="POST" action="teachers.py" id="teacherForm">
    """)

    if url_subjid:
        print(f"<input type='hidden' name='subjid' value='{url_subjid}'>")

    print("""
                            <table style="width: 100%;">
                                <tr>
                                    <td>Teacher ID:</td>
                                    <td><input type="text" name="tid" id="tid" style="width: 100px" readonly value=""" + f"'{prefill_data.get('tid', '')}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Name:</td>
                                    <td><input type="text" name="tname" id="tname" style="width: 200px" value=""" + f"'{html.escape(prefill_data.get('tname', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Department:</td>
                                    <td><input type="text" name="tdept" id="tdept" style="width: 200px" value=""" + f"'{html.escape(prefill_data.get('tdept', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Address:</td>
                                    <td><input type="text" name="tadd" id="tadd" style="width: 200px" value=""" + f"'{html.escape(prefill_data.get('tadd', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Contact:</td>
                                    <td><input type="text" name="tcontact" id="tcontact" style="width: 150px" value=""" + f"'{html.escape(prefill_data.get('tcontact', ''))}'" + """></td>
                                </tr>
                                <tr>
                                    <td>Status:</td>
                                    <td><input type="text" name="tstatus" id="tstatus" style="width: 100px" value=""" + f"'{html.escape(prefill_data.get('tstatus', ''))}'" + """></td>
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
                        <h3>Assign Subject to Teacher</h3>
    """)

    if url_subjid:
        if url_tid and prefill_data.get('tid'):
            teacher_id = prefill_data.get('tid')
            
            try:
                is_already_assigned = int(url_subjid) in assigned_subject_ids
            except:
                is_already_assigned = False
            
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                        <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Assign Subject to Teacher:</p>
                    </div>""")
            
            if conflict_detected:
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                    <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                        <div style="text-align: center; color: #dc3545; font-weight: bold;">
                            {conflict_message}
                        </div>
                     </div>
                    <button type="button" onclick="assignSubject('{url_subjid}')" class="enroll-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                        Assign Teacher ID: {teacher_id} to Subject ID: {url_subjid}
                    </button>
                    </div>
                    """)
            elif is_already_assigned:
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center; flex-direction: column; align-items: center;">
                    <div class="warning-message" style="width: 100%; max-width: 400px; margin-bottom: 15px;">
                        Teacher ID: {teacher_id} already assigned to Subject ID: {url_subjid}
                    </div>
                    <button type="button" onclick="assignSubject('{url_subjid}')" class="enroll-green-button" disabled style="opacity: 0.6; cursor: not-allowed;">
                        Assign Teacher ID: {teacher_id} to Subject ID: {url_subjid}
                    </button>
                </div>
                """)
            else:
                print(f"""
                <div class="enroll-buttons-container" style="justify-content: center;">
                    <button type="button" onclick="assignSubject('{url_subjid}')" class="enroll-green-button">
                        Assign Teacher ID: {teacher_id} to Subject ID: {url_subjid}
                    </button>
                </div>
                """)
        
        elif not url_tid:
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                        <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Assign Subject to Teacher:</p>
                    </div>""")
            
            print("""<div class="enroll-buttons-container" style="justify-content: center;">""")
            print(f"""<p style="text-align: center; color: #666; padding: 20px; width: 100%;">
                        Select a teacher from the table to assign Subject ID: {url_subjid}
                    </p>""")
            print("</div>")
    
    else:
        print("""<div style="text-align: center; padding: 20px;">
                    <p style="color: #666;">
                        To assign subjects to teachers, go to Subjects page and select a subject first
                    </p>
                </div>""")

    print("""
                    </div>
                </div>
                
                <div>
                    <div class="form-container">
                        <h2>Teachers Table for: enrollmentsystem</h2>
                        <table border="1" id="teachersTable">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Name</th>
                                    <th>Department</th>
                                    <th>Contact</th>
                                    <th>Status</th>
                                    <th>#Subj</th>
                                    <th>TotUnits</th>
                                </tr>
                            </thead>
                            <tbody>
    """)

    for teacher in teachers:
        print("<tr onclick='selectTeacher(" + str(teacher[0]) + ", \"" + 
               html.escape(str(teacher[1])) + "\", \"" + 
               html.escape(str(teacher[2])) + "\", \"" + 
               "\", \"" +  # tadd (not in query)
               html.escape(str(teacher[3])) + "\", \"" + 
               html.escape(str(teacher[4])) + "\")'>")
        print("<td>" + str(teacher[0]) + "</td>")
        print("<td>" + html.escape(str(teacher[1])) + "</td>")
        print("<td>" + html.escape(str(teacher[2])) + "</td>")
        print("<td>" + html.escape(str(teacher[3])) + "</td>")
        print("<td>" + html.escape(str(teacher[4])) + "</td>")
        print("<td>" + str(teacher[5]) + "</td>")
        print("<td>" + str(teacher[6]) + "</td>")
        print("</tr>")

    print("""
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="form-container" style="margin-top: 30px;">
                        <h2>Assigned Subjects</h2>
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

    print("""
                            </tbody>
                        </table>
                        <div style="margin-top: 20px; text-align: center;">
                            <button id="unassignButton" type="button" onclick="unassignSubject()" class="drop-button" style="width: 100%; padding: 12px; display: none;" disabled>
                                Unassign Subject
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
