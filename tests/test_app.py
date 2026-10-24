import pytest
from app import create_app
from app.models import db, User, Category, Transaction


@pytest.fixture
def app():
    """Create test application context with in-memory database."""
    from app import seed_default_categories
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        seed_default_categories()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for dispatching requests."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Authenticated client with pre-seeded user and default categories."""
    with app.app_context():
        user = User(username="alice", email="alice@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Log in user
    client.post("/auth/login", data={
        "identifier": "alice",
        "password": "password123"
    }, follow_redirects=True)

    client.user_id = user_id
    return client


# -------------------------------------------------------------
# Auth Tests
# -------------------------------------------------------------

def test_register_success(client, app):
    """Test user registration."""
    res = client.post("/auth/register", data={
        "username": "bob",
        "email": "bob@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="bob").first()
        assert user is not None
        assert user.email == "bob@example.com"
        assert user.check_password("password123")


def test_register_duplicate_username(client, app):
    """Test validation when registering an existing username."""
    with app.app_context():
        u = User(username="charlie", email="charlie@example.com")
        u.set_password("pass123")
        db.session.add(u)
        db.session.commit()

    res = client.post("/auth/register", data={
        "username": "charlie",
        "email": "charlie2@example.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)
    assert b"Username is already taken" in res.data


def test_login_and_logout(client, app):
    """Test user login and session termination."""
    with app.app_context():
        u = User(username="dave", email="dave@example.com")
        u.set_password("pass12345")
        db.session.add(u)
        db.session.commit()

    # Login
    login_res = client.post("/auth/login", data={
        "identifier": "dave",
        "password": "pass12345"
    }, follow_redirects=True)
    assert b"Welcome back, dave" in login_res.data

    # Logout
    logout_res = client.get("/auth/logout", follow_redirects=True)
    assert b"You have been logged out" in logout_res.data


def test_unauthenticated_api_returns_401(client):
    """Ensure unauthenticated access to API routes returns JSON 401 instead of redirect."""
    res = client.get("/api/transactions")
    assert res.status_code == 401
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "Authentication required" in json_data["error"]


# -------------------------------------------------------------
# Transaction CRUD Tests
# -------------------------------------------------------------

def test_transaction_crud(auth_client, app):
    """Test create, read, update, delete for transactions."""
    # Find a default category
    with app.app_context():
        food_cat = Category.query.filter_by(name="Food").first()
        food_id = food_cat.id

    # 1. Create transaction
    create_res = auth_client.post("/api/transactions", json={
        "amount": 45.50,
        "category_id": food_id,
        "transaction_date": "2026-10-10",
        "description": "Lunch with team"
    })
    assert create_res.status_code == 201
    trans_data = create_res.get_json()["data"]
    trans_id = trans_data["id"]
    assert trans_data["amount"] == 45.50
    assert trans_data["description"] == "Lunch with team"

    # 2. Get single transaction
    get_res = auth_client.get(f"/api/transactions/{trans_id}")
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["id"] == trans_id

    # 3. Update transaction
    update_res = auth_client.put(f"/api/transactions/{trans_id}", json={
        "amount": 50.00,
        "description": "Lunch and dessert"
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["data"]["amount"] == 50.00
    assert update_res.get_json()["data"]["description"] == "Lunch and dessert"

    # 4. Delete transaction
    del_res = auth_client.delete(f"/api/transactions/{trans_id}")
    assert del_res.status_code == 200

    # Verify not found after delete
    get_after_del = auth_client.get(f"/api/transactions/{trans_id}")
    assert get_after_del.status_code == 404


# -------------------------------------------------------------
# Multi-User Data Isolation Tests
# -------------------------------------------------------------

def test_data_isolation_between_users(app, client):
    """Test that User A cannot view, edit, or delete User B's transactions or categories."""
    with app.app_context():
        user_a = User(username="usera", email="usera@example.com")
        user_a.set_password("pass123")
        user_b = User(username="userb", email="userb@example.com")
        user_b.set_password("pass123")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        # Add transaction for User A
        from datetime import date
        food_cat = Category.query.filter_by(name="Food").first()
        t_a = Transaction(
            user_id=user_a.id,
            category_id=food_cat.id,
            amount=100.0,
            transaction_date=date(2026, 10, 1),
            description="User A Private Expense"
        )
        db.session.add(t_a)
        db.session.commit()
        t_a_id = t_a.id

    # Log in as User B
    client.post("/auth/login", data={"identifier": "userb", "password": "pass123"}, follow_redirects=True)

    # 1. User B lists transactions: should NOT see User A's transaction
    list_res = client.get("/api/transactions")
    assert list_res.status_code == 200
    assert list_res.get_json()["data"]["total"] == 0

    # 2. User B tries to get User A's transaction directly: 404
    get_res = client.get(f"/api/transactions/{t_a_id}")
    assert get_res.status_code == 404

    # 3. User B tries to update User A's transaction: 404
    put_res = client.put(f"/api/transactions/{t_a_id}", json={"amount": 999.0})
    assert put_res.status_code == 404

    # 4. User B tries to delete User A's transaction: 404
    delete_res = client.delete(f"/api/transactions/{t_a_id}")
    assert delete_res.status_code == 404


# -------------------------------------------------------------
# Analytics Tests
# -------------------------------------------------------------

def test_analytics_endpoints(auth_client, app):
    """Test /api/analytics/summary, /by-category, and /monthly."""
    with app.app_context():
        food = Category.query.filter_by(name="Food").first()
        salary = Category.query.filter_by(name="Salary").first()

    # Add expense $50
    auth_client.post("/api/transactions", json={
        "amount": 50.0,
        "category_id": food.id,
        "transaction_date": "2026-10-05"
    })

    # Add income $200
    auth_client.post("/api/transactions", json={
        "amount": 200.0,
        "category_id": salary.id,
        "transaction_date": "2026-10-06"
    })

    # Summary
    res_summary = auth_client.get("/api/analytics/summary")
    assert res_summary.status_code == 200
    summary_data = res_summary.get_json()["data"]
    assert summary_data["total_income"] == 200.0
    assert summary_data["total_expense"] == 50.0
    assert summary_data["net_balance"] == 150.0

    # By category
    res_cat = auth_client.get("/api/analytics/by-category?type=expense")
    assert res_cat.status_code == 200
    cat_data = res_cat.get_json()["data"]
    assert "Food" in cat_data["labels"]
    assert 50.0 in cat_data["amounts"]

    # Monthly
    res_monthly = auth_client.get("/api/analytics/monthly")
    assert res_monthly.status_code == 200
    monthly_data = res_monthly.get_json()["data"]
    assert "2026-10" in monthly_data["labels"]
