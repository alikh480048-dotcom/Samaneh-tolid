import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
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

PROVINCES_BY_COUNTY = {
    "آذربایجان شرقی": ["تبریز", "مراغه", "مرند", "میانه", "اهر", "بناب", "سراب", "آذرشهر", "اسکو", "شبستر", "عجب‌شیر", "جلفا"],
    "آذربایجان غربی": ["ارومیه", "خوی", "بوکان", "مهاباد", "میاندوآب", "سلماس", "پیرانشهر", "نقده", "سردشت", "ماکو", "شاهین‌دژ", "تکاب"],
    "اردبیل": ["اردبیل", "پارس‌آباد", "مشگین‌شهر", "خلخال", "گرمی", "نمین", "بیله‌سوار", "کوثر", "سرعین", "اصلاندوز"],
    "اصفهان": ["اصفهان", "کاشان", "خمینی‌شهر", "نجف‌آباد", "لنجان", "فلاورجان", "شاهین‌شهر و میمه", "شهرضا", "مبارکه", "برخوار", "آران و بیدگل", "گلپایگان", "نائین", "سمیرم", "خوانسار", "اردستان"],
    "البرز": ["کرج", "فردیس", "ساوجبلاغ", "نظرآباد", "اشتهارد", "طالقان", "چهارباغ"],
    "ایلام": ["ایلام", "دهلران", "ایوان", "آبدانان", "چرداول", "دره‌شهر", "مهران", "ملکشاهی", "بدره", "سیروان", "چوار", "هلیلان"],
    "بوشهر": ["بوشهر", "دشتستان", "کنگان", "گناوه", "دشتی", "تنگستان", "عسلویه", "جم", "دیر", "دیلم"],
    "تهران": ["تهران", "شهریار", "اسلامشهر", "بهارستان", "ملارد", "پاکدشت", "ری", "قدس", "رباط‌کریم", "ورامین", "قرچک", "پردیس", "دماوند", "پیشوا", "شمیرانات", "فیروزکوه"],
    "چهارمحال و بختیاری": ["شهرکرد", "بروجن", "لردگان", "فارسان", "کیار", "اردل", "کوهرنگ", "سامان", "بن", "خانمیرزا"],
    "خراسان جنوبی": ["بیرجند", "قائنات", "طبس", "فردوس", "نهبندان", "درمیان", "سربیشه", "سرایان", "بشرویه", "زیرکوه", "خوسف"],
    "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت حیدریه", "کاشمر", "قوچان", "تربت جام", "تایباد", "چناران", "سرخس", "گناباد", "فریمان", "خواف", "بردسکن", "طرقبه شاندیز"],
    "خراسان شمالی": ["بجنورد", "شیروان", "اسفراین", "مانه و سملقان", "جاجرم", "فاروج", "گرمه", "راز و جرگلان"],
    "خوزستان": ["اهواز", "دزفول", "آبادان", "ماهشهر", "شوشتر", "مسجد سلیمان", "بهبهان", "ایذه", "رامهرمز", "اندیمشک", "خرمشهر", "شوش", "شادگان", "امیدیه", "باغ‌ملک"],
    "زنجان": ["زنجان", "ابهر", "خدابنده", "خرمدره", "طارم", "ماه‌نشان", "ایجرود", "سلطانیه"],
    "سمنان": ["سمنان", "شاهرود", "دامغان", "گرمسار", "مهدی‌شهر", "میامی", "سرخه", "آرادان"],
    "سیستان و بلوچستان": ["زاهدان", "چابهار", "زابل", "ایرانشهر", "سراوان", "خاش", "کنارک", "نیک‌شهر", "دشتیاری", "راسک", "سیب و سوران"],
    "فارس": ["شیراز", "مرودشت", "کازرون", "جهرم", "فسا", "داراب", "لارستان", "آباده", "اقلید", "سپیدان", "لامرد", "نی‌ریز", "فیروزآباد", "استهبان", "قیر و کارزین"],
    "قزوین": ["قزوین", "البرز", "تاکستان", "بوئین‌زهرا", "آبیک", "آوج"],
    "قم": ["قم", "جعفریه", "کهک"],
    "کردستان": ["سنندج", "سقز", "مریوان", "بانه", "قروه", "کامیاران", "بیجار", "دیواندره", "دهگلان", "سروآباد"],
    "کرمان": ["کرمان", "سیرجان", "رفسنجان", "جیرفت", "بم", "زرند", "کهنوج", "شهربابک", "بافت", "بردسیر", "عنبرآباد", "منوجان", "راور"],
    "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "کنگاور", "سرپل ذهاب", "سنقر", "هرسین", "صحنه", "پاوه", "جوانرود", "گیلانغرب", "روانسر", "قصر شیرین"],
    "کهگیلویه و بویراحمد": ["یاسوج (بویراحمد)", "گچساران", "کهگیلویه (دهدشت)", "دنا", "بهمئی", "چرام", "لنده", "مارگون"],
    "گلستان": ["گرگان", "گنبد کاووس", "علی‌آباد کتول", "آق‌قلا", "کلاله", "آزادشهر", "کردکوی", "مینودشت", "ترکمن", "گمیشان", "رامیان", "بندر گز"],
    "گیلان": ["رشت", "بندر انزلی", "لاهیجان", "لنگرود", "تالش", "رودسر", "صومعه‌سرا", "آستارا", "فومن", "رودبار", "آستانه اشرفیه", "ماسال"],
    "لرستان": ["خرم‌آباد", "بروجرد", "دورود", "الیگودرز", "کوهدشت", "دلفان (نورآباد)", "ازنا", "پلدختر", "سلسله (الشتر)", "چگنی"],
    "مازندران": ["ساری", "بابل", "آمل", "قائم‌شهر", "بهشهر", "چالوس", "نکا", "بابلسر", "تنکابن", "نوشهر", "محمودآباد", "رامسر", "جویبار", "نور"],
    "مرکزی": ["اراک", "ساوه", "زرندیه", "خمین", "محلات", "دلیجان", "شازند", "فراهان", "تفرش", "آشتیان", "کمیجان", "خنداب"],
    "هرمزگان": ["بندرعباس", "میناب", "قشم", "بندرلنگه", "رودان", "بستک", "حاجی‌آباد", "کیش", "پارسیان", "جاسک", "خمیر"],
    "همدان": ["همدان", "ملایر", "نهاوند", "تویسرکان", "اسدآباد", "کبودرآهنگ", "بهار", "رزن", "فامنین", "درگزین"],
    "یزد": ["یزد", "میبد", "اردکان", "مهریز", "بافق", "ابرکوه", "تفت", "اشکذر", "خاتم", "مروست", "بهاباد"]
}

PROVINCES = list(PROVINCES_BY_COUNTY.keys())

INDUSTRY_CATALOG = {
    "کشاورزی و باغبانی": ["تولید بذر و نهال", "کشت گلخانه‌ای", "گیاهان دارویی", "زراعت و غلات", "باغداری و میوه‌کاری", "قارچ‌های خوراکی و صنعتی"],
    "دام، طیور، شیلات و آبزیان": ["دامپروری و پرورش دام سبک و سنگین", "مرغداری و پرورش طیور صنعتی و بومی", "زنبورداری و تولید عسل", "آبزی‌پروری و پرورش ماهی و میگو", "پرورش کرم ابریشم و حشرات مفید", "تولید خوراک دام و طیور"],
    "صنایع غذایی و نوشیدنی": ["لبنیات و فرآورده‌های شیری", "کنسرو، کمپوت و ترشیجات", "آرد، غلات، نان و شیرینی", "روغن‌کشی و فرآوری دانه‌های روغنی", "نوشیدنی‌ها، آبمیوه و دمنوش", "فرآوری گوشت، پروتئین و سوسیس کالباس", "خشکبار، زعفران و بسته‌بندی مواد غذایی"],
    "نساجی و پوشاک": ["ریسندگی و بافندگی پارچه", "تولید انواع پوشاک مردانه و زنانه", "پوشاک تریکو و کشباف", "تکمیل و رنگرزی منسوجات", "منسوجات بی‌بافت و فنی", "تولید نخ و الیاف طبیعی و مصنوعی"],
    "چرم و کفش": ["دباغی و فرآوری چرم طبیعی", "تولید چرم مصنوعی", "تولید کیف و مصنوعات چرمی", "کفش صنعتی، اسپرت و ایمنی", "اجزا و یراق‌آلات چرم و کفش"],
    "چوب، مبلمان و سلولزی": ["مبلمان خانگی و اداری", "درب، پنجره و مصنوعات چوبی", "تخته فیبر، نئوپان و MDF", "پالت، جعبه و بسته‌بندی چوبی", "طراحی و دکوراسیون چوبی داخلی"],
    "کاغذ، چاپ و بسته‌بندی": ["تولید خمیر کاغذ و مقوا", "کارتن‌سازی و جعبه مقوایی", "خدمات چاپ افست، دیجیتال و رول", "چاپ لیبل و هولوگرام", "بسته‌بندی انعطاف‌پذیر و سلفون"],
    "صنایع دستی و تولیدات خرد": ["فرش و گلیم دستباف", "سفال، سرامیک و کاشی سنتی", "میناکاری، قلم‌زنی و مسگری", "خاتم‌کاری، منبت و معرق", "تولیدات خانگی و خرد کارگاهی", "زیورآلات دست‌ساز و تزئینی"],
    "شیمیایی و شوینده": ["شوینده‌ها و پاک‌کننده‌های بهداشتی و صنعتی", "رنگ، رزین و پوشش‌های صنعتی", "چسب‌ها و درزگیرها", "کودها و سموم کشاورزی", "مواد شیمیایی پایه و واسطه"],
    "دارویی، آرایشی و بهداشتی": ["داروهای انسانی و مکمل‌ها", "داروهای دامی و دامپزشکی", "محصولات آرایشی و مراقبت پوست و مو", "محصولات ضدعفونی‌کننده", "اسانس‌ها و عصاره‌های گیاهی دارویی"],
    "پلیمر، پلاستیک و لاستیک": ["ظروف یکبار مصرف و پلیمری", "نایلون، نایلکس و فیلم‌های پلیمری", "لوله و اتصالات پلی‌اتیلن و PVC", "قطعات لاستیکی صنعتی و خودرویی", "مستربچ، کامپاند و گرانول"],
    "نفت، گاز، پتروشیمی و فرآورده‌ها": ["روانکارها، روغن موتور و گریس", "قیر و عایق‌های رطوبتی", "محصولات پتروشیمیایی پایین‌دستی", "حلال‌های هیدروکربوری", "فرآورده‌های گازی و کپسول‌پرکنی"],
    "معدن و فرآوری مواد معدنی": ["استخراج و خردایش سنگ‌های معدنی", "فرآوری فلزات پایه (آهن، مس، سرب و روی)", "پودرهای میکرونیزه معدنی", "شن، ماسه و سنگدانه‌بندی", "سنگ‌های تزئینی و ساختمانی معدنی"],
    "کانی غیرفلزی و مصالح ساختمانی": ["سیمان، گچ و آهک", "کاشی، سرامیک و چینی بهداشتی", "آجر، سفال و بلوک ساختمانی", "شیشه ساختمانی و صنعتی", "بتن آماده و قطعات پیش‌ساخته"],
    "صنایع فلزی": ["ریخته‌گری و ذوب فلزات", "نورد، ورق‌کاری و پروفیل", "اسکلت فلزی و سازه‌های مهندسی", "تراشکاری، فرزکاری و قالب‌سازی فلزی", "یراق‌آلات، لوله و اتصالات فلزی", "مفتول، توری و پرسکاری فلزات"],
    "ماشین‌سازی و تجهیزات": ["ماشین‌آلات صنایع غذایی و دارویی", "ماشین‌آلات کشاورزی و باغبانی", "دیگ بخار، چیلر و تجهیزات حرارتی/برودتی", "پمپ، کمپرسور و دمنده‌ها", "نوار نقاله و تجهیزات جابجایی مواد", "ابزار دقیق و خطوط تولید سفارشی"],
    "خودرو و قطعه‌سازی": ["قطعات موتوری و گیربکس", "سیستم تعلیق، ترمز و فرمان", "قطعات برقی و الکترونیک خودرو", "تزئینات داخلی و بدنه خودرو", "ماشین‌آلات ترابری سنگین و کشاورزی"],
    "برق، الکترونیک و مخابرات": ["تابلوهای برق صنعتی و اتوماسیون", "تجهیزات روشنایی، چراغ و ال‌ای‌دی", "سیم، کابل و اتصالات الکتریکی", "بردهای الکترونیکی (PCB) و مونتاژ", "تجهیزات مخابراتی، رادیویی و شبکه", "یوپی‌اس، ترانسفورماتور و اینورتر"],
    "لوازم خانگی": ["لوازم خانگی بزرگ (یخچال، لباسشویی، گاز)", "لوازم صوتی و تصویری", "لوازم خانگی کوچک و برقی آشپزخانه", "ظروف و ابزار آشپزخانه", "شیرآلات و تجهیزات بهداشتی خانگی"],
    "انرژی‌های تجدیدپذیر": ["پنل‌ها و سازه‌های خورشیدی", "توربین‌ها و ژنراتورهای بادی", "باتری‌ها و سامانه‌های ذخیره انرژی", "آبگرمکن‌های خورشیدی و سامانه‌های بیوگاز", "اینورترها و کنترل‌کننده‌های شارژ خورشیدی"],
    "بازیافت و محیط‌زیست": ["بازیافت پلاستیک و مواد پلیمری", "بازیافت فلزات و ضایعات الکترونیکی", "بازیافت کاغذ، مقوا و شیشه", "تصفیه فاضلاب صنعتی و فیلتراسیون هوا", "تولید کمپوست از پسماندهای آلی"],
    "فناوری و محصولات دانش‌بنیان": ["سامانه‌های اینترنت اشیاء (IoT) صنعتی", "نرم‌افزارها و سامانه‌های هوشمندسازی", "نانومواد و مواد پیشرفته", "رباتیک و اتوماسیون هوشمند", "بیوتکنولوژی و سامانه‌های زیستی نوین"],
    "تجهیزات پزشکی": ["تجهیزات و ابزار جراحی و دندانپزشکی", "تجهیزات تصویربرداری و مانیتورینگ بیمار", "لوازم یکبار مصرف پزشکی و استریل", "پروتز، ارتز و ایمپلنت‌های ارتوپدی", "کیت‌های آزمایشگاهی و تشخیصی"],
    "چاپ سه‌بعدی و تولید پیشرفته": ["خدمات پرینت سه‌بعدی پلیمری و رزینی", "پرینت سه‌بعدی فلزی و ماسه‌ای", "اسکن و مهندسی معکوس سه‌بعدی", "تولید نمونه اولیه سریع (Rapid Prototyping)", "ساخت قطعات پیشرفته با تلرانس دقیق"],
    "خدمات فنی و مهندسی تولید": ["طراحی صنعتی و مدل‌سازی CAD/CAM", "خدمات آزمایشگاهی و آزمون استاندارد", "تعمیرات اساسی، اورهال و نگهداری", "پوشش‌دهی سطحی، آبکاری و عملیات حرارتی", "مشاوره خطوط تولید و بهره‌وری صنعتی"],
    "سایر تولیدات": ["تولیدات ترکیبی و چندرشته‌ای", "محصولات نوظهور و غیرطبقه‌بندی شده", "محصولات بسته‌بندی سفارشی", "صنایع جانبی و تکمیلی کارگاهی"]
}

INDUSTRY_GROUPS = list(INDUSTRY_CATALOG.keys())

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
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

    cursor.execute("PRAGMA table_info(workshops)")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    
    new_cols = {
        "sub_group": "TEXT",
        "product_name": "TEXT",
        "address": "TEXT",
        "postal_code": "TEXT",
        "landline": "TEXT",
        "email": "TEXT",
        "activity_status": "TEXT",
        "employees": "INTEGER DEFAULT 0",
        "current_capacity": "REAL DEFAULT 0",
        "target_market": "TEXT",
        "export_status": "TEXT",
        "licenses": "TEXT",
        "website": "TEXT",
        "ownership_type": "TEXT",
        "production_season": "TEXT",
        "notes": "TEXT"
    }

    for col, col_type in new_cols.items():
        if col not in existing_columns:
            cursor.execute(f"ALTER TABLE workshops ADD COLUMN {col} {col_type}")

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

def parse_number(val, default=0.0, is_int=False):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        num = val
    else:
        s = str(val).strip()
        if not s:
            return default
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        for i, (p, a) in enumerate(zip(persian_digits, arabic_digits)):
            s = s.replace(p, str(i)).replace(a, str(i))
        s = s.replace(",", "").replace("،", "").replace(" ", "").replace("_", "")
        try:
            num = float(s)
        except ValueError:
            return None
    if num < 0:
        return None
    return int(num) if is_int else num

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
        p = w.get("phone", "")
        w["masked_phone"] = f"{p[:4]}***{p[-4:]}" if len(p) >= 11 else "۰۹*********"
        
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

@app.route("/api/counties/<path:province>")
def api_counties(province):
    counties = PROVINCES_BY_COUNTY.get(province, [])
    return jsonify(counties)

@app.route("/register", methods=["GET", "POST"])
def register():
    form_data = {}
    selected_barriers = []

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        phone = request.form.get("phone", "").strip()
        province = request.form.get("province", "").strip()
        county = request.form.get("county", "").strip()
        industry_group = request.form.get("industry_group", "").strip()
        sub_group = request.form.get("sub_group", "").strip()
        product_name = request.form.get("product_name", "").strip()
        
        address = request.form.get("address", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        landline = request.form.get("landline", "").strip()
        email = request.form.get("email", "").strip()
        activity_status = request.form.get("activity_status", "").strip()
        ownership_type = request.form.get("ownership_type", "").strip()
        production_season = request.form.get("production_season", "").strip()
        
        unit = request.form.get("unit", "عدد در ماه").strip()
        price_currency = request.form.get("price_currency", "تومان").strip()
        target_market = request.form.get("target_market", "").strip()
        export_status = request.form.get("export_status", "").strip()
        licenses = request.form.get("licenses", "").strip()
        website = request.form.get("website", "").strip()
        notes = request.form.get("notes", "").strip()

        capacity = parse_number(request.form.get("capacity"), 0.0)
        current_capacity = parse_number(request.form.get("current_capacity"), 0.0)
        employees = parse_number(request.form.get("employees"), 0, is_int=True)
        price = parse_number(request.form.get("price"), 0.0)

        barriers_list = request.form.getlist("barriers")
        selected_barriers = barriers_list[:]
        other_barrier = request.form.get("other_barrier", "").strip()
        if other_barrier:
            barriers_list.append(f"سایر: {other_barrier}")
        barriers_str = " | ".join(barriers_list) if barriers_list else "بدون مانع اعلامی"

        form_data = {
            "title": title, "owner_name": owner_name, "phone": phone,
            "province": province, "county": county, "industry_group": industry_group,
            "sub_group": sub_group, "product_name": product_name, "address": address,
            "postal_code": postal_code, "landline": landline, "email": email,
            "activity_status": activity_status, "ownership_type": ownership_type,
            "production_season": production_season, "capacity": request.form.get("capacity", ""),
            "current_capacity": request.form.get("current_capacity", ""), "unit": unit,
            "employees": request.form.get("employees", ""), "price": request.form.get("price", ""),
            "price_currency": price_currency, "target_market": target_market,
            "export_status": export_status, "licenses": licenses, "website": website,
            "other_barrier": other_barrier, "notes": notes
        }

        errors = []
        if not title or not owner_name or not phone or not province or not county or not industry_group or not sub_group or not product_name:
            errors.append("لطفاً تمامی فیلدهای ستاره‌دار (عنوان، نام مسئول، تلفن، استان، شهرستان، گروه، زیرگروه و نام محصول) را پر کنید.")
        
        if province not in PROVINCES:
            errors.append("استان انتخاب‌شده نامعتبر است.")
        elif county not in PROVINCES_BY_COUNTY.get(province, []):
            errors.append("شهرستان انتخاب‌شده متعلق به استان مورد نظر نیست.")

        if industry_group not in INDUSTRY_CATALOG:
            errors.append("گروه تولیدی انتخاب‌شده نامعتبر است.")
        elif sub_group not in INDUSTRY_CATALOG.get(industry_group, []):
            errors.append("زیرگروه انتخاب‌شده متعلق به گروه صنعتی مورد نظر نیست.")

        if capacity is None or current_capacity is None or employees is None or price is None:
            errors.append("مقادیر عددی واردشده نامعتبر یا منفی هستند.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                "register.html",
                industry_groups=INDUSTRY_GROUPS,
                industry_catalog=INDUSTRY_CATALOG,
                provinces_by_county=PROVINCES_BY_COUNTY,
                form_data=form_data,
                selected_barriers=selected_barriers
            )

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO workshops (
                    title, owner_name, phone, province, county, industry_group,
                    sub_group, product_name, address, postal_code, landline, email,
                    activity_status, employees, capacity, current_capacity, unit,
                    price, price_currency, target_market, export_status, licenses,
                    website, ownership_type, production_season, barriers, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'در انتظار بررسی')
            """, (
                title, owner_name, phone, province, county, industry_group,
                sub_group, product_name, address, postal_code, landline, email,
                activity_status, employees, capacity, current_capacity, unit,
                price, price_currency, target_market, export_status, licenses,
                website, ownership_type, production_season, barriers_str, notes
            ))
            workshop_id = cursor.lastrowid

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
            flash("واحد تولیدی با موفقیت ثبت شد و در چرخه هم‌رسانی قرار گرفت.", "success")
            return redirect(url_for("index"))
        except Exception as e:
            conn.rollback()
            flash(f"خطا در ثبت اطلاعات واحد تولیدی: {str(e)}", "danger")
            return render_template(
                "register.html",
                industry_groups=INDUSTRY_GROUPS,
                industry_catalog=INDUSTRY_CATALOG,
                provinces_by_county=PROVINCES_BY_COUNTY,
                form_data=form_data,
                selected_barriers=selected_barriers
            )
        finally:
            conn.close()

    return render_template(
        "register.html",
        industry_groups=INDUSTRY_GROUPS,
        industry_catalog=INDUSTRY_CATALOG,
        provinces_by_county=PROVINCES_BY_COUNTY,
        form_data=form_data,
        selected_barriers=selected_barriers
    )

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

# روت ورود مدیران با هر دو نام login و admin جهت تطابق ۱۰۰٪ با قالب‌ها
@app.route("/login", methods=["GET", "POST"])
@app.route("/admin", methods=["GET", "POST"], endpoint="admin")
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

# ==========================================
# ماژول هوشمند تطبیق بازار و صادرات
# ==========================================
@app.route("/export")
@app.route("/export-market", endpoint="export_market")
def export():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workshops ORDER BY id DESC")
    workshops = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    category_matches = {
        "کشاورزی و باغبانی": {
            "domestic": [
                "اتحادیه سراسری شرکت‌های توزیع و زنجیره‌ای کوروش و اتکا",
                "بنکداران عمده میدان مرکزی تره‌بار و صنایع بسته‌بندی",
                "هتل‌ها و رستوران‌های زنجیره‌ای فدک و پارسیان"
            ],
            "export": [
                "بازرگانان اقلیم کردستان (اربیل و سلیمانیه) - بسته‌بندی صادراتی",
                "شرکت‌های پخش عمان و امارات (دبی)",
                "تقاضای تأمین غلات و محصولات باغی روسیه و اوراسیا"
            ]
        },
        "صنایع دستی و تولیدات خرد": {
            "domestic": [
                "گالری‌های مرکزی میدان نقش‌جهان و ویترین‌های تهران",
                "تأمین هدایای سازمانی پایان سال بانک‌ها و هلدینگ‌های دولتی",
                "فروشگاه‌های زنجیره‌ای سوغات و گردشگری"
            ],
            "export": [
                "تجار قطری و عمانی برای آثار دست‌بافت نفیس",
                "پلتفرم‌های صادرات چمدانی و خرد صنایع دستی به اروپا",
                "بازارچه‌های صنایع دستی مرزی عراق و ترکیه"
            ]
        },
        "نساجی و پوشاک": {
            "domestic": ["بنکداران بازار بزرگ تهران و عمده‌فروشان استانی", "برندهای پوشاک سفارش‌دهنده دوخت اشتراکی"],
            "export": ["صادرکنندگان پوشاک به سلیمانیه و بصره عراق", "خریداران عمده آسیای میانه (ترکمنستان و قزاقستان)"]
        }
    }

    default_match = {
        "domestic": ["شبکه توزیع بنکداری کشوری", "تأمین‌کنندگان زنجیره ارزش استانی"],
        "export": ["صادرکنندگان فعال به بازار عراق و عمان", "هلدینگ‌های بازرگانی مرزی"]
    }

    matching_data = []
    for w in workshops:
        cat = w.get("industry_group", "")
        rules = category_matches.get(cat, default_match)
        matching_data.append({
            "unit": w,
            "domestic_buyers": rules["domestic"],
            "export_targets": rules["export"]
        })

    return render_template("export.html", matching_data=matching_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
