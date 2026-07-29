import os
import secrets
import logging
from flask import Flask, abort, request, session
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db, migrate, login_manager



def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SECURE"] = os.getenv("REMEMBER_COOKIE_SECURE", "false").lower() == "true"
    app.config["REMEMBER_COOKIE_SAMESITE"] = os.getenv("REMEMBER_COOKIE_SAMESITE", "Lax")
    app.config["REGISTRATION_INVITE_ENABLED"] = os.getenv("REGISTRATION_INVITE_ENABLED", "false").lower() == "true"
    app.config["REGISTRATION_INVITE_CODE"] = None
    app.config["REGISTRATION_INVITE_DAY"] = None

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    if os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    def csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @app.before_request
    def protect_post_requests():
        if request.method != "POST":
            return None

        expected_token = session.get("_csrf_token")
        submitted_token = request.form.get("_csrf_token")

        if not expected_token or not submitted_token or not secrets.compare_digest(expected_token, submitted_token):
            abort(400, "Jeton de formulaire invalide.")

        return None

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), geolocation=(), microphone=()",
        )

        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token}

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from . import models

    from .routes import main
    app.register_blueprint(main)

    return app
