from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'smart_network_secret_key_12345'

# ساختار نگهداری داده‌های واحدهای تولیدی ثبت‌شده
workshops_data = [
    {
        'id': 1,
        'name': 'کارگاه گلیم‌بافی عشایری تار و پود',
        'owner': 'فاطمه احمدی',
        'field': 'گلیم و دست‌بافته‌ها',
        'province': 'فارس - شیراز',
        'capacity': '۱۵ تخته در ماه',
        'issue': 'تأمین رنگرزی گیاهی سنتی و کانال صادراتی'
    },
    {
        'id': 2,
        'name': 'سفالگری و مینای خاک و نقش',
        'owner': 'علی محمدی',
        'field': 'سفال و سرامیک',
        'province': 'همدان - لالجین',
        'capacity': '۲۰۰ ست در ماه',
        'issue': 'بسته‌بندی ایمن ضدضربه جهت ارسال مرسوله‌ای'
    }
]

@app.route('/')
def home():
    """نمایش صفحه اصلی سامانه با آمار لحظه‌ای و محصولات"""
    total = len(workshops_data)
    # شمارش موانع ثبت‌شده
    active_issues = sum(1 for w in workshops_data if w.get('issue'))
    # رسته‌های فعال
    categories = list(set(w.get('field', '') for w in workshops_data if w.get('field')))
    active_categories = len(categories) if len(categories) > 0 else 4

    return render_template(
        'index.html',
        total_workshops=total,
        active_issues=active_issues,
        active_categories=active_categories,
        workshops=workshops_data
    )

@app.route('/register-workshop', methods=['GET', 'POST'])
def register_workshop():
    """ماژول نخست: ثبت مشخصات کارگاه و دریافت موانع تولید"""
    if request.method == 'POST':
        workshop_name = request.form.get('name')
        owner_name = request.form.get('owner')
        field = request.form.get('field')
        province = request.form.get('province')
        capacity = request.form.get('capacity')
        issue = request.form.get('issue')

        # ذخیره کارگاه جدید
        if workshop_name:
            workshops_data.append({
                'id': len(workshops_data) + 1,
                'name': workshop_name,
                'owner': owner_name,
                'field': field,
                'province': province,
                'capacity': capacity,
                'issue': issue
            })
        return redirect(url_for('workshops'))

    # در صورت باز شدن فرم به صورت GET
    return redirect(url_for('home'))

@app.route('/workshops')
def workshops():
    """مشاهده لیست کلیه واحدهای تولیدی و پایش موانع"""
    return render_template('index.html', workshops=workshops_data, total_workshops=len(workshops_data))

@app.route('/login')
def login():
    """مسیر اولیه ورود مدیر سامانه"""
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
