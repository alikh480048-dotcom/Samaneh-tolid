import os
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, url_for

app = Flask(__name__)
app.secret_key = "samaneh-tolid-secret-key"

DB_NAME = "database.db"


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


# HTML Template با طراحی زیبا، ریسپانسیو و مدرن (شامل فرم ثبت کارگاه و لیست خروجی‌ها)
TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه هوشمند توسعه تولید - ثبت کارگاه</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
    <div class="max-w-4xl mx-auto px-4 py-8">
        <header class="text-center mb-10">
            <span class="bg-emerald-500/10 text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/20">ماژول نخست: سامانه جامع ثبت کارگاه‌ها</span>
            <h1 class="text-3xl font-bold mt-3 text-emerald-400">شبکه هوشمند توسعه تولید و رفع موانع</h1>
            <p class="text-slate-400 text-sm mt-2">ثبت مشخصات کارگاه و واحدهای تولیدی صنایع دستی کوچک و خانگی</p>
        </header>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-6 p-4 rounded-xl {% if category == 'success' %}bg-emerald-900/50 border border-emerald-500 text-emerald-200{% else %}bg-rose-900/50 border border-rose-500 text-rose-200{% endif %}">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="bg-slate-800/80 backdrop-blur border border-slate-700/60 rounded-2xl p-6 shadow-xl mb-10">
            <h2 class="text-xl font-semibold mb-6 text-slate-200 border-b border-slate-700 pb-3">فرم ثبت‌نام واحد تولیدی / کارگاه</h2>
            
            <form method="POST" action="/" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">نام کارگاه / واحد تولیدی</label>
                        <input type="text" name="workshop_name" required class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">نام و نام خانوادگی مسئول</label>
                        <input type="text" name="owner_name" required class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">شماره تماس</label>
                        <input type="text" name="phone" required class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">استان</label>
                        <input type="text" name="province" required class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">شهر / شهرستان</label>
                        <input type="text" name="city" required class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">نوع هنر / صنایع دستی</label>
                        <input type="text" name="craft_type" required placeholder="مثلاً: میناکاری، گلیم‌بافی، معرق..." class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-sm text-slate-300 mb-1">تعداد شاغلین</label>
                        <input type="number" name="employees_count" value="1" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none">
                    </div>
                </div>
                <div>
                    <label class="block text-sm text-slate-300 mb-1">توضیحات تکمیلی یا موانع تولید</label>
                    <textarea name="description" rows="3" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 focus:border-emerald-500 focus:outline-none"></textarea>
                </div>
                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold py-3 rounded-xl transition duration-200 mt-4 shadow-lg shadow-emerald-600/20">
                    ثبت و ذخیره اطلاعات کارگاه
                </button>
            </form>
        </div>

        <div class="bg-slate-800/80 backdrop-blur border border-slate-700/60 rounded-2xl p-6 shadow-xl">
            <h2 class="text-xl font-semibold mb-4 text-slate-200">کارگاه‌های ثبت‌شده اخیر (آزمایش خروجی‌ها)</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-right text-sm">
                    <thead>
                        <tr class="border-b border-slate-700 text-slate-400">
                            <th class="py-3 px-2">نام کارگاه</th>
                            <th class="py-3 px-2">مسئول</th>
                            <th class="py-3 px-2">استان/شهر</th>
                            <th class="py-3 px-2">حوزه فعالیت</th>
                            <th class="py-3 px-2">شاغلین</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-700/50">
                        {% for w in workshops %}
                        <tr class="hover:bg-slate-700/20">
                            <td class="py-3 px-2 font-medium text-emerald-400">{{ w[1] }}</td>
                            <td class="py-3 px-2 text-slate-300">{{ w[2] }}</td>
                            <td class="py-3 px-2 text-slate-300">{{ w[4] }} / {{ w[5] }}</td>
                            <td class="py-3 px-2 text-slate-300">{{ w[6] }}</td>
                            <td class="py-3 px-2 text-slate-300">{{ w[7] }} نفر</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="py-6 text-center text-slate-500">هنوز کارگاهی ثبت نشده است. اولین مورد را ثبت کنید!</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
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
      flash("کارگاه شما با موفقیت ثبت شد و در جدول زیر قابل مشاهده است.", "success")
    except Exception as e:
      flash(f"خطا در ثبت اطلاعات: {str(e)}", "error")
    return redirect(url_for("index"))

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT * FROM workshops ORDER BY id DESC"
  )  # جدیدترین‌ها در ابتدا
  workshops = cursor.fetchall()
  conn.close()

  return render_template_string(TEMPLATE, workshops=workshops)


if __name__ == "__main__":
  init_db()
  app.run(host="0.0.0.0", port=5000)
