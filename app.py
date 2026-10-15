import os
import sqlite3
from flask import Flask, g, redirect, render_template_string, request, url_for

app = Flask(__name__)
DATABASE = "samaneh.db"


def get_db():
  db = getattr(g, "_database", None)
  if db is None:
    db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
  return db


@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, "_database", None)
  if db is not None:
    db.close()


def init_db():
  with app.app_context():
    db = get_db()
    # جدول کارگاه‌ها و واحدهای تولیدی
    db.execute("""
            CREATE TABLE IF NOT EXISTS producers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                manager TEXT NOT NULL,
                phone TEXT NOT NULL,
                province TEXT NOT NULL,
                city TEXT NOT NULL,
                category TEXT NOT NULL,
                capacity TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    # جدول محصولات
    db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producer_id INTEGER NOT NULL,
                prod_name TEXT NOT NULL,
                prod_desc TEXT,
                min_order TEXT,
                price_range TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(producer_id) REFERENCES producers(id)
            )
        """)
    # جدول استعلامات و خریدهای عمده (مدل واسطه‌گری امن / RFQ)
    db.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                buyer_name TEXT NOT NULL,
                buyer_phone TEXT NOT NULL,
                buyer_company TEXT,
                quantity_needed TEXT NOT NULL,
                message TEXT,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
    db.commit()


# دیکشنری کامل استان‌ها و شهرستان‌ها (۳۱ استان کشور)
IRAN_DIVISIONS = {
    "تهران": [
        "تهران",
        "ری",
        "شمیرانات",
        "پردیس",
        "دماوند",
        "فیروزکوه",
        "اسلامشهر",
        "رباط‌کریم",
        "بهارستان",
        "ورامین",
        "پیشوا",
        "پاکدشت",
        "ملارد",
        "شهریار",
        "قدس",
    ],
    "اصفهان": [
        "اصفهان",
        "کاشان",
        "نجف‌آباد",
        "اصفهان",
        "خمینی‌شهر",
        "شاهین‌شهر",
        "شهرضا",
        "فلاورجان",
        "گلپایگان",
        "فریدن",
        "نائین",
        "نطنز",
        "اردستان",
        "سمیرم",
        "خوانسار",
        "برخوار",
        "تیران و کرون",
        "چادگان",
        "دهاقان",
        "خور و بیابانک",
    ],
    "خراسان رضوی": [
        "مشهد",
        "سبزوار",
        "نیشابور",
        "تربت حیدریه",
        "کاخک",
        "قوچان",
        "کاشمر",
        "تربت جام",
        "چناران",
        "خواف",
        "سرخس",
        "فریمان",
        "گناباد",
        "برکن آباد",
        "بجستان",
        "بردسکن",
        "تایباد",
        "رشتخوار",
        "زاوه",
        "خلیل‌آباد",
        "درگز",
        "کلات",
        "جغتای",
        "جوین",
        "داورزن",
        "باخرز",
    ],
    "فارس": [
        "شیراز",
        "مرودشت",
        "جهرم",
        "فسا",
        "داراب",
        "لارستان",
        "فیروزآباد",
        "اقلید",
        "abadeh",
        "آباده",
        "ممسنی",
        "کازرون",
        "استهبان",
        "نی‌ریز",
        "زرین‌دشت",
        "ارسنجان",
        "بوانات",
        "خرم‌بید",
        "رستم",
        "سپیدان",
        "کوار",
        "گراش",
        "لامرد",
        "مهر",
        "سرچهان",
        "بیضا",
        "پاسارگاد",
    ],
    "آذربایجان شرقی": [
        "تبریز",
        "مراغه",
        "مرند",
        "میانه",
        "اهر",
        "شبستر",
        "بناب",
        "سراب",
        "آذرشهر",
        "عجب‌شیر",
        "ملکان",
        "هریس",
        "چاراویماق",
        "خداآفرین",
        "ورزقان",
        "کلیبر",
        "جلفا",
        "هشترود",
        "سکان",
    ],
    "مازندران": [
        "ساری",
        "بابل",
        "آمل",
        "قائم‌شهر",
        "بهشهر",
        "بابلسر",
        "تنکابن",
        "نوشهر",
        "چالوس",
        "فریدونکنار",
        "رامسر",
        "نکا",
        "جویبار",
        "محمودآباد",
        "سوادکوه",
        "سوادکوه شمالی",
        "عباس‌آباد",
        "میاندرود",
        "کلاردشت",
        "گلوگاه",
        "سیمرغ",
    ],
    "گیلان": [
        "رشت",
        "بندرانزلی",
        "لاهیجان",
        "لنگرود",
        "هشتپر",
        "آستارا",
        "صومعه‌سرا",
        "آستانه اشرفیه",
        "رودسر",
        "فومن",
        "خمام",
        "شفت",
        "رضوانشهر",
        "ماسوله",
        "املش",
        "سیاهکل",
        "رضوان‌شهر",
        "رودبار",
    ],
    "گلستان": [
        "گرگان",
        "گنبد کاووس",
        "علی‌آباد کتول",
        "بندر ترکمن",
        "کردکوی",
        "آق‌قلا",
        "مینودشت",
        "آزادشهر",
        "کلاله",
        "مراوه‌تپه",
        "رامیان",
        "گمیشان",
        "گلیک",
    ],
    "البرز": [
        "کرج",
        "فردیس",
        "ساوجبلاغ",
        "نظرآباد",
        "طالقان",
        "اشتهارد",
        "چهارباغ",
    ],
    "آذربایجان غربی": [
        "ارومیه",
        "خوی",
        "بوکان",
        "مهاباد",
        "میاندوآب",
        "سلماس",
        "پیرانشهر",
        "نقده",
        "تکاب",
        "ماکو",
        "سردشت",
        "شاهین‌دژ",
        "اشنویه",
        "چایپاره",
        "پلدشت",
        "شوط",
        "باراندوز",
    ],
    "کرمان": [
        "کرمان",
        "سیرجان",
        "رفسنجان",
        "جیرفت",
        "بم",
        "زرند",
        "شهربابک",
        "بافت",
        "بردسیر",
        "کهنوج",
        "راور",
        "منوجان",
        "عنبرآباد",
        "رودبار جنوب",
        "فهرج",
        "قلعه‌گنج",
        "نرماشیر",
        "ارزوئیه",
        "رابر",
    ],
    "خوزستان": [
        "اهواز",
        "دزفول",
        "آبادان",
        "خرمشهر",
        "ماهشهر",
        "ایذه",
        "بهبهان",
        "شوشتر",
        "مسجدسلیمان",
        "شوش",
        "رامهرمز",
        "شادگان",
        "سوسنگرد",
        "بندر امام خمینی",
        "گتوند",
        "باغ‌ملک",
        "هندیجان",
        "لالی",
        "اندیکا",
        "هویزه",
        "آغاجاری",
        "حمیدیه",
    ],
    "قم": ["قم"],
    "کرمانشاه": [
        "کرمانشاه",
        "اسلام‌آباد غرب",
        "جوانرود",
        "سرپل ذهاب",
        "سنقر",
        "کنگاور",
        "پاوه",
        "صحنه",
        "گیلانغرب",
        "هرسین",
        "ڕوانسر",
        "دالاهو",
        "ثلاث باباجانی",
        "قصر شیرین",
    ],
    "سیستان و بلوچستان": [
        "زاهدان",
        "زابل",
        "ایرانشهر",
        "چابهار",
        "خاش",
        "سراوان",
        "کنارک",
        "نیک‌شهر",
        "سرباز",
        "راسک",
        "میرجاوه",
        "دلگان",
        "هامون",
        "نیمروز",
        "هیرمند",
        "فنوج",
        "قصرقند",
    ],
    "یزد": [
        "یزد",
        "میبد",
        "اردکان",
        "بافق",
        "مهریز",
        "ابرکوه",
        "اشکذر",
        "تفت",
        "هرات",
        "مروست",
    ],
    "هرمزگان": [
        "بندرعباس",
        "میناب",
        "قشم",
        "بندر لنگه",
        "کیش",
        "حاجی‌آباد",
        "رودان",
        "جاسک",
        "بستک",
        "پارسیان",
        "خمیر",
        "ابوموسی",
        "سیریک",
        "بشاگرد",
    ],
    "لرستان": [
        "خرم‌آباد",
        "بروجرد",
        "دورود",
        "ملایر",
        "الیگودرز",
        "کوهدشت",
        "پلدختر",
        "سلسله",
        "دلفان",
        "ازنا",
        "رومشکان",
        "چگنی",
    ],
    "مرکزی": [
        "اراک",
        "ساوه",
        "خمین",
        "محلات",
        "دلیجان",
        "تفرش",
        "آشتیان",
        "شازند",
        "زرندیه",
        "فراهان",
        "خنداب",
        "کمیجان",
    ],
    "همدان": [
        "همدان",
        "ملایر",
        "نهاوند",
        "کبودرآهنگ",
        "رزن",
        "اسدآباد",
        "تویسرکان",
        "بهار",
        "درگزین",
        "فامنین",
    ],
    "کردستان": [
        "سنندج",
        "سقز",
        "مریوان",
        "بانه",
        "قروه",
        "کامیاران",
        "بیجار",
        "دیواندره",
        "دهگلان",
        "سروآباد",
    ],
    "سمنان": [
        "سمنان",
        "شاهرود",
        "دامغان",
        "گرمسار",
        "مهدی‌شهر",
        "سرخه",
        "میامی",
        "آرادان",
    ],
    "چهارمحال و بختیاری": [
        "شهرکرد",
        "بروجن",
        "لردگان",
        "فارسان",
        "فرخ‌شهر",
        "هفشجان",
        "اردل",
        "کیار",
        "بن",
        "سامان",
    ],
    "خراسان شمالی": [
        "بجنورد",
        "شیروان",
        "اسفراین",
        "آشخانه",
        "جاجرم",
        "فاروج",
        "راز و جرگلان",
        "گرمه",
    ],
    "خراسان جنوبی": [
        "بیرجند",
        "قائن",
        "طبس",
        "فردوس",
        "نهبندان",
        "سرایان",
        "سربیشه",
        "بشرویه",
        "درمیان",
        "خوسف",
        "زیرکوه",
    ],
    "کهگیلویه و بویراحمد": [
        "یاسوج",
        "دوگنبدان",
        "دهدشت",
        "لیکک",
        "چرام",
        "لنده",
        "باشت",
        "سی‌سخت",
    ],
    "بوشهر": [
        "بوشهر",
        "برازجان",
        "بندر کنگان",
        "خورموج",
        "گناوه",
        "دلوار",
        "دیلم",
        "عسلویه",
        "جم",
        "خارگ",
        "بردخون",
    ],
    "زنجان": [
        "زنجان",
        "ابهر",
        "خرمدره",
        "قیدار",
        "هیدج",
        "صایین‌قلعه",
        "آب‌بر",
        "سلطانیه",
        "ماهنشان",
        "طارم",
    ],
    "قزوین": [
        "قزوین",
        "الوند",
        "تاکستان",
        "محمدیه",
        "آبیک",
        "بوئین‌زهرا",
        "آوج",
        "شال",
    ],
    "قم": ["قم"],
    "اردبیل": [
        "اردبیل",
        "پارس‌آباد",
        "مشگین‌شهر",
        "خلخال",
        "گرمی",
        "بیله‌سوار",
        "نمین",
        "ایرده",
        "اصلاندوز",
        "کوثر",
        "نیر",
    ],
};

HANDICRAFT_CATEGORIES = [
    "فرش و گلیم و دستبافته‌ها",
    "سفال و سرامیک",
    "معصوبه‌های چوبی و حصیری",
    "رودوزی‌های سنتی و زیورآلات",
    "محصولات چرمی دست‌دوز",
    "شیشه و کریستال سنتی",
    "سایر رسته‌های صنایع دستی",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شبکه هوشمند توسعه تولید و رفع موانع | پلتفرم ملی و بین‌المللی</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        brand: { 50: '#f0fdf4', 100: '#dcfce7', 500: '#22c55e', 600: '#16a34a', 700: '#15803d', 900: '#14532d' },
                        darkslate: { 800: '#1e293b', 900: '#0f172a' }
                    },
                    fontFamily: {
                        sans: ['Vazirmatn', 'sans-serif']
                    }
                }
            }
        }
    </script>
    <!-- Vazirmatn Font -->
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; background-color: #f8fafc; }
    </style>
    <script>
        const iranDivisions = {{ divisions_json | safe }};
        function updateCities() {
            const provinceSelect = document.getElementById('province');
            const citySelect = document.getElementById('city');
            const selectedProvince = provinceSelect.value;
            
            citySelect.innerHTML = '<option value="">انتخاب شهرستان...</option>';
            if (selectedProvince && iranDivisions[selectedProvince]) {
                iranDivisions[selectedProvince].forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city;
                    opt.textContent = city;
                    citySelect.appendChild(opt);
                });
            }
        }
    </script>
</head>
<body class="min-h-screen text-slate-800 flex flex-col justify-between">

    <!-- Header & Navigation -->
    <header class="bg-slate-900 text-white shadow-xl border-b border-slate-800 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center py-4">
                <!-- Brand Title & Badge -->
                <div class="flex items-center space-x-4 space-x-reverse">
                    <div class="bg-gradient-to-tr from-brand-600 to-emerald-400 p-2.5 rounded-xl shadow-lg">
                        <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                    </div>
                    <div>
                        <h1 class="text-xl sm:text-2xl font-black tracking-tight text-white">شبکه هوشمند توسعه تولید و رفع موانع</h1>
                        <p class="text-xs text-emerald-400 font-medium tracking-wide">پلتفرم تخصصی زنجیره تأمین، تنظیم بازار و اتصال امن صادراتی</p>
                    </div>
                </div>
                <!-- Global Badge -->
                <div class="hidden md:flex items-center space-x-2 space-x-reverse bg-slate-800/80 px-4 py-2 rounded-full border border-slate-700">
                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span class="text-xs font-semibold text-slate-300">موتور تجاری فعال (نسخه ملی)</span>
                </div>
            </div>

            <!-- Navigation Tabs -->
            <nav class="flex space-x-2 space-x-reverse overflow-x-auto pb-3 pt-1 border-t border-slate-800">
                <a href="/?tab=register" class="px-5 py-2.5 rounded-lg text-sm font-bold transition flex items-center space-x-2 space-x-reverse whitespace-nowrap {{ 'bg-brand-600 text-white shadow-md' if current_tab == 'register' else 'text-slate-300 hover:bg-slate-800 hover:text-white' }}">
                    <span>📝</span>
                    <span>ثبت کارگاه و واحد</span>
                </a>
                <a href="/?tab=product" class="px-5 py-2.5 rounded-lg text-sm font-bold transition flex items-center space-x-2 space-x-reverse whitespace-nowrap {{ 'bg-brand-600 text-white shadow-md' if current_tab == 'product' else 'text-slate-300 hover:bg-slate-800 hover:text-white' }}">
                    <span>📦</span>
                    <span>ثبت محصول در کاتالوگ</span>
                </a>
                <a href="/?tab=market" class="px-5 py-2.5 rounded-lg text-sm font-bold transition flex items-center space-x-2 space-x-reverse whitespace-nowrap {{ 'bg-brand-600 text-white shadow-md' if current_tab == 'market' else 'text-slate-300 hover:bg-slate-800 hover:text-white' }}">
                    <span>🛒</span>
                    <span>بازار عمومی و استعلام (RFQ)</span>
                </a>
                <a href="/?tab=admin" class="px-5 py-2.5 rounded-lg text-sm font-bold transition flex items-center space-x-2 space-x-reverse whitespace-nowrap {{ 'bg-brand-600 text-white shadow-md' if current_tab == 'admin' else 'text-slate-300 hover:bg-slate-800 hover:text-white' }}">
                    <span>⚙️</span>
                    <span>پنل مدیریت و سفارش‌ها (مدیر)</span>
                </a>
            </nav>
        </div>
    </header>

    <!-- Flash Messages -->
    {% if message %}
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 w-full">
        <div class="bg-emerald-50 border-r-4 border-brand-600 p-4 rounded-xl shadow-sm flex items-center justify-between">
            <div class="flex items-center space-x-3 space-x-reverse">
                <span class="text-2xl">✨</span>
                <p class="text-sm font-bold text-emerald-900">{{ message }}</p>
            </div>
        </div>
    </div>
    {% endif %}

    <!-- Main Content Area -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-grow">

        {% if current_tab == 'register' %}
        <!-- STATS CARDS -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center space-x-4 space-x-reverse">
                <div class="bg-brand-50 p-4 rounded-xl text-brand-600 text-2xl font-bold">🏭</div>
                <div>
                    <p class="text-xs text-slate-500 font-bold uppercase">واحدهای تولیدی ثبت‌شده</p>
                    <h3 class="text-2xl font-black text-slate-900 mt-1">{{ total_producers }} واحد</h3>
                </div>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center space-x-4 space-x-reverse">
                <div class="bg-indigo-50 p-4 rounded-xl text-indigo-600 text-2xl font-bold">📦</div>
                <div>
                    <p class="text-xs text-slate-500 font-bold uppercase">محصولات موجود در کاتالوگ</p>
                    <h3 class="text-2xl font-black text-slate-900 mt-1">{{ total_products }} محصول</h3>
                </div>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center space-x-4 space-x-reverse">
                <div class="bg-amber-50 p-4 rounded-xl text-amber-600 text-2xl font-bold">🛒</div>
                <div>
                    <p class="text-xs text-slate-500 font-bold uppercase">استعلامات عمده (RFQ)</p>
                    <h3 class="text-2xl font-black text-slate-900 mt-1">{{ total_inquiries }} درخواست</h3>
                </div>
            </div>
        </div>

        <!-- FORM & REGISTERED LIST GRID -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Register Form -->
            <div class="lg:col-span-1 bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200/80">
                <div class="border-b border-slate-100 pb-4 mb-6">
                    <h2 class="text-lg font-black text-slate-900 flex items-center space-x-2 space-x-reverse">
                        <span>📝</span>
                        <span>ثبت کارگاه و واحد تولیدی جدید</span>
                    </h2>
                    <p class="text-xs text-slate-500 mt-1">مشخصات هویتی و ظرفیت واحد خود را وارد کنید.</p>
                </div>

                <form method="POST" action="/add_producer" class="space-y-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">نام کارگاه / واحد تولیدی *</label>
                        <input type="text" name="name" required placeholder="مثال: کارگاه سفال نقش جهان" class="w-full text-sm px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:bg-white outline-none transition">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">نام و نام خانوادگی مدیر *</label>
                        <input type="text" name="manager" required placeholder="مثال: علی رضایی" class="w-full text-sm px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:bg-white outline-none transition">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">شماره تماس همراه *</label>
                        <input type="text" name="phone" required placeholder="۰۹۱۲۳۴۵۶۷۸۹" class="w-full text-sm px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:bg-white outline-none transition">
                    </div>

                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">استان *</label>
                            <select id="province" name="province" required onchange="updateCities()" class="w-full text-sm px-3 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none transition">
                                <option value="">انتخاب استان...</option>
                                {% for prov in divisions.keys() %}
                                <option value="{{ prov }}">{{ prov }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">شهرستان *</label>
                            <select id="city" name="city" required class="w-full text-sm px-3 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none transition">
                                <option value="">ابتدا استان را انتخاب کنید...</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">رسته صنایع دستی *</label>
                        <select name="category" required class="w-full text-sm px-3 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none transition">
                            <option value="">انتخاب رسته تخصصی...</option>
                            {% for cat in categories %}
                            <option value="{{ cat }}">{{ cat }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">ظرفیت تولید تقریبی (ماهانه) *</label>
                        <input type="text" name="capacity" required placeholder="مثال: ۲۰۰ قطعه یا ۳ تن در ماه" class="w-full text-sm px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:bg-white outline-none transition">
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">نوع واحد *</label>
                        <select name="unit_type" required class="w-full text-sm px-3 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none transition">
                            <option value="مشاغل خانگی">مشاغل خانگی</option>
                            <option value="کارگاه انفرادی">کارگاه انفرادی</option>
                            <option value="کارگاه گروهی / تعاونی">کارگاه گروهی / تعاونی</option>
                            <option value="واحد صنعتی کوچک">واحد صنعتی کوچک</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">آدرس دقیق پستی / روستا</label>
                        <textarea name="address" rows="2" placeholder="آدرس پستی محل کارگاه..." class="w-full text-sm px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:bg-white outline-none transition"></textarea>
                    </div>

                    <button type="submit" class="w-full bg-brand-600 hover:bg-brand-700 text-white font-black py-3.5 px-4 rounded-xl shadow-lg shadow-brand-500/30 transition duration-200 flex items-center justify-center space-x-2 space-x-reverse">
                        <span>🚀 ثبت نهایی واحد تولیدی در سامانه</span>
                    </button>
                </form>
            </div>

            <!-- List of Producers -->
            <div class="lg:col-span-2 space-y-4">
                <div class="bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200/80">
                    <div class="flex justify-between items-center mb-6">
                        <h2 class="text-lg font-black text-slate-900 flex items-center space-x-2 space-x-reverse">
                            <span>📋</span>
                            <span>بانک جامع واحدهای تولیدی ثبت‌شده ({{ producers|length }})</span>
                        </h2>
                    </div>

                    {% if producers|length == 0 %}
                    <div class="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                        <p class="text-slate-400 font-medium text-sm">هنوز هیچ واحد تولیدی ثبت نشده است. از فرم روبرو اقدام کنید.</p>
                    </div>
                    {% else %}
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {% for p in producers %}
                        <div class="bg-slate-50 p-5 rounded-2xl border border-slate-200/70 hover:shadow-md transition flex flex-col justify-between">
                            <div>
                                <div class="flex justify-between items-start mb-2">
                                    <h3 class="font-black text-base text-slate-900">{{ p.name }}</h3>
                                    <span class="bg-brand-100 text-brand-800 text-xs font-extrabold px-2.5 py-1 rounded-lg">{{ p.unit_type }}</span>
                                </div>
                                <p class="text-xs font-bold text-brand-700 mb-3">{{ p.category }}</p>
                                
                                <div class="space-y-1.5 text-xs text-slate-600">
                                    <p class="flex items-center space-x-2 space-x-reverse">
                                        <span class="font-bold">👤 مدیر:</span>
                                        <span>{{ p.manager }}</span>
                                    </p>
                                    <p class="flex items-center space-x-2 space-x-reverse">
                                        <span class="font-bold">📍 مکان:</span>
                                        <span>{{ p.province }} - {{ p.city }}</span>
                                    </p>
                                    <p class="flex items-center space-x-2 space-x-reverse">
                                        <span class="font-bold">⚙️ ظرفیت ماهانه:</span>
                                        <span class="text-slate-900 font-bold">{{ p.capacity }}</span>
                                    </p>
                                    {% if p.address %}
                                    <p class="flex items-center space-x-2 space-x-reverse">
                                        <span class="font-bold">🏠 آدرس:</span>
                                        <span class="truncate">{{ p.address }}</span>
                                    </p>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="mt-4 pt-3 border-t border-slate-200/60 flex justify-between items-center text-xs text-slate-400">
                                <span>کد شناسایی: #{{ p.id }}</span>
                                <span class="bg-emerald-50 text-emerald-700 font-bold px-2 py-0.5 rounded">تایید شده</span>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        {% elif current_tab == 'product' %}
        <!-- PRODUCT CATALOG REGISTRATION -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-1 bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-200/80">
                <div class="border-b border-slate-100 pb-4 mb-6">
                    <h2 class="text-lg font-black text-slate-900 flex items-center space-x-2 space-x-reverse">
                        <span>📦</span>
                        <span>ثبت محصول جدید در کاتالوگ</span>
                    </h2>
                    <p class="text-xs text-slate-500 mt-1">محصول تولیدی را به کارگاه مربوطه متصل کنید تا در بازار عمومی نمایش داده شود.</p>
                </div>

                {% if producers|length == 0 %}
                <div class="bg-amber-50 p-4 rounded-xl text-amber-800 text-xs font-bold">
                    ⚠️ ابتدا باید حداقل یک «واحد تولیدی» ثبت کنید تا بتوانید محصول به آن منتسب کنید.
                </div>
                {% else %}
                <form method="POST" action="/add_product" class="space-y-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">انتخاب کارگاه / واحد تولیدی *</label>
                        <select name="producer_id" required class="w-full text-sm px-3 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-brand-500 outline-none transition">
                            <option value="">انتخاب واحد تولیدی...</option>
                            {% for p in producers %}
