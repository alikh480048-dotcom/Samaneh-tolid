import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'saman-smart-secret-key-1405'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tolid.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # حداکثر ۵ مگابایت

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'), exist_ok=True)

db = SQLAlchemy(app)

# مدل پایگاه داده واحدها
class ProductionUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_name = db.Column(db.String(120), nullable=False)
    manager_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    province = db.Column(db.String(50), nullable=False, index=True)
    county = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=True)
    craft_type = db.Column(db.String(100), nullable=False)
    products_desc = db.Column(db.Text, nullable=False)
    monthly_capacity = db.Column(db.String(100), nullable=True)
    export_ready = db.Column(db.String(10), default='no')
    image_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# مدل تقاضای بازار
class MarketDemand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_name = db.Column(db.String(120), nullable=False)
    buyer_phone = db.Column(db.String(20), nullable=False)
    requested_item = db.Column(db.String(150), nullable=False)
    required_quantity = db.Column(db.String(100), nullable=False)
    target_market = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    total_units = ProductionUnit.query.count()
    total_export = ProductionUnit.query.filter_by(export_ready='yes').count()
    recent_units = ProductionUnit.query.order_by(ProductionUnit.created_at.desc()).limit(6).all()
    return render_template('index.html', total_units=total_units, total_export=total_export, recent_units=recent_units)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        unit_name = request.form.get('unit_name', '').strip()
        manager_name = request.form.get('manager_name', '').strip()
        phone = request.form.get('phone', '').strip()
        province = request.form.get('province', '').strip()
        county = request.form.get('county', '').strip()
        district = request.form.get('district', '').strip()
        craft_type = request.form.get('craft_type', '').strip()
        products_desc = request.form.get('products_desc', '').strip()
        monthly_capacity = request.form.get('monthly_capacity', '').strip()
        export_ready = request.form.get('export_ready', 'no')

        if not unit_name or not manager_name or not phone or not province or not county or not craft_type:
            flash('لطفاً تمامی فیلدهای ستاره‌دار و موقعیت مکانی را کامل پر کنید.', 'danger')
            return redirect(url_for('register'))

        filename = None
        file = request.files.get('image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('فرمت تصویر مجاز نیست (فقط PNG, JPG, WEBP).', 'warning')
                return redirect(url_for('register'))

        new_unit = ProductionUnit(
            unit_name=unit_name, manager_name=manager_name, phone=phone,
            province=province, county=county, district=district,
            craft_type=craft_type, products_desc=products_desc,
            monthly_capacity=monthly_capacity, export_ready=export_ready,
            image_filename=filename
        )
        db.session.add(new_unit)
        db.session.commit()
        flash('واحد تولیدی شما با موفقیت در شبکه هوشمند ثبت شد.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/export-market', methods=['GET', 'POST'])
def export_market():
    if request.method == 'POST':
        buyer_name = request.form.get('buyer_name', '').strip()
        buyer_phone = request.form.get('buyer_phone', '').strip()
        requested_item = request.form.get('requested_item', '').strip()
        required_quantity = request.form.get('required_quantity', '').strip()
        target_market = request.form.get('target_market', '').strip()

        if not buyer_name or not buyer_phone or not requested_item:
            flash('لطفاً فیلدهای ضروری تقاضای بازار را پر کنید.', 'danger')
            return redirect(url_for('export_market'))

        demand = MarketDemand(
            buyer_name=buyer_name, buyer_phone=buyer_phone,
            requested_item=requested_item, required_quantity=required_quantity,
            target_market=target_market
        )
        db.session.add(demand)
        db.session.commit()
        flash('تقاضای بازار و صادرات شما با موفقیت ثبت شد.', 'success')
        return redirect(url_for('export_market'))

    demands = MarketDemand.query.order_by(MarketDemand.created_at.desc()).all()
    return render_template('export.html', demands=demands)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'saman1405':
            session['admin_logged'] = True
            flash('با موفقیت وارد پنل مدیریت شدید.', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>ورود مدیر</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    </head>
    <body class="bg-light d-flex align-items-center justify-content-center" style="height: 100vh;">
        <div class="card p-4 shadow" style="width: 380px;">
            <h4 class="text-center mb-3 text-primary">ورود مدیریت سامانه</h4>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for cat, msg in messages %}
                <div class="alert alert-{{ cat }} py-2 small">{{ msg }}</div>
              {% endfor %}{% endif %}
            {% endwith %}
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label small fw-bold">نام کاربری</label>
                    <input type="text" name="username" class="form-control" required value="admin">
                </div>
                <div class="mb-3">
                    <label class="form-label small fw-bold">رمز عبور</label>
                    <input type="password" name="password" class="form-control" required placeholder="رمز عبور">
                </div>
                <button type="submit" class="btn btn-primary w-100">ورود</button>
            </form>
            <div class="text-center mt-3"><a href="{{ url_for('index') }}" class="small text-muted">بازگشت به سایت</a></div>
        </div>
    </body>
    </html>
    ''')

@app.route('/admin')
def admin_panel():
    if not session.get('admin_logged'):
        return redirect(url_for('login'))
    
    q = request.args.get('q', '').strip()
    province_filter = request.args.get('province', '').strip()

    query = ProductionUnit.query
    if q:
        query = query.filter(db.or_(
            ProductionUnit.unit_name.contains(q),
            ProductionUnit.manager_name.contains(q),
            ProductionUnit.phone.contains(q)
        ))
    if province_filter:
        query = query.filter_by(province=province_filter)

    units = query.order_by(ProductionUnit.created_at.desc()).all()
    total_count = ProductionUnit.query.count()
    provinces = [r[0] for r in db.session.query(ProductionUnit.province.distinct()).all()]

    return render_template('admin.html', units=units, total_count=total_count, provinces=provinces, search_query=q, selected_province=province_filter)

@app.route('/logout')
def logout():
    session.pop('admin_logged', None)
    flash('از پنل مدیریت خارج شدید.', 'info')
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
