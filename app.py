import os
import json
import hmac
import secrets
import tempfile
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "units_data.json"
DEMANDS_FILE = DATA_DIR / "market_requests.json"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
DATA_LOCK = RLock()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "samaneh-secret-key-1403")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()

INDUSTRY_CATEGORIES = {
    "صنایع دستی و هنرهای سنتی": [
        "فرش دست‌باف، گلیم و جاجیم",
        "سفال و سرامیک هنری",
        "قلم‌زنی و صنایع فلزی هنری",
        "خاتم، معرق و منبت",
        "حصیربافی و صنایع الیافی",
        "رودوزی و سوزن‌دوزی سنتی",
        "زیورآلات دست‌ساز",
    ],
    "مواد غذایی و صنایع تبدیلی خانگی": [
        "خشکبار و میوه خشک",
        "ترشی، شور، مربا و فرآورده‌های میوه",
        "نان، شیرینی و محصولات آردی",
        "ادویه و چاشنی",
        "بسته‌بندی محصولات کشاورزی",
        "فرآوری و بسته‌بندی عسل",
    ],
    "نساجی، پوشاک و کالای خواب": [
        "پوشاک زنانه و مردانه",
        "لباس کار و فرم",
        "بافت و تریکو",
        "کالای خواب و منسوجات منزل",
    ],
    "چرم، کیف و کفش": [
        "کیف و محصولات چرمی",
        "کفش و پاپوش دست‌دوز",
    ],
    "چوب، مبلمان و دکوراسیون": [
        "مبلمان و مصنوعات چوبی",
        "لوازم دکوراسیون و اسباب‌بازی چوبی",
    ],
    "گیاهان دارویی و محصولات ارگانیک": [
        "گیاهان دارویی خشک و بسته‌بندی",
        "عرقیات و گلاب",
    ],
    "تولیدات سبک صنعتی و کارگاهی": [
        "قطعات و مصنوعات فلزی سبک",
        "قطعات پلیمری و لوازم کارگاهی",
    ],
}

def read_records(path):
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def write_records(path, records):
    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

def load_data():
    return read_records(DATA_FILE)

def save_data(data):
    with DATA_LOCK:
        write_records(DATA_FILE, data)

def load_market_requests():
    return read_records(DEMANDS_FILE)

def normalized_phone(value):
    value = "".join(c for c in str(value or "") if c.isdigit() or c == "+")
    return value

def valid_phone(value):
    return len(value) >= 10

def save_product_image():
    uploaded = request.files.get("product_image") or request.files.get("image")
    if not uploaded or not uploaded.filename:
        return "", ""
    
    content = uploaded.stream.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("حجم عکس نباید بیشتر از ۵ مگابایت باشد.")
    
    if content.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        ext = ".webp"
    else:
        raise ValueError("فرمت عکس باید JPG یا PNG باشد.")
    
    filename = f"{uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename
    path.write_bytes(content)
    return filename, url_for("uploaded_file", filename=filename)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.context_processor
def inject_globals():
    return {
        "industry_categories": INDUSTRY_CATEGORIES,
        "is_admin": session.get("is_admin") is True
    }

@app.route("/")
def index():
    units = load_data()
    total_capacity = sum(float(u.get("nominal_capacity", 0)) for u in units if str(u.get("nominal_capacity", 0)).replace('.','',1).isdigit())
    return render_template(
        "index.html",
        units=units,
        units_count=len(units),
        total_capacity=int(total_capacity)
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        unit_name = request.form.get("unit_name", "").strip()
        manager_name = request.form.get("manager_name", "").strip()
        phone = normalized_phone(request.form.get("phone", ""))
        province = request.form.get("province", "").strip()
        
        if not unit_name or not manager_name or not phone or not province:
            flash("لطفاً تمامی فیلدهای الزامی را تکمیل کنید.", "error")
            return render_template("register.html")
            
        try:
            image_url, _ = save_product_image()
        except ValueError as e:
            flash(str(e), "error")
            return render_template("register.html")
            
        new_unit = {
            "id": int(datetime.now().timestamp()),
            "unit_name": unit_name,
            "manager_name": manager_name,
            "phone": phone,
            "province": province,
            "city": request.form.get("city", "").strip(),
            "category": request.form.get("category", "").strip(),
            "subcategory": request.form.get("subcategory", "").strip(),
            "product_name": request.form.get("product_name", "").strip(),
            "nominal_capacity": request.form.get("nominal_capacity", "0").strip(),
            "capacity_unit": request.form.get("capacity_unit", "عدد در ماه").strip(),
            "obstacles": request.form.get("obstacles", "").strip(),
            "image_url": image_url,
            "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
        }
        
        units = load_data()
        units.append(new_unit)
        save_data(units)
        
        flash("واحد تولیدی با موفقیت ثبت شد.", "success")
        return redirect(url_for("index"))
        
    return render_template("register.html")

@app.route("/export-market", methods=["GET", "POST"])
def export_market():
    units = load_data()
    unit_id = request.args.get("unit_id")
    selected_unit = next((u for u in units if str(u.get("id")) == str(unit_id)), None)
    
    demands = load_market_requests()
    
    if request.method == "POST":
        title = request.form.get("title") or request.form.get("product_name") or "درخواست خرید"
        buyer = request.form.get("buyer") or request.form.get("company_name") or "خریدار عمده"
        
        new_demand = {
            "id": int(datetime.now().timestamp()),
            "title": title,
            "buyer": buyer,
            "target_country": request.form.get("target_country", "ایران/صادراتی"),
            "volume": request.form.get("volume", "توافقی"),
            "delivery_days": request.form.get("delivery_days", "۳۰ روزه"),
            "description": request.form.get("description", ""),
            "badge": "سفارش جدید",
            "created_at": datetime.now().strftime("%Y/%m/%d")
        }
        
        demands.append(new_demand)
        with DATA_LOCK:
            write_records(DEMANDS_FILE, demands)
            
        flash("درخواست شما با موفقیت ثبت شد.", "success")
        return redirect(url_for("export_market"))
        
    return render_template(
        "export.html",
        units=units,
        selected_unit=selected_unit,
        demands=demands,
        buyer_success=request.args.get("submitted") == "1"
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("خوش آمدید مدیر عزیز.", "success")
            return redirect(url_for("admin"))
        flash("نام کاربری یا رمز عبور اشتباه است.", "error")
    return render_template("login.html")

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    units = load_data()
    demands = load_market_requests()
    return render_template("admin.html", units=units, demands=demands)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
