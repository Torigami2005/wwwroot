#!/usr/bin/env python3
import cgi
import mysql.connector
import json

print("Content-Type: application/json\n")

form = cgi.FieldStorage()

# Get student ID from query parameter
studid = form.getvalue("studid", "")

if not studid:
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

    # Get enrolled subjects for the student
    cursor.execute("""
        SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
        FROM enroll e 
        JOIN subjects s ON e.subjid = s.subjid 
        WHERE e.studid = %s
        ORDER BY s.subjid
    """, (studid,))
    
    enrolled_subjects = cursor.fetchall()
    
    # Convert to list of dictionaries
    result = []
    for subject in enrolled_subjects:
        result.append({
            'subjid': subject['subjid'],
            'subjcode': subject['subjcode'],
            'subjdesc': subject['subjdesc'],
            'subjunits': int(subject['subjunits']) if subject['subjunits'] else 0,
            'subjsched': subject['subjsched']
        })
    
    print(json.dumps(result))
    
except Exception as e:
    # Return empty array on error
    print(json.dumps([]))
    
finally:
    if 'conn' in locals():
        conn.close()