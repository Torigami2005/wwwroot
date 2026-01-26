#!/usr/bin/env python3
import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()

# Get form values
action_type = form.getvalue("action_type", "")  # insert, update, delete
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

# Variable to store conflict message
conflict_message = ""

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    cursor = conn.cursor()

    # Handle student actions (Insert, Update, Delete)
    if action_type == "insert" and studname:
        try:
            # Get the maximum studid and calculate the next one starting from 1000
            cursor.execute("SELECT MAX(studid) FROM students")
            result = cursor.fetchone()
            max_studid = result[0]
            
            # If no students exist yet, start from 1000
            if max_studid is None:
                next_studid = 1000
            else:
                # Find the next available ID starting from max(current_max + 1, 1000)
                next_studid = max(max_studid + 1, 1000)
            
            insert_sql = """
                INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (next_studid, studname, studadd, studcrs, studgender, yrlvl))
            conn.commit()
            # Redirect to show the new student in URL
            print(f"<script>window.location.href='students.py?studid={next_studid}';</script>")
        except Exception as e:
            print(f"<!-- Insert error: {e} -->")
            pass
    
    elif action_type == "update" and studid and studname:
        try:
            update_sql = """
                UPDATE students 
                SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s 
                WHERE studid=%s
            """
            cursor.execute(update_sql, (studname, studadd, studcrs, studgender, yrlvl, studid))
            conn.commit()
            # Redirect to show updated student in URL
            print(f"<script>window.location.href='students.py?studid={studid}';</script>")
        except Exception as e:
            print(f"<!-- Update error: {e} -->")
    
    elif action_type == "delete" and studid:
        try:
            # Get all enrollments for this student
            cursor.execute("SELECT eid FROM enroll WHERE studid=%s", (studid,))
            enrollments = cursor.fetchall()
            
            # Delete from grades for each enrollment
            for enrollment in enrollments:
                eid = enrollment[0]
                delete_grade = "DELETE FROM grades WHERE enroll_eid = %s"
                cursor.execute(delete_grade, (eid,))
            
            # Delete from enroll
            delete_enrollments = "DELETE FROM enroll WHERE studid=%s"
            cursor.execute(delete_enrollments, (studid,))
            
            # Finally delete the student
            delete_sql = "DELETE FROM students WHERE studid=%s"
            cursor.execute(delete_sql, (studid,))
            
            conn.commit()
            # Redirect to main page
            print("<script>window.location.href='students.py';</script>")
        except Exception as e:
            print(f"<!-- Delete error: {e} -->")
            # Still redirect even if there's an error
            print("<script>window.location.href='students.py';</script>")

    # Handle subject enrollment actions
    if subject_action == "enroll" and selected_studid and selected_subjid:
        try:
            # Check for schedule conflicts BEFORE enrolling
            cursor.callproc('conflictsched', [selected_studid, selected_subjid, ''])
            
            # Get the result from the stored procedure
            for result in cursor.stored_results():
                conflict_result = result.fetchone()[0]
            
            if conflict_result != 'No conflict':
                # There's a conflict, don't enroll
                conflict_message = f"""<div style='background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #f5c6cb;'>
                    <strong>Schedule Conflict Detected!</strong><br>
                    {conflict_result}
                </div>"""
            else:
                # No conflict, proceed with enrollment
                # Check if already enrolled
                check_sql = "SELECT COUNT(*) FROM enroll WHERE studid = %s AND subjid = %s"
                cursor.execute(check_sql, (selected_studid, selected_subjid))
                count = cursor.fetchone()[0]
                
                if count == 0:
                    insert_enroll = "INSERT INTO enroll (studid, subjid) VALUES (%s, %s)"
                    cursor.execute(insert_enroll, (selected_studid, selected_subjid))
                    conn.commit()
                    
                    # Also insert into grades table
                    get_eid = "SELECT eid FROM enroll WHERE studid = %s AND subjid = %s"
                    cursor.execute(get_eid, (selected_studid, selected_subjid))
                    result = cursor.fetchone()
                    if result:
                        eid = result[0]
                        insert_grade = "INSERT INTO grades (enroll_eid) VALUES (%s)"
                        cursor.execute(insert_grade, (eid,))
                        conn.commit()
                
                # Get the URL parameters to preserve
                url_subjid = form.getvalue("subjid", "")
                redirect_url = f'students.py?studid={selected_studid}&subjid={selected_subjid}'
                if url_subjid and url_subjid != selected_subjid:
                    redirect_url = f'students.py?studid={selected_studid}&subjid={url_subjid}'
                
                print(f"<script>window.location.href='{redirect_url}';</script>")
                exit()
                
        except Exception as e:
            print(f"<!-- Enroll error: {e} -->")
            # Still redirect
            print(f"<script>window.location.href='students.py?studid={selected_studid}';</script>")
    
    elif subject_action == "drop" and selected_studid and selected_subjid:
        try:
            # Get the eid first
            get_eid = "SELECT eid FROM enroll WHERE studid = %s AND subjid = %s"
            cursor.execute(get_eid, (selected_studid, selected_subjid))
            result = cursor.fetchone()
            if result:
                eid = result[0]
                # Delete from grades first (due to foreign key constraint)
                delete_grade = "DELETE FROM grades WHERE enroll_eid = %s"
                cursor.execute(delete_grade, (eid,))
                # Then delete from enroll
                delete_enroll = "DELETE FROM enroll WHERE eid = %s"
                cursor.execute(delete_enroll, (eid,))
                conn.commit()
        except Exception as e:
            print(f"<!-- Drop error: {e} -->")
        
        # Get the URL parameters to preserve
        url_subjid = form.getvalue("subjid", "")
        redirect_url = f'students.py?studid={selected_studid}'
        if url_subjid:
            redirect_url = f'students.py?studid={selected_studid}&subjid={url_subjid}'
        
        print(f"<script>window.location.href='{redirect_url}';</script>")

    # Get all students with total units calculation
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

    # Get all subjects for the enrollment buttons
    cursor.execute("SELECT subjid FROM subjects ORDER BY subjid")
    all_subjects = cursor.fetchall()
    subject_ids = [subject[0] for subject in all_subjects]

    # Get enrollment data if a student is selected (from URL parameter)
    enrolled_subjects = []
    enrolled_subject_ids = []  # List of subject IDs the student is already enrolled in
    total_units_enrolled = 0
    
    # Get URL parameters
    url_studid = form.getvalue("studid", "")
    url_subjid = form.getvalue("subjid", "")  # Get subjid from URL
    
    if url_studid:
        selected_studid = url_studid  # Override with URL parameter
        cursor.execute("""
            SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
            FROM enroll e 
            JOIN subjects s ON e.subjid = s.subjid 
            WHERE e.studid = %s
            ORDER BY s.subjid
        """, (selected_studid,))
        enrolled_subjects = cursor.fetchall()
        
        # Get list of enrolled subject IDs
        enrolled_subject_ids = [subject[0] for subject in enrolled_subjects]
        
        # Calculate total units for enrolled subjects
        for subject in enrolled_subjects:
            total_units_enrolled += subject[3] if subject[3] else 0

    # Pre-fill form if student ID is in URL
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
            @import url('https://fonts.cdnfonts.com/css/hywenhei');
            
            body {
                font-family: 'HYWenHei', sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            
            /* Blue Header - Top Left Alignment */
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
                font-family: 'HYWenHei', sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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
                display: none;
            }
            
            .drop-button:hover {
                background: linear-gradient(135deg, #c82333 0%, #bd2130 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(220, 53, 69, 0.2);
            }
            
            input, select {
                font-family: 'HYWenHei', sans-serif;
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
            
            /* Table Styles */
            table {
                font-family: 'HYWenHei', sans-serif;
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
                
                .header {
                    flex-direction: column;
                    align-items: flex-start;
                    padding: 15px 20px;
                }
                
                .header-left {
                    margin-bottom: 15px;
                }
                
                .logo {
                    height: 60px;
                    width: 60px;
                    margin-right: 15px;
                }
                
                .university-name {
                    font-size: 24px;
                }
                
                .enroll-green-button {
                    min-width: 250px;
                }
            }
        </style>
        <script>
            let selectedStudentId = null;
            let selectedStudentData = null;
            let selectedEnrolledSubjectId = null;
            
            function selectStudent(studid, studname, studadd, studcrs, studgender, yrlvl) {
                selectedStudentId = studid;
                selectedStudentData = {
                    name: studname,
                    address: studadd,
                    course: studcrs,
                    gender: studgender,
                    yrlvl: yrlvl
                };
                selectedEnrolledSubjectId = null;
                
                // Fill the form with student data WITHOUT refreshing
                document.getElementById('studid').value = studid;
                document.getElementById('studname').value = studname;
                document.getElementById('studadd').value = studadd;
                document.getElementById('studcrs').value = studcrs;
                document.getElementById('studgender').value = studgender;
                document.getElementById('yrlvl').value = yrlvl;
                
                // Get current subjid from URL if it exists
                const urlParams = new URLSearchParams(window.location.search);
                const currentSubjid = urlParams.get('subjid');
                
                // Reload page to show enrolled subjects
                let newUrl = 'students.py?studid=' + studid;
                if (currentSubjid) {
                    newUrl += '&subjid=' + currentSubjid;
                }
                window.location.href = newUrl;
            }
            
            function selectEnrolledSubject(subjid, subjcode) {
                selectedEnrolledSubjectId = subjid;
                
                // Remove previous selection
                let rows = document.querySelectorAll('#enrolledSubjectsTable tr');
                rows.forEach(row => row.classList.remove('selected-row'));
                
                // Highlight selected row
                let rowsArray = Array.from(rows);
                for (let row of rowsArray) {
                    let firstCell = row.querySelector('td:first-child');
                    if (firstCell && firstCell.textContent === subjid) {
                        row.classList.add('selected-row');
                        break;
                    }
                }
                
                // Show drop button ONLY if a subject is clicked
                let dropButton = document.getElementById('dropButton');
                if (dropButton && selectedStudentId && selectedEnrolledSubjectId) {
                    dropButton.style.display = 'block';
                    dropButton.innerHTML = 'Drop Student ID: <span id="dropStudId">' + selectedStudentId + '</span> from Subject ID: <span id="dropSubjId">' + selectedEnrolledSubjectId + '</span>';
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
                    
                    // Also include the studid in URL parameter
                    let urlStudId = document.createElement('input');
                    urlStudId.type = 'hidden';
                    urlStudId.name = 'studid';
                    urlStudId.value = studid;
                    form.appendChild(urlStudId);
                    
                    // Include subjid in URL parameter if it exists
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
                    // No confirmation dialog - directly drop the subject
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
                    
                    // Also include the studid in URL parameter
                    let urlStudId = document.createElement('input');
                    urlStudId.type = 'hidden';
                    urlStudId.name = 'studid';
                    urlStudId.value = selectedStudentId;
                    form.appendChild(urlStudId);
                    
                    // Include subjid in URL parameter if it exists
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
            
            // Initialize selectedStudentId from URL on page load
            window.onload = function() {
                const urlParams = new URLSearchParams(window.location.search);
                const studid = urlParams.get('studid');
                const subjid = urlParams.get('subjid');
                
                if (studid) {
                    selectedStudentId = studid;
                    // Highlight the selected student row
                    let rows = document.querySelectorAll('#studentsTable tr');
                    for (let row of rows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === studid) {
                            row.classList.add('selected-row');
                            break;
                        }
                    }
                }
                
                // If there's a subjid in URL (from subjects.py), highlight it in enrolled subjects
                if (subjid && studid) {
                    // Highlight the specific subject row if it exists in enrolled subjects
                    let subjectRows = document.querySelectorAll('#enrolledSubjectsTable tr');
                    for (let row of subjectRows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === subjid) {
                            row.classList.add('selected-row');
                            selectedEnrolledSubjectId = subjid;
                            
                            // Show drop button for this subject
                            let dropButton = document.getElementById('dropButton');
                            if (dropButton) {
                                dropButton.style.display = 'block';
                                dropButton.innerHTML = 'Drop Student ID: <span id="dropStudId">' + selectedStudentId + '</span> from Subject ID: <span id="dropSubjId">' + selectedEnrolledSubjectId + '</span>';
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
        <!-- Blue Header with Universitas Magistorium and Genshin Impact Image - Top Left -->
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

    # Display conflict message if there is one
    if conflict_message:
        print(conflict_message)

    print("""
            <div class="two-column-layout">
                <!-- Left column: Student Form -->
                <div>
                    <div class="form-container">
                        <h2>Student Form</h2>
                        <form method="POST" action="students.py" id="studentForm">
    """)

    # Add hidden field for subjid if it exists in URL
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
                    
                    <!-- Enroll Section (below student form) - ONLY SHOW WHEN SUBJECT ID IS FROM subjects.py -->
                    <div class="enroll-section">
                        <h3>Enroll Student to Subject</h3>
    """)

    # ONLY show enroll buttons if we have a subject ID from subjects.py
    if url_subjid:
        # We have a specific subject ID from subjects.py
        if url_studid and prefill_data.get('studid'):
            studid = prefill_data.get('studid')
            
            # Check if student is already enrolled in this specific subject
            is_already_enrolled = int(url_subjid) in enrolled_subject_ids
            
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                        <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Enroll Student to Subject:</p>
                    </div>""")
            
            print("""<div class="enroll-buttons-container" style="justify-content: center;">""")
            
            if not is_already_enrolled:
                # Show single button for the specific subject ID
                print(f"""<button type="button" onclick="enrollStudent('{url_subjid}')" class="enroll-green-button">
                            Enroll Student ID: {studid} to Subject ID: {url_subjid}
                        </button>""")
            else:
                print(f"""<p style="text-align: center; color: #28a745; padding: 10px; background-color: #f8f9fa; border-radius: 5px; width: 100%;">
                            Student ID: {studid} is already enrolled in Subject ID: {url_subjid}
                        </p>""")
            
            print("</div>")
        
        elif not url_studid:
            # Have subject ID but no student selected yet
            print(f"""<div style="text-align: center; margin-bottom: 15px;">
                        <p style="font-weight: bold; color: #1e3c72; margin-bottom: 15px;">Enroll Student to Subject:</p>
                    </div>""")
            
            print("""<div class="enroll-buttons-container" style="justify-content: center;">""")
            print(f"""<p style="text-align: center; color: #666; padding: 20px; width: 100%;">
                        Select a student from the table to enroll in Subject ID: {url_subjid}
                    </p>""")
            print("</div>")
    
    else:
        # NO subject ID from subjects.py - DO NOT SHOW ENROLLMENT BUTTONS
        print("""<div style="text-align: center; padding: 20px;">
                    <p style="color: #666;">
                        To enroll students in subjects, go to Subjects page and select a subject first
                    </p>
                </div>""")

    print("""
                    </div>
                </div>
                
                <!-- Right column: Students Table and Enrolled Subjects -->
                <div>
                    <!-- Students Table -->
                    <div class="form-container">
                        <h2>Students Table</h2>
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
                    
                    <!-- Enrolled Subjects Table -->
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

finally:
    if 'conn' in locals():
        conn.close()
