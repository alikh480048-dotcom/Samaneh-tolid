import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'samaneh-secret-key-1403')

DATA_FILE = 'units_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

@app.route('/')
def index():
    units = load_data()
    units_count = len(units)
    
    total_capacity = 0
    for u in units:
        try:
            cap = float(u.get('nominal_capacity', 0))
            total_capacity += cap
        except (ValueError, TypeError):
            pass
            
    return render_template(
        'index.html',
        units=units,
        units_count=units_count,
        total_capacity=int(total_capacity)
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        unit_name = request.form.get('unit_name', '').strip()
        manager_name = request.form.get('manager_name', '').strip()
        phone = request.form.get('phone', '').strip()
        province = request.form.get('province', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        postal_code = request.form.get('postal_code', '').strip()
        category = request.form.get('category', '').strip()
        subcategory = request.form.get('subcategory', '').strip()
        product_name = request.form.get('product_name', '').strip()
        nominal_capacity = request.form.get('nominal_capacity', '0').strip()
        capacity_unit = request.form.get('capacity_unit', 'عدد در ماه').strip()
        activity_status = request.form.get('activity_status', 'فعال').strip()
        obstacles = request.form.get('obstacles', '').strip()

        if not unit_name or not manager_name or not phone or not province:
            flash('لطفاً تمامی فیلدهای الزامی ستاره‌دار را تکمیل نمایید.', 'error')
            return render_template('register.html')

        new_unit = {
            'id': int(datetime.now().timestamp()),
            'unit_name': unit_name,
            'manager_name': manager_name,
            'phone': phone,
            'province': province,
            'city': city,
            'address': address,
            'postal_code': postal_code,
            'category': category,
            'subcategory': subcategory,
            'product_name': product_name,
            'nominal_capacity': nominal_capacity,
            'capacity_unit': capacity_unit,
            'activity_status': activity_status,
            'obstacles': obstacles,
            'created_at': datetime.now().strftime('%Y/%m/%d %H:%M')
        }

        units = load_data()
        units.append(new_unit)
        save_data(units)

        flash('واحد تولیدی با موفقیت ثبت شد و در چرخه هم‌رسانی قرار گرفت.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/export-market', methods=['GET', 'POST'])
def export_market():
    units = load_data()
    unit_id = request.args.get('unit_id')
    selected_unit = None
    if unit_id:
        for u in units:
            if str(u.get('id')) == str(unit_id):
                selected_unit = u
                break

    sample_demands = [
        {"title": "تقاضای عمده ۵۰۰۰ جفت کفش دست‌دوز و چرم", "buyer": "هلدینگ تجاری سلیمانیه عراق", "target_country": "عراق", "volume": "۵,۰۰۰ جفت", "delivery_days": "۳۰ روزه", "badge": "فوری و نقدی"},
        {"title": "سفارش صادراتی البسه محلی و کارگاهی سبک", "buyer": "مرکز پخش اوراسیا مسکو", "target_country": "روسیه", "volume": "۲,۵۰۰ ست", "delivery_days": "۴۵ روزه", "badge": "تضمین ارزی"},
        {"title": "تأمین محصولات سنتی و صنایع دستی خرد", "buyer": "کنسرسیوم تجاری مسقط", "target_country": "عمان", "volume": "تیراژ نامحدود", "delivery_days": "مستمر", "badge": "سفارش رسمی"},
        {"title": "تقاضای ظروف سفالی و دکوری درجه یک", "buyer": "شرکت صادراتی باکو", "target_country": "آذربایجان", "volume": "۱,۲۰۰ قطعه", "delivery_days": "۲۰ روزه", "badge": "نقدی"},
    ]

    buyer_success = False
    if request.method == 'POST':
        buyer_success = True

    return render_template(
        'export.html',
        units=units,
        selected_unit=selected_unit,
        demands=sample_demands,
        buyer_success=buyer_success
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
