import os
from typing import Optional
from flask import Flask, jsonify, request, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config_by_name
from app.models import db, User, Category

login_manager = LoginManager()
migrate = Migrate()

DEFAULT_CATEGORIES = [
    ("Food", "expense"),
    ("Rent", "expense"),
    ("Transport", "expense"),
    ("Utilities", "expense"),
    ("Entertainment", "expense"),
    ("Health", "expense"),
    ("Salary", "income"),
    ("Freelance", "income"),
]


def seed_default_categories() -> None:
    """Ensure default system categories exist in the database."""
    for name, cat_type in DEFAULT_CATEGORIES:
        exists = Category.query.filter_by(user_id=None, name=name).first()
        if not exists:
            db.session.add(Category(user_id=None, name=name, type=cat_type))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory for ExpenseTrack."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        # Check if the request is for the API or expects JSON
        if request.path.startswith("/api/") or request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({
                "success": False,
                "data": None,
                "error": "Authentication required. Please log in."
            }), 401
        return redirect(url_for("auth.login", next=request.path))

    # Register blueprints
    from app.auth import auth_bp
    from app.api import api_bp
    from app.views import views_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    # Global error handlers
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "data": None, "error": getattr(error, "description", "Bad Request")}), 400
        return "Bad Request", 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "data": None, "error": getattr(error, "description", "Resource Not Found")}), 404
        return "Resource Not Found", 404

    @app.errorhandler(500)
    def server_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "data": None, "error": "Internal Server Error"}), 500
        return "Internal Server Error", 500

    return app


def init_db(app: Flask) -> None:
    """Initialize database tables and seed default categories if needed."""
    with app.app_context():
        db.create_all()
        seed_default_categories()
