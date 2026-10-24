-- =======================================================
-- ExpenseTrack Database Schema (MySQL 8)
-- =======================================================

CREATE DATABASE IF NOT EXISTS expensetrack_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE expensetrack_db;

-- -------------------------------------------------------
-- Table: users
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------
-- Table: categories
-- Null user_id indicates a system-default category accessible by everyone.
-- Non-null user_id indicates a custom user-created category.
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    name VARCHAR(50) NOT NULL,
    type ENUM('income', 'expense') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_categories_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT uq_user_category UNIQUE (user_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------
-- Table: transactions
-- Foreign key to user with ON DELETE CASCADE
-- Foreign key to category with RESTRICT to prevent deleting in-use categories
-- Indexes on (user_id, transaction_date) and (category_id)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255) NULL,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_transactions_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_transactions_category
        FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_transactions_user_date ON transactions (user_id, transaction_date);
CREATE INDEX idx_transactions_category_id ON transactions (category_id);

-- -------------------------------------------------------
-- Seed: Default Categories
-- -------------------------------------------------------
INSERT IGNORE INTO categories (user_id, name, type) VALUES
    (NULL, 'Food', 'expense'),
    (NULL, 'Rent', 'expense'),
    (NULL, 'Transport', 'expense'),
    (NULL, 'Utilities', 'expense'),
    (NULL, 'Entertainment', 'expense'),
    (NULL, 'Health', 'expense'),
    (NULL, 'Salary', 'income'),
    (NULL, 'Freelance', 'income');
