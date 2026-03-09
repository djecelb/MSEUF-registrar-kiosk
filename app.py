from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import datetime
import qrcode
import io
import base64
import os

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), 'database.db')

TABLE_SQL = '''
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        queue_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        student_number TEXT NOT NULL,
        department TEXT NOT NULL,
        program TEXT NOT NULL,
        documents_requested TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'Waiting for Payment',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # Always ensure the table exists (handles deleted DB while server is running)
    conn.execute(TABLE_SQL)
    conn.commit()
    return conn

def generate_queue_number(conn):
    """Generate the next queue number using an existing connection."""
    # Compare dates using SQLite's 'localtime' modifier on both sides
    # to avoid UTC vs local time mismatch (created_at is stored as UTC)
    row = conn.execute(
        "SELECT MAX(CAST(REPLACE(queue_number, 'SR', '') AS INTEGER)) as max_num "
        "FROM requests WHERE date(created_at, 'localtime') = date('now', 'localtime')"
    ).fetchone()
    last_num = row['max_num'] if row['max_num'] else 0
    return f"SR{last_num + 1:05d}"

# Initialize on startup
get_db_connection().close()

@app.route('/')
def index():
    return redirect(url_for('kiosk'))

@app.route('/kiosk')
def kiosk():
    return render_template('kiosk.html')

@app.route('/request', methods=['GET', 'POST'])
def request_form():
    if request.method == 'POST':
        full_name = request.form['full_name']
        student_number = request.form['student_number']
        department = request.form['department']
        program = request.form['program']
        
        documents = []
        total_amount = 0
        
        # Prices
        prices = {
            'Copy_of_Grades': 0,
            'Transcript_of_Records': 90,
            'Honorable_Dismissal': 0,
            'Certification': 130, 
            'Scholarship_(Off-Campus)': 0,
            'Request_for_F137A_/_SF10': 0
        }
        
        for doc in prices.keys():
            qty_key = f"qty_{doc}"
            qty_str = request.form.get(qty_key, '0')
            if qty_str and int(qty_str) > 0:
                qty = int(qty_str)
                name = doc.replace('_', ' ')
                documents.append(f"{qty}x {name}")
                total_amount += qty * prices[doc]
                
        stamp_qty_str = request.form.get('stamp_qty', '0')
        if stamp_qty_str and int(stamp_qty_str) > 0:
            stamp_qty = int(stamp_qty_str)
            documents.append(f"{stamp_qty}x Documentary Stamp")
            total_amount += stamp_qty * 50
            
        docs_joined = ", ".join(documents)
        
        conn = get_db_connection()
        queue_number = None
        # Retry loop to handle any UNIQUE constraint race conditions
        for _ in range(5):
            queue_number = generate_queue_number(conn)
            try:
                conn.execute(
                    'INSERT INTO requests (queue_number, full_name, student_number, department, program, documents_requested, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (queue_number, full_name, student_number, department, program, docs_joined, total_amount)
                )
                conn.commit()
                break
            except sqlite3.IntegrityError:
                # Queue number conflict — retry with fresh number
                continue
        conn.close()
        
        return redirect(url_for('result', queue_number=queue_number))
        
    return render_template('request.html')

@app.route('/result/<queue_number>')
def result(queue_number):
    conn = get_db_connection()
    req = conn.execute('SELECT * FROM requests WHERE queue_number = ?', (queue_number,)).fetchone()
    conn.close()
    
    if not req:
        return "Not found", 404
        
    qr_url = url_for('queue_status', queue_number=queue_number, _external=True)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    qr_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
    
    return render_template('result.html', req=req, qr_base64=qr_base64)

@app.route('/queue/<queue_number>')
def queue_status(queue_number):
    conn = get_db_connection()
    req = conn.execute('SELECT * FROM requests WHERE queue_number = ?', (queue_number,)).fetchone()
    conn.close()
    
    if not req:
        return "Not found", 404
        
    return render_template('queue_status.html', req=req)

@app.route('/cashier')
def cashier():
    conn = get_db_connection()
    requests = conn.execute('SELECT * FROM requests ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('cashier.html', requests=requests)

@app.route('/cashier/pay/<queue_number>', methods=['POST'])
def cashier_pay(queue_number):
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status = 'Paid' WHERE queue_number = ?", (queue_number,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/window21')
def window21():
    conn = get_db_connection()
    waiting = conn.execute("SELECT * FROM requests WHERE status = 'Paid' ORDER BY id ASC").fetchall()
    serving = conn.execute("SELECT * FROM requests WHERE status = 'Now Serving' ORDER BY id ASC").fetchall()
    conn.close()
    return render_template('window21.html', waiting=waiting, serving=serving)

@app.route('/window21/serve/<queue_number>', methods=['POST'])
def window21_serve(queue_number):
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status = 'Now Serving' WHERE queue_number = ?", (queue_number,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/window21/complete/<queue_number>', methods=['POST'])
def window21_complete(queue_number):
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status = 'Completed' WHERE queue_number = ?", (queue_number,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/queue-monitor')
def queue_monitor():
    conn = get_db_connection()
    serving = conn.execute("SELECT * FROM requests WHERE status = 'Now Serving' ORDER BY id ASC LIMIT 5").fetchall()
    waiting = conn.execute("SELECT * FROM requests WHERE status = 'Paid' ORDER BY id ASC LIMIT 10").fetchall()
    conn.close()
    return render_template('monitor.html', serving=serving, waiting=waiting)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
