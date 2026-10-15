import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart-tolid-national-key-2026")

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.path.join(app.root_path, "production_network.db")

INDUSTRY_GROUPS = [
    "صنایع فلزی و ماشین‌سازی",
    "شیمیایی، پلیمر و پلاستیک",
    "صنایع غذایی، فرآوری و دارویی",
    "نساجی، پوشاک، چرم و کفش",
    "برق، الکترونیک و تجهیزات دقیق",
    "کانی غیرفلزی و مصالح ساختمانی",
    "صنایع چوب، مبلمان و سلولزی",
    "صنایع دستی، بومی و تولیدات خرد",
    "کشاورزی و صنایع تبدیلی وابسته",
    "سایر صنایع و خدمات مهندسی"
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # ۱. جدول مدیران
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin'
        )
    """)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "مدیر ارشد سامانه")
        )

    # ۲. جدول کارگاه‌ها و واحدهای تولیدی
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            province TEXT NOT NULL,
            county TEXT,
            industry_group TEXT NOT NULL,
            capacity REAL DEFAULT 0,
            unit TEXT DEFAULT 'عدد در ماه',
            price REAL DEFAULT 0,
            price_currency TEXT DEFAULT 'تومان',
            barriers TEXT,
            status TEXT DEFAULT 'در انتظار بررسی',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ۳. جدول تصاویر متصل به هر واحد
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workshop_id) REFERENCES workshops(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    selected_group = request.args.get("group")
    if selected_group and selected_group != "همه":
        cursor.execute("SELECT * FROM workshops WHERE industry_group = ? ORDER BY id DESC", (selected_group,))
    else:
        cursor.execute("SELECT * FROM workshops ORDER BY id DESC")
    
    raw_workshops = cursor.fetchall()
    
    workshops = []
    total_capacity = 0
    for r in raw_workshops:
        w = dict(r)
        # ماسک تلفن برای امنیت سامانه و ارجاع به دبیرخانه
        p = w.get("phone", "")
        w["masked_phone"] = f"{p[:4]}***{p[-4:]}" if len(p) >= 11 else "۰۹*********"
        
        # بارگذاری عکس‌ها
        cursor.execute("SELECT filename FROM workshop_images WHERE workshop_id = ?", (w["id"],))
        w["images"] = [row["filename"] for row in cursor.fetchall()]
        
        total_capacity += float(w.get("capacity") or 0)
        workshops.append(w)
        
    cursor.execute("SELECT COUNT(DISTINCT industry_group) as cnt FROM workshops")
    total_industries = cursor.fetchone()["cnt"] or len(INDUSTRY_GROUPS)

    conn.close()
    
    return render_template(
        "index.html",
        workshops=workshops,
        total_workshops=len(workshops),
        total_capacity=f"{int(total_capacity):,}" if total_capacity else "۱,۲۵۰,۰۰۰",
        total_industries=total_industries,
        industry_groups=INDUSTRY_GROUPS,
        selected_group=selected_group,
        is_admin=session.get("user_id") is not None
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        phone = request.form.get("phone", "").strip()
        province = request.form.get("province", "").strip()
        county = request.form.get("county", "").strip()
        industry_group = request.form.get("industry_group", "").strip()
        
        try:
            capacity = float(request.form.get("capacity", 0))
        except ValueError:
            capacity = 0.0
            
        unit = request.form.get("unit", "عدد در ماه").strip()
        
        try:
            price = float(request.form.get("price", 0))
        except ValueError:
            price = 0.0
            
        price_currency = request.form.get("price_currency", "تومان").strip()
        
        # جمع‌آوری چک‌لیست موانع
        barriers_list = request.form.getlist("barriers")
        other_barrier = request.form.get("other_barrier", "").strip()
        if other_barrier:
            barriers_list.append(f"سایر: {other_barrier}")
        barriers_str = " | ".join(barriers_list) if barriers_list else "بدون مانع اعلامی"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO workshops (
                title, owner_name, phone, province, county, industry_group,
                capacity, unit, price, price_currency, barriers, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'در انتظار بررسی')
        """, (
            title, owner_name, phone, province, county, industry_group,
            capacity, unit, price, price_currency, barriers_str
        ))
        workshop_id = cursor.lastrowid

        # ذخیره تصاویر ارسالی
        files = request.files.getlist("product_images")
        for file in files:
            if file and allowed_file(file.filename):
                fname = secure_filename(file.filename)
                saved_name = f"w{workshop_id}_{os.urandom(4).hex()}_{fname}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], saved_name))
                cursor.execute(
                    "INSERT INTO workshop_images (workshop_id, filename) VALUES (?, ?)",
                    (workshop_id, saved_name)
                )

        conn.commit()
        conn.close()
        flash("واحد تولیدی با موفقیت ثبت شد و در چرخه هم‌رسانی قرار گرفت.", "success")
        return redirect(url_for("index"))

    return render_template("register.html", industry_groups=INDUSTRY_GROUPS)

@app.route("/download/<filename>")
def download_file(filename):
    """دانلود مستقیم و مطمئن تصویر محصول"""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db()
        cursor = conn.cursor()
        user = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("ورود با موفقیت انجام شد. دسترسی مدیریتی فعال است.", "success")
            return redirect(url_for("index"))
        else:
            flash("نام کاربری یا رمز عبور اشتباه است (پیش‌فرض: admin / admin123)", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("از حساب مدیریت خارج شدید.", "info")
    return redirect(url_for("index"))

@app.route("/update-status/<int:workshop_id>", methods=["POST"])
def update_status(workshop_id):
    if not session.get("user_id"):
        flash("فقط مدیر امکان تغییر وضعیت را دارد.", "danger")
        return redirect(url_for("login"))
        
    new_status = request.form.get("status")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE workshops SET status = ? WHERE id = ?", (new_status, workshop_id))
    conn.commit()
    conn.close()
    flash("وضعیت واحد به‌روزرسانی شد.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
