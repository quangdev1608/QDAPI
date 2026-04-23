from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from admin.auth import (
    AdminLoginUser,
    authenticate_admin,
    check_admin_login_lockout,
    record_admin_login_attempt,
    remaining_admin_attempts,
    require_any_permission,
    require_permission,
)
from admin.services import (
    create_api_key,
    get_dashboard_data,
    list_keys,
    list_logs,
    query_data_manager,
    toggle_api_key,
    update_api_key,
    delete_api_key,
)

admin_bp = Blueprint("admin", __name__, template_folder="templates", static_folder="static", static_url_path="/static")


@admin_bp.get("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("admin.index"))
    return render_template("login.html")


@admin_bp.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    client_ip = request.remote_addr or "unknown"

    lockout_seconds = check_admin_login_lockout(username=username, client_ip=client_ip)
    if lockout_seconds > 0:
        flash(f"Đăng nhập tạm khóa. Vui lòng thử lại sau {lockout_seconds} giây", "danger")
        return redirect(url_for("admin.login_page"))

    user = authenticate_admin(username=username, password=password)
    if not user:
        record_admin_login_attempt(username=username, client_ip=client_ip, success=False)
        attempts_left = remaining_admin_attempts(username=username, client_ip=client_ip)
        if attempts_left > 0:
            flash(f"Sai tài khoản hoặc mật khẩu. Còn {attempts_left} lần thử.", "danger")
        else:
            flash("Sai tài khoản hoặc mật khẩu. Tài khoản đã bị khóa tạm thời.", "danger")
        return redirect(url_for("admin.login_page"))

    record_admin_login_attempt(username=username, client_ip=client_ip, success=True)
    login_user(AdminLoginUser(user))
    return redirect(url_for("admin.index"))


@admin_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login_page"))


@admin_bp.get("/")
@login_required
@require_permission("dashboard:view")
def index():
    total_keys, total_requests, latest_logs, chart_labels, chart_values = get_dashboard_data()
    return render_template(
        "index.html",
        total_keys=total_keys,
        total_requests=total_requests,
        latest_logs=latest_logs,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )


@admin_bp.get("/keys")
@login_required
@require_permission("keys:view")
def keys():
    one_time_raw_key = session.pop("one_time_raw_key", None)
    key_items = list_keys()
    return render_template("keys.html", key_items=key_items, one_time_raw_key=one_time_raw_key)


@admin_bp.post("/keys/create")
@login_required
@require_permission("keys:create")
def create_key():
    name = request.form.get("name", "").strip()
    note = request.form.get("note", "").strip() or None
    rate_limit_raw = request.form.get("rate_limit_per_minute", "100").strip() or "100"

    if not name:
        flash("Tên key không được để trống", "danger")
        return redirect(url_for("admin.keys"))

    try:
        rate_limit = max(1, int(rate_limit_raw))
    except ValueError:
        flash("Rate limit phải là số nguyên", "danger")
        return redirect(url_for("admin.keys"))

    success, raw_key_value = create_api_key(name=name, note=note, rate_limit=rate_limit)
    if not success:
        flash("Tên key đã tồn tại", "danger")
        return redirect(url_for("admin.keys"))

    session["one_time_raw_key"] = raw_key_value
    flash("Đã tạo API key mới", "success")
    return redirect(url_for("admin.keys"))


@admin_bp.post("/keys/<int:key_id>/update")
@login_required
@require_permission("keys:update")
def update_key(key_id: int):
    note = request.form.get("note", "").strip() or None
    rate_limit_raw = request.form.get("rate_limit_per_minute", "").strip()

    if not rate_limit_raw:
        flash("Rate limit không được để trống", "danger")
        return redirect(url_for("admin.keys"))

    try:
        rate_limit = max(1, int(rate_limit_raw))
    except ValueError:
        flash("Rate limit phải là số nguyên", "danger")
        return redirect(url_for("admin.keys"))

    if not update_api_key(key_id=key_id, note=note, rate_limit=rate_limit):
        flash("Không tìm thấy key", "danger")
        return redirect(url_for("admin.keys"))

    flash("Đã cập nhật key", "success")
    return redirect(url_for("admin.keys"))


@admin_bp.post("/keys/<int:key_id>/toggle")
@login_required
@require_permission("keys:toggle")
def toggle_key(key_id: int):
    if not toggle_api_key(key_id):
        flash("Không tìm thấy key", "danger")
    return redirect(url_for("admin.keys"))


@admin_bp.post("/keys/<int:key_id>/delete")
@login_required
@require_permission("keys:delete")
def delete_key(key_id: int):
    if delete_api_key(key_id):
        flash("Đã xóa key", "success")
    else:
        flash("Không tìm thấy key", "danger")
    return redirect(url_for("admin.keys"))


@admin_bp.get("/logs")
@login_required
@require_permission("logs:view")
def logs():
    page = max(int(request.args.get("page", 1)), 1)
    logs_items = list_logs(page=page)
    return render_template("logs.html", logs_items=logs_items, page=page)


@admin_bp.get("/data-manager")
@login_required
@require_any_permission("data:view", "keys:view")
def data_manager():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "all").strip().lower()
    data_rows = query_data_manager(search=search, status=status)
    return render_template(
        "data_manager.html",
        data_rows=data_rows,
        search=search,
        status=status,
    )
