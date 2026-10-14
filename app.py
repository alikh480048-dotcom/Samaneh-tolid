import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, url_for

app = Flask(__name__)
app.secret_key = "samaneh-tolid-secure-key"

# اطلاعات ۳۱ استان ایران و شهرهای مهم آن‌ها برای انتخاب پویا
PROVINCES_CITIES = {
    "تهران": ["تهران", "ري", "تجریش", "اسلامشهر", "شهریار", "دماوند"],
    "اصفهان": ["اصفهان", "کاشان", "نجف‌آباد", "شاهین‌شهر", "فلاورجان"],
    "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت حیدریه", "قوچان"],
    "فارس": ["شیراز", "مرودشت", "جهرم", "فسا", "کازرون"],
    "آذربایجان شرقی": ["تبریز", "مراغه", "مرند", "میانه", "اهر"],
    "مازندران": [
        "ساری",
        "بابل",
        "آمل",
        "قائم‌شهر",
        "تنکابن",
        "بابلسر",
        "بهشهر",
        "نوشهر",
    ],
    "گیلان": [
        "رشت",
        "انزلی",
        "لاهیجان",
        "لنگرود",
        "آستانه اشرفیه",
        "رودسر",
        "طالش",
    ],
    "گلستان": [
        "گرگان",
        "گنبد کاووس",
        "علی‌آباد کتول",
        "بندر ترکمن",
        "کردکوی",
        "آق‌قلا",
    ],
    "البرز": ["کرج", "فردیس", "هشتگرد", "نظرآباد", "طالقان"],
    "خوزستان": ["اهواز", "دزفول", "آبادان", "خرمشهر", "ماهشهر"],
    "سمنان": ["سمنان", "شاهرود", "دامغان", "گرمسار"],
    "یزد": ["یزد", "میبد", "اردکان", "بافق"],
    "قم": ["قم"],
    "قزوین": ["قزوین", "تاکستان", "بوئین‌زهرا"],
    "کرمان": ["کرمان", "سیرجان", "رفسنجان", "جیرفت", "بم"],
    "هرمزگان": ["بندرعباس", "قشم", "میناب", "بندرلنگه"],
    "سیستان و بلوچستان": ["زاهدان", "زابل", "ایرانشهر", "چابهار"],
    "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "سنقر", "پاوه"],
    "لرستان": ["خرم‌آباد", "بروجرد", "دورود", "الیگودرز"],
    "کردستان": ["سنندج", "سقز", "مریوان", "بانە"],
    "همدان": ["همدان", "ملایر", "نهاوند", "تویسرکان"],
    "مرکزی": ["اراک", "ساوه", "خمین", "محلات"],
    "اردبیل": ["اردبیل", "پارس‌آباد", "مشگین‌شهر", "خلخال"],
    "بوشهر": ["بوشهر", "برازجان", "بندر گناوه", "کنگان"],
    "چهارمحال و بختیاری": ["شهرکرد", "بروجن", "لردگان", "فارسان"],
    "کهگیلویه و بویر احمد": ["یاسوج", "دوگنبدان", "دهدشت"],
    "خراسان شمالی": ["بجنورد", "شیروان", "اسفراین"],
    "خراسان جنوبی": ["بیرجند", "قائن", "طبس", "فردوس"],
    "زنجان": ["زنجان", "ابهر", "خدابنده"],
    "ایلام": ["ایلام", "دهلران", "ایوان", "آبدانان"],
    "بوشهر": ["بوشهر", "برازجان", "بندر گناوه"],
}

CRAFTS_CATEGORIES = [
    "فرش و گلیم و دستبافته‌ها",
    "سفال و سرامیک",
    "معرق و منبت و مصنوعات چوبی",
    "رودوزی‌های سنتی و پوشاک محلی",
    "زيورآلات سنتی و سنگ‌های قیمتی",
    "صنایع دستی حصیری و چوبی",
    "محصولات خوراکی و بومی (روستا)",
    "سایر رسته‌های صنایع دستی",
]


def init_db():
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  # جدول کارگاه‌ها / واحدهای تولیدی
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS producers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_name TEXT NOT NULL,
            manager_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            province TEXT NOT NULL,
            city TEXT NOT NULL,
            craft_type TEXT NOT NULL,
            capacity TEXT NOT NULL,
            unit_type TEXT NOT NULL,
            address TEXT
        )
    """)
  # جدول محصولات کاتالوگ
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producer_id INTEGER,
            product_name TEXT NOT NULL,
            price TEXT NOT NULL,
            min_order TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY(producer_id) REFERENCES producers(id)
        )
    """)
  # جدول جدید: استعلام‌ها و درخواست‌های خرید عمده (RFQ / White-Label)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            buyer_name TEXT NOT NULL,
            buyer_phone TEXT NOT NULL,
            quantity TEXT NOT NULL,
            destination_province TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'جدید',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)
  conn.commit()
  conn.close()


init_db()


# قالب جامع HTML همراه با رابط کاربری تب‌بندی شده و فرم استعلام امن
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شبکه هوشمند توسعه تولید و رفع موانع</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        :root {
            --primary: #10b981;
            --primary-dark: #059669;
            --secondary: #3b82f6;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-main); line-height: 1.6; padding-bottom: 80px; }
        
        header {
            background: linear-gradient(135deg, #065f46 0%, #047857 100%);
            color: white;
            padding: 20px 16px;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        header h1 { font-size: 1.25rem; font-weight: 700; margin-bottom: 5px; }
        header p { font-size: 0.8rem; opacity: 0.9; }

        .container { max-width: 800px; margin: 16px auto; padding: 0 12px; }

        /* فلش ممسیج‌ها */
        .flash {
            background: #d1fae5; color: #065f46; padding: 12px; border-radius: 8px;
            margin-bottom: 16px; font-size: 0.85rem; border: 1px solid #a7f3d0; text-align: center;
        }

        /* کارت‌ها و فرم‌ها */
        .card {
            background: var(--card-bg); border-radius: 12px; padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 16px; border: 1px solid var(--border);
        }
        .card h2 { font-size: 1rem; color: #0f172a; margin-bottom: 14px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }

        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 6px; color: var(--text-main); }
        input, select, textarea {
            width: 100%; padding: 10px 12px; border: 1px solid var(--border);
            border-radius: 8px; font-size: 0.85rem; background: #fff; outline: none; transition: all 0.2s;
        }
        input:focus, select:focus, textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(16,185,129,0.1); }
        
        button, .btn {
            background: var(--primary); color: white; border: none; padding: 12px;
            border-radius: 8px; font-size: 0.9rem; font-weight: 600; width: 100%; cursor: pointer;
            text-align: center; display: inline-block; text-decoration: none; transition: background 0.2s;
        }
        button:hover, .btn:hover { background: var(--primary-dark); }
        .btn-secondary { background: var(--secondary); }
        .btn-secondary:hover { background: #2563eb; }

        /* لیست‌ها و کارت‌های اقلام */
        .item-card {
            background: #fff; border: 1px solid var(--border); border-radius: 10px;
            padding: 12px; margin-bottom: 10px; font-size: 0.85rem; position: relative;
        }
        .item-title { font-weight: 700; color: #0f172a; font-size: 0.95rem; margin-bottom: 4px; }
        .badge { background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; display: inline-block; }
        .badge-secure { background: #fef3c7; color: #d97706; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; display: inline-block; }

        /* نوار ناوبری پایین صفحه (موبایل‌فرندلی) */
        .tab-bar {
            position: fixed; bottom: 0; left: 0; right: 0; background: white;
            display: flex; justify-content: space-around; padding: 8px 0;
            box-shadow: 0 -4px 10px rgba(0,0,0,0.08); border-top: 1px solid var(--border); z-index: 1000;
        }
        .tab-item {
            text-align: center; color: var(--text-muted); text-decoration: none;
            font-size: 0.75rem; flex: 1; display: flex; flex-direction: column; align-items: center;
        }
        .tab-item.active { color: var(--primary); font-weight: 700; }
        .tab-item span.icon { font-size: 1.2rem; margin-bottom: 2px; }

        /* مدال ساده یا فرم استعلام */
        .inquiry-box { background: #f0fdf4; border: 1px dashed var(--primary); padding: 10px; border-radius: 8px; margin-top: 10px; }
    </style>
    <script>
        // پویایی شهرستان‌ها بر اساس استان انتخاب شده
        const provincesCities = {{ provinces_json | safe }};
        function updateCities() {
            const provinceSelect = document.getElementById('province');
            const citySelect = document.getElementById('city');
            const selectedProvince = provinceSelect.value;
            
            citySelect.innerHTML = '';
            if (provincesCities[selectedProvince]) {
                provincesCities[selectedProvince].forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city;
                    opt.textContent = city;
                    citySelect.appendChild(opt);
                });
            }
        }
    </script>
</head>
<body>

    <header>
        <h1>شبکه هوشمند توسعه تولید و رفع موانع</h1>
        <p>مدیریت متمرکز زنجیره تأمین و اتصال امن به بازار</p>
    </header>

    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="flash">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- تب ۱: ثبت واحد تولیدی -->
        {% if active_tab == 'register' %}
        <div class="card">
            <h2>📝 ثبت مشخصات کارگاه و واحد تولیدی</h2>
            <form method="POST" action="/register">
                <div class="form-group">
                    <label>نام کارگاه / واحد تولیدی *</label>
                    <input type="text" name="workshop_name" required placeholder="مثال: کارگاه سفال نقش جهان">
                </div>
                <div class="form-group">
                    <label>نام و نام خانوادگی مدیر کارگاه *</label>
                    <input type="text" name="manager_name" required placeholder="مثال: علی رضایی">
                </div>
                <div class="form-group">
                    <label>شماره تماس همراه *</label>
                    <input type="text" name="phone" required placeholder="۰۹۱۲۳۴۵۶۷۸۹">
                </div>
                <div class="form-group">
                    <label>استان محل فعالیت *</label>
                    <select name="province" id="province" onchange="updateCities()" required>
                        {% for prov in provinces_cities.keys() %}
                        <option value="{{ prov }}">{{ prov }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>شهرستان *</label>
                    <select name="city" id="city" required>
                        <!-- با جاوااسکریپت پر می‌شود -->
                    </select>
                </div>
                <div class="form-group">
                    <label>رسته و حوزه صنایع دستی *</label>
                    <select name="craft_type" required>
                        {% for craft in crafts %}
                        <option value="{{ craft }}">{{ craft }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>ظرفیت تولید تقریبی (ماهانه) *</label>
                    <input type="text" name="capacity" required placeholder="مثال: ۲۰۰ قطعه در ماه">
                </div>
                <div class="form-group">
                    <label>نوع واحد *</label>
                    <select name="unit_type" required>
                        <option value="مشاغل خانگی">مشاغل خانگی</option>
                        <option value="کارگاه">کارگاه نیمه‌صنعتی / سنتی</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>آدرس دقیق روستا / شهر</label>
                    <textarea name="address" rows="2" placeholder="آدرس پستی..."></textarea>
                </div>
                <button type="submit">ثبت واحد تولیدی در سامانه</button>
            </form>
        </div>
        <script>window.onload = updateCities;</script>
        {% endif %}

        <!-- تب ۲: مدیریت کاتالوگ محصولات -->
        {% if active_tab == 'catalog' %}
        <div class="card">
            <h2>📦 ثبت محصول جدید در کاتالوگ سامانه</h2>
            <form method="POST" action="/add_product">
                <div class="form-group">
                    <label>انتخاب واحد تولیدی / کارگاه *</label>
                    <select name="producer_id" required>
                        {% for p in producers %}
                        <option value="{{ p[0] }}">{{ p[1] }} (مدیر: {{ p[2] }} - {{ p[4] }})</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>نام محصول *</label>
                    <input type="text" name="product_name" required placeholder="مثال: گلیم پشمی اعلا ۱*۲">
                </div>
                <div class="form-group">
                    <label>قیمت همکاری عمده (تومان) *</label>
                    <input type="text" name="price" required placeholder="مثال: ۱,۲۰۰,۰۰۰ تومان">
                </div>
                <div class="form-group">
                    <label>حداقل تعداد سفارش (MOQ) *</label>
                    <input type="text" name="min_order" required placeholder="مثال: ۱۰ عدد">
                </div>
                <div class="form-group">
                    <label>توضیحات و ویژگی‌ها</label>
                    <textarea name="description" rows="2" placeholder="رنگ‌بندی، جنس نخ، ابعاد..."></textarea>
                </div>
                <button type="submit" class="btn-secondary">افزودن محصول به کاتالوگ</button>
            </form>
        </div>
        {% endif %}

        <!-- تب ۳: بازار عمومی (مشتریان و خریداران عمده - مدل سفید/استعلام امن) -->
        {% if active_tab == 'market' %}
        <div class="card">
            <h2>🛒 کاتالوگ بازار و استعلام خرید عمده</h2>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 14px;">
                جهت حفظ زنجیره تأمین، ارتباطات مالی و تجاری منحصراً از طریق مدیریت سامانه انجام می‌شود.
            </p>
            
            {% for prod in products %}
            <div class="item-card">
                <div class="item-title">{{ prod[1] }}</div>
                <div style="margin-bottom: 6px;">
                    <span class="badge">قیمت عمده: {{ prod[2] }}</span>
                    <span class="badge" style="background:#f3e8ff; color:#7e22ce;">حداقل سفارش: {{ prod[3] }}</span>
                    <span class="badge-secure">🔒 تأییدشده سامانه</span>
                </div>
                <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">{{ prod[4] or 'توضیحات تکمیلی ثبت نشده است.' }}</p>
                
                <!-- فرم استعلام و درخواست خرید (White-Label / RFQ) -->
                <div class="inquiry-box">
                    <form method="POST" action="/submit_inquiry">
                        <input type="hidden" name="product_id" value="{{ prod[0] }}">
                        <p style="font-size: 0.8rem; font-weight: 700; color: var(--primary-dark); margin-bottom: 6px;">📋 ثبت درخواست استعلام قیمت و خرید عمده</p>
                        <div style="display: flex; gap: 8px; margin-bottom: 6px;">
                            <input type="text" name="buyer_name" placeholder="نام خریدار / شرکت" required style="font-size:0.8rem; padding:6px;">
                            <input type="text" name="buyer_phone" placeholder="شماره تماس" required style="font-size:0.8rem; padding:6px;">
                        </div>
                        <div style="display: flex; gap: 8px; margin-bottom: 6px;">
                            <input type="text" name="quantity" placeholder="تعداد درخواستی" required style="font-size:0.8rem; padding:6px;">
                            <input type="text" name="destination_province" placeholder="استان مقصد تحویل" required style="font-size:0.8rem; padding:6px;">
                        </div>
                        <button type="submit" style="padding: 6px; font-size: 0.8rem;">ارسال درخواست به مدیریت سامانه</button>
                    </form>
                </div>
            </div>
            {% else %}
            <p style="text-align: center; color: var(--text-muted); font-size: 0.85rem;">هنوز محصولی در کاتالوگ ثبت نشده است.</p>
            {% endfor %}
        </div>
        {% endif %}

        <!-- تب ۴: پنل مدیریت سفارش‌ها و استعلام‌ها (اختصاصی مدیر سامانه) -->
        {% if active_tab == 'admin' %}
        <div class="card">
            <h2>⚙️ پنل مدیریت استعلام‌ها و درخواست‌های بازار</h2>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 14px;">
                این بخش فقط برای مدیر سامانه قابل مشاهده است تا سفارش‌های عمده تاجران را پیگیری کند.
            </p>
            
            {% for inq in inquiries %}
            <div class="item-card" style="border-left: 4px solid var(--primary);">
                <div class="item-title">محصول: {{ inq[8] }} (شناسه کالا: {{ inq[1] }})</div>
                <p style="font-size: 0.8rem; margin-bottom: 4px;">👤 <b>خریدار:</b> {{ inq[2] }} | 📞 <b>تماس:</b> {{ inq[3] }}</p>
                <p style="font-size: 0.8rem; margin-bottom: 4px;">📦 <b>تعداد درخواستی:</b> {{ inq[4] }} | 📍 <b>مقصد:</b> {{ inq[5] }}</p>
                <p style="font-size: 0.8rem; margin-bottom: 4px; color: var(--text-muted);">💬 <b>توضیحات:</b> {{ inq[6] or 'ندارد' }}</p>
                <span class="badge" style="background: #fef08a; color: #854d0e;">وضعیت: {{ inq[7] }}</span>
            </div>
            {% else %}
            <p style="text-align: center; color: var(--text-muted); font-size: 0.85rem;">هنوز درخواستی ثبت نشده است.</p>
            {% endfor %}
        </div>
        {% endif %}

    </div>

    <!-- نوار پایین صفحه -->
    <div class="tab-bar">
        <a href="/?tab=register" class="tab-item {% if active_tab == 'register' %}active{% endif %}">
            <span class="icon">📝</span>ثبت کارگاه
        </a>
        <a href="/?tab=catalog" class="tab-item {% if active_tab == 'catalog' %}active{% endif %}">
            <span class="icon">📦</span>ثبت محصول
        </a>
        <a href="/?tab=market" class="tab-item {% if active_tab == 'market' %}active{% endif %}">
            <span class="icon">🛒</span>بازار عمومی
        </a>
        <a href="/?tab=admin" class="tab-item {% if active_tab == 'admin' %}active{% endif %}">
            <span class="icon">⚙️</span>مدیریت سفارش‌ها
        </a>
    </div>

</body>
</html>
"""


@app.route("/")
def index():
  active_tab = request.args.get("tab", "register")
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()

  cursor.execute("SELECT * FROM producers")
  producers = cursor.fetchall()

  # پیوست نام محصول به جدول استعلام‌ها جهت نمایش در پنل مدیر
  cursor.execute("""
        SELECT inquiries.*, products.product_name 
        FROM inquiries 
        JOIN products ON inquiries.product_id = products.id
        ORDER BY inquiries.id DESC
    """)
  inquiries = cursor.fetchall()

  cursor.execute("SELECT * FROM products ORDER BY id DESC")
  products = cursor.fetchall()
  conn.close()

  import json

  return render_template_string(
      HTML_TEMPLATE,
      active_tab=active_tab,
      provinces_cities=PROVINCES_CITIES,
      provinces_json=json.dumps(PROVINCES_CITIES, ensure_ascii=False),
      crafts=CRAFTS_CATEGORIES,
      producers=producers,
      products=products,
      inquiries=inquiries,
  )


@app.route("/register", methods=["POST"])
def register():
  workshop_name = request.form.get("workshop_name")
  manager_name = request.form.get("manager_name")
  phone = request.form.get("phone")
  province = request.form.get("province")
  city = request.form.get("city")
  craft_type = request.form.get("craft_type")
  capacity = request.form.get("capacity")
  unit_type = request.form.get("unit_type")
  address = request.form.get("address")

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO producers (workshop_name, manager_name, phone, province, city, craft_type, capacity, unit_type, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
      (
          workshop_name,
          manager_name,
          phone,
          province,
          city,
          craft_type,
          capacity,
          unit_type,
          address,
      ),
  )
  conn.commit()
  conn.close()

  flash("واحد تولیدی با موفقیت ثبت شد.")
  return redirect(url_for("index", tab="register"))


@app.route("/add_product", methods=["POST"])
def add_product():
  producer_id = request.form.get("producer_id")
  product_name = request.form.get("product_name")
  price = request.form.get("price")
  min_order = request.form.get("min_order")
  description = request.form.get("description")

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO products (producer_id, product_name, price, min_order, description)
        VALUES (?, ?, ?, ?, ?)
    """,
      (producer_id, product_name, price, min_order, description),
  )
  conn.commit()
  conn.close()

  flash("محصول با موفقیت به کاتالوگ اضافه شد.")
  return redirect(url_for("index", tab="catalog"))


@app.route("/submit_inquiry", methods=["POST"])
def submit_inquiry():
  product_id = request.form.get("product_id")
  buyer_name = request.form.get("buyer_name")
  buyer_phone = request.form.get("buyer_phone")
  quantity = request.form.get("quantity")
  destination_province = request.form.get("destination_province")
  notes = request.form.get("notes", "")

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO inquiries (product_id, buyer_name, buyer_phone, quantity, destination_province, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (
          product_id,
          buyer_name,
          buyer_phone,
          quantity,
          destination_province,
          notes,
      ),
  )
  conn.commit()
  conn.close()

  flash("درخواست خرید عمده شما ثبت شد؛ مدیریت سامانه به زودی با شما تماس می‌گیرد.")
  return redirect(url_for("index", tab="market"))


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
