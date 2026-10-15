import os
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, url_for

app = Flask(__name__)
app.secret_key = "secret-samaneh-tolid-574cc"

DB_NAME = "database.db"

# تعریف ۲۱ ماژول با رنگ‌بندی و دسته‌بندی دقیق مطابق اینفوگرافی اصلی
MODULES = [
    # گروه ۱: مدیریت پایه و ثبت (سبز فیروزه‌ای)
    {
        "id": 1,
        "title": "ثبت و مدیریت واحدهای تولیدی",
        "desc": "ثبت‌نام خوداظهاری واحدها، اطلاعات پایه، ظرفیت‌ها",
        "category": "ثبت و پایه",
        "color": "emerald",
        "active": True,
    },
    {
        "id": 2,
        "title": "شناسایی و ثبت موانع تولید",
        "desc": "ثبت موانع، اولویت‌بندی بر اساس اثرگذاری و ریشه‌یابی",
        "category": "ثبت و پایه",
        "color": "emerald",
        "active": False,
    },
    {
        "id": 3,
        "title": "مدیریت پرونده‌ها و گردش کار",
        "desc": "ثبت و ارجاع درخواست‌ها، تعیین مسئول و پیگیری خودکار",
        "category": "ثبت و پایه",
        "color": "emerald",
        "active": False,
    },
    # گروه ۲: نظارت و ارزیابی (آبی کلاسیک)
    {
        "id": 4,
        "title": "کارشناسان و مدیران جهادی",
        "desc": "تخصیص کارشناسان، بازدید و تشخیص میدانی",
        "category": "نظارت و مدیریت",
        "color": "sky",
        "active": False,
    },
    {
        "id": 17,
        "title": "ارزیابی و پایش عملکرد",
        "desc": "شاخص‌های کمی/کیفی، گزارش‌های دوره‌ای",
        "category": "نظارت و مدیریت",
        "color": "sky",
        "active": False,
    },
    {
        "id": 18,
        "title": "توسعه منطقه‌ای و استانی",
        "desc": "پوشش ۳۱ استان، شهرستان‌ها و مناطق ویژه",
        "category": "نظارت و مدیریت",
        "color": "sky",
        "active": False,
    },
    # گروه ۳: بازار و تجارت (نارنجی / کهربایی)
    {
        "id": 5,
        "title": "بازار و تجارت هوشمند",
        "desc": "تحلیل بازار داخلی و خارجی، قیمت و تقاضا",
        "category": "بازار و تجارت",
        "color": "amber",
        "active": False,
    },
    {
        "id": 6,
        "title": "زنجیره تأمین و مواد اولیه",
        "desc": "شناسایی تأمین‌کنندگان، پایش قیمت و موجودی",
        "category": "بازار و تجارت",
        "color": "amber",
        "active": False,
    },
    {
        "id": 14,
        "title": "صادرات و توسعه بازار",
        "desc": "بازاریابی بین‌المللی، دیپلماسی اقتصادی",
        "category": "بازار و تجارت",
        "color": "amber",
        "active": False,
    },
    # گروه ۴: منابع مالی و حقوقی (بنفش / ارغوانی)
    {
        "id": 7,
        "title": "تسهیلات و منابع مالی",
        "desc": "معرفی بانک‌ها، درخواست تسهیلات، اعتبارسنجی",
        "category": "مالی و حقوقی",
        "color": "purple",
        "active": False,
    },
    {
        "id": 8,
        "title": "حقوقی و مقرراتی",
        "desc": "رصد قوانین، پاسخ به ابهامات، استعلام‌ها",
        "category": "مالی و حقوقی",
        "color": "purple",
        "active": False,
    },
    {
        "id": 9,
        "title": "بیمه و تأمین اجتماعی",
        "desc": "بیمه‌های تولید و صادرات، رفع مشکلات بیمه‌ای",
        "category": "مالی و حقوقی",
        "color": "purple",
        "active": False,
    },
    # گروه ۵: زیرساخت و فناوری (سرخابی / صورتی)
    {
        "id": 10,
        "title": "زیرساخت و انرژی",
        "desc": "برق، گاز، آب، حمل و نقل و لجستیک",
        "category": "زیرساخت و فناوری",
        "color": "rose",
        "active": False,
    },
    {
        "id": 11,
        "title": "فناوری و نوآوری",
        "desc": "توسعه فناوری، دانش‌بنیان، دیجیتال‌سازی",
        "category": "زیرساخت و فناوری",
        "color": "rose",
        "active": False,
    },
    {
        "id": 13,
        "title": "محیط زیست و استانداردها",
        "desc": "استانداردهای ملی/بین‌المللی، تولید سبز",
        "category": "زیرساخت و فناوری",
        "color": "rose",
        "active": False,
    },
    # گروه ۶: نیروی انسانی و داده (سبز تیره / زیتونی)
    {
        "id": 12,
        "title": "بازار کار و نیروی انسانی",
        "desc": "تأمین نیروی متخصص، آموزش و مهارت‌آموزی",
        "category": "منابع انسانی و داده",
        "color": "teal",
        "active": False,
    },
    {
        "id": 15,
        "title": "آموزش و توانمندسازی",
        "desc": "دوره‌های تخصصی، انتقال تجربه و دانش",
        "category": "منابع انسانی و داده",
        "color": "teal",
        "active": False,
    },
    {
        "id": 16,
        "title": "اطلاعات و داده‌کاوی",
        "desc": "بانک اطلاعات جامع، هوش مصنوعی و تحلیل",
        "category": "منابع انسانی و داده",
        "color": "teal",
        "active": False,
    },
    # گروه ۷: امنیت و ارتباطات (خاکستری مقتدر)
    {
        "id": 19,
        "title": "نظام حقوقی و امنیت",
        "desc": "حفاظت از داده‌ها، امنیت دسترسی‌ها و پشتیبان‌گیری",
        "category": "امنیت و ارتباطات",
        "color": "slate",
        "active": False,
    },
    {
        "id": 20,
        "title": "ارتباطات بین‌المللی",
        "desc": "همکاری با نهادهای خارجی و دیپلماسی تجاری",
        "category": "امنیت و ارتباطات",
        "color": "slate",
        "active": False,
    },
    {
        "id": 21,
        "title": "ارتباطات بین دستگاهی",
        "desc": "همکاری با وزارتخانه‌ها، مجلس و قوای سه‌گانه",
        "category": "امنیت و ارتباطات",
        "color": "slate",
        "active": False,
    },
]


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS workshops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            province TEXT NOT NULL,
            city TEXT NOT NULL,
            craft_type TEXT NOT NULL,
            employees_count INTEGER,
            description TEXT
        )
    """)
  conn.commit()
  conn.close()


TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شبکه هوشمند توسعه تولید و رفع موانع</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
    <!-- Header Banner -->
    <header class="bg-gradient-to-r from-slate-900 via-sky-950 to-slate-900 border-b border-sky-800/40 py-8 px-4 shadow-2xl">
        <div class="max-w-7xl mx-auto flex flex-col items-center text-center">
            <div class="flex items-center gap-2 mb-3">
                <span class="bg-emerald-500/20 text-emerald-400 text-xs font-bold px-3 py-1 rounded-full border border-emerald-500/30">سامانه جامع ملی</span>
                <span class="bg-sky-500/20 text-sky-300 text-xs font-bold px-3 py-1 rounded-full border border-sky-500/30">۲۱ ماژول تخصصی</span>
            </div>
            <h1 class="text-3xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-white to-emerald-300 tracking-tight">
                شبکه هوشمند توسعه تولید و رفع موانع
            </h1>
            <p class="text-sky-200/80 text-sm md:text-base mt-3 max-w-2xl font-medium">
                پلتفرم جامع مدیریت، تحلیل و رفع موانع صنایع دستی و واحدهای تولیدی کوچک
            </p>
            <div class="flex flex-wrap justify-center gap-4 mt-5 text-xs text-slate-300 bg-slate-900/80 border border-slate-800 px-6 py-2.5 rounded-full shadow-inner">
                <span>🎯 طراح طرح: مهندس علی توشه</span>
                <span>•</span>
                <span>📈 رفع موانع امروز، جهش تولید فردا</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8 space-y-10">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="p-4 rounded-xl {% if category == 'success' %}bg-emerald-950/90 border border-emerald-500 text-emerald-200 shadow-lg{% else %}bg-rose-950/90 border border-rose-500 text-rose-200{% endif %} text-xs font-bold">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- Active Module 1 Section (Workshop Registration) -->
        <div class="bg-slate-900/90 border border-emerald-500/40 rounded-3xl p-6 md:p-8 shadow-2xl backdrop-blur relative overflow-hidden">
            <div class="absolute top-0 right-0 w-40 h-40 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="flex flex-col md:flex-row items-start md:items-center justify-between border-b border-slate-800 pb-4 mb-6 gap-2">
                <div>
                    <span class="text-xs text-emerald-400 font-bold bg-emerald-500/20 px-3 py-1 rounded-full border border-emerald-500/30">ماژول ۱ (فعال و عملیاتی)</span>
                    <h2 class="text-xl md:text-2xl font-black mt-2 text-slate-100">ثبت و مدیریت واحدهای تولیدی</h2>
                    <p class="text-xs text-slate-400 mt-1">ثبت‌نام خوداظهاری واحدهای صنایع دستی کوچک و خانگی در سامانه</p>
                </div>
            </div>

            <form method="POST" action="/" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">نام کارگاه / واحد تولیدی</label>
                        <input type="text" name="workshop_name" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">نام و نام خانوادگی مسئول</label>
                        <input type="text" name="owner_name" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">شماره تماس</label>
                        <input type="text" name="phone" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">استان</label>
                        <input type="text" name="province" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">شهر / شهرستان</label>
                        <input type="text" name="city" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">نوع هنر / صنایع دستی</label>
                        <input type="text" name="craft_type" required placeholder="مثلاً: سفالگری، میناکاری، گلیم..." class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">تعداد شاغلین</label>
                        <input type="number" name="employees_count" value="1" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">توضیحات تکمیلی یا موانع تولید</label>
                        <input type="text" name="description" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm" placeholder="مشکلات تامین مواد اولیه یا بازار فروش...">
                    </div>
                </div>
                <button type="submit" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-950 font-extrabold py-3.5 rounded-xl transition duration-200 shadow-lg shadow-emerald-600/20 text-sm">
                    ثبت و ذخیره اطلاعات کارگاه در سامانه
                </button>
            </form>
        </div>

        <!-- Workshops Records Table -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl backdrop-blur">
            <h3 class="text-lg font-bold text-slate-200 mb-1">گزارش کارگاه‌های ثبت‌شده (آزمایش خروجی‌های زنده)</h3>
            <p class="text-xs text-slate-400 mb-6">دیتابیس زنده SQLite سامانه</p>
            <div class="overflow-x-auto">
                <table class="w-full text-right text-sm">
                    <thead>
                        <tr class="border-b border-slate-800 text-slate-400 text-xs">
                            <th class="py-3 px-3">نام کارگاه</th>
                            <th class="py-3 px-3">مسئول</th>
                            <th class="py-3 px-3">استان / شهر</th>
                            <th class="py-3 px-3">حوزه فعالیت</th>
                            <th class="py-3 px-3">شاغلین</th>
                            <th class="py-3 px-3">موانع / توضیحات</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/60">
                        {% for w in workshops %}
                        <tr class="hover:bg-slate-800/30 text-xs">
                            <td class="py-3 px-3 font-bold text-emerald-400">{{ w[1] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[2] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[4] }} / {{ w[5] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[6] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[7] }} نفر</td>
                            <td class="py-3 px-3 text-slate-400 max-w-xs truncate">{{ w[8] }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="py-10 text-center text-slate-500 text-xs">هنوز کارگاهی ثبت نشده است. اولین مورد را ثبت کنید!</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 21 Modules Graphical Dashboard (Infographic Layout) -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl backdrop-blur">
            <div class="flex flex-col md:flex-row items-start md:items-center justify-between mb-6 gap-2">
                <div>
                    <h3 class="text-lg font-bold text-slate-200">داشبورد جامع ۲۱ ماژول اینفوگرافی سامانه</h3>
                    <p class="text-xs text-slate-400 mt-0.5">نقشه راه ساختار کلان شبکه هوشمند توسعه تولید و رفع موانع</p>
                </div>
                <span class="text-xs bg-sky-500/10 text-sky-400 border border-sky-500/20 px-3 py-1 rounded-full">امکانات مرحله‌به‌مرحله</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {% for m in modules %}
                <div class="p-4 rounded-2xl border transition duration-200 {% if m.active %}bg-emerald-950/60 border-emerald-500 shadow-lg shadow-emerald-950/50{% else %}bg-slate-950/60 border-slate-800 hover:border-slate-700{% endif %}">
                    <div class="flex items-center justify-between mb-2">
                        <span class="w-7 h-7 rounded-xl {% if m.active %}bg-emerald-500 
