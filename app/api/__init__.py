from datetime import datetime, date
from typing import Tuple, Any, Dict
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from app.models import db, Category, Transaction

api_bp = Blueprint("api", __name__)


def api_response(data: Any = None, error: Any = None, status_code: int = 200) -> Tuple[Any, int]:
    """Helper function to build uniform REST JSON responses."""
    success = 200 <= status_code < 300
    return jsonify({
        "success": success,
        "data": data,
        "error": error
    }), status_code


# =====================================================================
# Transactions API
# =====================================================================

@api_bp.route("/transactions", methods=["GET"])
@login_required
def get_transactions():
    """
    List user transactions with optional filters and pagination.
    Filters: category_id, type, start_date, end_date
    Pagination: page, per_page
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        return api_response(error="page and per_page must be integers", status_code=400)

    query = Transaction.query.filter_by(user_id=current_user.id)

    # Optional filter: category_id
    category_id = request.args.get("category_id")
    if category_id:
        try:
            query = query.filter(Transaction.category_id == int(category_id))
        except ValueError:
            return api_response(error="category_id must be an integer", status_code=400)

    # Optional filter: type (income / expense)
    cat_type = request.args.get("type")
    if cat_type:
        cat_type = cat_type.lower()
        if cat_type not in ["income", "expense"]:
            return api_response(error="type must be 'income' or 'expense'", status_code=400)
        query = query.join(Category).filter(Category.type == cat_type)

    # Optional filter: start_date
    start_date = request.args.get("start_date")
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date >= parsed_start)
        except ValueError:
            return api_response(error="start_date must be in YYYY-MM-DD format", status_code=400)

    # Optional filter: end_date
    end_date = request.args.get("end_date")
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date <= parsed_end)
        except ValueError:
            return api_response(error="end_date must be in YYYY-MM-DD format", status_code=400)

    query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response(data={
        "items": [t.to_dict() for t in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }, status_code=200)


@api_bp.route("/transactions", methods=["POST"])
@login_required
def create_transaction():
    """Create a new transaction for the authenticated user."""
    data = request.get_json() or {}

    amount = data.get("amount")
    category_id = data.get("category_id")
    transaction_date_str = data.get("transaction_date")
    description = data.get("description", "").strip()

    if amount is None or category_id is None or not transaction_date_str:
        return api_response(error="amount, category_id, and transaction_date are required", status_code=400)

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            return api_response(error="amount must be greater than zero", status_code=400)
    except (ValueError, TypeError):
        return api_response(error="amount must be a valid positive number", status_code=400)

    try:
        parsed_date = datetime.strptime(transaction_date_str, "%Y-%m-%d").date()
    except ValueError:
        return api_response(error="transaction_date must be in YYYY-MM-DD format", status_code=400)

    # Verify category exists and is accessible to current_user (default or owned by current_user)
    category = Category.query.filter(
        (Category.id == category_id) &
        ((Category.user_id == current_user.id) | (Category.user_id.is_(None)))
    ).first()

    if not category:
        return api_response(error="Selected category does not exist or is not accessible", status_code=404)

    transaction = Transaction(
        user_id=current_user.id,
        category_id=category.id,
        amount=amount_val,
        description=description if description else None,
        transaction_date=parsed_date
    )

    db.session.add(transaction)
    db.session.commit()

    return api_response(data=transaction.to_dict(), status_code=201)


@api_bp.route("/transactions/<int:trans_id>", methods=["GET"])
@login_required
def get_transaction(trans_id: int):
    """Retrieve a single transaction owned by current user."""
    transaction = Transaction.query.filter_by(id=trans_id, user_id=current_user.id).first()
    if not transaction:
        return api_response(error="Transaction not found", status_code=404)
    return api_response(data=transaction.to_dict(), status_code=200)


@api_bp.route("/transactions/<int:trans_id>", methods=["PUT"])
@login_required
def update_transaction(trans_id: int):
    """Update an existing transaction owned by current user."""
    transaction = Transaction.query.filter_by(id=trans_id, user_id=current_user.id).first()
    if not transaction:
        return api_response(error="Transaction not found", status_code=404)

    data = request.get_json() or {}

    if "amount" in data:
        try:
            amount_val = float(data["amount"])
            if amount_val <= 0:
                return api_response(error="amount must be greater than zero", status_code=400)
            transaction.amount = amount_val
        except (ValueError, TypeError):
            return api_response(error="amount must be a valid positive number", status_code=400)

    if "category_id" in data:
        cat_id = data["category_id"]
        category = Category.query.filter(
            (Category.id == cat_id) &
            ((Category.user_id == current_user.id) | (Category.user_id.is_(None)))
        ).first()
        if not category:
            return api_response(error="Selected category does not exist or is not accessible", status_code=404)
        transaction.category_id = category.id

    if "transaction_date" in data:
        try:
            parsed_date = datetime.strptime(data["transaction_date"], "%Y-%m-%d").date()
            transaction.transaction_date = parsed_date
        except ValueError:
            return api_response(error="transaction_date must be in YYYY-MM-DD format", status_code=400)

    if "description" in data:
        transaction.description = data["description"].strip() if data["description"] else None

    db.session.commit()
    return api_response(data=transaction.to_dict(), status_code=200)


@api_bp.route("/transactions/<int:trans_id>", methods=["DELETE"])
@login_required
def delete_transaction(trans_id: int):
    """Delete a transaction owned by current user."""
    transaction = Transaction.query.filter_by(id=trans_id, user_id=current_user.id).first()
    if not transaction:
        return api_response(error="Transaction not found", status_code=404)

    db.session.delete(transaction)
    db.session.commit()
    return api_response(data={"message": "Transaction deleted successfully"}, status_code=200)


# =====================================================================
# Categories API
# =====================================================================

@api_bp.route("/categories", methods=["GET"])
@login_required
def get_categories():
    """List system default categories plus custom categories created by current user."""
    categories = Category.query.filter(
        (Category.user_id.is_(None)) | (Category.user_id == current_user.id)
    ).order_by(Category.type.asc(), Category.name.asc()).all()

    return api_response(data=[c.to_dict() for c in categories], status_code=200)


@api_bp.route("/categories", methods=["POST"])
@login_required
def create_category():
    """Create a user-owned custom category."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    cat_type = (data.get("type") or "").strip().lower()

    if not name:
        return api_response(error="Category name is required", status_code=400)
    if cat_type not in ["income", "expense"]:
        return api_response(error="Category type must be 'income' or 'expense'", status_code=400)

    # Check for existing duplicate name for this user or default system categories
    existing = Category.query.filter(
        ((Category.user_id == current_user.id) | (Category.user_id.is_(None))) &
        (func.lower(Category.name) == name.lower())
    ).first()

    if existing:
        return api_response(error=f"A category named '{name}' already exists", status_code=409)

    category = Category(
        user_id=current_user.id,
        name=name,
        type=cat_type
    )
    db.session.add(category)
    db.session.commit()

    return api_response(data=category.to_dict(), status_code=201)


@api_bp.route("/categories/<int:cat_id>", methods=["PUT"])
@login_required
def update_category(cat_id: int):
    """Update a custom category owned by current user."""
    category = Category.query.filter_by(id=cat_id, user_id=current_user.id).first()
    if not category:
        # Check if it is a default category
        if Category.query.filter_by(id=cat_id, user_id=None).first():
            return api_response(error="System default categories cannot be modified", status_code=403)
        return api_response(error="Category not found", status_code=404)

    data = request.get_json() or {}
    name = data.get("name", category.name).strip()
    cat_type = data.get("type", category.type).strip().lower()

    if not name:
        return api_response(error="Category name cannot be empty", status_code=400)
    if cat_type not in ["income", "expense"]:
        return api_response(error="Category type must be 'income' or 'expense'", status_code=400)

    # Check duplicate name
    existing = Category.query.filter(
        (Category.id != cat_id) &
        ((Category.user_id == current_user.id) | (Category.user_id.is_(None))) &
        (func.lower(Category.name) == name.lower())
    ).first()

    if existing:
        return api_response(error=f"A category named '{name}' already exists", status_code=409)

    category.name = name
    category.type = cat_type
    db.session.commit()

    return api_response(data=category.to_dict(), status_code=200)


@api_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
@login_required
def delete_category(cat_id: int):
    """Delete a custom category owned by current user (if no transactions use it)."""
    category = Category.query.filter_by(id=cat_id, user_id=current_user.id).first()
    if not category:
        if Category.query.filter_by(id=cat_id, user_id=None).first():
            return api_response(error="System default categories cannot be deleted", status_code=403)
        return api_response(error="Category not found", status_code=404)

    # Check if there are transactions associated with this category
    has_transactions = Transaction.query.filter_by(category_id=cat_id).first()
    if has_transactions:
        return api_response(
            error="Cannot delete category because transactions are attached to it. Please reassign or delete the transactions first.",
            status_code=409
        )

    db.session.delete(category)
    db.session.commit()

    return api_response(data={"message": "Category deleted successfully"}, status_code=200)


# =====================================================================
# Analytics API
# =====================================================================

@api_bp.route("/analytics/summary", methods=["GET"])
@login_required
def analytics_summary():
    """Calculate total income, total expense, and balance for a date range."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = db.session.query(
        Category.type,
        func.coalesce(func.sum(Transaction.amount), 0).label("total")
    ).join(Category, Transaction.category_id == Category.id)\
     .filter(Transaction.user_id == current_user.id)

    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date >= parsed_start)
        except ValueError:
            return api_response(error="start_date must be in YYYY-MM-DD format", status_code=400)

    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date <= parsed_end)
        except ValueError:
            return api_response(error="end_date must be in YYYY-MM-DD format", status_code=400)

    results = query.group_by(Category.type).all()

    total_income = 0.0
    total_expense = 0.0

    for cat_type, total in results:
        if cat_type == "income":
            total_income = float(total)
        elif cat_type == "expense":
            total_expense = float(total)

    net_balance = round(total_income - total_expense, 2)

    return api_response(data={
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net_balance": net_balance,
        "start_date": start_date,
        "end_date": end_date
    }, status_code=200)


@api_bp.route("/analytics/by-category", methods=["GET"])
@login_required
def analytics_by_category():
    """Breakdown of expenses or income by category."""
    cat_type = request.args.get("type", "expense").lower()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if cat_type not in ["expense", "income"]:
        return api_response(error="type must be 'expense' or 'income'", status_code=400)

    query = db.session.query(
        Category.name,
        func.coalesce(func.sum(Transaction.amount), 0).label("total")
    ).join(Category, Transaction.category_id == Category.id)\
     .filter(Transaction.user_id == current_user.id, Category.type == cat_type)

    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date >= parsed_start)
        except ValueError:
            return api_response(error="start_date must be in YYYY-MM-DD format", status_code=400)

    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date <= parsed_end)
        except ValueError:
            return api_response(error="end_date must be in YYYY-MM-DD format", status_code=400)

    results = query.group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()

    labels = [r[0] for r in results]
    amounts = [float(r[1]) for r in results]

    return api_response(data={
        "labels": labels,
        "amounts": amounts,
        "type": cat_type
    }, status_code=200)


@api_bp.route("/analytics/monthly", methods=["GET"])
@login_required
def analytics_monthly():
    """Monthly income vs expense breakdown for the last 12 months or specified year."""
    # Group by year and month
    query = db.session.query(
        extract("year", Transaction.transaction_date).label("year"),
        extract("month", Transaction.transaction_date).label("month"),
        Category.type.label("type"),
        func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id)\
     .filter(Transaction.user_id == current_user.id)\
     .group_by("year", "month", Category.type)\
     .order_by("year", "month")

    results = query.all()

    # Consolidate into structured monthly buckets
    months_dict: Dict[str, Dict[str, float]] = {}

    for row in results:
        year_val = int(row.year)
        month_val = int(row.month)
        month_key = f"{year_val}-{month_val:02d}"
        if month_key not in months_dict:
            months_dict[month_key] = {"income": 0.0, "expense": 0.0}
        months_dict[month_key][row.type] = float(row.total)

    sorted_months = sorted(months_dict.keys())

    return api_response(data={
        "labels": sorted_months,
        "income": [round(months_dict[m]["income"], 2) for m in sorted_months],
        "expense": [round(months_dict[m]["expense"], 2) for m in sorted_months]
    }, status_code=200)
