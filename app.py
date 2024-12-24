import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # สำหรับการใช้งาน flash message

# กำหนดที่เก็บไฟล์ที่อัปโหลด
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'db'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ฟังก์ชันตรวจสอบนามสกุลไฟล์
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ฟังก์ชันเชื่อมต่อกับฐานข้อมูลของระบบ
def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    logging.debug(f"Database path: {db_path}")
    logging.debug(f"Database exists: {os.path.exists(db_path)}")
    if not os.path.exists(db_path):
        logging.debug(f"Database permissions: {oct(os.stat(db_path).st_mode)}")
    return sqlite3.connect(db_path)

# สร้างตารางสมาชิกในฐานข้อมูล (หากยังไม่มี)
def create_users_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """หน้าแรกที่แสดงรายการไฟล์ที่อัปโหลด"""
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('index.html', files=files)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """หน้าสมัครสมาชิก"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username and password:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Please provide both username and password.', 'danger')

    return render_template('register.html')

# หน้าที่แสดงข้อมูลจากตาราง blocks
@app.route('/view_db', methods=['POST'])
def view_db():
    file_name = request.form.get('file_name')  # รับชื่อไฟล์จากฟอร์ม
    db_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    
    # เชื่อมต่อกับฐานข้อมูล SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ดึงข้อมูลจากตาราง blocks
    cursor.execute("SELECT * FROM blocks")
    rows = cursor.fetchall()  # ดึงข้อมูลทั้งหมด
    
    conn.close()  # ปิดการเชื่อมต่อ
    
    return render_template('view_db.html', rows=rows, file_name=file_name)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """หน้าล็อกอิน"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:  # ตรวจสอบว่า user พบหรือไม่
            # user เป็น tuple, ดังนั้นต้องใช้ดัชนีเพื่อเข้าถึงค่า
            return redirect(url_for('file_upload', user_id=user[0]))  # ใช้ user[0] เพื่อเข้าถึง user ID

        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')



@app.route('/upload/<user_id>', methods=['GET', 'POST'])
def file_upload(user_id):
    """รับไฟล์และบันทึก"""
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    if isinstance(user, tuple):  # ตรวจสอบว่าค่าคือ tuple
        username = user[0]  # ดึงข้อมูลจาก tuple
    else:
        username = user['username']  # หรือดึงข้อมูลจาก dictionary

    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            upload_date = datetime.now().strftime('%Y%m%d')
            filename = secure_filename(f"{user_id}-{username}-Capsule-{upload_date}.db")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash('File uploaded successfully.', 'success')
            return redirect(url_for('index'))

    return render_template('upload.html', user_id=user_id, username=username)


@app.route('/file/<filename>')
def view_file(filename):
    """เปิดดูไฟล์ในระบบและแสดงตาราง blocks"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        cursor.execute('SELECT index, message, timestamp FROM blocks')
        rows = cursor.fetchall()
        conn.close()
        return render_template('view_file.html', filename=filename, rows=rows)
    except sqlite3.Error as e:
        return f"An error occurred while opening the file: {e}", 500


# ดึงรายชื่อไฟล์รูปจากโฟลเดอร์ static/mn
@app.route('/mn')
def mn():
    # กำหนดพาธไปยังโฟลเดอร์ที่เก็บรูป
    image_folder = 'static/mn'
    
    # อ่านชื่อไฟล์ทั้งหมดในโฟลเดอร์
    image_files = [f"{i:02d}.png" for i in range(1, 13)]  # 01.png, 02.png, ..., 12.png
    
    # คำอธิบายสำหรับแต่ละรูป
    descriptions = [f"คำอธิบายสำหรับรูปที่ {i}" for i in range(1, 13)]
    
    # ส่งข้อมูลให้ HTML template
    return render_template('mn.html')  # ให้ไปที่ไฟล์ mn.html

if __name__ == "__main__":
    # สร้างตาราง users หากยังไม่มี
    create_users_table()

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
app.run(debug=True, host="0.0.0.0", port=3000)
   
