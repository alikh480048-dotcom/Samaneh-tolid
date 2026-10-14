import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS producers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            province TEXT,
            craft_type TEXT,
            capacity TEXT,
            status TEXT DEFAULT 'فعال',
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شبکه هوشمند توسعه تولید | ثبت واحد تولیدی</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --primary: #10b981;
            --primary-hover: #059669;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --gold: #f59e0b;
        }
        * { box-sizing: border-box; font-family: 'Vazirmatn', sans-serif; margin: 0; padding: 0; }
        body { background-color: var(--bg); color: var(--text-main); padding: 15px; }
        .container { max-width: 600px; margin: 0 auto; }
        
        .header { text-align: center; margin-bottom: 20px; padding: 10px; }
        .header h1 { font-size: 20px; color: var(--text-main); }
        .header p { font-size: 13px; color: var(--primary); margin-top: 5px; }
        
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 18px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
        .card-title { font-size: 16px; font-weight: bold; margin-bottom: 15px; color: var(--gold); display: flex; align-items: center; gap: 8px; }
        
        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 13px; margin-bottom: 6px; color: var(--text-muted); }
        input, select {
            width: 100%;
            padding: 10px 12px;
            background: #0b1120;
            border: 1px solid var(--border);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            outline: none;
        }
        input:focus, select:focus { border-color: var(--primary); }
        
        .btn-submit {
            width: 100%;
            padding: 12px;
            background: var(--primary);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 8px;
            transition: 0.2s;
        }
        .btn-submit:hover { background: var(--primary-hover); }

        .stat-badge {
            background: #022c22;
            color: #34d399;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            text-align: center;
            margin-bottom: 15px;
            border: 1px solid #065f46;
        }

        .unit-item {
            background: #0b1120;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .unit-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .unit-title { font-weight: bold; font-size: 14px; color: #fff; }
        .unit-craft { font-size: 12px; background: #1e3a8a; color: #93c5fd; padding: 2px 8px; border-radius: 4px; }
        .unit-details { font-size: 12px; color: var(--text-muted); line-height: 1.8; }
        .empty-state { text-align: center; color: var(--text-muted); font-size: 13px; padding: 20px 0; }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>سامانه هوشمند توسعه تولید</h1>
        <p>ماژول ۱: ورود و ثبت داده واحدهای تولیدی</p>
    </div>

    <!-- فرم ثبت اطلاعات -->
    <div class="card">
        <div class="card-title">📝 فرم ثبت مشخصات کارگاه و واحد تولیدی</div>
        <form method="POST" action="/add_producer">
            <div class="form-group">
                <label>نام کارگاه / واحد تولیدی *</label>
                <input type="text" name="workshop_name" placeholder="مثال: کارگاه سفال نقش جهان" required>
            </div>
            <div class="form-group">
                <label>نام و نام خانوادگی مدیر کارگاه *</label>
                <input type="text" name="owner_name" placeholder="مثال: علی رضایی" required>
            </div>
            <div class="form-group">
                <label>شماره تماس همراه *</label>
                <input type="tel" name="phone" placeholder="۰۹۱۲۳۴۵۶۷۸۹" required>
            </div>
            <div class="form-group">
                <label>استان محل فعالیت</label>
                <select name="province">
                    <option value="اصفهان">اصفهان</option>
                    <option value="تهران">تهران</option>
                    <option value="یزد">یزد</option>
                    <option value="فارس">فارس</option>
                    <option value="خراسان رضوی">خراسان رضوی</option>
                    <option value="همدان">همدان</option>
                    <option value="سایر">سایر استان‌ها</option>
                </select>
            </div>
            <div class="form-group">
                <label>رسته و حوزه صنایع دستی</label>
                <select name="craft_type">
                    <option value="سفال و سرامیک">سفال و سرامیک</option>
                    <option value="میناکاری و قلم‌زنی">میناکاری و فلزات</option>
                    <option value="فرش، گلیم و دستبافته‌ها">فرش و گلیم</option>
                    <option value="خاتم و چوب">خاتم‌کاری و صنایع چوب</option>
                    <option value="چرم دست‌دوز">چرم دست‌دوز</option>
                    <option value="پوشاک سنتی و سوزن‌دوزی">پوشاک سنتی و سوزن‌دوزی</option>
                    <option value="سایر">سایر موارد</option>
                </select>
            </div>
            <div class="form-group">
                <label>ظرفیت تولید تقریبی (ماهانه)</label>
                <input type="text" name="capacity" placeholder="مثال: ۲۰۰ قطعه در ماه">
            </div>
            <button type="submit" class="btn-submit">ثبت واحد تولیدی در سامانه</button>
        </form>
    </div>

    <!-- بخش نمایش خروجی داده‌های ذخیره شده -->
    <div class="card">
        <div class="card-title">📋 واحدهای تولیدی ثبت‌شده در سامانه</div>
        <div class="stat-badge">
            تعداد کل واحدهای ثبت شده: <strong>{{ producers|length }}</strong> واحد
        </div>

        {% if producers %}
            {% for p in producers %}
            <div class="unit-item">
                <div class="unit-header">
                    <span class="unit-title">{{ p[1] }}</span>
                    <span class="unit-craft">{{ p[5] }}</span>
                </div>
                <div class="unit-details">
                    👤 <strong>مدیر:</strong> {{ p[2] }} | 📞 <strong>تماس:</strong> {{ p[3] }}<br>
                    📍 <strong>استان:</strong> {{ p[4] }} | ⚙️ <strong>ظرفیت:</strong> {{ p[6] }}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">هنوز هیچ واحد تولیدی ثبت نشده است. از فرم بالا اولین واحد را ثبت کنید!</div>
        {% endif %}
    </div>
</div>

</body>
</html>
"""

@app.route('/')
def home():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM producers ORDER BY id DESC')
    producers = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, producers=producers)

@app.route('/add_producer', methods=['POST'])
def add_producer():
    workshop_name = request.form.get('workshop_name')
    owner_name = request.form.get('owner_name')
    phone = request.form.get('phone')
    province = request.form.get('province')
    craft_type = request.form.get('craft_type')
    capacity = request.form.get('capacity')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO producers (workshop_name, owner_name, phone, province, craft_type, capacity)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (workshop_name, owner_name, phone, province, craft_type, capacity))
    conn.commit()
    conn.close()

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
