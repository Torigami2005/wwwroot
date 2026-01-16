#!/usr/bin/env python3
import cgi
import mysql.connector
import json

print("Content-Type: application/json\n")

form = cgi.FieldStorage()

# Get subject ID from query parameter
subjid = form.getvalue("subjid", "")

if not subjid:
    print(json.dumps([]))
    exit()

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    cursor = conn.cursor(dictionary=True)  # Use dictionary cursor for easier JSON conversion

    # Get students enrolled in the subject
    cursor.execute("""
        SELECT st.studid, st.studname, st.studadd, st.studgender, st.studcrs, st.yrlvl 
        FROM enroll e 
        JOIN students st ON e.studid = st.studid 
        WHERE e.subjid = %s
        ORDER BY st.studid
    """, (subjid,))
    
    enrolled_students = cursor.fetchall()
    
    # Convert to list of dictionaries
    result = []
    for student in enrolled_students:
        result.append({
            'studid': student['studid'],
            'studname': student['studname'],
            'studadd': student['studadd'],
            'studgender': student['studgender'],
            'studcrs': student['studcrs'],
            'yrlvl': student['yrlvl']
        })
    
    print(json.dumps(result))
    
except Exception as e:
    # Return empty array on error
    print(json.dumps([]))
    
finally:
    if 'conn' in locals():
        conn.close()