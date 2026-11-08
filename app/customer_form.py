# ============================================================
# app/customer_form.py
# نسخه اصلاح‌شده — بخش ۱ (با همه پچ‌ها اعمال‌شده)
# ============================================================

import os
import re
import json
import hmac
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from flask import (
    Blueprint,
    request,
    render_template_string,
    session,
    jsonify,
    redirect,
    url_for,
    flash,
)
from sqlalchemy import Index, inspect, text

from . import db


customer_form = Blueprint(
    "customer_form",
    __name__,
    url_prefix="/customer-market",
)


# --------------------------------------------------
# ثابت‌های ماژول
# --------------------------------------------------
_ALLOWED_CURRENCIES = {"IRT", "USD", "EUR", "AED", "TRY"}
_ALLOWED_STATUSES = {
    "submitted",
    "approved",
    "rejected",
    "processing",
    "completed",
}
_MAX_PRICE = Decimal("9999999999999999.99")


# مهاجرت افزایشی و سازگار با داده‌های قبلی؛ ستون‌های قدیمی حذف یا بازسازی نمی‌شوند.
_customer_schema_ready = False
_customer_schema_attempted = False

_CUSTOMER_PURCHASE_ADDITIONS = {
    "market_type": "VARCHAR(20)",
    "destination_country": "VARCHAR(100)",
    "destination_province": "VARCHAR(100)",
    "destination_city": "VARCHAR(100)",
    "delivery_deadline": "VARCHAR(100)",
    "required_quality": "TEXT",
    "quantity_unit": "VARCHAR(50)",
    "price_currency": "VARCHAR(10) NOT NULL DEFAULT 'IRT'",
}


@customer_form.before_request
def _ensure_customer_market_schema():
    global _customer_schema_ready, _customer_schema_attempted

    if _customer_schema_attempted:
        return
    _customer_schema_attempted = True

    try:
        inspector = inspect(db.engine)
        if "customer_purchase_request" not in inspector.get_table_names():
            _customer_schema_ready = True
            return

        existing = {
            item["name"]
            for item in inspector.get_columns("customer_purchase_request")
        }

        with db.engine.begin() as connection:
            for column_name, column_type in _CUSTOMER_PURCHASE_ADDITIONS.items():
                if column_name not in existing:
                    connection.execute(text(
                        f"ALTER TABLE customer_purchase_request "
                        f"ADD COLUMN {column_name} {column_type}"
                    ))

        _customer_schema_ready = True

    except Exception:
        # در صورت خطا، درخواست متوقف نمی‌شود و دیگر تلاشی برای مهاجرت انجام نمی‌شود.
        db.session.rollback()


# --------------------------------------------------
# اعتبارسنجی و نرمال‌سازی تقاضای بازار
# --------------------------------------------------
def _market_request_fields(data):
    """اعتبارسنجی و نرمال‌سازی فیلدهای تقاضای بازار."""

    market_type = str(data.get("market_type") or "domestic").strip().lower()
    if market_type not in {"domestic", "export"}:
        return None, "نوع بازار باید مصرف داخل کشور یا صادرات باشد."

    # --- ارز ---
    if market_type == "domestic":
        price_currency = "IRT"
    else:
        price_currency = str(data.get("price_currency") or "IRT").strip().upper()
        if price_currency not in _ALLOWED_CURRENCIES:
            return None, "ارز انتخاب‌شده معتبر نیست."

    # --- مقصد ---
    country = str(data.get("destination_country") or "").strip()
    province = str(data.get("destination_province") or "").strip()
    city = str(data.get("destination_city") or "").strip()
    deadline = str(data.get("delivery_deadline") or "").strip()
    quality = str(data.get("required_quality") or "").strip()
    unit = str(data.get("quantity_unit") or "").strip()

    if market_type == "export" and not country:
        return None, "برای درخواست صادرات، کشور مقصد الزامی است."
    if market_type == "domestic":
        country = "ایران"

    # --- اعتبارسنجی استان/شهر ---
    if market_type == "domestic":
        provinces, cities_by_province = _load_divisions()

        if province and province not in provinces:
            return None, "استان انتخاب‌شده معتبر نیست."

        if city and province:
            allowed_cities = cities_by_province.get(province, [])
            if city not in allowed_cities:
                return None, "شهر انتخاب‌شده با استان مطابقت ندارد."

    # --- محدودیت طول ---
    if not unit:
        return None, "واحد مقدار محصول را مشخص کنید."
    if len(country) > 100 or len(province) > 100 or len(city) > 100:
        return None, "طول اطلاعات مقصد بیش از حد مجاز است."
    if len(deadline) > 100 or len(quality) > 2000 or len(unit) > 50:
        return None, "طول اطلاعات زمان، کیفیت یا واحد مقدار بیش از حد مجاز است."

    return {
        "market_type": market_type,
        "destination_country": country,
        "destination_province": province or None,
        "destination_city": city or None,
        "delivery_deadline": deadline or None,
        "required_quality": quality or None,
        "quantity_unit": unit or None,
        "price_currency": price_currency,
    }, None


# --------------------------------------------------
# مدل مستقل پرونده مشتری
# --------------------------------------------------
class CustomerProfile(db.Model):
    __tablename__ = "customer_profile"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    national_id = db.Column(
        db.String(10),
        nullable=False,
        unique=True,
        index=True,
    )
    phone = db.Column(
        db.String(11),
        nullable=False,
        unique=True,
        index=True,
    )
    province = db.Column(db.String(100), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    address = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    purchase_requests = db.relationship(
        "CustomerPurchaseRequest",
        backref="customer",
        lazy=True,
        cascade="all, delete-orphan",
    )


# --------------------------------------------------
# مدل مستقل درخواست خرید مشتری
# --------------------------------------------------
class CustomerPurchaseRequest(db.Model):
    __tablename__ = "customer_purchase_request"

    id = db.Column(db.Integer, primary_key=True)

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer_profile.id"),
        nullable=False,
        index=True,
    )

    tracking_code = db.Column(
        db.String(24),
        unique=True,
        nullable=False,
        index=True,
    )

    product_name = db.Column(
        db.String(200),
        nullable=False,
        index=True,
    )

    quantity = db.Column(db.String(100), nullable=False)

    target_price = db.Column(db.Numeric(18, 2))

    description = db.Column(db.Text)

    # اطلاعات ساختاریافته بازار
    market_type = db.Column(db.String(20), nullable=True, index=True)
    destination_country = db.Column(db.String(100), nullable=True)
    destination_province = db.Column(db.String(100), nullable=True, index=True)
    destination_city = db.Column(db.String(100), nullable=True)
    delivery_deadline = db.Column(db.String(100), nullable=True)
    required_quality = db.Column(db.Text, nullable=True)
    quantity_unit = db.Column(db.String(50), nullable=True)
    price_currency = db.Column(
        db.String(10),
        nullable=False,
        default="IRT",
    )

    status = db.Column(
        db.String(40),
        nullable=False,
        default="submitted",
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index(
            "ix_customer_request_product_status",
            "product_name",
            "status",
        ),
        db.CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'processing', 'completed')",
            name="ck_customer_request_status",
        ),
    )


# --------------------------------------------------
# ابزارهای عمومی اعتبارسنجی
# --------------------------------------------------
def _normalize_digits(value):
    value = str(value or "")

    table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )

    return value.translate(table)


def _valid_national_id(value):
    value = _normalize_digits(value).strip()

    if not re.fullmatch(r"\d{10}", value):
        return False

    if len(set(value)) == 1:
        return False

    total = sum(
        int(value[index]) * (10 - index)
        for index in range(9)
    )

    remainder = total % 11
    check_digit = int(value[9])

    if remainder < 2:
        return check_digit == remainder

    return check_digit == 11 - remainder


def _valid_phone(value):
    value = _normalize_digits(value).strip()
    return bool(re.fullmatch(r"09\d{9}", value))


def _csrf_token():
    if not session.get("customer_csrf"):
        session["customer_csrf"] = secrets.token_urlsafe(32)

    return session["customer_csrf"]


def _valid_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("customer_csrf", "")

    return bool(
        submitted
        and expected
        and hmac.compare_digest(submitted, expected)
    )


def _customer_lookup_csrf_token():
    token = session.get("_customer_lookup_csrf")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_customer_lookup_csrf"] = token

    return token


def _customer_lookup_csrf_valid(data):
    supplied_token = str(data.get("csrf_token") or "")

    session_token = str(
        session.get("_customer_lookup_csrf") or ""
    )

    return bool(
        supplied_token
        and session_token
        and hmac.compare_digest(
            supplied_token,
            session_token,
        )
    )


@lru_cache(maxsize=1)
def _load_divisions():
    path = os.path.join(
        os.path.dirname(__file__),
        "iran_divisions.json",
    )

    with open(path, "r", encoding="utf-8") as file:
        rows = json.load(file)

    provinces = sorted({
        row.get("province_name", "").strip()
        for row in rows
        if row.get("province_name")
    })

    cities_by_province = {}

    for row in rows:
        province = (row.get("province_name") or "").strip()
        city = (row.get("city_name") or "").strip()

        if province and city:
            cities_by_province.setdefault(
                province,
                set(),
            ).add(city)

    cities_by_province = {
        province: sorted(cities)
        for province, cities in cities_by_province.items()
    }

    return provinces, cities_by_province


def _new_tracking_code():
    while True:
        code = secrets.token_hex(6).upper()

        exists = CustomerPurchaseRequest.query.filter_by(
            tracking_code=code
        ).first()

        if not exists:
            return code


def _valid_price(value, allow_zero=False, currency="IRT"):
    """
    تبدیل و اعتبارسنجی قیمت بر اساس ارز.
    خروجی: (قیمت یا None، پیام خطا یا None)
    """

    raw = _normalize_digits(value)
    raw = raw.replace(",", "").replace("٬", "").strip()

    if not raw:
        return None, None

    currency = str(currency or "IRT").strip().upper()
    if currency not in _ALLOWED_CURRENCIES:
        return None, "ارز انتخاب‌شده معتبر نیست."

    try:
        price = Decimal(raw)

        if not price.is_finite():
            raise InvalidOperation

        if allow_zero:
            invalid = price < 0
        else:
            invalid = price <= 0

        if invalid:
            raise InvalidOperation

        if price > _MAX_PRICE:
            raise InvalidOperation

        return price, None

    except (InvalidOperation, ValueError):
        return None, "قیمت وارد‌شده معتبر نیست."


def _normalize_tracking_code(value):
    return _normalize_digits(value).strip().upper()


def _customer_owned_purchase(customer_id, tracking_code):
    """
    بازیابی درخواست فقط در محدوده مالکیت مشتری.
    """

    tracking_code = _normalize_tracking_code(tracking_code)

    if not customer_id or not tracking_code:
        return None

    return CustomerPurchaseRequest.query.filter_by(
        customer_id=customer_id,
        tracking_code=tracking_code,
    ).first()


def find_customer_purchase(tracking_code, phone):
    """
    جست‌وجوی یک درخواست با تطبیق کد پیگیری و تلفن ثبت‌شده.
    """

    tracking_code = _normalize_tracking_code(tracking_code)

    phone = _normalize_digits(phone).strip()

    if not tracking_code or not _valid_phone(phone):
        return None

    return (
        CustomerPurchaseRequest.query
        .join(CustomerProfile)
        .filter(
            CustomerPurchaseRequest.tracking_code == tracking_code,
            CustomerProfile.phone == phone,
        )
        .first()
    )
