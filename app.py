import os
import json
from pathlib import Path
from threading import RLock
from datetime import datetime
from uuid import uuid4
from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)

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

# نام کاربری و رمز عبور پیش‌فرض مدیر
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123").strip()

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
    return "".join(c for c in str(value or "") if c.isdigit() or c == "+")

def save_product_image():
    uploaded = request.files.get("product_image") or request.files.get("image")
    if not uploaded or not uploaded.filename:
        return ""
    
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
    return filename

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
    total_capacity = 0
    for u in units:
        try:
            total_capacity += float(str(u.get("nominal_capacity", 0)).strip() or 0)
        except Exception:
            pass
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
            image_filename = save_product_image()
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
            "image_url": image_filename,
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
        title = request.form.get("title") or request.form.get("product_name") or "درخواست خرید عمده"
        buyer = request.form.get("buyer") or request.form.get("company_name") or "خریدار تجاری"
        
        new_demand = {
            "id": int(datetime.now().timestamp()),
            "title": title,
            "buyer": buyer,
            "target_country": request.form.get("target_country", "ایران/صادراتی"),
            "volume": request.form.get("volume", "توافقی"),
            "delivery_days": request.form.get("delivery_days", "۳۰ روزه"),
            "description": request.form.get("description", ""),
            "badge": "سفارش جدید",
            "created_at": datetime.now().strftime("%Y/%m/%d %H:%M")
        }
        
        demands.insert(0, new_demand)
        with DATA_LOCK:
            write_records(DEMANDS_FILE, demands)
            
        flash("درخواست خرید با موفقیت در تالار بازار ثبت شد.", "success")
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
    if session.get("is_admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("خوش آمدید مدیر گرامی.", "success")
            return redirect(url_for("admin"))
        else:
            flash("نام کاربری یا رمز عبور اشتباه است.", "error")

    # اگر قالب login.html بود باز کن، در غیر این صورت فرم زیبا را مستقیم رندر کن
    try:
        return render_template("login.html")
    except Exception:
        pass

    login_html = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>ورود مدیریت | سامانه توسعه تولید</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
      <div class="w-full max-w-md bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-2xl">
        <h2 class="text-xl font-bold text-center text-emerald-400 mb-6">ورود به پنل مدیریت سامانه</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for cat, msg in messages %}
              <div class="mb-4 p-3 rounded-lg text-sm {{ 'bg-rose-900/60 text-rose-200 border border-rose-700' if cat == 'error' else 'bg-emerald-900/60 text-emerald-200 border border-emerald-700' }}">{{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        <form method="POST" class="space-y-4">
          <div>
            <label class="block text-xs text-slate-400 mb-1">نام کاربری</label>
            <input type="text" name="username" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-emerald-500">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">رمز عبور</label>
            <input type="password" name="password" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-emerald-500">
          </div>
          <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl transition">ورود به سامانه</button>
        </form>
        <div class="text-center mt-4">
          <a href="{{ url_for('index') }}" class="text-xs text-slate-400 hover:text-slate-200">بازگشت به صفحه اصلی</a>
        </div>
      </div>
    </body>
    </html>
    """
    return render_template_string(login_html)

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    units = load_data()
    demands = load_market_requests()

    try:
        return render_template("admin.html", units=units, demands=demands)
    except Exception:
        pass

    admin_html = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>پنل مدیریت | سامانه ملی توسعه تولید</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-4 md:p-8 font-sans">
      <div class="max-w-6xl mx-auto space-y-8">
        <div class="flex items-center justify-between bg-slate-900 border border-slate-800 p-4 rounded-2xl">
          <div>
            <h1 class="text-lg md:text-xl font-bold text-emerald-400">پنل مدیریت سامانه هوشمند تولید</h1>
            <p class="text-xs text-slate-400 mt-1">مشاهده واحدها و درخواست‌های تالار صادرات</p>
          </div>
          <div class="flex gap-2">
            <a href="{{ url_for('index') }}" class="text-xs bg-slate-800 hover:bg-slate-700 text-white px-3 py-2 rounded-xl">صفحه اصلی</a>
            <a href="{{ url_for('logout') }}" class="text-xs bg-rose-900/80 hover:bg-rose-800 text-rose-200 px-3 py-2 rounded-xl">خروج</a>
          </div>
        </div>

        <!-- بخش درخواست‌های بازار -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 md:p-6">
          <h2 class="text-md font-bold text-amber-400 mb-4 flex items-center gap-2">
            <span>درخواست‌های خرید و صادرات ثبت‌شده ({{ demands|length }})</span>
          </h2>
          {% if demands %}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {% for d in demands %}
            <div class="bg-slate-800/80 border border-slate-700 rounded-xl p-4 space-y-2">
              <div class="flex justify-between items-start">
                <span class="font-bold text-white text-sm">{{ d.title }}</span>
                <span class="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/30">{{ d.badge }}</span>
              </div>
              <p class="text-xs text-slate-300"><strong>خریدار:</strong> {{ d.buyer }}</p>
              <p class="text-xs text-slate-300"><strong>مقصد / حجم:</strong> {{ d.target_country }} | {{ d.volume }}</p>
              {% if d.description %}
              <p class="text-xs text-slate-400 bg-slate-900/60 p-2 rounded-lg">{{ d.description }}</p>
              {% endif %}
              <p class="text-[10px] text-slate-500 text-left">{{ d.created_at }}</p>
            </div>
            {% endfor %}
          </div>
          {% else %}
          <p class="text-xs text-slate-500 text-center py-6">هنوز هیچ درخواست بازاری ثبت نشده است.</p>
          {% endif %}
        </div>

        <!-- بخش واحدهای ثبت‌شده -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 md:p-6">
          <h2 class="text-md font-bold text-emerald-400 mb-4">واحدهای تولیدی ثبت‌شده ({{ units|length }})</h2>
          {% if units %}
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {% for u in units %}
            <div class="bg-slate-800/80 border border-slate-700 rounded-xl p-4 space-y-2">
              <div class="flex justify-between items-center">
                <span class="font-bold text-white text-sm">{{ u.unit_name }}</span>
                <span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full">{{ u.province }}</span>
              </div>
              <p class="text-xs text-slate-300"><strong>مدیر / تماس:</strong> {{ u.manager_name }} ({{ u.phone }})</p>
              <p class="text-xs text-slate-300"><strong>محصول:</strong> {{ u.product_name or 'ثبت نشده' }}</p>
              <p class="text-xs text-slate-300"><strong>ظرفیت ماهانه:</strong> {{ u.nominal_capacity }} {{ u.capacity_unit }}</p>
              {% if u.obstacles %}
              <div class="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/50 p-2 rounded-lg mt-2">
                <strong>مانع ثبت‌شده:</strong> {{ u.obstacles }}
              </div>
              {% endif %}
            </div>
            {% endfor %}
          </div>
          {% else %}
          <p class="text-xs text-slate-500 text-center py-6">هنوز واحدی ثبت نشده است.</p>
          {% endif %}
        </div>
      </div>
    </body>
    </html>
    """
    return render_template_string(admin_html, units=units, demands=demands)

@app.route("/logout")
def logout():
    session.clear()
    flash("با موفقیت خارج شدید.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
