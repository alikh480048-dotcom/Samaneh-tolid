import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# ایجاد دیتابیس و جدول کامل‌تر واحدهای تولیدی
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS producers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            province TEXT NOT NULL,
            city TEXT NOT NULL,
            workshop_type TEXT,
            craft_category TEXT NOT NULL,
            monthly_capacity TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>سامانه هوشمند توسعه تولید و رفع موانع</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/webfonts/Vazirmatn-font-face.css" rel="stylesheet">
    <style>
        :root {
            --primary: #1e3a8a;
            --primary-light: #3b82f6;
            --accent: #10b981;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-sub: #64748b;
            --border: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; }
        body { background: var(--bg); color: var(--text-main); padding-bottom: 70px; }
        
        .header {
            background: linear-gradient(135deg, #1e3a8a, #1e40af);
            color: #fff;
            padding: 18px 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(30, 58, 138, 0.15);
        }
        .header h1 { font-size: 1.15rem; font-weight: 700; margin-bottom: 4px; }
        .header p { font-size: 0.8rem; opacity: 0.85; }

        .container { max-width: 600px; margin: 0 auto; padding: 16px; }

        /* تب‌های ناوبری موبایلی */
        .tab-bar {
            display: flex;
            background: #fff;
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        .tab-btn {
            flex: 1;
            padding: 10px 8px;
            text-align: center;
            font-size: 0.85rem;
            font-weight: 600;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            background: transparent;
            color: var(--text-sub);
            transition: all 0.2s ease;
        }
        .tab-btn.active {
            background: var(--primary);
            color: #fff;
            box-shadow: 0 2px 6px rgba(30, 58, 138, 0.25);
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .card {
            background: var(--card-bg);
            border-radius: 14px;
            padding: 18px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
            margin-bottom: 16px;
        }
        .card-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 10px;
        }

        .form-group { margin-bottom: 14px; }
        .form-row { display: flex; gap: 10px; }
        .form-row .form-group { flex: 1; }
        label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-sub); margin-bottom: 6px; }
        input, select, textarea {
            width: 100%;
            padding: 11px 12px;
            border: 1.5px solid var(--border);
            border-radius: 9px;
            font-size: 0.9rem;
            background: #fff;
            color: var(--text-main);
            outline: none;
            transition: border-color 0.2s;
        }
        input:focus, select:focus, textarea:focus { border-color: var(--primary-light); }
        
        .btn-submit {
            width: 100%;
            padding: 13px;
            background: linear-gradient(135deg, #10b981, #059669);
            color: #fff;
            border: none;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }

        /* کارت نمایش داده‌ها */
        .item-card {
            background: #fff;
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 10px;
            border: 1px solid var(--border);
            border-right: 4px solid var(--primary-light);
        }
        .item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .item-title { font-size: 0.95rem; font-weight: 700; color: var(--primary); }
        .item-tag { font-size: 0.75rem; background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 6px; }
        .item-info { font-size: 0.8rem; color: var(--text-sub); line-height: 1.6; }
    </style>
</head>
<body>

    <div class="header">
        <h1>شبکه هوشمند توسعه تولید و رفع موانع</h1>
        <p>پلتفرم تخصصی پایش، توسعه و اتصال واحدهای تولیدی به بازار</p>
    </div>

    <div class="container">
        <!-- منوی جابجایی تب‌ها برای راحتی کار با موبایل -->
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchTab('form-tab')">📝 ثبت واحد جدید</button>
            <button class="tab-btn" onclick="switchTab('list-tab')">📋 بانک واحدها ({{ producers|length }})</button>
        </div>

        <!-- تب فرم ورود داده -->
        <div id="form-tab" class="tab-content active">
            <div class="card">
                <div class="card-title">📝 مشخصات کارگاه و واحد تولیدی</div>
                <form action="/add_producer" method="POST">
                    
                    <div class="form-group">
                        <label>نام واحد تولیدی / کارگاه *</label>
                        <input type="text" name="workshop_name" required placeholder="مثال: کارگاه میناکاری فیروزه">
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>نام مدیر یا صاحب کارگاه *</label>
                            <input type="text" name="owner_name" required placeholder="مثال: محمد امینی">
                        </div>
                        <div class="form-group">
                            <label>شماره تماس مستقیم *</label>
                            <input type="tel" name="phone" required placeholder="۰۹۱۲۳۴۵۶۷۸۹">
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>استان محل فعالیت *</label>
                            <select id="province-select" name="province" required onchange="updateCities()">
                                <option value="">انتخاب استان...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>شهرستان *</label>
                            <select id="city-select" name="city" required>
                                <option value="">ابتدا استان را انتخاب کنید</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label>رسته و حوزه فعالیت *</label>
                            <select name="craft_category" required>
                                <option value="">انتخاب رسته...</option>
                                <option value="فرش و گلیم و دستبافته‌ها">فرش، گلیم و زیرانداز سنتی</option>
                                <option value="سفال و سرامیک">سفال، سرامیک و لعاب‌کاری</option>
                                <option value="صنایع دستی چوبی">منبت، معرق، خاتم و خراطی</option>
                                <option value="صنایع دستی فلزی">قلم‌زنی، مسگری، ملیله و میناکاری</option>
                                <option value="پوشاک و نساجی سنتی">پته‌دوزی، سوزن‌دوزی، سرمه‌دوزی، چاپ سنتی</option>
                                <option value="محصولات چرمی دست‌دوز">چرم‌دوزی و حکاکی روی چرم</option>
                                <option value="حصیربافی و بامبوبافی">حصیربافی، کپوبافی و مرواربافی</option>
                                <option value="سنگ‌های قیمتی و زیورآلات سنتی">تراش سنگ، فیروزه‌کوبی، زیورآلات</option>
                                <option value="صنایع غذایی خانگی و سوغات">صنایع تبدیلی، عرقیات، خشکبار، سوغات</option>
                                <option value="سایر رسته‌های صنایع دستی">سایر رسته‌ها</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>نوع واحد</label>
                            <select name="workshop_type">
                                <option value="مشاغل خانگی">مشاغل خانگی / تولید در خانه</option>
                                <option value="کارگاه خرد و کوچک">کارگاه خرد و کوچک مستقل</option>
                                <option value="تعاونی / شبکه تولید">تعاونی تولیدی یا شبکه همکار</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>ظرفیت تقریبی تولید در ماه</label>
                        <input type="text" name="monthly_capacity" placeholder="مثال: ۱۵۰ قطعه ظروف میناکاری، ۳۰ متر مربع گلیم و...">
                    </div>

                    <div class="form-group">
                        <label>آدرس یا نشانی دقیق کارگاه / روستا</label>
                        <textarea name="address" rows="2" placeholder="شهر / روستا، خیابان، پلاک یا مشخصه محلی"></textarea>
                    </div>

                    <button type="submit" class="btn-submit">ثبت قطعی واحد در سامانه</button>
                </form>
            </div>
        </div>

        <!-- تب نمایش لیست واحدهای ثبت شده -->
        <div id="list-tab" class="tab-content">
            <div class="card">
                <div class="card-title">
                    📋 بانک واحدهای تولیدی
                    <span style="font-size:0.8rem; font-weight:normal; color:var(--text-sub); margin-right:auto;">
                        مجموع: {{ producers|length }} واحد
                    </span>
                </div>
                
                {% if not producers %}
                    <p style="text-align: center; color: var(--text-sub); font-size: 0.9rem; padding: 20px;">
                        هنوز اطلاعات هیچ واحدی ثبت نشده است.
                    </p>
                {% endif %}

                {% for p in producers %}
                    <div class="item-card">
                        <div class="item-header">
                            <span class="item-title">{{ p[1] }}</span>
                            <span class="item-tag">{{ p[7] }}</span>
                        </div>
                        <div class="item-info">
                            👤 مدیر: <b>{{ p[2] }}</b> | 📞 تماس: <a href="tel:{{ p[3] }}" style="color:var(--primary-light); text-decoration:none;">{{ p[3] }}</a><br>
                            📍 مکان: <b>{{ p[4] }} - {{ p[5] }}</b> | 🏷️ نوع: {{ p[6] }}<br>
                            ⚙️ ظرفیت ماهانه: {{ p[8] or 'نامشخص' }}<br>
                            {% if p[9] %}
                                🏠 آدرس: {{ p[9] }}
                            {% endif %}
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>

    </div>

    <!-- اسکریپت استان‌ها و شهرستان‌های ایران و مدیریت تب‌ها -->
    <script>
        const iranDivisions = {
            "آذربایجان شرقی": ["تبریز", "مراغه", "مرند", "میانه", "اهر", "بناب", "سراب", "آذرشهر", "اسکو", "شبستر", "کلیبر", "جلفا", "هشترود", "ورزقان", "هوراند", "چاراویماق", "عجب‌شیر", "خداآفرین"],
            "آذربایجان غربی": ["ارومیه", "خوی", "بوکان", "مهاباد", "میاندوآب", "سلماس", "پیرانشهر", "نقده", "سردشت", "شاهین‌دژ", "تکاب", "اشنویه", "شوط", "پلدشت", "چالدران", "چایپاره"],
            "اردبیل": ["اردبیل", "پارس‌آباد", "مشگین‌شهر", "خلخال", "گرمی", "نمین", "بیله‌سوار", "کوثر", "سرعین", "اصلاندوز"],
            "اصفهان": ["اصفهان", "کاشان", "خمینی‌شهر", "نجف‌آباد", "لنجان", "فلاورجان", "شاهین‌شهر", "شهرضا", "مبارکه", "برخوار", "آران و بیدگل", "گلپایگان", "فریدن", "تیران و کرون", "سمیرم", "خوانسار", "اردستان", "نطنز", "نایین", "فریدون‌شهر", "دهاقان", "چادگان", "خور و بیابانک", "بویین میاندشت"],
            "البرز": ["کرج", "فردیس", "ساوجبلاغ", "نظرآباد", "چهارباغ", "اشتهارد", "طالقان"],
            "ایلام": ["ایلام", "دهلران", "ایوان", "آبدانان", "چرداول", "دره‌شهر", "مهران", "ملکشاهی", "بدره", "هلیلان", "سیروان", "چوار"],
            "بوشهر": ["بوشهر", "دشتستان", "کنگان", "گناوه", "دشتی", "تنگستان", "عسلویه", "جم", "دیر", "دیلم"],
            "تهران": ["تهران", "شهریار", "اسلامشهر", "بهارستان", "ملارد", "پاکدشت", "ری", "قدس", "رباط‌کریم", "ورامین", "قرچک", "پردیس", "دماوند", "پیشوا", "شمیرانات", "فیروزکوه"],
            "چهارمحال و بختیاری": ["شهرکرد", "بروجن", "لردگان", "فارسان", "کیار", "اردل", "کوهرنگ", "سامان", "بن", "خانمیرزا"],
            "خراسان جنوبی": ["بیرجند", "قائنات", "طبس", "فردوس", "نهبندان", "درمیان", "سربیشه", "سرایان", "زیرکوه", "بشرویه", "خوسف"],
            "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت حیدریه", "کاشمر", "قوچان", "تربت جام", "تایباد", "چناران", "سرخس", "گناباد", "فریمان", "خواف", "درگز", "بردسکن", "طرقبه شاندیز", "زاوه", "بجستان"],
            "خراسان شمالی": ["بجنورد", "شیروان", "اسفراین", "مانه و سملقان", "جاجرم", "فاروج", "گرمه", "راز و جرگلان"],
            "خوزستان": ["اهواز", "دزفول", "آبادان", "بندر ماهشهر", "شوشتر", "ایذه", "بهبهان", "خرمشهر", "شوش", "شادگان", "دشت آزادگان", "مسجدسلیمان", "امیدیه", "باغ‌ملک", "رامهرمز", "گتوند", "لالی", "هندیجان", "هویزه", "اندیمشک"],
            "زنجان": ["زنجان", "ابهر", "خدابنده", "خرمدره", "طارم", "ماه‌نشان", "ایجرود", "سلطانیه"],
            "سمنان": ["سمنان", "شاهرود", "دامغان", "گرمسار", "مهدی‌شهر", "میامی", "سرخه", "آرادان"],
            "سیستان و بلوچستان": ["زاهدان", "چابهار", "زابل", "ایرانشهر", "سراوان", "خاش", "کنارک", "نیک‌شهر", "دشتیاری", "هیرمند", "زهک", "سیب و سوران", "دلگان", "مهرستان", "میرجاوه", "قصرقند"],
            "فارس": ["شیراز", "مرودشت", "کازرون", "فسا", "جهرم", "داراب", "لارستان", "آباده", "فیروزآباد", "ممسنی", "نی‌ریز", "اقلید", "استهبان", "سپیدان", "کوار", "زرین‌دشت", "قیر و کارزین", "لامرد", "مهر", "ارسنجان", "بوانات"],
            "قزوین": ["قزوین", "البرز", "تاکستان", "بویین‌زهرا", "آبیک", "آوج"],
            "قم": ["قم", "جعفرآباد", "کهک"],
            "کردستان": ["سنندج", "سقز", "مریوان", "بانه", "قروه", "کامیاران", "بیجار", "دیواندره", "دهگلان", "سروآباد"],
            "کرمان": ["کرمان", "سیرجان", "رفسنجان", "جیرفت", "بم", "زرند", "کهنوج", "شهربابک", "بافت", "بردسیر", "عنبرآباد", "راور", "منوجان", "رودبار جنوب", "قلعه گنج"],
            "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "سرپل ذهاب", "سنقر", "هرسین", "کنگاور", "جوانرود", "صحنه", "پاوه", "گیلانغرب", "روانسر", "دالاهو", "ثلاث باباجانی", "قصرشیرین"],
            "کهگیلویه و بویراحمد": ["بویراحمد (یاسوج)", "کهگیلویه (دهدشت)", "گچساران (دوگنبدان)", "دنا (سی‌سخت)", "بهمئی", "چرام", "باشت", "لنده", "مارگون"],
            "گلستان": ["گرگان", "گنبد کاووس", "علی‌آباد کتول", "آق‌قلا", "کلاله", "آزادشهر", "رامیان", "کردکوی", "ترکمن", "مینودشت", "گالیکش", "گمیشان", "مراوه‌تپه", "بندر گز"],
            "گیلان": ["رشت", "بندر انزلی", "لاهیجان", "تالش", "لنگرود", "رودسر", "صومعه‌سرا", "آستانه اشرفیه", "رودبار", "فومن", "آستارا", "رضوانشهر", "شفت", "ماسال", "سیاهکل", "املش"],
            "لرستان": ["خرم‌آباد", "بروجرد", "دورود", "الیگودرز", "کوهدشت", "دلفان", "ازنا", "پلدختر", "سلسله", "چگنی", "رومشکان"],
            "مازندران": ["ساری", "بابل", "آمل", "قائم‌شهر", "بهشهر", "چالوس", "نکا", "بابلسر", "تنکابن", "نوشهر", "فریدونکنار", "رامسر", "جویبار", "محمودآباد", "سوادکوه", "گلوگاه", "عباس‌آباد"],
            "مرکزی": ["اراک", "ساوه", "شازند", "خمین", "محلات", "زرندیه", "دلیجان", "تفرش", "فراهان", "کمیجان", "آشتیان", "خنداب"],
            "هرمزگان": ["بندرعباس", "میناب", "قشم", "بندرلنگه", "رودان", "بستک", "حاجی‌آباد", "جاسک", "بندر خمیر", "پارسیان", "سیریک", "بشاگرد", "بوموسی"],
            "همدان": ["همدان", "ملایر", "نهاوند", "اسدآباد", "تویسرکان", "بهار", "کبودرآهنگ", "رزن", "فامنین", "درگزین"],
            "یزد": ["یزد", "میبد", "اردکان", "مهریز", "ابرکوه", "بافق", "تفت", "خاتم", "اشکذر", "بهاباد", "مروست"]
        };

        // پر کردن کشویی استان‌ها در زمان لود صفحه
        const provSelect = document.getElementById("province-select");
        const citySelect = document.getElementById("city-select");

        for (const prov in iranDivisions) {
            let opt = document.createElement("option");
            opt.value = prov;
            opt.textContent = prov;
            provSelect.appendChild(opt);
        }

        // به‌روزرسانی کشویی شهرستان بر اساس استان انتخاب شده
        function updateCities() {
            const selectedProv = provSelect.value;
            citySelect.innerHTML = '<option value="">انتخاب شهرستان...</option>';
            
            if (selectedProv && iranDivisions[selectedProv]) {
                iranDivisions[selectedProv].forEach(city => {
                    let opt = document.createElement("option");
                    opt.value = city;
                    opt.textContent = city;
                    citySelect.appendChild(opt);
                });
            }
        }

        // مدیریت تغییر تب‌ها برای ساختار اپ موبایلی
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, workshop_name, owner_name, phone, province, city, workshop_type, craft_category, monthly_capacity, address FROM producers ORDER BY id DESC')
    producers = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, producers=producers)

@app.route('/add_producer', methods=['POST'])
def add_producer():
    workshop_name = request.form.get('workshop_name')
    owner_name = request.form.get('owner_name')
    phone = request.form.get('phone')
    province = request.form.get('province')
    city = request.form.get('city')
    workshop_type = request.form.get('workshop_type')
    craft_category = request.form.get('craft_category')
    monthly_capacity = request.form.get('monthly_capacity')
    address = request.form.get('address')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO producers (workshop_name, owner_name, phone, province, city, workshop_type, craft_category, monthly_capacity, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (workshop_name, owner_name, phone, province, city, workshop_type, craft_category, monthly_capacity, address))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
