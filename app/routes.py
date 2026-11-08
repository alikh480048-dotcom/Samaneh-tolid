import os
from datetime import datetime
from html import escape

from flask import (
    Blueprint,
    current_app,
    request,
    redirect,
    url_for,
    jsonify,
    render_template,
    flash,
)
from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required,
)
from sqlalchemy import inspect, func, text
from werkzeug.security import check_password_hash

# --------------------------------------------------
# BLUEPRINTS
# --------------------------------------------------

main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)
api = Blueprint("api", __name__)

ROLE_PERMISSIONS = {
    "admin": ["all"],
    "national_manager": [
        "view_all",
        "manage_units",
        "manage_cases",
        "manage_workflow",
        "view_dashboard",
    ],
    "province_manager": [
        "view_province",
        "manage_units",
        "manage_cases",
        "manage_workflow",
        "view_dashboard",
    ],
    "county_manager": [
        "view_county",
        "manage_units",
        "manage_cases",
        "manage_workflow",
        "view_dashboard",
    ],
    "expert": [
        "view_units",
        "view_cases",
        "manage_cases",
        "view_workflow",
    ],
    "field_expert": [
        "view_units",
        "view_cases",
        "manage_cases",
    ],
    "producer": [
        "view_own_unit",
        "manage_own_unit",
        "view_own_cases",
    ],
    "trader": [
        "view_units",
        "view_market",
    ],
    "agency": [
        "view_assigned_cases",
        "manage_assigned_cases",
    ],
}
SYSTEM_NAME = "شبکه هوشمند توسعه تولید و رفع موانع"
SYSTEM_SUBTITLE = "مرکز راهبردی شبکه تولید"


# --------------------------------------------------
# MODEL DISCOVERY
# --------------------------------------------------

def get_db():
    from . import db
    return db


def get_models():
    db = get_db()
    registry = db.Model.registry._class_registry
    result = {}

    for name, model in list(registry.items()):
        if isinstance(name, str) and isinstance(type(model), type):
            if hasattr(model, "__table__"):
                result[name] = model

    return result


def find_model(*names):
    models = get_models()

    for name in names:
        if name in models:
            return models[name]

    for name in names:
        target = name.lower().replace("_", "")

        for model_name, model in models.items():
            candidate = model_name.lower().replace("_", "")
            if candidate == target:
                return model

    return None


def column_names(model):
    if model is None:
        return set()

    try:
        return {column.key for column in inspect(model).columns}
    except Exception:
        return set()


def get_value(record, *names, default=""):
    if record is None:
        return default

    for name in names:
        try:
            value = getattr(record, name, None)
            if value is not None:
                return value
        except Exception:
            pass

    return default


def count_records(*model_names):
    model = find_model(*model_names)

    if model is None:
        return 0

    try:
        return get_db().session.query(model).count()
    except Exception:
        get_db().session.rollback()
        current_app.logger.exception(
            "Could not count records for %s",
            model.__name__,
        )
        return 0


def safe_text(value, limit=300):
    if value is None:
        return ""

    return escape(str(value)[:limit])


def get_user_model():
    return find_model("User", "SystemUser", "Account")


def find_user(login_value):
    model = get_user_model()

    if model is None:
        return None

    available = column_names(model)

    for field in ("username", "email", "national_id", "phone"):
        if field in available:
            try:
                user = get_db().session.query(model).filter(
                    getattr(model, field) == login_value
                ).first()

                if user:
                    return user
            except Exception:
                get_db().session.rollback()

    return None


def verify_user_password(user, password):
    if user is None:
        return False

    for field in ("password_hash", "password", "hashed_password"):
        stored = get_value(user, field, default=None)

        if not stored:
            continue

        try:
            if check_password_hash(str(stored), password):
                return True
        except (ValueError, TypeError):
            pass

        break

    for method_name in ("check_password", "verify_password"):
        method = getattr(user, method_name, None)

        if callable(method):
            try:
                if method(password):
                    return True
            except Exception:
                pass

    return False


def user_is_active(user):
    if user is None:
        return False

    if hasattr(user, "active"):
        return bool(user.active)

    active = get_value(user, "is_active", default=True)

    if active is None:
        return True

    return bool(active)


def user_role():
    if not current_user.is_authenticated:
        return "guest"

    return str(
        get_value(current_user, "role", "user_role", default="user")
    )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@main.route("/")
def home():
    unit_count = count_records("ProductionUnit", "Unit")
    profile_count = count_records("ProductionUnitProfile")
    case_count = count_records("BarrierCase", "ProductionCase")
    task_count = count_records("WorkflowTask", "Workflow", "Task")
    user_count = count_records("User", "SystemUser", "Account")
    
    # شمارش زنده مشتریان و درخواست‌های خرید
    customer_count = count_records("CustomerProfile", "Customer")
    purchase_request_count = count_records("CustomerPurchaseRequest", "PurchaseRequest", "MarketRequest")

    # شمارش امن پرونده‌های باز با فیلتر وضعیت
    open_cases_model = find_model("BarrierCase", "ProductionCase")
    open_cases_count = 0
    if open_cases_model:
        try:
            if "status" in column_names(open_cases_model):
                open_cases_count = get_db().session.query(open_cases_model).filter(
                    open_cases_model.status.notin_(['closed', 'resolved', 'بسته شده', 'تکمیل شده'])
                ).count()
            else:
                open_cases_count = case_count
        except Exception:
            get_db().session.rollback()
            open_cases_count = case_count

    total_units = unit_count + profile_count

    return render_template(
        "home.html",
        system_name=SYSTEM_NAME,
        system_subtitle=SYSTEM_SUBTITLE,
        unit_count=total_units,
        units_count=total_units,
        production_units_count=total_units,
        profile_count=profile_count,
        case_count=case_count,
        cases_count=case_count,
        open_cases_count=open_cases_count,
        task_count=task_count,
        tasks_count=task_count,
        user_count=user_count,
        users_count=user_count,
        customer_count=customer_count,
        customers_count=customer_count,
        purchase_request_count=purchase_request_count,
        purchase_requests_count=purchase_request_count,
        requests_count=purchase_request_count,
        is_authenticated=current_user.is_authenticated,
        role=user_role(),
    )


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = find_user(username)
        
        if user and user_is_active(user) and verify_user_password(user, password):
            login_user(user)
            flash("با موفقیت وارد شدید.", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.home"))
        flash("نام کاربری یا رمز عبور اشتباه است.", "danger")
        
    return render_template("login.html", system_name=SYSTEM_NAME)


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("با موفقیت خارج شدید.", "info")
    return redirect(url_for("main.home"))
