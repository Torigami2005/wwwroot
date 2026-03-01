#!/usr/bin/env python3
import os
import sys
import json
import warnings

# ---- IMPORTANT: SILENCE ALL OUTPUT BEFORE HEADERS ----
# Redirect stdout/stderr during imports/model load so IIS doesn't see noise before headers.
class _NullWriter:
    def write(self, *_args, **_kwargs): pass
    def flush(self): pass

_ORIG_STDOUT = sys.stdout
_ORIG_STDERR = sys.stderr
sys.stdout = _NullWriter()
sys.stderr = _NullWriter()

# Silence warnings
warnings.filterwarnings("ignore")

# HF cache in a writable folder
CACHE_DIR = r"C:\inetpub\wwwroot\hf_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

os.environ["HF_HOME"] = CACHE_DIR
os.environ["HF_HUB_CACHE"] = os.path.join(CACHE_DIR, "hub")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(CACHE_DIR, "transformers")
os.environ["XDG_CACHE_HOME"] = CACHE_DIR
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"  # hide symlink warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"  # reduce transformers logs
os.environ["TRANSFORMERS_VERBOSITY"] = "error"  # avoid noisy parallel warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # hide tqdm progress bars
os.environ["TQDM_DISABLE"] = "1"

# Now import CGI libs (deprecated in 3.13, but ok in 3.12)
import cgi

from transformers import pipeline

MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
sentiment_analyzer = pipeline("sentiment-analysis", model=MODEL_NAME)

# Restore stdout/stderr for actual response output
sys.stdout = _ORIG_STDOUT
sys.stderr = _ORIG_STDERR

import mysql.connector
import html
import http.cookies
import re

print("Content-Type: text/html")

form = cgi.FieldStorage()

# Handle logout
logout_action = form.getvalue("logout_action", "")
if logout_action == "1":
    print("Set-Cookie: session_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; HttpOnly")
    print("Set-Cookie: username=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: database=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print("Set-Cookie: user_role=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/")
    print()
    print("<script>window.location.href = 'index.py';</script>")
    sys.exit()

# Load cookies
cookie_string = os.environ.get('HTTP_COOKIE', '')
cookies = http.cookies.SimpleCookie()
if cookie_string:
    cookies.load(cookie_string)

# Session check
is_logged_in = False
username = ""
database_name = ""
user_role = ""
is_admin = False
is_teacher = False

if 'session_id' in cookies and 'username' in cookies:
    session_id = cookies['session_id'].value
    username = cookies['username'].value
    database_name = cookies['database'].value if 'database' in cookies else ""
    user_role = cookies['user_role'].value if 'user_role' in cookies else ""
    
    if session_id:
        is_logged_in = True
        is_admin = (user_role == "admin")
        is_teacher = (user_role == "teacher")

print()

if not is_logged_in:
    print("<script>alert('Please login first');window.location.href = 'index.py';</script>")
    sys.exit()

if not database_name:
    print("<script>alert('Please select a database first');window.location.href = 'index.py';</script>")
    sys.exit()

# Only teachers and admins can access
if not (is_admin or is_teacher):
    print("<script>alert('Access Denied: This page is for teachers only');window.location.href = 'studrec.py';</script>")
    sys.exit()

# Get subject ID from URL
subjid = form.getvalue("subjid", "")

if not subjid:
    print("<script>alert('No subject selected');window.location.href = 'encodegrades.py';</script>")
    sys.exit()

# Get filter values
filter_sentiment = form.getvalue("filter_sentiment", "All")
filter_category = form.getvalue("filter_category", "All")

# AI-powered sentiment analysis function
def analyze_sentiment_ai(text):
    """Use Hugging Face model for sentiment analysis"""
    if not text or len(text.strip()) == 0:
        return "NEUTRAL", 0.5
    
    try:
        # Limit text length for API
        text = text[:2000]
        result = sentiment_analyzer(text)[0]
        
        # result = {'label': 'POSITIVE'/'NEGATIVE', 'score': 0.999}
        label = result['label']
        confidence = float(result['score'])
        
        # Convert to our format
        if label == "POSITIVE":
            sentiment = "POSITIVE"
        elif label == "NEGATIVE":
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"
        
        return sentiment, confidence
    except Exception as e:
        # Fallback to neutral if AI fails
        return "NEUTRAL", 0.5

# Extract categories from evaluation text
def extract_categories(text):
    """Extract categories based on keywords"""
    if not text:
        return []
    
    text_lower = text.lower()
    categories = []
    
    if any(word in text_lower for word in ['laboratory', 'lab', 'equipment', 'space']):
        categories.append('Laboratory')
    if any(word in text_lower for word in ['facility', 'facilities', 'building', 'room', 'classroom']):
        categories.append('Facility')
    if any(word in text_lower for word in ['instruction', 'teaching', 'instructor', 'teacher', 'professor', 'lecture']):
        categories.append('Instruction')
    if any(word in text_lower for word in ['curriculum', 'syllabus', 'course', 'content', 'material']):
        categories.append('Curriculum')
    if any(word in text_lower for word in ['assessment', 'exam', 'test', 'quiz', 'grading', 'evaluation']):
        categories.append('Assessment')
    if any(word in text_lower for word in ['management', 'organization', 'planning', 'schedule', 'time']):
        categories.append('Management')
    
    return categories

# Extract clauses from evaluation text
def extract_clauses(text):
    """Split evaluation text into individual clauses/sentences"""
    if not text:
        return []
    
    # Split by common sentence delimiters
    clauses = re.split(r'[.!?;]\s+', text)
    # Filter out empty clauses and strip whitespace
    clauses = [c.strip() for c in clauses if c.strip() and len(c.strip()) > 10]
    return clauses

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database=database_name
    )
    cursor = conn.cursor(buffered=True)
    
    # Get subject information
    cursor.execute("""
        SELECT subjid, subjcode, subjdesc
        FROM subjects
        WHERE subjid = %s
    """, (subjid,))
    subject_info = cursor.fetchone()
    
    if not subject_info:
        print("<script>alert('Subject not found');window.location.href = 'encodegrades.py';</script>")
        sys.exit()
    
    subj_id, subj_code, subj_desc = subject_info
    
    # Get all evaluations for this subject
    cursor.execute("""
        SELECT e.studid, e.subjid, e.evaluation_comment, s.studname
        FROM evaluations e
        INNER JOIN students s ON e.studid = s.studid
        WHERE e.subjid = %s
        ORDER BY e.eval_date DESC
    """, (subjid,))
    evaluations = cursor.fetchall()
    
    # Process evaluations - break into clauses and analyze with AI
    evaluation_data = []
    all_categories = set()
    
    for eval_row in evaluations:
        studid, subjid_eval, comment, studname = eval_row
        
        if not comment:
            continue
        
        # Extract clauses from the evaluation
        clauses = extract_clauses(comment)
        
        for clause in clauses:
            # AI sentiment analysis
            sentiment, confidence = analyze_sentiment_ai(clause)
            
            # Extract categories
            categories = extract_categories(clause)
            
            # Add to all categories set
            for cat in categories:
                all_categories.add(cat)
            
            evaluation_data.append({
                'studid': studid,
                'subjid': subjid_eval,
                'clause': clause,
                'sentiment': sentiment,
                'confidence': confidence,
                'categories': categories,
                'full_comment': comment
            })
    
    # Filter evaluations based on selected filters
    filtered_data = evaluation_data
    
    if filter_sentiment != "All":
        filtered_data = [e for e in filtered_data if e['sentiment'] == filter_sentiment.upper()]
    
    if filter_category != "All":
        filtered_data = [e for e in filtered_data if filter_category in e['categories']]
    
    # Sort categories alphabetically
    all_categories = sorted(list(all_categories))
    
    cursor.close()
    conn.close()
    
    # HTML output
    print(f"""
    <html>
    <head>
        <title>Student Evaluation - AI Sentiment Analysis</title>
        <style>
            @import url('https://fonts.cdnfonts.com/css/hywenhei');
            * {{ font-family: HYWenHei, sans-serif !important; }}
            body {{
                font-family: HYWenHei, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #4267B2 0%, #5578C4 100%);
                color: white;
                padding: 20px 40px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: center;
            }}
            .logo {{
                width: 50px;
                height: 50px;
                background: white;
                margin-right: 20px;
                border-radius: 5px;
            }}
            .header-text {{
                flex: 1;
            }}
            .header-title {{
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }}
            .header-subtitle {{
                font-size: 14px;
                opacity: 0.9;
                margin-top: 5px;
            }}
            .container {{
                max-width: 1400px;
                margin: 30px auto;
                padding: 0 20px;
            }}
            .page-title {{
                font-size: 28px;
                font-weight: bold;
                margin: 30px 0 10px 0;
                color: #333;
            }}
            .subject-filter {{
                color: #666;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            .ai-badge {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                margin-left: 10px;
            }}
            .filter-section {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
                display: flex;
                gap: 20px;
                align-items: center;
            }}
            .filter-group {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .filter-group label {{
                font-weight: bold;
                color: #333;
            }}
            .filter-group select {{
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                min-width: 150px;
            }}
            .apply-button {{
                background: linear-gradient(135deg, #4267B2 0%, #5578C4 100%);
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            }}
            .apply-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            table {{
                width: 100%;
                background: white;
                border-collapse: collapse;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                overflow: hidden;
            }}
            th {{
                background: linear-gradient(135deg, #4267B2 0%, #5578C4 100%);
                color: white;
                padding: 12px;
                text-align: center;
                font-weight: bold;
                font-size: 14px;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #e0e0e0;
                text-align: center;
                font-size: 14px;
            }}
            tr:hover {{
                background-color: #f9f9f9;
            }}
            .sentiment-badge {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            .sentiment-positive {{
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .sentiment-negative {{
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            .sentiment-neutral {{
                background-color: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }}
            .confidence-score {{
                font-size: 10px;
                color: #666;
                display: block;
                margin-top: 3px;
            }}
            .category-tag {{
                display: inline-block;
                padding: 3px 8px;
                margin: 2px;
                background-color: #e9ecef;
                border-radius: 5px;
                font-size: 11px;
                color: #495057;
            }}
            .clause-text {{
                text-align: left;
                max-width: 300px;
            }}
            .full-evaluation {{
                text-align: left;
                max-width: 400px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo"></div>
            <div class="header-text">
                <div class="header-title">STUDENT INFORMATION SYSTEM</div>
                <div class="header-subtitle">UNIVERSITY NAME</div>
            </div>
        </div>
        
        <div class="container">
            <h1 class="page-title">
                Student Evaluation
                <span class="ai-badge">AI-POWERED</span>
            </h1>
            <div class="subject-filter">Subject filter: {subjid}</div>
            
            <form method="GET" action="sentiment.py">
                <input type="hidden" name="subjid" value="{subjid}">
                <div class="filter-section">
                    <div class="filter-group">
                        <label for="filter_sentiment">Filter by Sentiment:</label>
                        <select name="filter_sentiment" id="filter_sentiment">
                            <option value="All" {"selected" if filter_sentiment == "All" else ""}>All</option>
                            <option value="Positive" {"selected" if filter_sentiment == "Positive" else ""}>Positive</option>
                            <option value="Negative" {"selected" if filter_sentiment == "Negative" else ""}>Negative</option>
                            <option value="Neutral" {"selected" if filter_sentiment == "Neutral" else ""}>Neutral</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label for="filter_category">Filter by Category:</label>
                        <select name="filter_category" id="filter_category">
                            <option value="All" {"selected" if filter_category == "All" else ""}>All</option>
    """)
    
    for category in all_categories:
        selected = "selected" if filter_category == category else ""
        print(f'<option value="{category}" {selected}>{category}</option>')
    
    print(f"""
                        </select>
                    </div>
                    
                    <button type="submit" class="apply-button">Apply</button>
                </div>
            </form>
            
            <table>
                <thead>
                    <tr>
                        <th>StudID</th>
                        <th>SubjID</th>
                        <th>Clause</th>
                        <th>Sentiment (AI)</th>
                        <th>Category</th>
                        <th>Full Evaluation</th>
                    </tr>
                </thead>
                <tbody>
    """)
    
    if not filtered_data:
        print("<tr><td colspan='6' style='padding: 30px; color: #666;'>No evaluations found for this subject</td></tr>")
    else:
        for eval_item in filtered_data:
            sentiment_class = f"sentiment-{eval_item['sentiment'].lower()}"
            confidence_pct = int(eval_item['confidence'] * 100)
            
            categories_html = ""
            if eval_item['categories']:
                for cat in eval_item['categories']:
                    categories_html += f'<span class="category-tag">{cat}</span>'
            else:
                categories_html = '<span style="color: #999;">None</span>'
            
            print(f"""
                <tr>
                    <td>{eval_item['studid']}</td>
                    <td>{eval_item['subjid']}</td>
                    <td class="clause-text">{html.escape(eval_item['clause'])}</td>
                    <td>
                        <span class="sentiment-badge {sentiment_class}">
                            {eval_item['sentiment']}
                            <span class="confidence-score">{confidence_pct}% confident</span>
                        </span>
                    </td>
                    <td>{categories_html}</td>
                    <td class="full-evaluation">{html.escape(eval_item['full_comment'])}</td>
                </tr>
            """)
    
    print("""
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """)

except Exception as e:
    print(f"<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>")