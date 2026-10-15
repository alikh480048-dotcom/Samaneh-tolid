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

    # جدول کارگاه‌ها و واحدهای تولیدی با موانع
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

    # جدول محصولات و دست‌سازه‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id INTEGER,
            title TEXT NOT NULL,
            category TEXT,
            city TEXT,
            capacity TEXT,
            icon TEXT DEFAULT 'fa-gem',
            FOREIGN KEY(workshop_id) REFERENCES workshops(id)
        )
    ''')

    # ایجاد کاربر پیش‌فرض مدیر سامانه (admin / admin123)
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'مدیر ارشد سامانه')
        )

    # افزودن داده‌های پایه در صورت خالی بودن
    cursor.execute('SELECT COUNT(*) as count FROM workshops')
    if cursor.fetchone()['count'] == 0:
        cursor.executemany('''
            INSERT INTO workshops (name, owner, field, province, phone, capacity, issue, issue_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            ('کارگاه گلیم‌بافی عشایری تار و پود', 'فاطمه احمدی', 'گلیم و فرش دست‌باف', 'فارس - شیراز', '09171112233', '۱۵ تخته در ماه', 'تأمین رنگرزی گیاهی سنتی استاندارد برای صادرات', 'in_progress'),
            ('سفالگری و مینای خاک و نقش', 'علی محمدی', 'سفال و سرامیک', 'همدان - لالجین', '09183334455', '۲۰۰ ست در ماه', 'بسته‌بندی ایمن ضدضربه جهت ارسال پستی بین‌المللی', 'pending'),
            ('کارگاه نقره‌سازی و نگین‌تراشی رضوی', 'رضا اکبری', 'زیورآلات سنتی', 'خراسان رضوی - مشهد', '09155556677', '۸۰ قطعه در ماه', 'تأمین شمش نقره با نرخ مصوب و استاندارد عیار', 'resolved'),
            ('سراجی و چرم دست‌دوز کهن', 'مریم حسینی', 'صنایع چرم', 'آذربایجان شرقی - تبریز', '09148889900', '۴۵ عدد در ماه', 'دسترسی به یراق‌آلات باکیفیت و بازاریابی نمایشگاهی', 'pending')
        ])

    cursor.execute('SELECT COUNT(*) as count FROM products')
    if cursor.fetchone()['count'] == 0:
        cursor.executemany('''
            INSERT INTO products (title, category, city, capacity, icon)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            ('گلیم عشایری پشمی قشقایی', 'گلیم و فرش', 'شیراز', '۱۵ تخته/ماه', 'fa-rug'),
            ('ظروف سرامیکی میناکاری برجسته', 'سفال و سرامیک', 'لالجین', '۲۰۰ ست/ماه', 'fa-jar'),
            ('زیورآلات نقره سنتی فیروزه‌کوب', 'زیورآلات سنتی', 'مشهد', '۸۰ قطعه/ماه', 'fa-ring'),
            ('کیف اداری چرم طبیعی دست‌دوز', 'صنایع چرم', 'تبریز', '۴۵ عدد/ماه', 'fa-bag-shopping')
        ])

    conn.commit()
    conn.close()

# اجرای راه‌اندازی دیتابیس در شروع برنامه
init_db()

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    
    workshops = cursor.execute('SELECT * FROM workshops ORDER BY id DESC').fetchall()
    products = cursor.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    
    total_workshops = len(workshops)
    active_issues = sum(1 for w in workshops if w['issue_status'] != 'resolved')
    categories = len(set(w['field'] for w in workshops if w['field']))
    
    conn.close()
    return render_template(
        'index.html',
        workshops=workshops,
        products=products,
        total_workshops=total_workshops,
        active_issues=active_issues,
        active_categories=categories if categories > 0 else 4,
        is_admin=session.get('user_id') is not None
    )

@app.route('/register-workshop', methods=['POST'])
def register_workshop():
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
        flash('کارگاه با موفقیت در سامانه ثبت شد و در چرخه عارضه‌یابی قرار گرفت.', 'success')

    return redirect(url_for('home'))

@app.route('/update-issue-status/<int:workshop_id>', methods=['POST'])
def update_issue_status(workshop_id):
    if not session.get('user_id'):
        flash('برای ویرایش وضعیت باید وارد حساب مدیریت شوید.', 'danger')
        return redirect(url_for('home'))

    new_status = request.form.get('status')
    if new_status in ['pending', 'in_progress', 'resolved']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE workshops SET issue_status = ? WHERE id = ?', (new_status, workshop_id))
        conn.commit()
        conn.close()
        flash('وضعیت مانع با موفقیت به‌روزرسانی شد.', 'success')

    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
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
        flash(f'خوش آمدید {user["username"]}! دسترسی مدیریت فعال شد.', 'success')
    else:
        flash('نام کاربری یا رمز عبور اشتباه است (اطلاعات پیش‌فرض: admin / admin123)', 'danger')

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('از حساب مدیریت خارج شدید.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
