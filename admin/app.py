from __future__ import annotations

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from admin.auth import init_login_manager, inject_admin_permission_helpers
from admin.bootstrap import bootstrap_admin_user
from admin.routes import admin_bp
from core.config import settings

csrf = CSRFProtect()


def create_admin_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.secret_key = settings.FLASK_SESSION_SECRET
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = settings.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_SAMESITE"] = settings.SESSION_COOKIE_SAMESITE

    csrf.init_app(app)
    init_login_manager(app)
    app.context_processor(inject_admin_permission_helpers)
    bootstrap_admin_user()

    app.register_blueprint(admin_bp, url_prefix="/admin")
    return app


app = create_admin_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.API_ADMIN)
