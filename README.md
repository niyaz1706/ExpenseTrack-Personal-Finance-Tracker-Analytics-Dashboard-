# ExpenseTrack - Full-Stack Personal Finance Tracker

ExpenseTrack is a full-stack personal finance tracker built with Python, Flask, MySQL, and vanilla JavaScript (Bootstrap 5 & Chart.js).

---

## Features
- **Session Authentication:** Registration, login, remember-me, and logout powered by Flask-Login and Werkzeug password hashing.
- **Data Isolation:** All database queries and modifications are strictly scoped to the authenticated user.
- **RESTful API:** Clean `/api/` endpoints with uniform JSON responses (`{"success": bool, "data": ..., "error": ...}`) and appropriate HTTP status codes.
- **Interactive Dashboard:** Summary cards for total income, expense, and net balance with date filtering, alongside Chart.js doughnut and bar charts.
- **Transaction Management:** Dynamic transaction table with modal add/edit, confirm deletion, pagination, type filtering, and date range filters.
- **Category Customization:** Pre-seeded default categories (Food, Rent, Transport, Utilities, Entertainment, Health, Salary, Freelance) plus custom user categories.

---

## Tech Stack
- **Backend:** Python 3.11+, Flask, Flask-Login, Flask-SQLAlchemy, PyMySQL, Flask-Migrate
- **Database:** MySQL 8 (supports SQLite for local friction-free development)
- **Frontend:** Jinja2 templates, Bootstrap 5, Bootstrap Icons, Chart.js 4 (no build step needed)
- **Configuration:** python-dotenv

---

## Project Structure
```text
expensetrack/
├── app/
│   ├── __init__.py          # App factory, extensions, error handlers, seed logic
│   ├── models.py            # User, Category, Transaction SQLAlchemy models
│   ├── auth/                # Auth blueprint (register, login, logout)
│   ├── api/                 # REST API blueprint (/api/*)
│   ├── views/               # Page routes (dashboard, transactions, categories)
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html
│   │   ├── auth/            # login.html, register.html
│   │   ├── dashboard/       # index.html
│   │   ├── transactions/    # index.html
│   │   └── categories/      # index.html
│   └── static/              # Custom CSS and JavaScript helpers
│       ├── css/style.css
│       └── js/main.js
├── migrations/              # Flask-Migrate / Alembic migration scripts
├── schema.sql               # Normalized MySQL 8 schema + default seed categories
├── tests/
│   └── test_app.py          # Pytest suite (auth, CRUD, multi-user isolation, analytics)
├── config.py                # Environment-driven configurations
├── .env.example             # Example configuration template
├── requirements.txt         # Project dependencies
├── run.py                   # Application entry point
└── README.md
```

---

## Setup & Installation

### 1. Clone & Navigate
```bash
cd expensetrack
```

### 2. Install Dependencies
Ensure you have Python 3.11+ installed.
```bash
pip install -r requirements.txt
```

### 3. Setup MySQL Database
Open your MySQL terminal or client and run the provided `schema.sql`:
```bash
mysql -u root -p < schema.sql
```
This creates the `expensetrack_db` database, tables with foreign key constraints, indexes, and default categories.

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your MySQL connection:
```ini
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/expensetrack_db
SECRET_KEY=your-secure-random-secret-key
FLASK_ENV=development
```
*(Note: If MySQL is not running on your machine, ExpenseTrack automatically defaults to SQLite `sqlite:///expensetrack.db` for instant local testing).*

### 5. Apply Database Migrations (Optional / Flask-Migrate)
```bash
flask --app run:app db upgrade
```

### 6. Run the Application
```bash
python run.py
```
Open your browser at [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Running the Tests
ExpenseTrack includes an automated test suite verifying session auth, transaction CRUD, multi-user security isolation, and financial analytics:
```bash
python -m pytest tests -v
```

---

## REST API Reference

All `/api/*` endpoints require authentication. Unauthenticated requests receive HTTP `401 Unauthorized` with JSON:
```json
{
  "success": false,
  "data": null,
  "error": "Authentication required. Please log in."
}
```

### Transactions
| Method | Endpoint | Description | Query Parameters / Body |
|---|---|---|---|
| `GET` | `/api/transactions` | List user transactions | `page`, `per_page`, `type`, `category_id`, `start_date`, `end_date` |
| `POST` | `/api/transactions` | Create a transaction | JSON: `amount`, `category_id`, `transaction_date`, `description` |
| `GET` | `/api/transactions/<id>` | Get single transaction | - |
| `PUT` | `/api/transactions/<id>` | Update transaction | JSON: `amount`, `category_id`, `transaction_date`, `description` |
| `DELETE` | `/api/transactions/<id>` | Delete transaction | - |

### Categories
| Method | Endpoint | Description | Query Parameters / Body |
|---|---|---|---|
| `GET` | `/api/categories` | List default + user categories | - |
| `POST` | `/api/categories` | Create custom category | JSON: `name`, `type` (`income` or `expense`) |
| `PUT` | `/api/categories/<id>` | Update custom category | JSON: `name`, `type` |
| `DELETE` | `/api/categories/<id>` | Delete custom category | Fails with 409 if transactions are linked |

### Analytics
| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `GET` | `/api/analytics/summary` | Total income, expense & balance | `start_date`, `end_date` |
| `GET` | `/api/analytics/by-category` | Breakdown by category | `type` (`expense` or `income`), `start_date`, `end_date` |
| `GET` | `/api/analytics/monthly` | Income vs expense per month | - |
