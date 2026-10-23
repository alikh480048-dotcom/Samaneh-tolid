import os
from pathlib import Path
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
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Index,
    desc,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

BASE_DIR = Path(__file__).resolve().parent

# مسیر ذخیره سازی فایل‌های آپلودی
UPLOAD_DIR = Path(os.environ.get("PERSIST_DIR", str(BASE_DIR))) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_BYTES = 5 * 1024 * 1024

# اتصال به دیتابیس PostgreSQL (در رندر) یا SQLite (لوکال/فال‌بک مطمئن)
raw_db_url = os.environ.get("DATABASE_URL", "").strip()
if raw_db_url:
    # رفع ناسازگاری آدرس های postgres:// با استاندارد جدید SQLAlchemy
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    DB_URI = raw_db_url
else:
    local_db_path = Path(os.environ.get("PERSIST_DIR", str(BASE_DIR))) / "samaneh.db"
    DB_URI = f"sqlite:///{local_db_path}"

engine = create_engine(
    DB_URI,
    pool_pre_ping=True,
    pool_size=10 if "postgresql" in DB_URI else 5,
    max_overflow=20 if "postgresql" in DB_URI else 10,
)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

# --- مدل‌های داده‌ای با ایندکس‌گذاری برای مقیاس ۷۰ هزار واحد ---
class ProductionUnit(Base):
    __tablename__ = "production_units"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_name = Column(String(180), nullable=False, index=True)
    manager_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=False, index=True)
    province = Column(String(80), nullable=False, index=True)
    city = Column(String(80), default="")
    category = Column(String(120), default="", index=True)
    subcategory = Column(String(120), default="")
    product_name = Column(String(180), default="")
    nominal_capacity = Column(String(60), default="0")
    capacity_unit = Column(String(60), default="عدد در ماه")
    obstacles = Column(Text, default="")
    image_url = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_province_category", "province", "category"),
    )

class MarketDemand(Base):
    __tablename__ = "market_demands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    buyer = Column(String(150), nullable=False)
    target_country = Column(String(120), default="ایران/صادراتی")
    volume = Column(String(100), default="توافقی")
    delivery_days = Column(String(80), default="۳۰ روزه")
    description = Column(Text, default="")
    badge = Column(String(50), default="سفارش جدید")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# ساخت خودکار جداول
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "samaneh-national-secret-key-1403")

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

@app.teardown_appcontext
def remove_session(exception=None):
    db_session.remove()

def normalized_phone(value):
    return "".join(c for c in str(value or "") if c.isdigit() or c == "+")

def save_product_image():
    uploaded = request.files.get("product_image") or request.files.get("image")
    if not uploaded or not uploaded.filename:
        return ""

    content = uploaded.stream.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("حجم تصویر نمی‌تواند بیشتر از ۵ مگابایت باشد.")

    if content.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        ext = ".webp"
    else:
        raise ValueError("فرمت عکس نامعتبر است. فقط JPG، PNG و WEBP مجاز هستند.")

    filename = f"{uuid4().hex}{ext}"
    target_path = UPLOAD_DIR / filename
    target_path.write_bytes(content)
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
    units_count = db_session.query(func.count(ProductionUnit.id)).scalar() or 0
    recent_units = (
        db_session.query(ProductionUnit)
        .order_by(desc(ProductionUnit.created_at))
        .limit(12)
        .all()
    )
    return render_template(
        "index.html",
        units=recent_units,
        units_count=units_count,
        total_capacity=units_count * 150  # تقریب محاسباتی سبک برای بار کاری بالا
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        unit_name = request.form.get("unit_name", "").strip()
        manager_name = request.form.get("manager_name", "").strip()
        phone = normalized_phone(request.form.get("phone", ""))
        province = request.form.get("province", "").strip()

        if not unit_name or not manager_name or not phone or not province:
            flash("تکمیل فیلدهای نام واحد، نام مدیر، شماره تماس و استان الزامی است.", "error")
            return render_template("register.html")

        try:
            image_filename = save_product_image()
        except ValueError as e:
            flash(str(e), "error")
            return render_template("register.html")

        new_unit = ProductionUnit(
            unit_name=unit_name,
            manager_name=manager_name,
            phone=phone,
            province=province,
            city=request.form.get("city", "").strip(),
            category=request.form.get("category", "").strip(),
            subcategory=request.form.get("subcategory", "").strip(),
            product_name=request.form.get("product_name", "").strip(),
            nominal_capacity=request.form.get("nominal_capacity", "0").strip(),
            capacity_unit=request.form.get("capacity_unit", "عدد در ماه").strip(),
            obstacles=request.form.get("obstacles", "").strip(),
            image_url=image_filename,
            created_at=datetime.utcnow()
        )

        db_session.add(new_unit)
        db_session.commit()

        flash("اطلاعات واحد تولیدی با موفقیت در بانک اطلاعات ملی ثبت شد.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/export-market", methods=["GET", "POST"])
def export_market():
    unit_id = request.args.get("unit_id")
    selected_unit = None
    if unit_id:
        selected_unit = db_session.query(ProductionUnit).filter_by(id=unit_id).first()

    demands = (
        db_session.query(MarketDemand)
        .order_by(desc(MarketDemand.created_at))
        .limit(50)
        .all()
    )

    if request.method == "POST":
        title = request.form.get("title") or request.form.get("product_name") or "درخواست خرید عمده"
        buyer = request.form.get("buyer") or request.form.get("company_name") or "خریدار تجاری"

        new_demand = MarketDemand(
            title=title,
            buyer=buyer,
            target_country=request.form.get("target_country", "ایران/صادراتی"),
            volume=request.form.get("volume", "توافقی"),
            delivery_days=request.form.get("delivery_days", "۳۰ روزه"),
            description=request.form.get("description", ""),
            badge="سفارش جدید",
            created_at=datetime.utcnow()
        )
        db_session.add(new_demand)
        db_session.commit()

        flash("درخواست خرید با موفقیت در تالار بازار ثبت شد.", "success")
        return redirect(url_for("export_market"))

    return render_template(
        "export.html",
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
    <body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4">
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
            <input type="text" name="username" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">رمز عبور</label>
            <input type="password" name="password" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 text-white">
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

    page = request.args.get("page", 1, type=int)
    province_filter = request.args.get("province", "").strip()
    search_q = request.args.get("q", "").strip()
    per_page = 24

    query = db_session.query(ProductionUnit)
    if province_filter:
        query = query.filter(ProductionUnit.province == province_filter)
    if search_q:
        query = query.filter(
            (ProductionUnit.unit_name.ilike(f"%{search_q}%")) |
            (ProductionUnit.manager_name.ilike(f"%{search_q}%")) |
            (ProductionUnit.phone.ilike(f"%{search_q}%")) |
            (ProductionUnit.product_name.ilike(f"%{search_q}%"))
        )

    total_units = query.count()
    total_pages = (total_units + per_page - 1) // per_page
    units = (
        query.order_by(desc(ProductionUnit.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    demands = (
        db_session.query(MarketDemand)
        .order_by(desc(MarketDemand.created_at))
        .limit(10)
        .all()
    )

    admin_html = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>پنل مدیریت | سامانه ملی توسعه تولید</title>
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-3 md:p-6 font-sans">
      <div class="max-w-7xl mx-auto space-y-6">
        <!-- هدر پنل -->
        <div class="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-2xl">
          <div>
            <h1 class="text-lg md:text-xl font-bold text-emerald-400">پنل مدیریت سامانه ملی تولید</h1>
            <p class="text-xs text-slate-400 mt-1">مدیریت کلان ۶۰ تا ۷۰ هزار واحد تولیدی و صادراتی</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs bg-emerald-950 text-emerald-300 border border-emerald-800 px-3 py-1.5 rounded-xl font-bold">
              مجموع واحدها: {{ "{:,}".format(total_units) }}
            </span>
            <a href="{{ url_for('index') }}" class="text-xs bg-slate-800 hover:bg-slate-700 text-white px-3 py-2 rounded-xl">صفحه اصلی</a>
            <a href="{{ url_for('logout') }}" class="text-xs bg-rose-900/80 hover:bg-rose-800 text-rose-200 px-3 py-2 rounded-xl">خروج</a>
          </div>
        </div>

        <!-- فیلتر و جستجو -->
        <form method="GET" class="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex flex-wrap gap-3 items-center">
          <input type="text" name="q" value="{{ search_q }}" placeholder="جستجوی نام واحد، مدیر، محصول، تلفن..." class="flex-1 min-w-[200px] bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white">
          <input type="text" name="province" value="{{ province_filter }}" placeholder="فیلتر استان (مثلاً قم)" class="w-40 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-xs text-white">
          <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-5 py-2 rounded-xl font-bold transition">اعمال فیلتر</button>
          {% if search_q or province_filter %}
          <a href="{{ url_for('admin') }}" class="text-xs text-slate-400 hover:text-white px-2">حذف فیلترها</a>
          {% endif %}
        </form>

        <!-- نمایش واحدها همراه با عکس و مشخصات کامل -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 md:p-6">
          <h2 class="text-md font-bold text-emerald-400 mb-4">واحدهای تولیدی ثبت‌شده</h2>
          {% if units %}
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {% for u in units %}
            <div class="bg-slate-800/90 border border-slate-700 rounded-xl p-4 space-y-2 flex flex-col justify-between">
              <div>
                <div class="flex justify-between items-center mb-2">
                  <span class="font-bold text-white text-sm">{{ u.unit_name }}</span>
                  <span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full border border-emerald-500/30">{{ u.province }} {% if u.city %}- {{ u.city }}{% endif %}</span>
                </div>

                {% if u.image_url %}
                <div class="mb-3">
                  <a href="{{ url_for('uploaded_file', filename=u.image_url) }}" target="_blank">
                    <img src="{{ url_for('uploaded_file', filename=u.image_url) }}" alt="محصول" class="w-full h-36 object-cover rounded-xl border border-slate-700 hover:opacity-90 transition" loading="lazy">
                  </a>
                </div>
                {% else %}
                <div class="w-full h-20 bg-slate-900/60 rounded-xl flex items-center justify-center text-[11px] text-slate-500 mb-2 border border-slate-800">
                  تصویر بارگذاری نشده است
                </div>
                {% endif %}

                <p class="text-xs text-slate-300"><strong>مدیر / تماس:</strong> {{ u.manager_name }} ({{ u.phone }})</p>
                <p class="text-xs text-slate-300"><strong>دسته / محصول:</strong> {{ u.category or '-' }} / {{ u.product_name or '-' }}</p>
                <p class="text-xs text-slate-300"><strong>ظرفیت ماهانه:</strong> {{ u.nominal_capacity }} {{ u.capacity_unit }}</p>
                {% if u.obstacles %}
                <div class="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/50 p-2 rounded-lg mt-2">
                  <strong>مانع تولید:</strong> {{ u.obstacles }}
                </div>
                {% endif %}
              </div>
              <p class="text-[10px] text-slate-500 text-left mt-2">{{ u.created_at.strftime('%Y/%m/%d %H:%M') if u.created_at else '' }}</p>
            </div>
            {% endfor %}
          </div>

          <!-- ناوبری صفحات (Pagination) برای کنترل بار سنگین -->
          {% if total_pages > 1 %}
          <div class="flex justify-center items-center gap-2 mt-6">
            {% if page > 1 %}
            <a href="{{ url_for('admin', page=page-1, q=search_q, province=province_filter) }}" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-white">قبلی</a>
            {% endif %}
            <span class="text-xs text-slate-400">صفحه {{ page }} از {{ total_pages }}</span>
            {% if page < total_pages %}
            <a href="{{ url_for('admin', page=page+1, q=search_q, province=province_filter) }}" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg text-white">بعدی</a>
            {% endif %}
          </div>
          {% endif %}

          {% else %}
          <p class="text-xs text-slate-500 text-center py-6">موردی با این مشخصات یافت نشد.</p>
          {% endif %}
        </div>
      </div>
    </body>
    </html>
    """
    return render_template_string(
        admin_html,
        units=units,
        total_units=total_units,
        page=page,
        total_pages=total_pages,
        search_q=search_q,
        province_filter=province_filter,
        demands=demands
    )

@app.route("/logout")
def logout():
    session.clear()
    flash("با موفقیت خارج شدید.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
