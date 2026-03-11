#!/usr/bin/env python3
import sys
import os

# ── Ensure stdout is in binary mode (critical on Windows CGI / IIS) ──
if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

def send_html_error(msg):
    import html as html_mod
    out = sys.stdout.buffer
    out.write(b"Content-Type: text/html\r\n\r\n")
    out.write(f"<html><body><h1>Error</h1><p>{html_mod.escape(str(msg))}</p></body></html>".encode("utf-8"))
    out.flush()
    sys.exit(1)

def send_redirect(msg, url):
    out = sys.stdout.buffer
    out.write(b"Content-Type: text/html\r\n\r\n")
    out.write(f"<script>alert('{msg}');window.location.href='{url}';</script>".encode("utf-8"))
    out.flush()
    sys.exit(0)

def send_expire_cookie(name):
    return f"Set-Cookie: {name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/\r\n".encode()

try:
    import cgi
    import mysql.connector
    import http.cookies
    import re
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
except Exception as e:
    send_html_error(f"Import error: {e}")

try:
    form = cgi.FieldStorage()

    # ── Handle logout ──
    if form.getvalue("logout_action", "") == "1":
        out = sys.stdout.buffer
        out.write(b"Content-Type: text/html\r\n")
        out.write(send_expire_cookie("session_id"))
        out.write(send_expire_cookie("username"))
        out.write(send_expire_cookie("database"))
        out.write(send_expire_cookie("user_role"))
        out.write(b"\r\n")
        out.write(b"<script>window.location.href='index.py';</script>")
        out.flush()
        sys.exit(0)

    # ── Load cookies ──
    cookies = http.cookies.SimpleCookie()
    cookie_string = os.environ.get('HTTP_COOKIE', '')
    if cookie_string:
        cookies.load(cookie_string)

    is_logged_in = False
    username = ""
    database_name = ""
    user_role = ""
    is_student = False

    if 'session_id' in cookies and 'username' in cookies:
        session_id = cookies['session_id'].value
        username = cookies['username'].value
        database_name = cookies['database'].value if 'database' in cookies else ""
        user_role = cookies['user_role'].value if 'user_role' in cookies else ""
        if session_id:
            is_logged_in = True
            is_student = (user_role == "student")

    if not is_logged_in:
        send_redirect('Please login first', 'index.py')
    if not database_name:
        send_redirect('Please select a database first', 'index.py')
    if not is_student:
        send_redirect('Access Denied: This page is for students only', 'encodegrades.py')

    student_id_match = re.search(r'^(\d{4})', username)
    student_id = int(student_id_match.group(1)) if student_id_match else None

    # ── Database ──
    conn = mysql.connector.connect(
        host="localhost", user="root", password="root", database=database_name
    )
    cursor = conn.cursor()

    grade_cols = ['prelim', 'midterm', 'prefinal', 'final']
    cursor.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'grades'
    """, (database_name,))
    existing_cols = [row[0].lower() for row in cursor.fetchall()]

    schema_changed = False
    for col in grade_cols:
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE grades ADD COLUMN {col} VARCHAR(5)")
                schema_changed = True
            except Exception:
                pass

    if schema_changed:
        conn.commit()
        cursor.close()
        conn.close()
        conn = mysql.connector.connect(
            host="localhost", user="root", password="root", database=database_name
        )
        cursor = conn.cursor()

    cursor.execute("""
        SELECT studid, studname, studcrs, yrlvl
        FROM students WHERE studid = %s
    """, (student_id,))
    student_info = cursor.fetchone()

    if not student_info:
        send_redirect('Student record not found', 'index.py')

    studid, studname, studcrs, yrlvl = student_info

    cursor.execute("""
        SELECT s.subjid, s.subjcode, g.prelim, g.midterm, g.prefinal, g.final
        FROM enroll e
        INNER JOIN subjects s ON e.subjid = s.subjid
        LEFT JOIN grades g ON e.eid = g.enroll_eid
        WHERE e.studid = %s
        ORDER BY s.subjid
    """, (student_id,))
    enrolled_subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    # ── Build PDF ──
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch,  bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        'Title2', parent=styles['Normal'],
        alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=16,
        spaceBefore=10, spaceAfter=10
    )
    style_label = ParagraphStyle(
        'Label', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11
    )
    style_value = ParagraphStyle(
        'Value', parent=styles['Normal'], fontSize=11
    )
    style_right = ParagraphStyle(
        'Right', parent=styles['Normal'],
        alignment=TA_RIGHT, fontSize=11
    )
    style_univ = ParagraphStyle(
        'Univ', parent=styles['Normal'],
        alignment=TA_LEFT, fontName='Helvetica-Bold', fontSize=14, spaceAfter=3
    )
    style_office_left = ParagraphStyle(
        'OfficeLeft', parent=styles['Normal'],
        alignment=TA_LEFT, fontSize=11, spaceAfter=0
    )
    style_cell = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        alignment=TA_CENTER, fontSize=11
    )
    style_link = ParagraphStyle(
        'Link', parent=styles['Normal'],
        alignment=TA_CENTER, fontSize=11,
        textColor=colors.HexColor('#1a0dab'),  # blue link color
    )

    story = []

    # ── Header: logo left + university name/office ──
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "sumeru.jpg")

    logo_cell = Image(logo_path, width=0.85 * inch, height=0.85 * inch) \
                if os.path.exists(logo_path) \
                else Paragraph("", styles['Normal'])

    header_text = [
        Paragraph("Sumeru Akademiya", style_univ),
        
        Paragraph("Registrar's Office", style_office_left),
    ]

    header_table = Table([[logo_cell, header_text]], colWidths=[1 * inch, 6 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (0, 0),   0),
        ('RIGHTPADDING',  (0, 0), (0, 0),   12),
        ('LEFTPADDING',   (1, 0), (1, 0),   0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceAfter=6))
    story.append(Paragraph("Student Grade Sheet", style_title))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=14))

    # ── Student info ──
    def info_row(label, value):
        return [Paragraph(label, style_label), Paragraph(str(value), style_value)]

    info_table = Table([
        info_row("Student ID:",     studid),
        info_row("School Year:",    database_name),
        info_row("Student Name:",   studname or ""),
        info_row("Student Course:", studcrs or ""),
        info_row("Student Year:",   yrlvl or ""),
    ], colWidths=[2 * inch, 5 * inch])
    info_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    # ── Grades table with evaluate.py links ──
    # Get server and script path info
    server_name = os.environ.get('SERVER_NAME', 'localhost')
    server_port = os.environ.get('SERVER_PORT', '80')
    script_name = os.environ.get('SCRIPT_NAME', '/cgi-bin/studrec.py')
    
    # Build base URL (http://localhost/cgi-bin)
    protocol = 'https' if server_port == '443' else 'http'
    port_str = '' if server_port in ['80', '443'] else f':{server_port}'
    base_path = script_name.rsplit('/', 1)[0]  # Get directory path
    base_url = f"{protocol}://{server_name}{port_str}{base_path}"

    table_data = [['SubjID', 'Subj Code', 'Prelim', 'Midterm', 'Prefinal', 'Final']]

    for s in enrolled_subjects:
        subjid_val, subjcode, prelim, midterm, prefinal, final = s

        # A subject is considered "graded" if any grade field has a value
        is_graded = any([prelim, midterm, prefinal, final])

        if is_graded:
            # Clickable blue underlined SubjID that links to evaluate.py with subjid parameter
            evaluate_link = f"{base_url}/evaluate.py?subjid={subjid_val}"
            subjid_cell = Paragraph(
                f'<link href="{evaluate_link}"><u>{subjid_val}</u></link>',
                style_link
            )
        else:
            # Plain text SubjID
            subjid_cell = Paragraph(str(subjid_val), style_cell)

        table_data.append([
            subjid_cell,
            Paragraph(str(subjcode) if subjcode else "", style_cell),
            Paragraph(str(prelim)   if prelim   else "", style_cell),
            Paragraph(str(midterm)  if midterm  else "", style_cell),
            Paragraph(str(prefinal) if prefinal else "", style_cell),
            Paragraph(str(final)    if final    else "", style_cell),
        ])

    if not enrolled_subjects:
        table_data.append([
            Paragraph("No subjects enrolled", style_cell),
            "", "", "", "", ""
        ])

    grades_table = Table(
        table_data,
        colWidths=[0.8*inch, 2.2*inch, 1*inch, 1*inch, 1*inch, 1*inch],
        repeatRows=1
    )
    grades_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#e8e8e8')),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 11),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 1.5, colors.black),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        *([('SPAN', (0, 1), (-1, 1))] if not enrolled_subjects else []),
    ]))
    story.append(grades_table)
    story.append(Spacer(1, 10))

    # ── Subject count ──
    story.append(Paragraph(
        f"<b>Number of Subjects Listed: {len(enrolled_subjects)}</b>",
        ParagraphStyle('Count', parent=styles['Normal'], fontSize=11)
    ))
    story.append(Spacer(1, 50))

    # ── Registrar signature block (bottom right, no actual signature) ──
    # Left col is a spacer; right col is 2 inches wide with the underline.
    SIG_LINE_WIDTH = 2 * inch
    SIG_LEFT_WIDTH = 7 * inch - SIG_LINE_WIDTH  # 5 inches

    sig_table = Table(
        [
            ["", Paragraph("", style_right)],
            ["", Paragraph("", style_right)],
            ["", Paragraph("<b>University Registrar</b>", style_right)],
            ["", Paragraph("Office of the Registrar", style_right)],
        ],
        colWidths=[SIG_LEFT_WIDTH, SIG_LINE_WIDTH],
        rowHeights=[20, 2, 20, 16]
    )
    sig_table.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW',     (1, 1), (1, 1),   1, colors.black),
    ]))
    story.append(sig_table)

    doc.build(story)

    # ── Send PDF response ──
    pdf_bytes = buffer.getvalue()
    out = sys.stdout.buffer
    out.write(b"Content-Type: application/pdf\r\n")
    out.write(f"Content-Disposition: inline; filename=\"grade_sheet_{studid}.pdf\"\r\n".encode())
    out.write(f"Content-Length: {len(pdf_bytes)}\r\n".encode())
    out.write(b"\r\n")
    out.write(pdf_bytes)
    out.flush()

except Exception as e:
    send_html_error(e)