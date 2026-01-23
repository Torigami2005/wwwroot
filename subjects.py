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

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    cursor = conn.cursor()

    # Handle subject actions (Insert, Update, Delete)
    if action_type == "insert" and subjcode:
        try:
            # Get the maximum subjid and calculate the next one starting from 2000
            cursor.execute("SELECT MAX(subjid) FROM subjects")
            result = cursor.fetchone()
            max_subjid = result[0]
            
            # If no subjects exist yet, start from 2000
            if max_subjid is None:
                next_subjid = 2000
            else:
                # Find the next available ID starting from max(current_max + 1, 2000)
                next_subjid = max(max_subjid + 1, 2000)
            
            insert_sql = """
                INSERT INTO subjects (subjid, subjcode, subjdesc, subjunits, subjsched) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (next_subjid, subjcode, subjdesc, subjunits, subjsched))
            conn.commit()
            # Redirect to show the new subject in URL
            print(f"<script>window.location.href='subjects.py?subjid={next_subjid}';</script>")
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
        cursor.execute("""
            SELECT st.studid, st.studname, st.studadd, st.studgender, st.studcrs, st.yrlvl 
            FROM enroll e 
            JOIN students st ON e.studid = st.studid 
            WHERE e.subjid = %s
            ORDER BY st.studid
        """, (url_subjid,))
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
        <title>Sumeru Akademiya - Subject Management System</title>
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
            
            .nav-links {
                display: flex;
                gap: 15px;
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
                
                .nav-links {
                    width: 100%;
                    justify-content: flex-start;
                    flex-wrap: wrap;
                }
            }
        </style>
        <script>
            function selectSubject(subjid, subjcode, subjdesc, subjunits, subjsched) {
                // Redirect to URL with subject ID
                window.location.href = 'subjects.py?subjid=' + subjid;
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
            
            // Initialize selectedSubjectId from URL on page load
            window.onload = function() {
                const urlParams = new URLSearchParams(window.location.search);
                const subjid = urlParams.get('subjid');
                if (subjid) {
                    // Highlight the selected row in the subjects table
                    let rows = document.querySelectorAll('#subjectsTable tr');
                    for (let row of rows) {
                        let firstCell = row.querySelector('td:first-child');
                        if (firstCell && firstCell.textContent === subjid) {
                            row.style.backgroundColor = 'rgba(42, 82, 152, 0.15)';
                            row.style.fontWeight = 'bold';
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
                    <div class="subtitle">Subject Management System</div>
                </div>
            </div>
            <div class="nav-links">
                <a href="students.py" class="nav-link">Students</a>
                <a href="teachers.py" class="nav-link">Teachers</a>
            </div>
        </div>
        
        <div class="main-container">
            <!-- Two-column layout -->
            <table width="100%" cellpadding="10">
                <tr>
                    <!-- Left column: Subject Form -->
                    <td width="40%" valign="top">
                        <div class="form-container">
                            <h2>Subject Form</h2>
                            <form method="POST" action="subjects.py" id="subjectForm">
                                <table style="width: 100%;">
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
                                        <td colspan="2" style="text-align: center; padding-top: 20px;">
                                            <button type="button" onclick="submitForm('insert')" style="width: 80px; margin: 0 5px;">Insert</button>
                                            <button type="button" onclick="submitForm('update')" style="width: 80px; margin: 0 5px;">Update</button>
                                            <button type="button" onclick="submitForm('delete')" style="width: 80px; margin: 0 5px;">Delete</button>
                                        </td>
                                    </tr>
                                </table>
                            </form>
                        </div>
                    </td>
                    
                    <!-- Right column: Subjects Table and Enrolled Students -->
                    <td width="60%" valign="top">
                        <!-- Subjects Table -->
                        <div class="form-container">
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
                        </div>
                        
                        <!-- Enrolled Students Table -->
                        <div class="form-container" style="margin-top: 30px;">
                            <h2>Students Enrolled in Subject ID: """ + (str(url_subjid) if url_subjid else 'None Selected') + """</h2>
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
            print("<tr>")
            print("<td align='center'>" + str(student[0]) + "</td>")
            print("<td align='center'>" + html.escape(str(student[1])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[2])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[3])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[4])) + "</td>")
            print("<td align='center'>" + html.escape(str(student[5])) + "</td>")
            print("</tr>")
    else:
        if url_subjid:
            print("<tr><td colspan='6' align='center'>No students enrolled in this subject</td></tr>")
        else:
            print("<tr><td colspan='6' align='center'>Select a subject from the table above to view enrolled students</td></tr>")

    print("""
                            </table>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """)

finally:
    if 'conn' in locals():
        conn.close()
        
