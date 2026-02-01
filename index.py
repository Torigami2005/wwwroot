#!/usr/bin/env python3
import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()

# Get login form values
username = form.getvalue("username", "")
password = form.getvalue("password", "")
database_name = form.getvalue("database", "")

# Check if this is a login attempt
login_attempt = form.getvalue("login_attempt", "")

# Check admin credentials
is_logged_in = False
is_admin = False
login_error = ""

if login_attempt == "1" and username and password:
    if username == "root" and password == "root":
        is_admin = True
        is_logged_in = True
    else:
        login_error = "Invalid username or password"

# Check if we should redirect to students.py
if is_logged_in and is_admin and database_name:
    print(f"""
    <script>
        window.location.href = 'students.py?database={html.escape(database_name)}';
    </script>
    """)
    exit()

# If logged in as admin, show database selection
if is_logged_in and is_admin:
    # Get all databases from MySQL using mysql.connector
    all_databases = []
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        
        databases = cursor.fetchall()
        for db in databases:
            all_databases.append(db[0])
        
        all_databases.sort()
        
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        all_databases = ['information_schema', 'mysql', 'performance_schema', 'sys', 'enrollmentsystem']


print("""
<html>
<head>
    <title>STUDENT INFORMATION SYSTEM</title>
    <style>
        * {
            font-family: Arial, sans-serif;
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        
        .login-container {
            width: 400px;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            color: #1e3c72;
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header h2 {
            color: #2a5298;
            font-size: 22px;
            margin-top: 0;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #2a5298;
            box-shadow: 0 0 0 2px rgba(42, 82, 152, 0.2);
        }
        
        .error-message {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }
        
        .success-message {
            background-color: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }
        
        .database-selection {
            margin-bottom: 20px;
            display: none;
        }
        
        .database-selection label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        
        .database-selection select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            background: white;
        }
        
        .login-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .login-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .continue-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .continue-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(40, 167, 69, 0.2);
        }
        
        .welcome-message {
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-style: italic;
        }
        
        .school-year-table {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #dee2e6;
            max-height: 200px;
            overflow-y: auto;
            display: none;
        }
        
        .school-year-table h4 {
            color: #1e3c72;
            margin-top: 0;
            margin-bottom: 10px;
        }
        
        .school-year-table table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        .school-year-table th {
            background-color: #e9ecef;
            padding: 8px;
            text-align: left;
            border: 1px solid #dee2e6;
            position: sticky;
            top: 0;
        }
        
        .school-year-table td {
            padding: 8px;
            border: 1px solid #dee2e6;
        }
        
        .database-info {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            text-align: center;
        }
        
        .back-button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
            display: none;
        }
        
        .back-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(108, 117, 125, 0.2);
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="header">
            <h1>STUDENT INFORMATION SYSTEM</h1>
            <h2>UNIVERSITY NAME</h2>
        </div>
        
        <h3>Login</h3>
""")

if is_logged_in and is_admin:
    # Show database selection after successful login
    print(f"""
        <div class="success-message">
            Login successful! Welcome, Administrator.
        </div>
        
        <form method="POST" action="index.py">
            <input type="hidden" name="username" value="{html.escape(username)}">
            <input type="hidden" name="password" value="{html.escape(password)}">
            <input type="hidden" name="login_attempt" value="1">
            
            <div class="database-selection" style="display: block;">
                <label for="database">Select Database:</label>
                <select id="database" name="database" required>
                    <option value="">-- Select a database --</option>
    """)
    
    # Populate database dropdown with ALL databases
    for db in all_databases:
        selected = 'selected' if db == database_name else ''
        print(f'<option value="{html.escape(db)}" {selected}>{html.escape(db)}</option>')
    
    print("""
                </select>
            </div>
            
            <button type="submit" class="continue-button">Continue to System</button>
        </form>
        
        <div class="school-year-table" style="display: block;">
            <h4>Available Databases:</h4>
            <table>
                <tr>
                    <th>Database Name</th>
                </tr>
    """)
    
    # Display ALL databases in a table
    if all_databases:
        for db in all_databases:
            print(f'<tr><td>{html.escape(db)}</td></tr>')
    else:
        print('<tr><td>No databases found</td></tr>')
    
    print(f"""
            </table>
            <div class="database-info">
                Total: {len(all_databases)} database(s)
            </div>
        </div>
        
        <form method="POST" action="index.py">
            <button type="submit" class="back-button" style="display: block;">Back to Login</button>
        </form>
    """)
    
elif login_error:
    # Show error message
    print(f"""
        <div class="error-message">
            {login_error}
        </div>
        
        <form method="POST" action="index.py">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" placeholder="Username" value="{html.escape(username)}" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" placeholder="Password" value="" required>
            </div>
            
            <input type="hidden" name="login_attempt" value="1">
            
            <button type="submit" class="login-button">Login</button>
        </form>
        
        <div class="welcome-message">
            Welcome to Student System<br>
            Please login to continue.
        </div>
    """)
else:
    # Show initial login form
    print("""
        <form method="POST" action="index.py">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" placeholder="Username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" placeholder="Password" required>
            </div>
            
            <input type="hidden" name="login_attempt" value="1">
            
            <button type="submit" class="login-button">Login</button>
        </form>
        
        <div class="welcome-message">
            Welcome to Student System<br>
            Please login to continue.
        </div>
    """)

print("""
    </div>
</body>
</html>
""")