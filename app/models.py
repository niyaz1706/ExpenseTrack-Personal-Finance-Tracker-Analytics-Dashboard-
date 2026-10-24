import enum
from datetime import datetime, date
from typing import Dict, Any, Optional
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint, Index

db = SQLAlchemy()


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class User(UserMixin, db.Model):
    """User account model for authentication and data ownership."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    categories = db.relationship("Category", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    transactions = db.relationship("Transaction", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and store the given password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize user object without sensitive information."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Category(db.Model):
    """
    Category model for classifying transactions.
    user_id is None for default system categories available to all users.
    """
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="categories")
    transactions = db.relationship("Transaction", back_populates="category", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_category"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize category object."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type,
            "is_default": self.user_id is None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.type})>"


class Transaction(db.Model):
    """Transaction model representing an income or expense entry."""
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_user_date", "user_id", "transaction_date"),
        Index("idx_transactions_category_id", "category_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize transaction object with category details."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_type": self.category.type if self.category else None,
            "amount": float(self.amount),
            "description": self.description,
            "transaction_date": self.transaction_date.strftime("%Y-%m-%d") if self.transaction_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Transaction {self.id}: {self.amount}>"
