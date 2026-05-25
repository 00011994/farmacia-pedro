import os
import sqlite3
import tempfile

import pytest

from src.core.config import load_settings


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            avg_cost REAL NOT NULL,
            stock INTEGER NOT NULL
        );
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            sale_date TEXT NOT NULL,
            region TEXT NOT NULL
        );
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            invoice_date TEXT NOT NULL,
            supplier TEXT NOT NULL
        );
        CREATE TABLE competitor_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            competitor TEXT NOT NULL,
            price REAL NOT NULL,
            collected_at TEXT NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            customer TEXT NOT NULL,
            total REAL NOT NULL
        );
        CREATE TABLE order_items (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO products (sku, name, category, price, avg_cost, stock) VALUES (?, ?, ?, ?, ?, ?)",
        ("MED001", "Dipirona 500mg", "Analgesico", 12.90, 5.20, 50),
    )
    conn.execute(
        "INSERT INTO products (sku, name, category, price, avg_cost, stock) VALUES (?, ?, ?, ?, ?, ?)",
        ("HIG001", "Alcool Gel 70%", "Higiene", 9.90, 3.50, 2),
    )
    conn.execute(
        "INSERT INTO products (sku, name, category, price, avg_cost, stock) VALUES (?, ?, ?, ?, ?, ?)",
        ("MED003", "Amoxicilina 500mg", "Antibiotico", 42.00, 28.00, 0),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def settings(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("ERP_DB_PATH", tmp_db)
    monkeypatch.setenv("REPORT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("OPERATIONAL_SCOPES", "stock,orders")
    monkeypatch.setenv("AUDIT_SCOPES", "invoices,costs")
    monkeypatch.setenv("STRATEGIST_SCOPES", "sales,competitors")
    monkeypatch.setenv("INVENTORY_SCOPES", "stock,turnover")
    return load_settings()
