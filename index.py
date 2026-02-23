#!/usr/bin/env python3
import cgi
import mysql.connector
import html
import re
import os
import http.cookies
import datetime
import secrets
import sys

print("Content-Type: text/html")

form = cgi.FieldStorage()

# Check for logout action FIRST
logout_request = form.getvalue("logout", "")

# Handle logout
if logout_request == "1":
    # Clear all cookies by setting expired cookies
    print("Set-Cookie: session_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; HttpOnly")
    print("Set-Cookie: username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: user_role=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print()
    print(f"""
    <script>
        window.location.href = 'index.py';
    </script>
    """)
    sys.exit()

# Check for existing cookies
cookie_string = os.environ.get('HTTP_COOKIE', '')
cookies = http.cookies.SimpleCookie()
if cookie_string:
    cookies.load(cookie_string)

# Get login form values
username = form.getvalue("username", "")
password = form.getvalue("password", "")
database_name = form.getvalue("database", "")

# Check if this is a login attempt
login_attempt = form.getvalue("login_attempt", "")

# Check admin credentials
is_logged_in = False
is_admin = False
is_teacher = False
is_student = False
user_role = ""
login_error = ""

# Store password temporarily for this request only
temp_password = ""

# Check cookies first - SESSION-BASED CHECK
if 'session_id' in cookies and 'username' in cookies and 'user_role' in cookies:
    session_id = cookies['session_id'].value
    cookie_username = cookies['username'].value
    cookie_database = cookies['database'].value if 'database' in cookies else ""
    user_role = cookies['user_role'].value
    
    # Verify session exists
    if session_id:
        is_logged_in = True
        username = cookie_username
        database_name = cookie_database
        
        # Set role flags
        if user_role == "admin":
            is_admin = True
        elif user_role == "teacher":
            is_teacher = True
        elif user_role == "student":
            is_student = True

# If not logged in via cookies, check form submission
if not is_logged_in and login_attempt == "1" and username and password:
    # Store password for this session
    temp_password = password
    
    # FIRST CHECK: If user is root admin
    if username == "root" and password == "root":
        is_logged_in = True
        is_admin = True
        user_role = "admin"
        
        # Generate a secure session ID
        session_id = secrets.token_hex(32)
        
        # SET SESSION COOKIES ON LOGIN
        print(f"Set-Cookie: session_id={session_id}; path=/; HttpOnly; SameSite=Lax")
        print(f"Set-Cookie: username={username}; path=/; SameSite=Lax")
        print(f"Set-Cookie: user_role={user_role}; path=/; SameSite=Lax")
    
    else:
        # SECOND CHECK: Try student/teacher MySQL user authentication
        # First, connect as root to check the database
        try:
            # Connect as root to check the database
            root_conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            root_cursor = root_conn.cursor()
            
            # Get all databases with year pattern
            current_year = datetime.datetime.now().year
            next_year = current_year + 1
            year_pattern = f"_{current_year}_{next_year}"
            
            root_cursor.execute("SHOW DATABASES")
            all_databases = root_cursor.fetchall()
            
            user_found = False
            user_name_from_db = ""
            user_role_from_db = ""
            user_db_found = ""  # Track which database the user was found in
            
            for db_row in all_databases:
                db_name = db_row[0]
                if year_pattern in db_name:
                    try:
                        # Check students table in this database
                        root_cursor.execute(f"USE `{db_name}`")
                        
                        # Check students table
                        root_cursor.execute("SELECT studid, studname FROM students")
                        students = root_cursor.fetchall()
                        
                        for studid, studname in students:
                            # Create username from studid + studname
                            safe_name = ''.join(c for c in studname if c.isalnum() or c.isspace()).replace(' ', '').lower()
                            mysql_username = f"{studid}{safe_name}"
                            
                            if mysql_username == username:
                                # Password should be AdDU + name only (without ID)
                                expected_password = f"AdDU{safe_name}"
                                if password == expected_password:
                                    user_found = True
                                    user_name_from_db = safe_name
                                    user_role_from_db = "student"
                                    user_db_found = db_name
                                    break
                        
                        # Check teachers table if student not found
                        if not user_found:
                            root_cursor.execute("SELECT tid, tname FROM teachers")
                            teachers = root_cursor.fetchall()
                            
                            for tid, tname in teachers:
                                # Create username from tid + tname
                                safe_name = ''.join(c for c in tname if c.isalnum() or c.isspace()).replace(' ', '').lower()
                                mysql_username = f"{tid}{safe_name}"
                                
                                if mysql_username == username:
                                    # Password should be AdDU + name only (without ID)
                                    expected_password = f"AdDU{safe_name}"
                                    if password == expected_password:
                                        user_found = True
                                        user_name_from_db = safe_name
                                        user_role_from_db = "teacher"
                                        user_db_found = db_name
                                        break
                        
                        if user_found:
                            break
                            
                    except mysql.connector.Error:
                        continue
            
            root_cursor.close()
            root_conn.close()
            
            if user_found:
                # Now try to connect with MySQL user credentials
                try:
                    # Password format: AdDU + name (without ID)
                    mysql_password = f"AdDU{user_name_from_db}"
                    
                    # Try to connect with provided credentials
                    conn = mysql.connector.connect(
                        host="localhost",
                        user=username,
                        password=mysql_password
                    )
                    
                    conn.close()
                    
                    is_logged_in = True
                    user_role = user_role_from_db
                    
                    if user_role == "teacher":
                        is_teacher = True
                    elif user_role == "student":
                        is_student = True
                    
                    # Generate a secure session ID
                    session_id = secrets.token_hex(32)
                    
                    # SET SESSION COOKIES ON LOGIN
                    print(f"Set-Cookie: session_id={session_id}; path=/; HttpOnly; SameSite=Lax")
                    print(f"Set-Cookie: username={username}; path=/; SameSite=Lax")
                    print(f"Set-Cookie: user_role={user_role}; path=/; SameSite=Lax")
                    
                except mysql.connector.Error as e:
                    login_error = "Invalid username or password"
            else:
                login_error = "User not found in any database"
                
        except mysql.connector.Error as e:
            login_error = "Database error. Please contact administrator."
            



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
    
# Handle database deletion - ADMIN ONLY
delete_db_action = form.getvalue("delete_db_action", "")
db_to_delete = form.getvalue("db_to_delete", "")

if delete_db_action == "1" and db_to_delete:
    if not is_admin:
        print("<script>alert('Access Denied: Admin privileges required');window.location.href = 'index.py';</script>")
        sys.exit()
    
    try:
        # Revoke permissions for all users on this database
        success, revoked_count = revoke_database_permissions(db_to_delete)
        
        # Drop the database
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        cursor.execute(f"DROP DATABASE IF EXISTS `{db_to_delete}`")
        conn.commit()
        cursor.close()
        conn.close()
        
        # Clear database cookie if user was using the deleted database
        if database_name == db_to_delete:
            print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
        
        print()
        if revoked_count > 0:
            print(f"<script>alert('Database \"{db_to_delete}\" deleted successfully!\\n\\n{revoked_count} users had their permissions revoked.\\n\\nUsers still exist and can access other databases.');window.location.href = 'index.py';</script>")
        else:
            print(f"<script>alert('Database \"{db_to_delete}\" deleted successfully!');window.location.href = 'index.py';</script>")
        sys.exit()
        
    except Exception as e:
        error_msg = f"Database deletion failed: {str(e)}"
        print()
        print(f"<script>alert('{error_msg}');window.location.href = 'index.py';</script>")
        sys.exit()

# Check if user has selected a database from the dropdown
if is_logged_in and form.getvalue("database"):
    selected_db = form.getvalue("database")
    
    # Get existing session_id
    session_id = cookies['session_id'].value if 'session_id' in cookies else secrets.token_hex(32)
    
    # Check if user has access to the selected database AND still exists in that database
    try:
        # For root admin, use root credentials
        if is_admin:
            # For root user, allow access to any database
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database=selected_db
            )
        else:
            # For student/teacher users, verify they still exist in this specific database
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database=selected_db
            )
            root_cursor = conn.cursor()
            
            # Extract ID from username
            import re
            numbers = re.findall(r'\d+', username)
            user_id = int(numbers[0]) if numbers else 0
            
            # Check if user exists in this specific database
            user_exists_in_db = False
            
            if is_student:
                root_cursor.execute("SELECT COUNT(*) FROM students WHERE studid = %s", (user_id,))
                count = root_cursor.fetchone()[0]
                user_exists_in_db = (count > 0)
            elif is_teacher:
                root_cursor.execute("SELECT COUNT(*) FROM teachers WHERE tid = %s", (user_id,))
                count = root_cursor.fetchone()[0]
                user_exists_in_db = (count > 0)
            
            conn.close()
            
            if not user_exists_in_db:
                login_error = f"Your account does not exist in database: {selected_db}. You may have been dropped from this database."
                # Clear database cookie
                print(f"Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
                print()
                # Show error message and redirect back to database selection
                print(f"""
                <html>
                <head>
                    <meta http-equiv="refresh" content="3;url=index.py">
                </head>
                <body>
                    <div style="font-family: HYWenHei, sans-serif; margin: 50px auto; width: 500px; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;">
                        <h2 style="color: #dc3545;">Access Denied</h2>
                        <p style="color: #721c24; background: #f8d7da; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb;">
                            {html.escape(login_error)}
                        </p>
                        <p>Redirecting to database selection page...</p>
                    </div>
                </body>
                </html>
                """)
                sys.exit()
            
            # Now connect with actual user credentials
            name_only = ''.join([c for c in username if not c.isdigit()])
            mysql_password = f"AdDU{name_only}"
            
            conn = mysql.connector.connect(
                host="localhost",
                user=username,
                password=mysql_password,
                database=selected_db
            )
        
        conn.close()
        
        # Set cookies with the selected database
        print(f"Set-Cookie: session_id={session_id}; path=/; HttpOnly; SameSite=Lax")
        print(f"Set-Cookie: username={username}; path=/; SameSite=Lax")
        print(f"Set-Cookie: database={selected_db}; path=/; SameSite=Lax")
        print(f"Set-Cookie: user_role={user_role}; path=/; SameSite=Lax")
        print()
        
        # # Redirect based on user role
        # if is_admin or is_teacher:
        #     print(f"""
        #     <html>
        #     <head>
        #         <meta http-equiv="refresh" content="0;url=students.py">
        #     </head>
        #     <body>
        #         <p>Redirecting to students page...</p>
        #     </body>
        #     </html>
        #     """)
        # elif is_student:
        #     print(f"""
        #     <html>
        #     <head>
        #         <meta http-equiv="refresh" content="0;url=subjects.py">
        #     </head>
        #     <body>
        #         <p>Redirecting to subjects page...</p>
        #     </body>
        #     </html>
        #     """)
        
                # Redirect based on user role
        if is_admin:
            print(f"""
            <html>
            <head>
                <meta http-equiv="refresh" content="0;url=students.py">
            </head>
            <body>
                <p>Redirecting to students page...</p>
            </body>
            </html>
            """)
        elif is_teacher:
            print(f"""
            <html>
            <head>
                <meta http-equiv="refresh" content="0;url=encodegrades.py">
            </head>
            <body>
                <p>Redirecting to grade encoding page...</p>
            </body>
            </html>
            """)
        elif is_student:
            print(f"""
            <html>
            <head>
                <meta http-equiv="refresh" content="0;url=studrec.py">
            </head>
            <body>
                <p>Redirecting to grade sheet...</p>
            </body>
            </html>
            """)
        sys.exit()
        
    except mysql.connector.Error as e:
        # User doesn't have access to this database
        login_error = f"Access denied to database: {selected_db}"

# If already logged in with database selected via cookies, verify user still exists in that database
if is_logged_in and database_name:
    # For non-admin users, verify they still exist in the database
    if not is_admin:
        try:
            # Connect as root to check
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database=database_name
            )
            cursor = conn.cursor()
            
            # Extract ID from username
            import re
            numbers = re.findall(r'\d+', username)
            user_id = int(numbers[0]) if numbers else 0
            
            # Check if user exists in this database
            user_exists = False
            
            if is_student:
                cursor.execute("SELECT COUNT(*) FROM students WHERE studid = %s", (user_id,))
                count = cursor.fetchone()[0]
                user_exists = (count > 0)
            elif is_teacher:
                cursor.execute("SELECT COUNT(*) FROM teachers WHERE tid = %s", (user_id,))
                count = cursor.fetchone()[0]
                user_exists = (count > 0)
            
            conn.close()
            
            if not user_exists:
                # Clear database cookie since user no longer exists in this database
                print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
                print()
                # Redirect back to database selection
                print(f"""
                <html>
                <head>
                    <meta http-equiv="refresh" content="0;url=index.py">
                </head>
                <body>
                    <p>Your account no longer exists in this database. Redirecting...</p>
                </body>
                </html>
                """)
                sys.exit()
                
        except mysql.connector.Error:
            # Database might not exist anymore, clear cookie
            print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
            print()
            print(f"""
            <html>
            <head>
                <meta http-equiv="refresh" content="0;url=index.py">
            </head>
            <body>
                <p>Database no longer available. Redirecting...</p>
            </body>
            </html>
            """)
            sys.exit()
    
    # print()
    # if is_admin or is_teacher:
    #     print(f"""
    #     <html>
    #     <head>
    #         <meta http-equiv="refresh" content="0;url=students.py">
    #     </head>
    #     <body>
    #         <p>Redirecting to students page...</p>
    #     </body>
    #     </html>
    #     """)
    # elif is_student:
    #     print(f"""
    #     <html>
    #     <head>
    #         <meta http-equiv="refresh" content="0;url=subjects.py">
    #     </head>
    #     <body>
    #         <p>Redirecting to subjects page...</p>
    #     </body>
    #     </html>
    #     """)
    
        print()
    if is_admin:
        print(f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=students.py">
        </head>
        <body>
            <p>Redirecting to students page...</p>
        </body>
        </html>
        """)
    elif is_teacher:
        print(f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=encodegrades.py">
        </head>
        <body>
            <p>Redirecting to grade encoding page...</p>
        </body>
        </html>
        """)
    elif is_student:
        print(f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=studrec.py">
        </head>
        <body>
            <p>Redirecting to grade sheet...</p>
        </body>
        </html>
        """)
    sys.exit()

# Print header separator for all other cases
print()

# If logged in but hasn't selected a database yet, show database selection
if is_logged_in:
    # Get databases that the user has access to AND still exists in
    formatted_databases = []
    database_error = ""
    
    try:
        # Connect with appropriate credentials
        if is_admin:
            # Root admin can see all databases
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            all_databases_result = cursor.fetchall()
            
            # Filter databases that match the format: string_currentYear_nextYear
            current_year = datetime.datetime.now().year
            next_year = current_year + 1
            year_pattern = f"_{current_year}_{next_year}"
            
            for db_result in all_databases_result:
                db_name = db_result[0]
                # Check if database name matches the format
                if year_pattern in db_name:
                    formatted_databases.append(db_name)
            
            formatted_databases.sort()
            cursor.close()
            conn.close()
            
        elif is_teacher or is_student:
            # For student/teacher users, get databases they have privileges for AND still exist in
            # Extract ID from username
            import re
            numbers = re.findall(r'\d+', username)
            user_id = int(numbers[0]) if numbers else 0
            
            # Extract name from username (remove digits)
            name_only = ''.join([c for c in username if not c.isdigit()])
            mysql_password = f"AdDU{name_only}"
            
            try:
                # First connect as root to check which databases the user exists in
                root_conn = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="root"
                )
                root_cursor = root_conn.cursor()
                
                root_cursor.execute("SHOW DATABASES")
                all_databases = root_cursor.fetchall()
                
                current_year = datetime.datetime.now().year
                next_year = current_year + 1
                year_pattern = f"_{current_year}_{next_year}"
                
                for db_row in all_databases:
                    db_name = db_row[0]
                    
                    if year_pattern in db_name:
                        try:
                            # Check if user exists in this database
                            root_cursor.execute(f"USE `{db_name}`")
                            
                            if is_student:
                                root_cursor.execute("SELECT COUNT(*) FROM students WHERE studid = %s", (user_id,))
                            elif is_teacher:
                                root_cursor.execute("SELECT COUNT(*) FROM teachers WHERE tid = %s", (user_id,))
                            
                            count = root_cursor.fetchone()[0]
                            
                            # Only add database if user exists in it
                            if count > 0:
                                # Also verify MySQL user has access
                                try:
                                    user_conn = mysql.connector.connect(
                                        host="localhost",
                                        user=username,
                                        password=mysql_password,
                                        database=db_name
                                    )
                                    user_conn.close()
                                    formatted_databases.append(db_name)
                                except mysql.connector.Error:
                                    # User doesn't have MySQL privileges
                                    pass
                                    
                        except mysql.connector.Error:
                            # Cannot access this database
                            pass
                
                root_cursor.close()
                root_conn.close()
                
                formatted_databases = list(set(formatted_databases))  # Remove duplicates
                formatted_databases.sort()
                
                if not formatted_databases:
                    database_error = "No databases available for your account. You may have been dropped from all databases. Please contact administrator."
                
            except mysql.connector.Error as e:
                database_error = "Cannot retrieve database list. Please login again."
                formatted_databases = []
        
    except mysql.connector.Error as e:
        formatted_databases = []
        database_error = f"Database error: {str(e)}"

    # Determine role display
    role_display = ""
    if is_admin:
        role_display = "Administrator"
    elif is_teacher:
        role_display = "Teacher"
    elif is_student:
        role_display = "Student"

    # Show database selection page
    print("""
    <html>
    <head>
        <title>STUDENT INFORMATION SYSTEM</title>
        <style>
        @import url('https://fonts.cdnfonts.com/css/hywenhei');
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
            
            .logout-button {
                background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
                color: white;
                cursor: pointer;
                transition: all 0.3s ease;
                border: none;
            }
            
            .logo{
                width: 50px;
                height: 50px;
                margin-right: 15px;
                border-radius: 5px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
            
            .logout-button:hover {
                background: linear-gradient(135deg, #5a6268 0%, #4e555b 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(108, 117, 125, 0.2);
            }
            
            .main-container {
                margin: 30px;
                padding: 20px;
            }
            
            .form-container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                margin-bottom: 30px;
                width: 400px;
            }
            
            .form-container h2 {
                color: #1e3c72;
                margin-top: 0;
                margin-bottom: 25px;
                border-bottom: 2px solid #1e3c72;
                padding-bottom: 10px;
                text-align: left;
            }
            
            .success-message {
                background-color: #d4edda;
                color: #155724;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #c3e6cb;
                text-align: left;
                font-weight: bold;
                width: 400px;
            }
            
            .error-message {
                background-color: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #f5c6cb;
                text-align: left;
                font-weight: bold;
                width: 400px;
            }
            
            .info-message {
                background-color: #d1ecf1;
                color: #0c5460;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #bee5eb;
                text-align: left;
                width: 400px;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: bold;
            }
            
            select {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
            }
            
            select:focus {
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
            }
            
            button {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                font-family: HYWenHei;
                font-size: 14px;
                width: 100%;
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
        </style>
        <script>
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    window.location.href = 'index.py?logout=1';
                }
            }
        </script>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <div class="university-info">
                <img src="sumeru.jpg" alt="Genshin Impact Logo" class="logo">
                    <div class="university-name">SUMERU AKADEMIYA</div>
                    <div class="subtitle">STUDENT INFORMATION SYSTEM</div>
                    <div class="subtitle">User: """ + html.escape(username) + " (" + role_display + """)</div>
                </div>
            </div>
            <button onclick="logout()" class="logout-button">Logout</button>
        </div>
        
        <div class="main-container">
    """)
    
    if login_error:
        print(f"""
            <div class="error-message">
                {html.escape(login_error)}
            </div>
        """)
    elif database_error:
        print(f"""
            <div class="info-message">
                {html.escape(database_error)}
            </div>
        """)
    else:
        print("""
            <div class="success-message">
                Login successful! Welcome.
            </div>
        """)
    
    # # Show role-specific instructions
    # if is_student:
    #     print(f"""
    #         <div class="info-message">
    #             You are logged in as <strong>Student</strong>. You will be redirected to the Subjects page where you can view your enrolled subjects.
    #         </div>
    #     """)
    # elif is_teacher:
    #     print(f"""
    #         <div class="info-message">
    #             You are logged in as <strong>Teacher</strong>. You can:
    #             <ul style="margin: 10px 0; padding-left: 20px;">
    #                 <li>Modify subjects (insert, update, delete)</li>
    #                 <li>Enroll/drop students from subjects you teach</li>
    #                 <li>View all students and subjects</li>
    #             </ul>
    #         </div>
    #     """)
    
        # Show role-specific instructions
    if is_student:
        print(f"""
            <div class="info-message">
                You are logged in as <strong>Student</strong>. You will be redirected to your Grade Sheet page where you can view your grades.
            </div>
        """)
    elif is_teacher:
        print(f"""
            <div class="info-message">
                You are logged in as <strong>Teacher</strong>. You will be redirected to the Grade Encoding page where you can:
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>View subjects assigned to you</li>
                    <li>Encode grades for enrolled students</li>
                    <li>Save grades for all grading periods</li>
                </ul>
            </div>
        """)
    elif is_admin:
        print(f"""
            <div class="info-message">
                You are logged in as <strong>Administrator</strong>. You have full access to all system functions including:
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Create new semester databases</li>
                    <li>Manage all student records</li>
                    <li>Manage all subject records</li>
                    <li>Manage all teacher records</li>
                    <li>Assign teachers to subjects</li>
                </ul>
            </div>
        """)
    
    print(f"""
            <div class="form-container">
                <h2>Select School Year Database</h2>
                <p style="margin-bottom: 20px; color: #666;">
                    School Year: {datetime.datetime.now().year}-{datetime.datetime.now().year + 1}
                </p>
                <form method="POST" action="index.py">
                    <div class="form-group">
                        <label for="database">Available Databases:</label>
                        <select name="database" id="database" required>
                            <option value="">-- Select Database --</option>
    """)
    
    # Populate dropdown with formatted databases
    for db in formatted_databases:
        selected = 'selected' if db == database_name else ''
        print(f"<option value='{html.escape(db)}' {selected}>{html.escape(db)}</option>")
    
    print("""
                        </select>
                    </div>
                    <button type="submit">Continue to System</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """)

elif login_error:
    # Show error message
    print(f"""
<html>
<head>
    <title>STUDENT INFORMATION SYSTEM</title>
    <style>
        * {{
            font-family: HYWenHei, sans-serif !important;
        }}
        
        body {{
            font-family: HYWenHei, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 15px 30px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
        }}
        
        .university-info {{
            display: flex;
            flex-direction: column;
        }}
        
        .university-name {{
            font-size: 28px;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            letter-spacing: 1px;
                line-height: 1.2;
            }}
            
            .subtitle {{
                font-size: 16px;
                opacity: 0.9;
                margin-top: 3px;
            }}
            
            .main-container {{
                margin: 30px;
                padding: 20px;
            }}
            
            .login-container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                width: 400px;
            }}
            
            .login-container h2 {{
                color: #1e3c72;
                margin-top: 0;
                margin-bottom: 25px;
                border-bottom: 2px solid #1e3c72;
                padding-bottom: 10px;
                text-align: left;
            }}
            
            .error-message {{
                background-color: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #f5c6cb;
                text-align: left;
                font-weight: bold;
            }}
            
            .form-group {{
                margin-bottom: 20px;
            }}
            
            label {{
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: bold;
            }}
            
            input[type="text"],
            input[type="password"] {{
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                box-sizing: border-box;
            }}
            
            input:focus {{
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
            }}
            
            button {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                font-family: HYWenHei;
                font-size: 14px;
                width: 100%;
            }}
            
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }}
            
            .welcome-text {{
                text-align: left;
                color: #666;
                margin-top: 20px;
            }}
            
            .login-info {{
                background-color: #f0f8ff;
                border-left: 4px solid #1e3c72;
                padding: 10px;
                margin-top: 15px;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <div class="university-info">
                    <div class="university-name">SUMERU AKADEMIYA</div>
                    <div class="subtitle">STUDENT INFORMATION SYSTEM</div>
                </div>
            </div>
        </div>
        
        <div class="main-container">
            <div class="login-container">
                <h2>Login</h2>
                <div class="error-message">
                    {html.escape(login_error)}
                </div>
                <form method="POST" action="index.py">
                    <input type="hidden" name="login_attempt" value="1">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" name="username" id="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" name="password" id="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
                <div class="welcome-text">
                    <p>Welcome to Student Information System</p>
                    <p>Please login to continue.</p>
                    <div class="login-info">
                        <strong>Login Options:</strong><br>
                        • Administrator: <code>root</code> / <code>root</code><br>
                        • Teachers: Username = ID+Name (e.g., 3000johndoe)<br>
                        • Students: Username = ID+Name (e.g., 1000janedoe)<br>
                        • Password = <code>AdDU</code> + Name only (e.g., AdDUjohndoe)<br>
                        <strong>Role Permissions:</strong><br>
                        • Admin: Full access to all functions<br>
                        • Teachers: Can modify subjects and enroll/drop students in subjects they teach<br>
                        • Students: Read-only access to enrolled subjects
                    </div>
                </div>
            </div>
        </div>
    </body>
</html>
""")

else:
    # Show initial login form
    print("""
    <html>
    <head>
        <title>STUDENT INFORMATION SYSTEM</title>
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
            }
            
            .header-left {
                display: flex;
                align-items: center;
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
            
            .main-container {
                margin: 30px;
                padding: 20px;
            }
            
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
                width: 400px;
            }
            
            .login-container h2 {
                color: #1e3c72;
                margin-top: 0;
                margin-bottom: 25px;
                border-bottom: 2px solid #1e3c72;
                padding-bottom: 10px;
                text-align: left;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: bold;
            }
            
            input[type="text"],
            input[type="password"] {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                box-sizing: border-box;
            }
            
            input:focus {
                outline: none;
                border-color: #2a5298;
                box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
            }
            
            button {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                font-family: HYWenHei;
                font-size: 14px;
                width: 100%;
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
            
            .welcome-text {
                text-align: left;
                color: #666;
                margin-top: 20px;
            }
            
            .login-info {
                background-color: #f0f8ff;
                border-left: 4px solid #1e3c72;
                padding: 10px;
                margin-top: 15px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <div class="university-info">
                    <div class="university-name">SUMERU AKADEMIYA</div>
                    <div class="subtitle">STUDENT INFORMATION SYSTEM</div>
                </div>
            </div>
        </div>
        
        <div class="main-container">
            <div class="login-container">
                <h2>Login</h2>
                <form method="POST" action="index.py">
                    <input type="hidden" name="login_attempt" value="1">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" name="username" id="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" name="password" id="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
                <div class="welcome-text">
                    <p>Welcome to Student Information System</p>
                    <p>Please login to continue.</p>
                    <div class="login-info">
                        <strong>Login Options:</strong><br>
                        • Administrator: <code>root</code> / <code>root</code><br>
                        • Teachers: Username = ID+Name (e.g., 3000johndoe)<br>
                        • Students: Username = ID+Name (e.g., 1000janedoe)<br>
                        • Password = <code>AdDU</code> + Name only (e.g., AdDUjohndoe)<br>
                        <strong>Role Permissions:</strong><br>
                        • Admin: Full access to all functions<br>
                        • Teachers: Can modify subjects and enroll/drop students in subjects they teach<br>
                        • Students: Read-only access to enrolled subjects
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)