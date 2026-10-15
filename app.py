import os
import sqlite3
import json
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart_production_secret_key_2026")

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # حداکثر ۱۶ مگابایت مجموع فایل‌ها

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = os.path.join(os.path.dirname(__file__), "production_network.db")

# فهرست استاندارد گروه‌های تولید
INDUSTRY_GROUPS = [
    "صنایع دستی و هنرهای سنتی",
    "صنایع غذایی، فرآوری و بسته‌بندی",
    "نساجی، پوشاک، چرم و کفش",
    "کشاورزی، گیاهان دارویی و محصولات ارگانیک",
    "صنایع چوب، مبلمان و مصنوعات چوبی",
    "فلزکاری، ابزارآلات و خدمات فنی خرد",
    "سفال، سرامیک، چینی و شیشه",
    "شیمیایی خرد، شوینده‌ها و بهداشتی",
    "چاپ، نشر و کارتن‌سازی",
    "سایر تولیدات خرد و خانگی"
]

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_and_migrate_db():
    conn = get_db()
    cursor = conn.cursor()

    # ۱. ایجاد جدول کارگاه‌ها در صورت عدم وجود
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            owner_name TEXT,
            phone TEXT,
            province TEXT,
            county TEXT,
            industry_group TEXT,
            capacity REAL,
            unit TEXT,
            price REAL,
            price_currency TEXT DEFAULT 'تومان',
            issue TEXT,
            barriers TEXT,
            field TEXT,
            status TEXT DEFAULT 'در انتظار بررسی',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # بررسی ستون‌های موجود برای ارتقای بدون خطا
    cursor.execute("PRAGMA table_info(workshops)")
    columns = [col[1] for col in cursor.fetchall()]

    new_columns = {
        "title": "TEXT",
        "owner_name": "TEXT",
        "phone": "TEXT",
        "county": "TEXT",
        "industry_group": "TEXT",
        "capacity": "REAL",
        "unit": "TEXT",
        "price": "REAL",
        "price_currency": "TEXT DEFAULT 'تومان'",
        "barriers": "TEXT",
        "status": "TEXT DEFAULT 'در انتظار بررسی'"
    }

    for col_name, col_def in new_columns.items():
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE workshops ADD COLUMN {col_name} {col_def}")

    # ۲. جدول عکس‌های محصول کارگاه‌ها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshop_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id INTEGER,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workshop_id) REFERENCES workshops(id)
        )
    """)

    # ۳. جدول کاربران مدیر
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'admin'
        )
    """)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")

    conn.commit()
    conn.close()

init_and_migrate_db()

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()

    # بازیابی تمام کارگاه‌ها با نگه‌داشتن داده‌های پیشین
    workshops_raw = cursor.execute("""
        SELECT * FROM workshops ORDER BY id DESC
    """).fetchall()

    workshops = []
    for w in workshops_raw:
        item = dict(w)
        # دریافت عکس‌های متصل به کارگاه
        imgs = cursor.execute("SELECT file_path FROM workshop_images WHERE workshop_id = ?", (item["id"],)).fetchall()
        item["images"] = [img["file_path"] for img in imgs]
        workshops.append(item)

    total_workshops = len(workshops)
    pending_issues = sum(1 for w in workshops if w.get("status") in ["در انتظار بررسی", "در انتظار"])
    
    # شمارش رسته‌ها/گروه‌ها
    groups_set = set(w.get("industry_group") or w.get("field") for w in workshops if (w.get("industry_group") or w.get("field")))
    total_industries = len(groups_set)

    conn.close()
    return render_template(
        "index.html",
        workshops=workshops,
        total_workshops=total_workshops,
        pending_issues=pending_issues,
        total_industries=total_industries
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

        # ظرفیت به صورت عددی
        capacity_raw = request.form.get("capacity", "").strip()
        capacity = float(capacity_raw) if capacity_raw.replace(".", "", 1).isdigit() else 0.0

        unit = request.form.get("unit", "عدد در ماه").strip()

        # قیمت واحد
        price_raw = request.form.get("price", "").strip()
        price = float(price_raw) if price_raw.replace(".", "", 1).isdigit() else 0.0
        price_currency = request.form.get("price_currency", "تومان").strip()

        # استخراج موانع از چک‌لیست
        selected_barriers = request.form.getlist("barriers")
        other_barrier = request.form.get("other_barrier", "").strip()
        if other_barrier:
            selected_barriers.append(f"سایر: {other_barrier}")

        barriers_str = " | ".join(selected_barriers) if selected_barriers else "بدون مانع گلوگاهی اعلامی"
        issue_legacy = barriers_str  # سازگاری با ستون قدیمی issue

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO workshops (
                title, owner_name, phone, province, county, industry_group,
                capacity, unit, price, price_currency, barriers, issue, field, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, owner_name, phone, province, county, industry_group,
            capacity, unit, price, price_currency, barriers_str, issue_legacy, industry_group, "در انتظار بررسی"
        ))
        workshop_id = cursor.lastrowid

        # مدیریت ذخیره چند عکس
        uploaded_files = request.files.getlist("product_images")
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                safe_name = f"w{workshop_id}_{secure_filename(file.filename)}"
                save_dest = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                file.save(save_dest)
                cursor.execute("""
                    INSERT INTO workshop_images (workshop_id, file_path)
                    VALUES (?, ?)
                """, (workshop_id, f"uploads/{safe_name}"))

        conn.commit()
        conn.close()

        flash("مشخصات واحد تولیدی، چک‌لیست موانع و تصاویر با موفقیت ثبت شدند.", "success")
        return redirect(url_for("index"))

    return render_template("register.html", industry_groups=INDUSTRY_GROUPS)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.cursor().execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("ورود با موفقیت انجام شد.", "success")
            return redirect(url_for("index"))
        else:
            flash("نام کاربری یا کلمه عبور نادرست است.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("خروج با موفقیت انجام شد.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
