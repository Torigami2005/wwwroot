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

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    cursor = conn.cursor()

    # First, let's modify the tables to have auto-increment IDs
    try:
        # Modify students table to auto-increment studid starting from 1000
        cursor.execute("ALTER TABLE students MODIFY studid INT NOT NULL AUTO_INCREMENT")
        cursor.execute("ALTER TABLE students AUTO_INCREMENT = 1000")
        
        # Modify subjects table to auto-increment subjid starting from 2000
        cursor.execute("ALTER TABLE subjects MODIFY subjid INT NOT NULL AUTO_INCREMENT")
        cursor.execute("ALTER TABLE subjects AUTO_INCREMENT = 2000")
        
        conn.commit()
    except:
        pass  # Tables might already be modified

    # Handle student actions (Insert, Update, Delete)
    if action_type == "insert" and studname:
        try:
            insert_sql = """
                INSERT INTO students (studname, studadd, studcrs, studgender, yrlvl) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (studname, studadd, studcrs, studgender, yrlvl))
            conn.commit()
            # Redirect to show the new student in URL
            new_studid = cursor.lastrowid
            print(f"<script>window.location.href='students.py?studid={new_studid}';</script>")
        except:
            pass
    
    elif action_type == "update" and studid and studname:
        update_sql = """
            UPDATE students 
            SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s 
            WHERE studid=%s
        """
        cursor.execute(update_sql, (studname, studadd, studcrs, studgender, yrlvl, studid))
        conn.commit()
        # Redirect to show updated student in URL
        print(f"<script>window.location.href='students.py?studid={studid}';</script>")
    
    elif action_type == "delete" and studid:
        delete_sql = "DELETE FROM students WHERE studid=%s"
        cursor.execute(delete_sql, (studid,))
        conn.commit()
        # Also delete related enrollments and grades
        delete_enrollments = "DELETE FROM enroll WHERE studid=%s"
        cursor.execute(delete_enrollments, (studid,))
        conn.commit()
        # Redirect to main page
        print("<script>window.location.href='students.py';</script>")

    # Handle subject enrollment actions
    if subject_action == "enroll" and selected_studid and selected_subjid:
        try:
            insert_enroll = "INSERT INTO enroll (studid, subjid) VALUES (%s, %s)"
            cursor.execute(insert_enroll, (selected_studid, selected_subjid))
            conn.commit()
            
            # Also insert into grades table
            get_eid = "SELECT eid FROM enroll WHERE studid = %s AND subjid = %s"
            cursor.execute(get_eid, (selected_studid, selected_subjid))
            eid = cursor.fetchone()[0]
            
            insert_grade = "INSERT INTO grades (enroll_eid) VALUES (%s)"
            cursor.execute(insert_grade, (eid,))
            conn.commit()
        except:
            pass  # Already enrolled
    
    elif subject_action == "drop" and selected_studid and selected_subjid:
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
        # Redirect to show student in URL
        print(f"<script>window.location.href='students.py?studid={selected_studid}';</script>")

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

    # Get all subjects for the dropdown
    cursor.execute("SELECT subjid, subjcode FROM subjects ORDER BY subjid")
    all_subjects = cursor.fetchall()

    # Get enrollment data if a student is selected (from URL parameter)
    enrolled_subjects = []
    total_units_enrolled = 0
    # Use URL parameter studid if available, otherwise use form parameter
    url_studid = form.getvalue("studid", "")
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
        <title>Student Enrollment System</title>
        <script>
            let selectedStudentId = null;
            let selectedStudentData = null;
            let selectedEnrolledSubjectId = null;
            let selectedSubjectId = null;
            
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
                
                // Hide drop button
                document.getElementById('dropButton').style.display = 'none';
                
                // Update URL to show selected student
                window.history.pushState({}, '', 'students.py?studid=' + studid);
                
                // Load enrolled subjects for this student using AJAX
                loadEnrolledSubjects(studid);
            }
            
            function loadEnrolledSubjects(studid) {
                // Create a simple AJAX request to get enrolled subjects
                let xhr = new XMLHttpRequest();
                xhr.open('GET', 'get_enrolled.py?studid=' + studid, true);
                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4 && xhr.status === 200) {
                        // Parse the response and update the enrolled subjects table
                        let enrolledSubjects = JSON.parse(xhr.responseText);
                        updateEnrolledSubjectsTable(enrolledSubjects);
                    }
                };
                xhr.send();
            }
            
            function updateEnrolledSubjectsTable(subjects) {
                let table = document.getElementById('enrolledSubjectsTable');
                // Clear existing rows except header
                while (table.rows.length > 1) {
                    table.deleteRow(1);
                }
                
                // Add new rows
                if (subjects.length === 0) {
                    let row = table.insertRow();
                    let cell = row.insertCell();
                    cell.colSpan = 5;
                    cell.align = 'center';
                    cell.textContent = 'No enrolled subjects';
                } else {
                    for (let subject of subjects) {
                        let row = table.insertRow();
                        row.onclick = function() {
                            selectEnrolledSubject(subject.subjid, subject.subjcode);
                        };
                        row.style.cursor = 'pointer';
                        
                        let cell1 = row.insertCell();
                        cell1.align = 'center';
                        cell1.textContent = subject.subjid;
                        
                        let cell2 = row.insertCell();
                        cell2.align = 'center';
                        cell2.textContent = subject.subjcode;
                        
                        let cell3 = row.insertCell();
                        cell3.align = 'center';
                        cell3.textContent = subject.subjdesc;
                        
                        let cell4 = row.insertCell();
                        cell4.align = 'center';
                        cell4.textContent = subject.subjunits;
                        
                        let cell5 = row.insertCell();
                        cell5.align = 'center';
                        cell5.textContent = subject.subjsched;
                    }
                }
            }
            
            function selectEnrolledSubject(subjid, subjcode) {
                selectedEnrolledSubjectId = subjid;
                document.getElementById('dropButton').style.display = 
                    selectedStudentId && selectedEnrolledSubjectId ? 'inline' : 'none';
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
                    
                    // Also include the studid in URL parameter
                    let urlStudId = document.createElement('input');
                    urlStudId.type = 'hidden';
                    urlStudId.name = 'studid';
                    urlStudId.value = selectedStudentId;
                    form.appendChild(urlStudId);
                    
                    document.body.appendChild(form);
                    form.submit();
                }
            }
            
            function selectSubject() {
                selectedSubjectId = document.getElementById('subjectSelect').value;
                updateEnrollButton();
            }
            
            function updateEnrollButton() {
                let studid = document.getElementById('studid').value;
                let subjid = document.getElementById('subjectSelect').value;
                let enrollButton = document.getElementById('enrollButton');
                
                if (studid && subjid) {
                    enrollButton.disabled = false;
                    enrollButton.innerHTML = 'Enroll Student ID: <span id="enrollStudId">' + studid + '</span> to Subject ID: <span id="enrollSubjId">' + subjid + '</span>';
                } else {
                    enrollButton.disabled = true;
                    enrollButton.innerHTML = 'Enroll Student';
                }
            }
            
            function enrollStudent() {
                let studid = document.getElementById('studid').value;
                let subjid = document.getElementById('subjectSelect').value;
                
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
                    
                    document.body.appendChild(form);
                    form.submit();
                } else {
                    alert('Please select a student and a subject');
                }
            }
            
            // Update button text dynamically
            setInterval(function() {
                document.getElementById('dropStudId').textContent = selectedStudentId || '';
                document.getElementById('dropSubjId').textContent = selectedEnrolledSubjectId || '';
                updateEnrollButton();
            }, 100);
        </script>
    </head>
    <body>
        <h1><a href="subjects.py">Subjects</a></h1>
        
        <!-- Two-column layout -->
        <table width="100%" cellpadding="10">
            <tr>
                <!-- Left column: Student Form -->
                <td width="40%" valign="top">
                    <h2>Student Form</h2>
                    <form method="POST" action="students.py" id="studentForm">
                        <table>
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
                                <td colspan="2">
                                    <button type="button" onclick="submitForm('insert')" style="width: 80px">Insert</button>
                                    <button type="button" onclick="submitForm('update')" style="width: 80px">Update</button>
                                    <button type="button" onclick="submitForm('delete')" style="width: 80px">Delete</button>
                                </td>
                            </tr>
                        </table>
                    </form>
                    
                    <!-- Enroll Section (below student form) -->
                    <br>
                    <h3>Enroll Student to Subject</h3>
                    <table>
                        <tr>
                            <td>Student ID:</td>
                            <td><input type="text" id="displayStudId" style="width: 100px; background-color: #f0f0f0;" readonly value=""" + f"'{prefill_data.get('studid', '')}'" + """></td>
                        </tr>
                        <tr>
                            <td>Subject:</td>
                            <td>
                                <select id="subjectSelect" style="width: 150px;" onchange="selectSubject()">
                                    <option value="">Select Subject</option>
    """)

    # Add all subjects to the dropdown
    for subject in all_subjects:
        print(f"<option value='{subject[0]}'>{subject[0]} - {html.escape(str(subject[1]))}</option>")

    print("""
                                </select>
                            </td>
                        </tr>
                        <tr>
                            <td colspan="2" align="center">
                                <button id="enrollButton" type="button" onclick="enrollStudent()" style="width: 300px; margin-top: 10px;" disabled>
                                    Enroll Student
                                </button>
                            </td>
                        </tr>
                    </table>
                </td>
                
                <!-- Right column: Students Table and Enrolled Subjects -->
                <td width="60%" valign="top">
                    <!-- Students Table -->
                    <h2>Students Table</h2>
                    <table border="1" width="100%" id="studentsTable">
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Address</th>
                            <th>Gender</th>
                            <th>Course</th>
                            <th>Year</th>
                            <th>Total Units</th>
                        </tr>
    """)

    for student in students:
        print("<tr onclick='selectStudent(" + str(student[0]) + ", \"" + 
               html.escape(str(student[1])) + "\", \"" + 
               html.escape(str(student[2])) + "\", \"" + 
               html.escape(str(student[4])) + "\", \"" + 
               html.escape(str(student[3])) + "\", \"" + 
               html.escape(str(student[5])) + "\")' style='cursor:pointer;'>")
        print("<td align='center'>" + str(student[0]) + "</td>")
        print("<td align='center'>" + html.escape(str(student[1])) + "</td>")
        print("<td align='center'>" + html.escape(str(student[2])) + "</td>")
        print("<td align='center'>" + html.escape(str(student[3])) + "</td>")
        print("<td align='center'>" + html.escape(str(student[4])) + "</td>")
        print("<td align='center'>" + html.escape(str(student[5])) + "</td>")
        print("<td align='center'>" + str(student[6]) + "</td>")
        print("</tr>")

    print("""
                    </table>
                    
                    <br><br>
                    
                    <!-- Enrolled Subjects Table -->
                    <h2>Enrolled Subjects</h2>
                    <table border="1" width="100%" id="enrolledSubjectsTable">
                        <tr>
                            <th>Subject ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                        </tr>
    """)

    if enrolled_subjects:
        for subject in enrolled_subjects:
            print("<tr onclick='selectEnrolledSubject(" + str(subject[0]) + ", \"" + html.escape(str(subject[1])) + "\")' style='cursor:pointer;'>")
            print("<td align='center'>" + str(subject[0]) + "</td>")
            print("<td align='center'>" + html.escape(str(subject[1])) + "</td>")
            print("<td align='center'>" + html.escape(str(subject[2])) + "</td>")
            print("<td align='center'>" + str(subject[3]) + "</td>")
            print("<td align='center'>" + html.escape(str(subject[4])) + "</td>")
            print("</tr>")
    else:
        print("<tr><td colspan='5' align='center'>No enrolled subjects</td></tr>")

    print("""
                    </table>
                </td>
            </tr>
        </table>
        
        <!-- Drop Button (hidden by default) -->
        <div style="position: fixed; bottom: 10px; right: 10px;">
            <button id="dropButton" onclick="dropSubject()" style="display:none; margin: 5px;">
                Drop Subject ID: <span id="dropSubjId"></span> of Student ID: <span id="dropStudId"></span>
            </button>
        </div>
        
        <script>
            // Update the display of selected student ID in the enroll section
            setInterval(function() {
                document.getElementById('displayStudId').value = document.getElementById('studid').value || '';
            }, 100);
        </script>
    </body>
    </html>
    """)

finally:
    if 'conn' in locals():
        conn.close()