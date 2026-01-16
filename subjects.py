#!/usr/bin/env python3
import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()

# Get form values for subjects
action_type = form.getvalue("action_type", "")  # insert, update, delete
subjid = form.getvalue("subjid", "")
subjcode = html.escape(form.getvalue("subjcode", ""))
subjdesc = html.escape(form.getvalue("subjdesc", ""))
subjunits = form.getvalue("subjunits", "")
subjsched = html.escape(form.getvalue("subjsched", ""))

# For student enrollment to subject
selected_studid = form.getvalue("selected_studid", "")
selected_subjid = form.getvalue("selected_subjid", "")
enroll_action = form.getvalue("enroll_action", "")

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    cursor = conn.cursor()

    # First, let's modify the tables to have auto-increment IDs if not already done
    try:
        # Modify subjects table to auto-increment subjid starting from 2000
        cursor.execute("ALTER TABLE subjects MODIFY subjid INT NOT NULL AUTO_INCREMENT")
        cursor.execute("ALTER TABLE subjects AUTO_INCREMENT = 2000")
        
        # Modify students table to auto-increment studid starting from 1000
        cursor.execute("ALTER TABLE students MODIFY studid INT NOT NULL AUTO_INCREMENT")
        cursor.execute("ALTER TABLE students AUTO_INCREMENT = 1000")
        
        conn.commit()
    except:
        pass  # Tables might already be modified

    # Handle subject actions (Insert, Update, Delete)
    if action_type == "insert" and subjcode:
        try:
            insert_sql = """
                INSERT INTO subjects (subjcode, subjdesc, subjunits, subjsched) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (subjcode, subjdesc, subjunits, subjsched))
            conn.commit()
            # Redirect to show the new subject in URL
            new_subjid = cursor.lastrowid
            print(f"<script>window.location.href='subjects.py?subjid={new_subjid}';</script>")
        except Exception as e:
            print(f"<!-- Insert error: {e} -->")
            pass
    
    elif action_type == "update" and subjid and subjcode:
        try:
            update_sql = """
                UPDATE subjects 
                SET subjcode=%s, subjdesc=%s, subjunits=%s, subjsched=%s 
                WHERE subjid=%s
            """
            cursor.execute(update_sql, (subjcode, subjdesc, subjunits, subjsched, subjid))
            conn.commit()
            # Redirect to show updated subject in URL
            print(f"<script>window.location.href='subjects.py?subjid={subjid}';</script>")
        except Exception as e:
            print(f"<!-- Update error: {e} -->")
    
    elif action_type == "delete" and subjid:
        try:
            # First delete from enroll (cascade to grades)
            delete_enrollments = "DELETE FROM enroll WHERE subjid=%s"
            cursor.execute(delete_enrollments, (subjid,))
            
            # Then delete the subject
            delete_sql = "DELETE FROM subjects WHERE subjid=%s"
            cursor.execute(delete_sql, (subjid,))
            conn.commit()
            # Redirect to main page
            print("<script>window.location.href='subjects.py';</script>")
        except Exception as e:
            print(f"<!-- Delete error: {e} -->")

    # Handle student enrollment to subject
    if enroll_action == "enroll" and selected_studid and selected_subjid:
        try:
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
            # Redirect with both IDs in URL
            print(f"<script>window.location.href='subjects.py?subjid={selected_subjid}&studid={selected_studid}';</script>")
        except Exception as e:
            print(f"<!-- Enroll error: {e} -->")  # Already enrolled or error
    
    elif enroll_action == "drop" and selected_studid and selected_subjid:
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
        # Redirect to show subject in URL
        print(f"<script>window.location.href='subjects.py?subjid={selected_subjid}';</script>")

    # Get all subjects with student count calculation
    cursor.execute("""
        SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched, 
               COUNT(e.studid) as student_count
        FROM subjects s
        LEFT JOIN enroll e ON s.subjid = e.subjid
        GROUP BY s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched
        ORDER BY s.subjid
    """)
    subjects = cursor.fetchall()

    # Get students enrolled in a specific subject (from URL parameter)
    enrolled_students = []
    # Use URL parameter subjid if available
    url_subjid = form.getvalue("subjid", "")
    if url_subjid:
        selected_subjid = url_subjid  # Override with URL parameter
        cursor.execute("""
            SELECT st.studid, st.studname, st.studadd, st.studgender, st.studcrs, st.yrlvl 
            FROM enroll e 
            JOIN students st ON e.studid = st.studid 
            WHERE e.subjid = %s
            ORDER BY st.studid
        """, (selected_subjid,))
        enrolled_students = cursor.fetchall()

    # Pre-fill form if subject ID is in URL
    prefill_data = {}
    if url_subjid:
        cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects WHERE subjid = %s", (url_subjid,))
        subject_data = cursor.fetchone()
        if subject_data:
            prefill_data = {
                'subjid': subject_data[0],
                'subjcode': subject_data[1],
                'subjdesc': subject_data[2],
                'subjunits': subject_data[3],
                'subjsched': subject_data[4]
            }

    print("""
    <html>
    <head>
        <title>Subject Enrollment System</title>
        <style>
            @import url('https://fonts.cdnfonts.com/css/hywenhei');
            
            body {
                font-family: 'HYWenHei', sans-serif;
            }
            
            button {
                font-family: 'HYWenHei', sans-serif !important;
            }
        </style>
        <script>
            let selectedSubjectId = null;
            let selectedSubjectData = null;
            let selectedEnrolledStudentId = null;
            
            function selectSubject(subjid, subjcode, subjdesc, subjunits, subjsched) {
                selectedSubjectId = subjid;
                selectedSubjectData = {
                    code: subjcode,
                    desc: subjdesc,
                    units: subjunits,
                    sched: subjsched
                };
                selectedEnrolledStudentId = null;
                
                // Fill the form with subject data
                document.getElementById('subjid').value = subjid;
                document.getElementById('subjcode').value = subjcode;
                document.getElementById('subjdesc').value = subjdesc;
                document.getElementById('subjunits').value = subjunits;
                document.getElementById('subjsched').value = subjsched;
                
                // Hide drop button
                document.getElementById('dropStudentButton').style.display = 'none';
                
                // Update URL to show selected subject
                window.history.pushState({}, '', 'subjects.py?subjid=' + subjid);
                
                // Load enrolled students for this subject
                loadEnrolledStudents(subjid);
            }
            
            function loadEnrolledStudents(subjid) {
                // Reload the page with the subjid parameter to show enrolled students
                window.location.href = 'subjects.py?subjid=' + subjid;
            }
            
            function selectEnrolledStudent(studid, studname) {
                selectedEnrolledStudentId = studid;
                document.getElementById('dropStudentButton').style.display = 
                    selectedSubjectId && selectedEnrolledStudentId ? 'block' : 'none';
            }
            
            function submitForm(action) {
                let form = document.getElementById('subjectForm');
                let actionInput = document.createElement('input');
                actionInput.type = 'hidden';
                actionInput.name = 'action_type';
                actionInput.value = action;
                form.appendChild(actionInput);
                form.submit();
            }
            
            function enrollStudent() {
                let studid = prompt("Enter Student ID to enroll:");
                if (studid && selectedSubjectId) {
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
                    subjidInput.value = selectedSubjectId;
                    form.appendChild(subjidInput);
                    
                    let actionInput = document.createElement('input');
                    actionInput.type = 'hidden';
                    actionInput.name = 'enroll_action';
                    actionInput.value = 'enroll';
                    form.appendChild(actionInput);
                    
                    // Also include the subjid in URL parameter
                    let urlSubjId = document.createElement('input');
                    urlSubjId.type = 'hidden';
                    urlSubjId.name = 'subjid';
                    urlSubjId.value = selectedSubjectId;
                    form.appendChild(urlSubjId);
                    
                    document.body.appendChild(form);
                    form.submit();
                }
            }
            
            function dropStudent() {
                if (selectedSubjectId && selectedEnrolledStudentId) {
                    let form = document.createElement('form');
                    form.method = 'POST';
                    form.action = 'subjects.py';
                    
                    let studidInput = document.createElement('input');
                    studidInput.type = 'hidden';
                    studidInput.name = 'selected_studid';
                    studidInput.value = selectedEnrolledStudentId;
                    form.appendChild(studidInput);
                    
                    let subjidInput = document.createElement('input');
                    subjidInput.type = 'hidden';
                    subjidInput.name = 'selected_subjid';
                    subjidInput.value = selectedSubjectId;
                    form.appendChild(subjidInput);
                    
                    let actionInput = document.createElement('input');
                    actionInput.type = 'hidden';
                    actionInput.name = 'enroll_action';
                    actionInput.value = 'drop';
                    form.appendChild(actionInput);
                    
                    // Also include the subjid in URL parameter
                    let urlSubjId = document.createElement('input');
                    urlSubjId.type = 'hidden';
                    urlSubjId.name = 'subjid';
                    urlSubjId.value = selectedSubjectId;
                    form.appendChild(urlSubjId);
                    
                    document.body.appendChild(form);
                    form.submit();
                }
            }
            
            // Initialize selectedSubjectId from URL on page load
            window.onload = function() {
                const urlParams = new URLSearchParams(window.location.search);
                const subjid = urlParams.get('subjid');
                if (subjid) {
                    selectedSubjectId = subjid;
                }
            };
            
            // Update button text dynamically
            setInterval(function() {
                document.getElementById('dropStudId').textContent = selectedEnrolledStudentId || '';
                document.getElementById('dropSubjId').textContent = selectedSubjectId || '';
            }, 100);
        </script>
    </head>
    <body>
        <p><a href="students.py">Students</a></p>
        
        <!-- Two-column layout -->
        <table width="100%" cellpadding="10">
            <tr>
                <!-- Left column: Subject Form -->
                <td width="40%" valign="top">
                    <h2>Subject Form</h2>
                    <form method="POST" action="subjects.py" id="subjectForm">
                        <table>
                            <tr>
                                <td>Subject ID:</td>
                                <td><input type="text" name="subjid" id="subjid" style="width: 100px" readonly value=""" + f"'{prefill_data.get('subjid', '')}'" + """></td>
                            </tr>
                            <tr>
                                <td>Subject Code:</td>
                                <td><input type="text" name="subjcode" id="subjcode" style="width: 150px" value=""" + f"'{html.escape(str(prefill_data.get('subjcode', '')))}'" + """></td>
                            </tr>
                            <tr>
                                <td>Description:</td>
                                <td><input type="text" name="subjdesc" id="subjdesc" style="width: 200px" value=""" + f"'{html.escape(str(prefill_data.get('subjdesc', '')))}'" + """></td>
                            </tr>
                            <tr>
                                <td>Units:</td>
                                <td><input type="text" name="subjunits" id="subjunits" style="width: 100px" value=""" + f"'{str(prefill_data.get('subjunits', ''))}'" + """></td>
                            </tr>
                            <tr>
                                <td>Schedule:</td>
                                <td><input type="text" name="subjsched" id="subjsched" style="width: 150px" value=""" + f"'{html.escape(str(prefill_data.get('subjsched', '')))}'" + """></td>
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
                    
                    <!-- Enroll Button (directly below subject form) -->
                    <br>

                    
                    <!-- Drop Student Button (below enroll button) -->
                    <br>
                    <div id="dropButtonContainer">
                        <button id="dropStudentButton" onclick="dropStudent()" style="display:none; width: 300px;">
                            Drop Student ID: <span id="dropStudId"></span> from Subject ID: <span id="dropSubjId"></span>
                        </button>
                    </div>

                    </form>
                    
                    <!-- Only keep the Drop Student Button -->
                    <br>
                    <div id="dropButtonContainer">
                        <button id="dropStudentButton" onclick="dropStudent()" style="display:none; width: 300px;">
                            Drop Student ID: <span id="dropStudId"></span> from Subject ID: <span id="dropSubjId"></span>
                        </button>
                    </div>
                </td>
                
                <!-- Right column: Subjects Table and Enrolled Students -->
                <td width="60%" valign="top">
                    <!-- Subjects Table -->
                    <h2>Subjects Table</h2>
                    <table border="1" width="100%" id="subjectsTable">
                        <tr>
                            <th>ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                            <th>#Students</th>
                        </tr>
    """)

    for subject in subjects:
        print("<tr onclick='selectSubject(" + str(subject[0]) + ", \"" + 
               html.escape(str(subject[1])) + "\", \"" + 
               html.escape(str(subject[2])) + "\", \"" + 
               str(subject[3]) + "\", \"" +  # subjunits - don't escape integer
               html.escape(str(subject[4])) + "\")' style='cursor:pointer;'>")
        print("<td align='center'>" + str(subject[0]) + "</td>")
        print("<td align='center'>" + html.escape(str(subject[1])) + "</td>")
        print("<td align='center'>" + html.escape(str(subject[2])) + "</td>")
        print("<td align='center'>" + str(subject[3]) + "</td>")  # subjunits - don't escape
        print("<td align='center'>" + html.escape(str(subject[4])) + "</td>")
        print("<td align='center'>" + str(subject[5]) + "</td>")
        print("</tr>")

    print("""
                    </table>
                    
                    <br><br>
                    
                    <!-- Enrolled Students Table -->
                    <h2>Students Enrolled in Subject ID """ + (str(url_subjid) if url_subjid else '') + """</h2>
                    <table border="1" width="100%" id="enrolledStudentsTable">
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Address</th>
                            <th>Gender</th>
                            <th>Course</th>
                            <th>Year Level</th>
                        </tr>
    """)

    if enrolled_students:
        for student in enrolled_students:
            print("<tr onclick='selectEnrolledStudent(" + str(student[0]) + ", \"" + html.escape(str(student[1])) + "\")' style='cursor:pointer;'>")
            print("<td align='center'>" + str(student[0]) + "</td>")
            print("<td align='center'>" + html.escape(str(student[1])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[2])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[3])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[4])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[5])) + "</td>")
            print("</tr>")
    else:
        print("<tr><td colspan='6' align='center'>No students enrolled</td></tr>")

    print("""
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """)

finally:
    if 'conn' in locals():
        conn.close()