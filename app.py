import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart_network_production_super_secret_2026')
DB_PATH = 'production_network.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # جدول کاربران و مدیران سامانه
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin'
        )
    ''')

    # جدول کارگاه‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            field TEXT NOT NULL,
            province TEXT,
            phone TEXT,
            capacity TEXT,
            issue TEXT,
            issue_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ایجاد مدیر پیش‌فرض (admin / admin123)
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'مدیر ارشد سامانه')
        )

    # افزودن داده‌های پیش‌فرض
    cursor.execute('SELECT COUNT(*) as count FROM workshops')
    if cursor.fetchone()['count'] == 0:
        cursor.executemany('''
            INSERT INTO workshops (name, owner, field, province, phone, capacity, issue, issue_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            ('کارگاه گلیم‌بافی عشایری تار و پود', 'فاطمه احمدی', 'گلیم و فرش دست‌باف', 'فارس - شیراز', '09171112233', '۱۵ تخته در ماه', 'تأمین رنگرزی گیاهی سنتی استاندارد برای صادرات', 'in_progress'),
            ('سفالگری و مینای خاک و نقش', 'علی محمدی', 'سفال و سرامیک', 'همدان - لالجین', '09183334455', '۲۰۰ ست در ماه', 'بسته‌بندی ایمن ضدضربه جهت ارسال پستی بین‌المللی', 'pending'),
            ('کارگاه نقره‌سازی رضوی', 'رضا اکبری', 'زیورآلات سنتی', 'خراسان رضوی - مشهد', '09155556677', '۸۰ قطعه در ماه', 'تأمین شمش نقره با نرخ مصوب و استاندارد عیار', 'resolved')
        ])

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    workshops = cursor.execute('SELECT * FROM workshops ORDER BY id DESC').fetchall()
    total_workshops = len(workshops)
    active_issues = sum(1 for w in workshops if w['issue_status'] != 'resolved')
    categories = len(set(w['field'] for w in workshops if w['field']))
    conn.close()

    return render_template(
        'index.html',
        workshops=workshops,
        total_workshops=total_workshops,
        active_issues=active_issues,
        active_categories=categories if categories > 0 else 3,
        is_admin=session.get('user_id') is not None
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('با موفقیت وارد شدید! دسترسی مدیریت فعال شد.', 'success')
            return redirect(url_for('home'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است (اطلاعات ورود: admin / admin123)', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('از حساب مدیریت خارج شدید.', 'info')
    return redirect(url_for('home'))

@app.route('/register-workshop', methods=['GET', 'POST'])
def register_workshop():
    if request.method == 'POST':
        name = request.form.get('name')
        owner = request.form.get('owner')
        field = request.form.get('field')
        province = request.form.get('province')
        phone = request.form.get('phone')
        capacity = request.form.get('capacity')
        issue = request.form.get('issue')

        if name and owner:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO workshops (name, owner, field, province, phone, capacity, issue, issue_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (name, owner, field, province, phone, capacity, issue))
            conn.commit()
            conn.close()
            flash('کارگاه با موفقیت ثبت شد.', 'success')
            return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/update-issue-status/<int:workshop_id>', methods=['POST'])
def update_issue_status(workshop_id):
    if not session.get('user_id'):
        flash('برای ویرایش وضعیت باید وارد سیستم شوید.', 'danger')
        return redirect(url_for('home'))

    new_status = request.form.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE workshops SET issue_status = ? WHERE id = ?', (new_status, workshop_id))
    conn.commit()
    conn.close()
    flash('وضعیت مانع با موفقیت به‌روزرسانی شد.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
