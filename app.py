import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
)
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Index,
    desc,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

BASE_DIR = Path(__file__).resolve().parent

# مسیر ذخیره سازی فایل‌های آپلودی (پشتیبانی از Render Persistent Disk یا محلی)
UPLOAD_DIR = Path(os.environ.get("PERSIST_DIR", BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "samaneh-tolid-secure-key-2026")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # محدودیت ۵ مگابایت برای تصویر

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------- دیتابیس (PostgreSQL / SQLite) -----------------
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

# مدل واحدهای تولیدی با ساختار مکانی سه‌سطحی (استان، شهرستان، بخش)
class ProductionUnit(Base):
    __tablename__ = "production_units"
    
    id = Column(Integer, primary_key=True)
    unit_name = Column(String(150), nullable=False)
    manager_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    
    # مکان جغرافیایی سه‌سطحی
    province = Column(String(50), nullable=False, index=True)
    county = Column(String(50), nullable=False, index=True)      # شهرستان
    district = Column(String(50), nullable=True, index=True)    # بخش / دهستان / منطقه
    
    craft_type = Column(String(100), nullable=False, index=True)
    products_desc = Column(Text, nullable=False)
    capacity = Column(String(100), nullable=True)
    export_ready = Column(String(10), nullable=False, default="no")
    image_filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_location_search', 'province', 'county', 'district'),
    )

# مدل تقاضای بازار
class MarketDemand(Base):
    __tablename__ = "market_demands"
    
    id = Column(Integer, primary_key=True)
    buyer_name = Column(String(150), nullable=False)
    target_craft = Column(String(100), nullable=False)
    quantity_needed = Column(String(100), nullable=False)
    contact_info = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# ----------------- روت‌ها و صفحات -----------------

@app.route("/")
def index():
    total_units = db_session.query(func.count(ProductionUnit.id)).scalar() or 0
    total_export = db_session.query(func.count(ProductionUnit.id)).filter(ProductionUnit.export_ready == 'yes').scalar() or 0
    recent_units = db_session.query(ProductionUnit).order_by(desc(ProductionUnit.created_at)).limit(6).all()
    return render_template("index.html", total_units=total_units, total_export=total_export, recent_units=recent_units)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            unit_name = request.form.get("unit_name", "").strip()
            manager_name = request.form.get("manager_name", "").strip()
            phone = request.form.get("phone", "").strip()
            province = request.form.get("province", "").strip()
            county = request.form.get("county", "").strip()
            district = request.form.get("district", "").strip()
            craft_type = request.form.get("craft_type", "").strip()
            products_desc = request.form.get("products_desc", "").strip()
            capacity = request.form.get("capacity", "").strip()
            export_ready = request.form.get("export_ready", "no")

            if not all([unit_name, manager_name, phone, province, county, craft_type, products_desc]):
                flash("لطفاً تمامی فیلدهای ستاره‌دار را به دقت تکمیل نمایید.", "danger")
                return redirect(url_for("register"))

            # مدیریت آپلود تصویر واحد
            image_filename = None
            file = request.files.get("image")
            if file and file.filename != "":
                if allowed_file(file.filename):
                    ext = file.filename.rsplit(".", 1)[1].lower()
                    image_filename = f"{uuid4().hex}.{ext}"
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
                else:
                    flash("فرمت تصویر مجاز نیست (فقط png, jpg, jpeg, webp).", "warning")
                    return redirect(url_for("register"))

            new_unit = ProductionUnit(
                unit_name=unit_name,
                manager_name=manager_name,
                phone=phone,
                province=province,
                county=county,
                district=district,
                craft_type=craft_type,
                products_desc=products_desc,
                capacity=capacity,
                export_ready=export_ready,
                image_filename=image_filename
            )
            db_session.add(new_unit)
            db_session.commit()
            
            flash("واحد تولیدی شما با موفقیت در شبکه هوشمند ثبت شد!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            db_session.rollback()
            flash(f"خطا در ثبت اطلاعات: {str(e)}", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/export-market", methods=["GET", "POST"])
def export_market():
    if request.method == "POST":
        buyer_name = request.form.get("buyer_name")
        target_craft = request.form.get("target_craft")
        quantity_needed = request.form.get("quantity_needed")
        contact_info = request.form.get("contact_info")
        
        if buyer_name and target_craft and contact_info:
            demand = MarketDemand(
                buyer_name=buyer_name,
                target_craft=target_craft,
                quantity_needed=quantity_needed,
                contact_info=contact_info
            )
            db_session.add(demand)
            db_session.commit()
            flash("نیازمندی بازار و صادرات ثبت شد.", "success")
            return redirect(url_for("export_market"))
            
    demands = db_session.query(MarketDemand).order_by(desc(MarketDemand.created_at)).all()
    return render_template("export_market.html", demands=demands)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # دسترسی ادمین امن
        if username == os.environ.get("ADMIN_USER", "admin") and password == os.environ.get("ADMIN_PASS", "saman1405"):
            session["logged_in"] = True
            flash("با موفقیت وارد پنل مدیریت شدید.", "success")
            return redirect(url_for("admin_panel"))
        else:
            flash("نام کاربری یا رمز عبور اشتباه است.", "danger")
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    page = request.args.get("page", 1, type=int)
    per_page = 20
    
    province_filter = request.args.get("province", "").strip()
    county_filter = request.args.get("county", "").strip()
    search_query = request.args.get("q", "").strip()
    
    query = db_session.query(ProductionUnit)
    
    if province_filter:
        query = query.filter(ProductionUnit.province == province_filter)
    if county_filter:
        query = query.filter(ProductionUnit.county == county_filter)
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (ProductionUnit.unit_name.ilike(search_term)) |
            (ProductionUnit.manager_name.ilike(search_term)) |
            (ProductionUnit.craft_type.ilike(search_term)) |
            (ProductionUnit.phone.ilike(search_term))
        )
        
    total_count = query.count()
    units = query.order_by(desc(ProductionUnit.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    provinces = [p[0] for p in db_session.query(ProductionUnit.province.distinct()).all() if p[0]]
    
    return render_template(
        "admin.html",
        units=units,
        total_count=total_count,
        page=page,
        per_page=per_page,
        provinces=provinces,
        selected_province=province_filter,
        selected_county=county_filter,
        search_query=search_query
    )

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    flash("از پنل مدیریت خارج شدید.", "info")
    return redirect(url_for("index"))

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
