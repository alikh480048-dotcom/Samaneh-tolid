import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'secret-f29ecb46-smart-production-system')

# Database Configuration (PostgreSQL on Render or local SQLite)
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///smart_production.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models ---
class ProductionUnit(db.Model):
    __tablename__ = 'production_units'
    id = db.Column(db.Integer, primary_key=True)
    province = db.Column(db.String(100), nullable=False)
    county = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    craft_type = db.Column(db.String(150), nullable=False)
    owner_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MarketDemand(db.Model):
    __tablename__ = 'market_demands'
    id = db.Column(db.Integer, primary_key=True)
    buyer_name = db.Column(db.String(150), nullable=False)
    buyer_phone = db.Column(db.String(50), nullable=False)
    requested_item = db.Column(db.String(150), nullable=False)
    required_quantity = db.Column(db.String(100), nullable=False)
    target_market = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BottleneckCase(db.Model):
    __tablename__ = 'bottleneck_cases'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='در حال بررسی')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- Routes ---
@app.route('/')
def index():
    units_count = ProductionUnit.query.count()
    export_count = MarketDemand.query.count()
    bottlenecks_count = BottleneckCase.query.count()
    return render_template('index.html', 
                           units_count=units_count, 
                           export_count=export_count, 
                           bottlenecks_count=bottlenecks_count)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            unit = ProductionUnit(
                province=request.form.get('province'),
                county=request.form.get('county'),
                district=request.form.get('district'),
                craft_type=request.form.get('craft_type'),
                owner_name=request.form.get('owner_name'),
                phone=request.form.get('phone'),
                capacity=request.form.get('capacity')
            )
            db.session.add(unit)
            db.session.commit()
            flash('واحد تولیدی شما با موفقیت در شبکه ثبت شد!', 'success')
            return redirect(url_for('register'))
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در ثبت اطلاعات: {str(e)}', 'danger')
    
    units = ProductionUnit.query.order_by(ProductionUnit.id.desc()).all()
    return render_template('register.html', units=units)

@app.route('/export', methods=['GET', 'POST'])
def export():
    if request.method == 'POST':
        try:
            demand = MarketDemand(
                buyer_name=request.form.get('buyer_name'),
                buyer_phone=request.form.get('buyer_phone'),
                requested_item=request.form.get('requested_item'),
                required_quantity=request.form.get('required_quantity'),
                target_market=request.form.get('target_market')
            )
            db.session.add(demand)
            db.session.commit()
            flash('تقاضای بازار و صادرات با موفقیت ثبت شد!', 'success')
            return redirect(url_for('export'))
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در ثبت تقاضا: {str(e)}', 'danger')

    demands = MarketDemand.query.order_by(MarketDemand.id.desc()).all()
    return render_template('export.html', demands=demands)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['admin_logged'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged'):
        return redirect(url_for('admin'))
    units = ProductionUnit.query.all()
    demands = MarketDemand.query.all()
    bottlenecks = BottleneckCase.query.all()
    return render_template('admin_panel.html', units=units, demands=demands, bottlenecks=bottlenecks)

@app.route('/logout')
def logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
