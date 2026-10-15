import os
import sqlite3
from flask import Flask, g, redirect, render_template_string, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "samaneh-tolid-secure-key")

DATABASE = "database.db"


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
    cursor = db.cursor()
    # جدول کارگاه‌ها و واحدهای تولیدی
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS workshops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workshop_name TEXT NOT NULL,
                manager_name TEXT NOT NULL,
                province TEXT NOT NULL,
                city TEXT NOT NULL,
                category TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    # جدول محصولات
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workshop_id INTEGER,
                product_name TEXT NOT NULL,
                price TEXT,
                capacity TEXT,
                image_url TEXT,
                FOREIGN KEY (workshop_id) REFERENCES workshops (id)
            )
        """)
    # جدول استعلام‌ها (RFQ)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                buyer_name TEXT NOT NULL,
                buyer_contact TEXT NOT NULL,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
    db.commit()


# راه‌اندازی اولیه پایگاه داده
init_db()

# قالب HTML یکپارچه با طراحی مدرن Enterprise B2B و پشتیبانی کامل از زبان فارسی
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شبکه هوشمند توسعه تولید و رفع موانع</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Vazirmatn', sans-serif; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex flex-col">
    <!-- هدر سامانه -->
    <header class="bg-slate-800 border-b border-slate-700 shadow-lg">
        <div class="max-w-7xl mx-auto px-4 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-3">
                <div class="bg-emerald-600 p-2.5 rounded-xl shadow-md text-white font-bold text-xl">ص</div>
                <div>
                    <h1 class="text-xl font-bold tracking-wide">شبکه هوشمند توسعه تولید</h1>
                    <p class="text-xs text-slate-400">مرکز ملی ارتباط بازار، ثبت کارگاه‌ها و رفع موانع صنایع دستی و خانگی</p>
                </div>
            </div>
            <nav class="flex items-center gap-3 bg-slate-900/60 p-1.5 rounded-xl border border-slate-700/60">
                <a href="/" class="px-4 py-2 rounded-lg text-sm font-medium transition {{ 'bg-emerald-600 text-white shadow' if tab == 'home' else 'text-slate-300 hover:bg-slate-800' }}">ثبت کارگاه و واحد</a>
                <a href="/?tab=catalog" class="px-4 py-2 rounded-lg text-sm font-medium transition {{ 'bg-emerald-600 text-white shadow' if tab == 'catalog' else 'text-slate-300 hover:bg-slate-800' }}">کاتالوگ محصولات</a>
                <a href="/?tab=admin" class="px-4 py-2 rounded-lg text-sm font-medium transition {{ 'bg-emerald-600 text-white shadow' if tab == 'admin' else 'text-slate-300 hover:bg-slate-800' }}">پنل مدیریت و آمار</a>
            </nav>
        </div>
    </header>

    <!-- محتوای اصلی -->
    <main class="flex-grow max-w-7xl w-full mx-auto px-4 py-8">
        
        <!-- تب اول: ثبت مشخصات کارگاه -->
        {% if tab == 'home' %}
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-1 space-y-6">
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-xl">
                    <h2 class="text-lg font-bold text-emerald-400 mb-2">راهنمای ثبت‌نام اولیه</h2>
                    <p class="text-sm text-slate-300 leading-relaxed">
                        با ثبت اطلاعات کارگاه یا واحد تولیدی خود در این سامانه، ضمن دسترسی به شبکه سراسری بازار B2B، از تسهیلات توسعه، بازاریابی صادراتی و رفع موانع تولید بهره‌مند شوید.
                    </p>
                    <div class="mt-6 p-4 bg-slate-900/60 rounded-xl border border-slate-700/50 space-y-3">
                        <div class="flex items-center gap-3 text-sm text-slate-300">
                            <span class="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">۱</span>
                            <span>تکمیل مشخصات فنی و استانی</span>
                        </div>
                        <div class="flex items-center gap-3 text-sm text-slate-300">
                            <span class="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">۲</span>
                            <span>افزودن محصولات و ظرفیت تولید</span>
                        </div>
                        <div class="flex items-center gap-3 text-sm text-slate-300">
                            <span class="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs">۳</span>
                            <span>اتصال مستقیم به خریداران عمده (RFQ)</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-2">
                <div class="bg-slate-800 p-8 rounded-2xl border border-slate-700 shadow-xl">
                    <h2 class="text-xl font-bold mb-6 pb-3 border-b border-slate-700 flex items-center gap-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                        فرم ثبت اطلاعات کارگاه / واحد تولیدی
                    </h2>
                    
                    {% if success_msg %}
                    <div class="mb-6 p-4 bg-emerald-900/50 border border-emerald-600 text-emerald-200 rounded-xl text-sm flex items-center gap-3">
                        <svg class="w-5 h-5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                        <span>{{ success_msg }}</span>
                    </div>
                    {% endif %}

                    <form method="POST" action="/register-workshop" class="grid grid-cols-1 md:grid-cols-2 gap-5">
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">نام کارگاه یا واحد تولیدی *</label>
                            <input type="text" name="workshop_name" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">نام مسئول / مدیر *</label>
                            <input type="text" name="manager_name" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">استان *</label>
                            <select name="province" id="province" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                                <option value="">انتخاب استان...</option>
                                <option value="تهران">تهران</option>
                                <option value="اصفهان">اصفهان</option>
                                <option value="خراسان رضوی">خراسان رضوی</option>
                                <option value="فارس">فارس</option>
                                <option value="آذربایجان شرقی">آذربایجان شرقی</option>
                                <option value="مازندران">مازندران</option>
                                <option value="گیلان">گیلان</option>
                                <option value="یزد">یزد</option>
                                <option value="کرمان">کرمان</option>
                                <option value="سایر استان‌ها">سایر استان‌ها</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">شهرستان / منطقه *</label>
                            <input type="text" name="city" required placeholder="مثلا: کاشان، میبد، شیراز..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">حوزه فعالیت *</label>
                            <select name="category" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                                <option value="ص صنایع دستی و هنرهای سنتی">صنایع دستی و هنرهای سنتی</option>
                                <option value="فرش و گلیم دستباف">فرش و گلیم دستباف</option>
                                <option value="محصولات خانگی و روستایی">محصولات خانگی و روستایی</option>
                                <option value="تولیدات خرد و کارگاهی">تولیدات خرد و کارگاهی</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">شماره تماس / موبایل *</label>
                            <input type="text" name="phone" required placeholder="۰۹۱۲..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">آدرس دقیق پستی</label>
                            <input type="text" name="address" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-sm font-medium text-slate-300 mb-1.5">توضیحات و ظرفیت‌ها</label>
                            <textarea name="description" rows="3" placeholder="توضیح مختصر درباره محصولات، توان تولید ماهانه و نیازمندی‌ها..." class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"></textarea>
                        </div>
                        <div class="md:col-span-2 pt-3">
                            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 px-6 rounded-xl transition shadow-lg shadow-emerald-900/40">
                                ثبت اطلاعات کارگاه و ورود به مرحله محصولات
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- تب دوم: کاتالوگ محصولات و ثبت محصول جدید -->
        {% elif tab == 'catalog' %}
        <div class="space-y-8">
            <div class="bg-slate-800 p-8 rounded-2xl border border-slate-700 shadow-xl">
                <h2 class="text-xl font-bold mb-6 pb-3 border-b border-slate-700 flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                    افزودن محصول جدید به کاتالوگ کارگاه
                </h2>
                <form method="POST" action="/add-product" class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-1.5">انتخاب کارگاه *</label>
                        <select name="workshop_id" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                            <option value="">انتخاب کنید...</option>
                            {% for w in workshops %}
                            <option value="{{ w.id }}">{{ w.workshop_name }} ({{ w.province }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-1.5">نام محصول *</label>
                        <input type="text" name="product_name" required class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-1.5">قیمت تقریبی (تومان)</label>
                        <input type="text" name="price" placeholder="مثلا: ۵۰۰,۰۰۰" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-slate-300 mb-1.5">ظرفیت تولید ماهانه</label>
                        <input type="text" name="capacity" placeholder="مثلا: ۲۰۰ عدد" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500">
                    </div>
                    <div class="md:col-span-4 pt-2">
                        <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 px-6 rounded-xl transition text-sm">
                            ثبت محصول در کاتالوگ
                        </button>
                    </div>
                </form>
            </div>

            <div>
                <h2 class="text-xl font-bold mb-6 flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                    کاتالوگ محصولات ثبت شده و استعلام بازار (RFQ)
                </h2>
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {% for p in products %}
                    <div class="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl flex flex-col justify-between">
                        <div class="p-6 space-y-4">
                            <div class="flex justify-between items-start">
                                <div>
                                    <span class="inline-block px-2.5 py-1 bg-emerald-900/60 text-emerald-300 text-xs rounded-lg mb-2">{{ p.province }} - {{ p.city }}</span>
                                    <h3 class="font-bold text-lg text-white">{{ p.product_name }}</h3>
                                </div>
                                <span class="text-xs text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg">کارگاه: {{ p.workshop_name }}</span>
                            </div>
                            <div class="space-y-1.5 text-sm text-slate-300 pt-2 border-t border-slate-700/60">
                                <div class="flex justify-between">
                                    <span class="text-slate-400">قیمت:</span>
                                    <span class="font-semibold text-emerald-400">{{ p.price if p.price else 'توافقی' }}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-slate-400">ظرفیت تولید:</span>
                                    <span>{{ p.capacity if p.capacity else 'مشخص نشده' }}</span>
                                </div>
                            </div>
                        </div>
                        <div class="bg-slate-900/80 p-4 border-t border-slate-700">
                            <form method="POST" action="/send-inquiry" class="space-y-3">
                                <input type="hidden" name="product_id" value="{{ p.id }}">
                                <input type="text" name="buyer_name" required placeholder="نام خریدار / شرکت" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-emerald-500">
                                <input type="text" name="buyer_contact" required placeholder="شماره تماس یا ایمیل" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-emerald-500">
                                <button type="submit" class="w-full bg-slate-700 hover:bg-emerald-600 text-slate-200 hover:text-white font-medium py-2 rounded-lg transition text-xs">
                                    ارسال استعلام خرید (RFQ)
                                </button>
                            </form>
                        </div>
                    </div>
                    {% else %}
                    <div class="col-span-full bg-slate-800 p-8 rounded-2xl border border-slate-700 text-center text-slate-400">
                        هنوز محصولی در سامانه ثبت نشده است. از فرم بالا برای ثبت محصول استفاده کنید.
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- تب سوم: پنل مدیریت و آمار -->
        {% elif tab == 'admin' %}
        <div class="space-y-8">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-xl flex items-center gap-4">
                    <div class="p-4 bg-emerald-600/20 text-emerald-400 rounded-xl">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
                    </div>
                    <div>
                        <div class="text-2xl font-bold">{{ stats.workshops_count }}</div>
                        <div class="text-xs text-slate-400">کارگاه‌های ثبت‌شده</div>
                    </div>
                </div>
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-xl flex items-center gap-4">
                    <div class="p-4 bg-blue-600/20 text-blue-400 rounded-xl">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>
                    </div>
                    <div>
                        <div class="text-2xl font-bold">{{ stats.products_count }}</div>
                        <div class="text-xs text-slate-400">محصولات کاتالوگ</div>
                    </div>
                </div>
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-xl flex items-center gap-4">
                    <div class="p-4 bg-amber-600/20 text-amber-400 rounded-xl">
                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
                    </div>
                    <div>
                        <div class="text-2xl font-bold">{{ stats.inquiries_count }}</div>
                        <div class="text-xs text-slate-400">استعلام‌های دریافتی (RFQ)</div>
                    </div>
                </div>
            </div>

            <div class="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden shadow-xl">
                <div class="p-6 border-b border-slate-700">
                    <h2 class="text-lg font-bold text-white">آخرین استعلام‌ها و ارتباطات تجاری بازار</h2>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-right text-sm">
                        <thead class="bg-slate-900 text-slate-400 border-b border-slate-700">
                            <tr>
                                <th class="p-4">خریدار / متقاضی</th>
                                <th class="p-4">راه ارتباطی</th>
                                <th class="p-4">محصول مورد نظر</th>
                                <th class="p-4">تاریخ ثبت</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-700/60">
                            {% for inq in inquiries %}
                            <tr>
                                <td class="p-4 font-medium text-white">{{ inq.buyer_name }}</td>
                                <td class="p-4 text-emerald-400">{{ inq.buyer_contact }}</td>
                                <td class="p-4 text-slate-300">{{ inq.product_name }}</td>
                                <td class="p-4 text-slate-400 text-xs">{{ inq.created_at }}</td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="4" class="p-8 text-center text-slate-400">هنوز استعلامی ثبت نشده است.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endif %}

    </main>

    <!-- فوتر -->
    <footer class="bg-slate-800 border-t border-slate-700 py-6 mt-12 text-center text-xs text-slate-400">
        <p>شبکه هوشمند توسعه تولید و رفع موانع | سامانه جامع مدیریت و اتصال زنجیره تامین صنایع خرد و خانگی</p>
    </footer>
</body>
</html>
"""


@app.route("/")
def index():
  tab = request.args.get("tab", "home")
  success_msg = request.args.get("success", "")
  db = get_db()

  workshops = db.execute("SELECT * FROM workshops ORDER BY id DESC").fetchall()
  products = db.execute("""
        SELECT products.*, workshops.workshop_name, workshops.province, workshops.city 
        FROM products 
        JOIN workshops ON products.workshop_id = workshops.id 
        ORDER BY products.id DESC
    """).fetchall()

  inquiries = db.execute("""
        SELECT inquiries.*, products.product_name 
        FROM inquiries 
        JOIN products ON inquiries.product_id = products.id 
        ORDER BY inquiries.id DESC
    """).fetchall()

  stats = {
      "workshops_count": db.execute(
          "SELECT COUNT(*) FROM workshops"
      ).fetchone()[0],
      "products_count": db.execute(
          "SELECT COUNT(*) FROM products"
      ).fetchone()[0],
      "inquiries_count": db.execute(
          "SELECT COUNT(*) FROM inquiries"
      ).fetchone()[0],
  }

  return render_template_string(
      HTML_TEMPLATE,
      tab=tab,
      success_msg=success_msg,
      workshops=workshops,
      products=products,
      inquiries=inquiries,
      stats=stats,
  )


@app.route("/register-workshop", methods=["POST"])
def register_workshop():
  workshop_name = request.form.get("workshop_name")
  manager_name = request.form.get("manager_name")
  province = request.form.get("province")
  city = request.form.get("city")
  category = request.form.get("category")
  phone = request.form.get("phone")
  address = request.form.get("address")
  description = request.form.get("description")

  db = get_db()
  db.execute(
      """
        INSERT INTO workshops (workshop_name, manager_name, province, city, category, phone, address, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
      (
          workshop_name,
          manager_name,
          province,
          city,
          category,
          phone,
          address,
          description,
      ),
  )
  db.commit()

  return redirect(
      url_for(
          "index",
          tab="catalog",
          success="کارگاه شما با موفقیت ثبت شد. اکنون می‌توانید محصولات خود را به کاتالوگ اضافه کنید.",
      )
  )


@app.route("/add-product", methods=["POST"])
def add_product():
  workshop_id = request.form.get("workshop_id")
  product_name = request.form.get("product_name")
  price = request.form.get("price")
  capacity = request.form.get("capacity")

  db = get_db()
  db.execute(
      """
        INSERT INTO products (workshop_id, product_name, price, capacity)
        VALUES (?, ?, ?, ?)
    """,
      (workshop_id, product_name, price, capacity),
  )
  db.commit()

  return redirect(
      url_for(
          "index",
          tab="catalog",
          success="محصول جدید با موفقیت به کاتالوگ اضافه شد.",
      )
  )


@app.route("/send-inquiry", methods=["POST"])
def send_inquiry():
  product_id = request.form.get("product_id")
  buyer_name = request.form.get("buyer_name")
  buyer_contact = request.form.get("buyer_contact")

  db = get_db()
  db.execute(
      """
        INSERT INTO inquiries (product_id, buyer_name, buyer_contact)
        VALUES (?, ?, ?)
    """,
      (product_id, buyer_name, buyer_contact),
  )
  db.commit()

  return redirect(
      url_for(
          "index",
          tab="catalog",
          success="استعلام خرید (RFQ) شما با موفقیت ثبت و به مدیر واحد ارسال شد.",
      )
  )


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
