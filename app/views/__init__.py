from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Landing route: redirect to dashboard if logged in, else login."""
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    return redirect(url_for("auth.login"))


@views_bp.route("/dashboard")
@login_required
def dashboard():
    """Render financial analytics and metrics dashboard."""
    return render_template("dashboard/index.html")


@views_bp.route("/transactions")
@login_required
def transactions():
    """Render transactions management table with filters and modals."""
    return render_template("transactions/index.html")


@views_bp.route("/categories")
@login_required
def categories():
    """Render categories management page."""
    return render_template("categories/index.html")
