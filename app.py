import os
import json
import hmac
import secrets
import tempfile
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4
from decimal import Decimal, InvalidOperation
from collections import defaultdict

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
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash


# =========================================================
# تنظیمات اصلی
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# اگر دیسک دائمی Render دارید، مقدار DATA_DIR را برابر
# مسیر Mount دیسک، مثلاً /var/data قرار دهید.
configured_data_dir = os.environ.get("DATA_DIR", "").strip()

DATA_DIR = (
    Path(configured_data_dir).expanduser().resolve()
    if configured_data_dir
    else BASE_DIR
)

DATA_DIR.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "units_data.json"
DEMANDS_FILE = DATA_DIR / "market_requests.json"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
DATA_LOCK = RLock()

app = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY", "").strip()

if not secret_key:
    # کلید تصادفی محلی؛ برای محیط واقعی SECRET_KEY را در Render تنظیم کنید.
    secret_path = DATA_DIR / ".session_secret"

    try:
        with secret_path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_hex(32))
        try:
            secret_path.chmod(0o600)
        except OSError:
            pass
    except FileExistsError:
        pass

    secret_key = secret_path.read_text(encoding="utf-8").strip()

    if not secret_key:
        raise RuntimeError("کلید نشست معتبر نیست؛ SECRET_KEY را تنظیم کنید.")

app.config.update(
    SECRET_KEY=secret_key,
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.environ.get("SESSION_COOKIE_SECURE", "").lower()
        in {"1", "true", "yes"}
        or bool(os.environ.get("RENDER"))
    ),
)

# فقط از متغیرهای محیطی خوانده می‌شوند.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")


# =========================================================
# گروه‌های صنایع
# در مرحله بعد، فرم ثبت نیز به این گروه‌ها متصل می‌شود.
# =========================================================

INDUSTRY_CATEGORIES = {
    "صنایع دستی و هنرهای سنتی": [
        "فرش دست‌باف، گلیم و جاجیم",
        "سفال و سرامیک هنری",
        "قلم‌زنی و صنایع فلزی هنری",
        "خاتم، معرق و منبت",
        "حصیربافی و صنایع الیافی",
        "رودوزی و سوزن‌دوزی سنتی",
        "زیورآلات دست‌ساز",
        "سایر صنایع دستی",
    ],
    "مواد غذایی و صنایع تبدیلی کشاورزی": [
        "خشکبار و میوه خشک",
        "ترشی، شور، مربا و فرآورده‌های میوه",
        "نان، شیرینی و محصولات آردی",
        "ادویه و چاشنی",
        "بسته‌بندی محصولات کشاورزی",
        "فرآوری و بسته‌بندی عسل",
        "سایر فرآورده‌های غذایی",
    ],
    "نساجی، پوشاک و کالای خواب": [
        "پوشاک زنانه",
        "پوشاک مردانه",
        "پوشاک کودک",
        "لباس کار و فرم",
        "بافت و تریکو",
        "پارچه و منسوجات",
        "کالای خواب و منسوجات منزل",
    ],
    "چرم، کیف و کفش": [
        "کیف چرمی و غیرچرمی",
        "کفش و پاپوش",
        "محصولات و اکسسوری چرمی",
    ],
    "چوب، مبلمان و دکوراسیون": [
        "مبلمان و مصنوعات چوبی",
        "کابینت و تجهیزات چوبی",
        "لوازم دکوراسیون",
        "اسباب‌بازی چوبی",
    ],
    "گیاهان دارویی و فرآورده‌های گیاهی": [
        "کشت و خشک‌کردن گیاهان دارویی",
        "بسته‌بندی گیاهان دارویی",
        "عرقیات و گلاب",
        "فرآورده‌های گیاهی دارای مجوز",
    ],
    "تولیدات سبک صنعتی و کارگاهی": [
        "قطعات و مصنوعات فلزی",
        "قطعات و مصنوعات پلیمری",
        "تجهیزات و ابزار کارگاهی",
        "مونتاژ تجهیزات برقی و الکترونیکی",
        "سایر تولیدات سبک صنعتی",
    ],
    "بسته‌بندی و محصولات کاغذی": [
        "جعبه و کارتن",
        "پاکت و بسته‌بندی کاغذی",
        "چاپ و تکمیل بسته‌بندی",
        "سایر ملزومات بسته‌بندی",
    ],
    "سایر فعالیت‌های تولیدی": [
        "سایر فعالیت‌های تولیدی",
    ],
}


# =========================================================
# خواندن و ذخیره اطلاعات
# =========================================================

def read_records(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"ساختار فایل {path.name} باید فهرست باشد."
        )

    if not all(isinstance(item, dict) for item in data):
        raise ValueError(
            f"رکورد نامعتبر در فایل {path.name} وجود دارد."
        )

    return data


def write_records(path, records):
    temporary_name = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_name = file.name
            json.dump(records, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_name, path)
        temporary_name = None

    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass


def append_record(path, record):
    with DATA_LOCK:
        records = read_records(path)
        records.append(record)
        write_records(path, records)


# نام توابع قبلی برای سازگاری حفظ شده است.
def load_data():
    return read_records(DATA_FILE)


def save_data(data):
    with DATA_LOCK:
        write_records(DATA_FILE, data)


def load_market_requests():
    return read_records(DEMANDS_FILE)


# =========================================================
# ابزارهای مشترک
# =========================================================

DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def normalize_digits(value):
    return str(value or "").translate(DIGIT_TRANSLATION)


def form_value(*names, default=""):
    for name in names:
        value = request.form.get(name)

        if value is not None and str(value).strip():
            return str(value).strip()

    return default


def number_value(value):
    cleaned = normalize_digits(value)
    cleaned = cleaned.replace(",", "").replace("٬", "")
    cleaned = cleaned.replace("٫", ".").strip()

    try:
        number = Decimal(cleaned or "0")
    except InvalidOperation:
        raise ValueError("مقدار ظرفیت باید عددی باشد.")

    if not number.is_finite() or number < 0:
        raise ValueError("مقدار ظرفیت باید عددی معتبر و غیرمنفی باشد.")

    return number


def number_text(value):
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(
        value, "f"
    ) else format(value, "f")


def normalized_phone(value):
    value = normalize_digits(value)
    value = "".join(
        char for char in value if char not in " -()"
    )

    if value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("+98"):
        value = "0" + value[3:]

    return value


def valid_phone(value):
    digits = value[1:] if value.startswith("+") else value
    return digits.isdigit() and 10 <= len(digits) <= 15


def timestamps():
    now = datetime.now(timezone.utc)

    return {
        "created_at": now.strftime("%Y/%m/%d %H:%M UTC"),
        "created_at_iso": now.isoformat(),
    }


def collect_obstacles():
    selected = []

    for name in (
        "obstacles",
        "obstacles[]",
        "obstacle_types",
        "obstacle_types[]",
    ):
        for value in request.form.getlist(name):
            value = str(value).strip()

            if value and value not in selected:
                selected.append(value)

    details = form_value(
        "obstacle_description",
        "obstacles_description",
        "obstacle_details",
        "other_obstacles",
    )

    return selected, details


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def valid_csrf():
    supplied = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")

    return (
        bool(supplied)
        and bool(expected)
        and hmac.compare_digest(supplied, expected)
    )


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("is_admin") is not True:
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def shared_template_values():
    return {
        "industry_categories": INDUSTRY_CATEGORIES,
        "categories": INDUSTRY_CATEGORIES,
        "is_admin": session.get("is_admin") is True,
    }


# =========================================================
# دریافت عکس محصول
# =========================================================

def save_product_image():
    uploaded = None

    for name in (
        "product_image",
        "product_photo",
        "image",
        "photo",
        "image_file",
    ):
        candidate = request.files.get(name)

        if candidate and candidate.filename:
            uploaded = candidate
            break

    if uploaded is None:
        return "", ""

    content = uploaded.stream.read(MAX_IMAGE_BYTES + 1)

    if not content:
        raise ValueError("فایل عکس خالی است.")

    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("حجم عکس نباید بیشتر از ۵ مگابایت باشد.")

    # نام فایل کاربر مبنای ذخیره‌سازی نیست.
    # فقط قالب‌های تصویری زیر پذیرفته می‌شوند.
    if content.startswith(b"\xff\xd8\xff"):
        extension = ".jpg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = ".png"
    elif (
        len(content) >= 12
        and content[:4] == b"RIFF"
        and content[8:12] == b"WEBP"
    ):
        extension = ".webp"
    else:
        raise ValueError("عکس باید از نوع JPG، PNG یا WEBP باشد.")

    filename = f"{uuid4().hex}{extension}"
    path = UPLOAD_DIR / filename
    path.write_bytes(content)

    return filename, url_for("uploaded_file", filename=filename)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    response = send_from_directory(
        str(UPLOAD_DIR),
        filename,
        conditional=True,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# =========================================================
# صفحه اصلی و آمار
# =========================================================

def dashboard_statistics(units):
    capacities = defaultdict(Decimal)
    open_obstacles = 0
    resolved_obstacles = 0

    for unit in units:
        try:
            capacity = number_value(unit.get("nominal_capacity", 0))
        except ValueError:
            capacity = Decimal("0")

        measure = str(
            unit.get("capacity_unit") or "واحد نامشخص"
        ).strip()

        capacities[measure] += capacity

        obstacles = unit.get("obstacles")
        details = unit.get("obstacle_description")

        no_obstacle_values = {
            "",
            "ندارد",
            "بدون مانع",
            "هیچ‌کدام",
            "هیچکدام",
        }

        has_obstacle = bool(details)

        if isinstance(obstacles, list):
            has_obstacle = has_obstacle or any(
                str(item).strip() not in no_obstacle_values
                for item in obstacles
            )
        elif obstacles is not None:
            has_obstacle = has_obstacle or (
                str(obstacles).strip() not in no_obstacle_values
            )

        if has_obstacle:
            status = str(
                unit.get("obstacle_status", "در حال پیگیری")
            ).strip()

            if status in {"رفع‌شده", "رفع شده", "resolved", "closed"}:
                resolved_obstacles += 1
            else:
                open_obstacles += 1

    # برای سازگاری با عنوان «تن در ماه» در قالب فعلی،
    # فقط ظرفیت‌هایی که صراحتاً تن در ماه هستند جمع می‌شوند.
    ton_labels = {
        "تن",
        "تن در ماه",
        "تن/ماه",
        "تن / ماه",
        "ton/month",
        "tons/month",
    }

    total_tons = sum(
        (
            value
            for measure, value in capacities.items()
            if measure in ton_labels
        ),
        Decimal("0"),
    )

    return {
        "units_count": len(units),
        "total_units": len(units),
        "total_capacity": number_text(total_tons),
        "capacity_totals": {
            measure: number_text(value)
            for measure, value in capacities.items()
        },
        # این دو عدد، تعداد پرونده‌های واحدهای دارای مانع هستند.
        "obstacles_count": open_obstacles,
        "pending_obstacles": open_obstacles,
        "resolved_count": resolved_obstacles,
        "resolved_obstacles": resolved_obstacles,
    }


@app.route("/")
def index():
    units = load_data()
    statistics = dashboard_statistics(units)

    return render_template(
        "index.html",
        units=units,
        registered_units=units,
        production_units=units,
        **statistics,
    )


# =========================================================
# ثبت واحد تولیدی
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    unit_name = form_value("unit_name")
    manager_name = form_value("manager_name")
    phone = normalized_phone(form_value("phone"))
    province = form_value("province")
    city = form_value("city")

    if not all((unit_name, manager_name, phone, province)):
        flash(
            "نام واحد، نام مدیر، شماره تماس و استان را تکمیل کنید.",
            "error",
        )
        return render_template("register.html"), 400

    if not valid_phone(phone):
        flash("شماره تماس معتبر وارد کنید.", "error")
        return render_template("register.html"), 400

    try:
        capacity = number_value(
            form_value("nominal_capacity", default="0")
        )
    except ValueError as error:
        flash(str(error), "error")
        return render_template("register.html"), 400

    selected_obstacles, obstacle_details = collect_obstacles()
    image_filename = ""

    try:
        image_filename, image_url = save_product_image()
    except ValueError as error:
        flash(str(error), "error")
        return render_template("register.html"), 400

    new_unit = {
        "id": uuid4().hex,
        "unit_name": unit_name,
        "manager_name": manager_name,
        "phone": phone,
        "province": province,
        "city": city,
        "address": form_value("address"),
        "postal_code": normalize_digits(form_value("postal_code")),
        "business_type": form_value("business_type", "unit_type"),
        "category": form_value("category"),
        "subcategory": form_value("subcategory"),
        "product_name": form_value("product_name"),
        "product_description": form_value(
            "product_description",
            "description",
        ),
        "nominal_capacity": number_text(capacity),
        "capacity_unit": form_value(
            "capacity_unit",
            default="عدد در ماه",
        ),
        "workers_count": form_value(
            "workers_count",
            "worker_count",
            "employees",
        ),
        "activity_status": form_value(
            "activity_status",
            default="فعال",
        ),
        # رشته برای سازگاری با قالب‌های قبلی حفظ شده است.
        "obstacles": "، ".join(selected_obstacles),
        "obstacle_types": selected_obstacles,
        "obstacle_description": obstacle_details,
        "obstacle_status": (
            "در حال پیگیری"
            if selected_obstacles or obstacle_details
            else "بدون مانع"
        ),
        "product_image": image_url,
        "image_url": image_url,
        "image": image_url,
        "image_filename": image_filename,
        **timestamps(),
    }

    try:
        append_record(DATA_FILE, new_unit)
    except Exception:
        if image_filename:
            try:
                (UPLOAD_DIR / image_filename).unlink()
            except OSError:
                pass
        raise

    flash(
        "واحد تولیدی با موفقیت ثبت و اطلاعات آن ذخیره شد.",
        "success",
    )
    return redirect(url_for("index"))


# =========================================================
# بازار و درخواست‌های خرید
# =========================================================

@app.route("/export-market", methods=["GET", "POST"])
def export_market():
    units = load_data()

    unit_id = (
        request.args.get("unit_id")
        or request.form.get("unit_id")
        or ""
    )

    selected_unit = next(
        (
            unit
            for unit in units
            if str(unit.get("id")) == str(unit_id)
        ),
        None,
    )

    if request.method == "POST":
        # نام فیلدهای فرم فعلی نیز نگهداری می‌شود تا پس از
        # اصلاح قالب، داده‌های ثبت‌شده قابل استفاده باشند.
        excluded_fields = {
            "csrf_token",
            "password",
            "confirm_password",
            "admin_password",
            "submit",
        }

        submitted_fields = {
            str(key): [
                str(value).strip()
                for value in request.form.getlist(key)
            ]
            for key in request.form
            if key.lower() not in excluded_fields
        }

        has_content = any(
            any(value for value in values)
            for key, values in submitted_fields.items()
            if key != "unit_id"
        )

        if not has_content:
            flash("اطلاعات درخواست خرید را وارد کنید.", "error")
            return redirect(url_for("export_market"))

        title = form_value(
            "title",
            "request_title",
            "product_name",
            "requested_product",
            "product",
            "buyer_product",
            "product_type",
            default="درخواست خرید",
        )

        buyer = form_value(
            "buyer",
            "buyer_name",
            "company_name",
            "buyer_company",
            "full_name",
            "name",
            default="خریدار",
        )

        phone = normalized_phone(
            form_value(
                "buyer_phone",
                "phone",
                "contact_phone",
                "mobile",
                "contact",
            )
        )

        if phone and not valid_phone(phone):
            flash("شماره تماس درخواست خرید معتبر نیست.", "error")
            return redirect(url_for("export_market"))

        demand = {
            "id": uuid4().hex,
            "unit_id": str(unit_id),
            "title": title,
            "buyer": buyer,
            "buyer_name": buyer,
            "phone": phone,
            "email": form_value("email", "buyer_email"),
            "target_country": form_value(
                "target_country",
                "country",
                "buyer_country",
                default="مشخص نشده",
            ),
            "volume": form_value(
                "volume",
                "quantity",
                "amount",
                "order_quantity",
                "buyer_volume",
                default="مشخص نشده",
            ),
            "delivery_days": form_value(
                "delivery_days",
                "delivery_time",
                "deadline",
                default="توافقی",
            ),
            "description": form_value(
                "description",
                "details",
                "message",
                "buyer_description",
                "requirements",
            ),
            "status": "ثبت‌شده",
            "badge": "درخواست ثبت‌شده",
            "form_data": submitted_fields,
            **timestamps(),
        }

        append_record(DEMANDS_FILE, demand)

        flash(
            "درخواست خرید ذخیره شد و در پنل مدیر قابل مشاهده است.",
            "success",
        )

        return redirect(
            url_for("export_market", submitted="1")
        )

    market_requests = list(reversed(load_market_requests()))

    # شماره تماس و داده‌های خام فرم به قالب عمومی داده نمی‌شود.
    public_demands = [
        {
            key: demand.get(key, "")
            for key in (
                "id",
                "unit_id",
                "title",
                "buyer",
                "target_country",
                "volume",
                "delivery_days",
                "description",
                "badge",
                "status",
                "created_at",
            )
        }
        for demand in market_requests
    ]

    return render_template(
        "export.html",
        units=units,
        selected_unit=selected_unit,
        demands=public_demands,
        market_requests=public_demands,
        buyer_requests=public_demands,
        buyer_success=request.args.get("submitted") == "1",
    )


# =========================================================
# قالب داخلی ورود و مدیریت
# پنل مدیر بدون نیاز به فایل HTML جدید فعال می‌شود.
# =========================================================

ADMIN_TEMPLATE = """
<!doctype html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} | شبکه ملی توسعه تولید</title>
    <link
        href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap"
        rel="stylesheet"
    >
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background: #0b132b;
            color: #edf2ff;
            font-family: Vazirmatn, Tahoma, sans-serif;
            line-height: 1.9;
        }
        main {
            width: min(1100px, 94%);
            margin: 28px auto;
        }
        header, .actions, .stats {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        header {
            justify-content: space-between;
            margin-bottom: 24px;
        }
        .card {
            background: rgba(28, 37, 65, .88);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 20px;
            padding: 20px;
            margin: 16px 0;
            overflow-wrap: anywhere;
        }
        .login {
            max-width: 440px;
            margin: 45px auto;
        }
        h1 { font-size: 23px; margin: 0; }
        h2 { font-size: 20px; }
        h3 { font-size: 17px; }
        a { color: #8eddf6; }
        label { display: block; margin: 14px 0 6px; }
        input {
            width: 100%;
            padding: 13px;
            border-radius: 12px;
            border: 1px solid #526180;
            background: #0b132b;
            color: white;
            font: inherit;
        }
        button {
            padding: 11px 18px;
            border: 0;
            border-radius: 12px;
            background: #50d3b1;
            color: #071925;
            font: inherit;
            cursor: pointer;
        }
        .wide { width: 100%; margin-top: 20px; }
        .muted { color: #b7c6df; }
        .message {
            padding: 12px;
            border: 1px solid #607697;
            border-radius: 12px;
            margin: 12px 0;
        }
        .error { border-color: #fa8b8b; }
        .stats .card { flex: 1; min-width: 145px; }
        .record { border-right: 3px solid #50d3b1; }
        pre {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-family: inherit;
        }
        img {
            width: 120px;
            max-height: 120px;
            object-fit: cover;
            border-radius: 12px;
        }
        form { margin: 0; }
    </style>
</head>
<body>
<main>
    <header>
        <div>
            <h1>🇮🇷 شبکه ملی توسعه تولید</h1>
            <div class="muted">{{ title }}</div>
        </div>
        <div class="actions">
            <a href="{{ url_for('index') }}">صفحه اصلی</a>
            {% if mode == 'dashboard' %}
            <form method="post" action="{{ url_for('logout') }}">
                <input
                    type="hidden"
                    name="csrf_token"
                    value="{{ csrf_token() }}"
                >
                <button type="submit">خروج مدیر</button>
            </form>
            {% endif %}
        </div>
    </header>

    {% for category, message in get_flashed_messages(with_categories=true) %}
        <div class="message {{ category }}">{{ message }}</div>
    {% endfor %}

    {% if mode == 'login' %}
        <section class="card login">
            <h2>ورود مدیر سامانه</h2>

            {% if not configured %}
                <p class="message error">
                    ورود مدیر هنوز تنظیم نشده است.
                    متغیر ADMIN_PASSWORD را در Render تنظیم کنید.
                </p>
            {% endif %}

            <form method="post" action="{{ url_for('login') }}">
                <input
                    type="hidden"
                    name="csrf_token"
                    value="{{ csrf_token() }}"
                >
                <label for="username">نام کاربری</label>
                <input
                    id="username"
                    name="username"
                    autocomplete="username"
                    required
                >
                <label for="password">رمز عبور</label>
                <input
                    id="password"
                    name="password"
                    type="password"
                    autocomplete="current-password"
                    required
                >
                <button class="wide" type="submit">ورود به مدیریت</button>
            </form>
        </section>
    {% else %}
        <div class="stats">
            <div class="card">
                واحدهای ثبت‌شده
                <h2>{{ units|length }}</h2>
            </div>
            <div class="card">
                درخواست‌های بازار
                <h2>{{ demands|length }}</h2>
            </div>
            <div class="card">
                پرونده‌های دارای مانع
                <h2>{{ statistics.pending_obstacles }}</h2>
            </div>
        </div>

        <nav class="actions">
            <a href="#demands">درخواست‌های بازاریابی</a>
            <a href="#units">واحدهای تولیدی</a>
        </nav>

        <section id="demands">
            <h2>درخواست‌های خرید و بازاریابی</h2>

            {% for demand in demands %}
                <article class="card record">
                    <h3>{{ demand.get('title', 'درخواست خرید') }}</h3>
                    <p>خریدار: {{ demand.get('buyer', '—') }}</p>
                    <p>تماس: {{ demand.get('phone') or 'ثبت نشده' }}</p>
                    <p>ایمیل: {{ demand.get('email') or 'ثبت نشده' }}</p>
                    <p>کشور: {{ demand.get('target_country', '—') }}</p>
                    <p>مقدار: {{ demand.get('volume', '—') }}</p>
                    <p>تحویل: {{ demand.get('delivery_days', '—') }}</p>
                    <p>{{ demand.get('description', '') }}</p>
                    <p class="muted">{{ demand.get('created_at', '') }}</p>

                    {% if demand.get('form_data') %}
                        <details>
                            <summary>تمام اطلاعات فرم ثبت‌شده</summary>
                            {% for field, values in demand['form_data'].items() %}
                                <p>
                                    <strong>{{ field }}:</strong>
                                    {{ values|join('، ') }}
                                </p>
                            {% endfor %}
                        </details>
                    {% endif %}
                </article>
            {% else %}
                <div class="card">هنوز درخواست خریدی ذخیره نشده است.</div>
            {% endfor %}
        </section>

        <section id="units">
            <h2>واحدهای تولیدی ثبت‌شده</h2>

            {% for unit in units %}
                <article class="card record">
                    <h3>{{ unit.get('unit_name', 'واحد تولیدی') }}</h3>
                    <p>مدیر: {{ unit.get('manager_name', '—') }}</p>
                    <p>تماس: {{ unit.get('phone', '—') }}</p>
                    <p>
                        محل فعالیت:
                        {{ unit.get('province', '') }}
                        ـ {{ unit.get('city', '') }}
                    </p>
                    <p>
                        گروه:
                        {{ unit.get('category', '') }}
                        / {{ unit.get('subcategory', '') }}
