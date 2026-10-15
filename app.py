import os
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, url_for

app = Flask(__name__)
app.secret_key = "samaneh-tolid-secret-key"

DB_NAME = "database.db"

# لیست ۲۱ ماژول کلیدی بر اساس اینفوگرافی رسمی سامانه
MODULES = [
    {
        "id": 1,
        "title": "ثبت و مدیریت واحدهای تولیدی",
        "desc": (
            "ثبت‌نام خوداظهاری واحدها، اطلاعات پایه و ظرفیت‌ها، اطلاعات مکانی"
        ),
        "active": True,
    },
    {
        "id": 2,
        "title": "شناسایی و ثبت موانع تولید",
        "desc": "ثبت و دسته‌بندی موانع، اولویت‌بندی، تعیین علت‌های ریشه‌ای",
        "active": False,
    },
    {
        "id": 3,
        "title": "مدیریت پرونده‌ها و گردش کار",
        "desc": "ثبت و ارجاع درخواست‌ها، تعیین مسئول و پیگیری خودکار",
        "active": False,
    },
    {
        "id": 4,
        "title": "کارشناسان و مدیران جهادی",
        "desc": "شناسایی و تخصیص کارشناسان، بازدید و تشخیص میدانی",
        "active": False,
    },
    {
        "id": 5,
        "title": "بازار و تجارت هوشمند",
        "desc": "تحلیل بازار داخلی و خارجی، فرصت‌های صادراتی، قیمت و تقاضا",
        "active": False,
    },
    {
        "id": 6,
        "title": "زنجیره تأمین و مواد اولیه",
        "desc": "شناسایی تأمین‌کنندگان داخلی، پایش قیمت و موجودی مواد اولیه",
        "active": False,
    },
    {
        "id": 7,
        "title": "تسهیلات و منابع مالی",
        "desc": "معرفی منابع و بانک‌ها، درخواست و پیگیری تسهیلات، اعتبارسنچی",
        "active": False,
    },
    {
        "id": 8,
        "title": "حقوقی و مقرراتی",
        "desc": "رصد قوانین و مقررات، پاسخ به ابهامات حقوقی، پیگیری مجوزها",
        "active": False,
    },
    {
        "id": 9,
        "title": "بیمه و تأمین اجتماعی",
        "desc": (
            "بیمه‌های تولید و صادرات، رفع مشکلات بیمه‌ای، تسهیلات تأمین"
            " اجتماعی"
        ),
        "active": False,
    },
    {
        "id": 10,
        "title": "زیرساخت و انرژی",
        "desc": "برق و گاز و آب، حمل و نقل و لجستیک، توسعه زیرساخت‌های صنعتی",
        "active": False,
    },
    {
        "id": 11,
        "title": "فناوری و نوآوری",
        "desc": (
            "توسعه فناوری‌های تولید، دانش‌بنیان و تحقیق و توسعه، دیجیتال‌سازی"
        ),
        "active": False,
    },
    {
        "id": 12,
        "title": "بازار کار و نیروی انسانی",
        "desc": (
            "تأمین نیروی متخصص، آموزش و ارتقای مهارت، جذب و نگهداری نیرو"
        ),
        "active": False,
    },
    {
        "id": 13,
        "title": "محیط زیست و استانداردها",
        "desc": (
            "ر رعایت استانداردهای ملی و بین‌المللی، مدیریت پسماند و آلودگی"
        ),
        "active": False,
    },
    {
        "id": 14,
        "title": "صادرات و توسعه بازار",
        "desc": "بازاریابی بین‌المللی، حضور در نمایشگاه‌ها، تسهیل صادرات و واردات",
        "active": False,
    },
    {
        "id": 15,
        "title": "آموزش و توانمندسازی",
        "desc": "دوره‌های آموزشی تخصصی، آموزش مجازی و حضوری، انتقال تجربه",
        "active": False,
    },
    {
        "id": 16,
        "title": "اطلاعات و داده‌کاوی",
        "desc": "بانک اطلاعات جامع، تحلیل داده‌های تولید، پیش‌بینی و هوش مصنوعی",
        "active": False,
    },
    {
        "id": 17,
        "title": "ارزیابی و پایش عملکرد",
        "desc": "شاخص‌های کمی و کیفی، گزارش‌های دوره‌ای، تحلیل روندها",
        "active": False,
    },
    {
        "id": 18,
        "title": "توسعه منطقه‌ای و استانی",
        "desc": "پوشش ۳۱ استان کشور، شهرستان‌ها و مناطق ویژه، تخصیص منابع",
        "active": False,
    },
    {
        "id": 19,
        "title": "نظام حقوقی و امنیت",
        "desc": "حفاظت از داده‌ها، امنیت دسترسی‌ها، پشتیبان‌گیری و بازیابی",
        "active": False,
    },
    {
        "id": 20,
        "title": "ارتباطات بین‌المللی",
        "desc": "همکاری با نهادهای خارجی، دیپلماسی اقتصادی و تجاری",
        "active": False,
    },
    {
        "id": 21,
        "title": "ارتباطات و تعاملات بین دستگاهی",
        "desc": "همکاری با وزارتخانه‌ها، ارتباط با مجلس و دولت، هماهنگی قوه قضائیه",
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
    <!-- Header / Banner -->
    <header class="bg-gradient-to-b from-slate-900 to-slate-950 border-b border-slate-800 py-6 px-4 shadow-2xl">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="text-center md:text-right">
                <span class="bg-emerald-500/10 text-emerald-400 text-xs font-bold px-3 py-1 rounded-full border border-emerald-500/20">سامانه جامع ملی</span>
                <h1 class="text-2xl md:text-4xl font-extrabold mt-2 text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200">
                    شبکه هوشمند توسعه تولید و رفع موانع
                </h1>
                <p class="text-slate-400 text-sm mt-1">پلتفرمی جامع برای شناسایی، تحلیل، هماهنگی و رفع موانع تولید در کشور | توسعه پایدار</p>
            </div>
            <div class="flex items-center gap-3 bg-slate-900/80 border border-slate-800 px-4 py-2.5 rounded-2xl">
                <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
                <span class="text-xs text-slate-300 font-medium">سیستم آنلاین و فعال</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8 space-y-10">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="p-4 rounded-xl {% if category == 'success' %}bg-emerald-950/80 border border-emerald-500 text-emerald-200{% else %}bg-rose-950/80 border border-rose-500 text-rose-200{% endif %}">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- Active Module 1 Section: Workshop Registration -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur">
                <div class="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
                    <div>
                        <span class="text-xs text-emerald-400 font-bold bg-emerald-500/10 px-2.5 py-1 rounded">ماژول ۱</span>
                        <h2 class="text-xl font-bold mt-1 text-slate-100">ثبت و مدیریت واحدهای تولیدی</h2>
                    </div>
                </div>

                <form method="POST" action="/" class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">نام کارگاه / واحد تولیدی</label>
                            <input type="text" name="workshop_name" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">نام و نام خانوادگی مسئول</label>
                            <input type="text" name="owner_name" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">شماره تماس</label>
                            <input type="text" name="phone" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">استان</label>
                            <input type="text" name="province" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">شهر / شهرستان</label>
                            <input type="text" name="city" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">نوع هنر / صنایع دستی</label>
                            <input type="text" name="craft_type" required placeholder="مثلاً: سفالگری، میناکاری، گلیم..." class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-400 mb-1">تعداد شاغلین</label>
                            <input type="number" name="employees_count" value="1" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm">
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1">توضیحات تکمیلی یا موانع تولید</label>
                        <textarea name="description" rows="2" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none text-sm"></textarea>
                    </div>
                    <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold py-3 rounded-xl transition duration-200 shadow-lg shadow-emerald-600/20 text-sm">
                        ثبت و ذخیره اطلاعات کارگاه در سامانه
                    </button>
                </form>
            </div>

            <!-- Sidebar Info & 21 Modules Overview -->
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur flex flex-col justify-between">
                <div>
                    <h3 class="text-lg font-bold text-slate-200 mb-3">ساختار ۲۱ ماژول کلیدی سامانه</h3>
                    <p class="text-xs text-slate-400 mb-4 leading-relaxed">
                        این پلتفرم بر اساس معماری ۲۱ ماژول تخصصی جهت توانمندسازی صنایع دستی کوچک و خانگی طراحی شده است.
                    </p>
                    <div class="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                        {% for m in modules %}
                        <div class="p-3 rounded-xl border text-xs {% if m.active %}bg-emerald-950/40 border-emerald-500/50 text-emerald-300 font-semibold{% else %}bg-slate-950/50 border-slate-800 text-slate-300{% endif %}">
                            <span class="inline-block w-5 text-slate-500 font-bold">{{ m.id }}.</span> {{ m.title }}
                        </div>
                        {% endfor %}
                    </div>
                </div>
                <div class="mt-6 pt-4 border-t border-slate-800 text-center text-xs text-slate-500">
                    شبکه هوشمند توسعه تولید و رفع موانع © ۱۴۰۵
                </div>
            </div>
        </div>

        <!-- Workshops Records Table -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur">
            <h3 class="text-lg font-bold mb-4 text-slate-200">گزارش کارگاه‌های ثبت‌شده در سامانه</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-right text-sm">
                    <thead>
                        <tr class="border-b border-slate-800 text-slate-400 text-xs">
                            <th class="py-3 px-3">نام کارگاه</th>
                            <th class="py-3 px-3">مسئول</th>
                            <th class="py-3 px-3">استان / شهر</th>
                            <th class="py-3 px-3">حوزه فعالیت</th>
                            <th class="py-3 px-3">شاغلین</th>
                            <th class="py-3 px-3">توضیحات</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/60">
                        {% for w in workshops %}
                        <tr class="hover:bg-slate-800/30 text-xs">
                            <td class="py-3 px-3 font-semibold text-emerald-400">{{ w[1] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[2] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[4] }} / {{ w[5] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[6] }}</td>
                            <td class="py-3 px-3 text-slate-300">{{ w[7] }} نفر</td>
                            <td class="py-3 px-3 text-slate-400 truncate max-w-xs">{{ w[8] }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="py-8 text-center text-slate-500 text-xs">هنوز کارگاهی ثبت نشده است.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </main>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
  init_db()
  if request.method == "POST":
    try:
      workshop_name = request.form.get("workshop_name")
      owner_name = request.form.get("owner_name")
      phone = request.form.get("phone")
      province = request.form.get("province")
      city = request.form.get("city")
      craft_type = request.form.get("craft_type")
      employees_count = request.form.get("employees_count", 1)
      description = request.form.get("description", "")

      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO workshops (workshop_name, owner_name, phone, province, city, craft_type, employees_count, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              workshop_name,
              owner_name,
              phone,
              province,
              city,
              craft_type,
              employees_count,
              description,
          ),
      )
      conn.commit()
      conn.close()
      flash("کارگاه شما با موفقیت در شبکه ثبت شد.", "success")
    except Exception as e:
      flash(f"خطا در ثبت اطلاعات: {str(e)}", "error")
    return redirect(url_for("index"))

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM workshops ORDER BY id DESC")
  workshops = cursor.fetchall()
  conn.close()

  return render_template_string(
      TEMPLATE, modules=MODULES, workshops=workshops
  )


if __name__ == "__main__":
  init_db()
  app.run(host="0.0.0.0", port=5000)
