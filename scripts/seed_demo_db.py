import os
import sqlite3
from datetime import datetime, timedelta, timezone


DB_PATH = os.path.join("data", "erp_demo.db")


def reset_schema(conn):
    conn.executescript(
        """
        DROP TABLE IF EXISTS delivery_assignments;
        DROP TABLE IF EXISTS driver_locations;
        DROP TABLE IF EXISTS drivers;
        DROP TABLE IF EXISTS delivery_settings;
        DROP TABLE IF EXISTS customer_orders;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS competitor_prices;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS sales;
        DROP TABLE IF EXISTS products;

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
            region TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            invoice_date TEXT NOT NULL,
            supplier TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
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
            qty INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'funcionario',
            is_active INTEGER NOT NULL DEFAULT 1,
            nome_completo TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE customer_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            customer_name TEXT DEFAULT '',
            customer_phone TEXT DEFAULT '',
            items_json TEXT NOT NULL DEFAULT '[]',
            delivery_type TEXT DEFAULT 'retirada',
            delivery_address TEXT DEFAULT '',
            taxa_entrega REAL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'pendente',
            total REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE drivers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            pin_hash    TEXT NOT NULL,
            photo_path  TEXT,
            status      TEXT NOT NULL DEFAULT 'available',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE driver_locations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id   INTEGER NOT NULL REFERENCES drivers(id),
            order_id    INTEGER,
            lat         REAL NOT NULL,
            lon         REAL NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE delivery_assignments (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id         INTEGER NOT NULL REFERENCES drivers(id),
            order_id          INTEGER NOT NULL REFERENCES orders(id),
            status            TEXT NOT NULL DEFAULT 'assigned',
            tracking_token    TEXT NOT NULL UNIQUE,
            eta_minutes       INTEGER,
            dest_lat          REAL,
            dest_lon          REAL,
            assigned_at       TEXT NOT NULL DEFAULT (datetime('now')),
            started_at        TEXT,
            completed_at      TEXT,
            stopped_alert_min INTEGER NOT NULL DEFAULT 5
        );

        CREATE TABLE delivery_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telefone TEXT NOT NULL DEFAULT '',
            senha_hash TEXT NOT NULL,
            endereco_rua TEXT DEFAULT '',
            endereco_numero TEXT DEFAULT '',
            endereco_complemento TEXT DEFAULT '',
            endereco_bairro TEXT DEFAULT '',
            endereco_cidade TEXT DEFAULT 'Rio de Janeiro',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )


def _hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception:
        import hashlib, hmac as hmac_mod
        print("[AVISO] bcrypt indisponivel - usando SHA-256 (apenas para demo)")
        return "sha256:" + hmac_mod.new(b"demo-key", password.encode(), hashlib.sha256).hexdigest()


def seed_data(conn):
    products = [
        ("MED001", "Dipirona 500mg", "Analgesico", 12.90, 5.20, 120),
        ("MED002", "Paracetamol 750mg", "Analgesico", 18.50, 7.00, 60),
        ("MED003", "Amoxicilina 500mg", "Antibiotico", 42.00, 28.00, 15),
        ("HIG001", "Alcool Gel 70%", "Higiene", 9.90, 3.50, 300),
        ("HIG002", "Mascara Descartavel", "Higiene", 2.50, 0.80, 500),
        ("SUP001", "Vitamina C 1g", "Suplemento", 39.90, 18.00, 8),
    ]
    conn.executemany(
        "INSERT INTO products (sku, name, category, price, avg_cost, stock) VALUES (?, ?, ?, ?, ?, ?)",
        products,
    )

    today = datetime.now(timezone.utc).date()

    vendas = [
        (1, "2025-12-01", "Centro", "Joao", 125.80),
        (2, "2025-12-05", "Centro", "Maria", 89.50),
        (3, "2026-01-10", "Centro", "Carlos", 42.00),
        (4, "2026-01-15", "Centro", "Joao", 18.50),
    ]
    venda_datas = {row[0]: row[1] for row in vendas}
    itens_venda = [
        (1, 1, 1, 5, 12.90),
        (2, 1, 4, 3, 9.90),
        (3, 2, 2, 2, 18.50),
        (4, 3, 3, 1, 42.00),
        (5, 4, 2, 1, 18.50),
    ]
    sales_rows = []
    for _, id_venda, id_produto, quantidade, preco_unitario in itens_venda:
        sale_date = venda_datas.get(id_venda, today.isoformat())
        sales_rows.append((id_produto, quantidade, preco_unitario, sale_date, "centro"))

    conn.executemany(
        "INSERT INTO sales (product_id, qty, price, sale_date, region) VALUES (?, ?, ?, ?, ?)",
        sales_rows,
    )

    invoice_rows = []
    for i, (sku, _, _, _, cost, _) in enumerate(products, start=1):
        inv_date = (today - timedelta(days=(i % 14))).isoformat()
        unit_cost = cost * (1.1 if i in (3,) else 1.0)
        invoice_rows.append((i, unit_cost, inv_date, "Fornecedor A"))

    conn.executemany(
        "INSERT INTO invoices (product_id, unit_cost, invoice_date, supplier) VALUES (?, ?, ?, ?)",
        invoice_rows,
    )

    comp_rows = [
        ("MED001", "ConcorrenteA", 11.50, today.isoformat()),
        ("MED002", "ConcorrenteB", 16.90, today.isoformat()),
        ("SUP001", "ConcorrenteC", 34.90, today.isoformat()),
    ]
    conn.executemany(
        "INSERT INTO competitor_prices (sku, competitor, price, collected_at) VALUES (?, ?, ?, ?)",
        comp_rows,
    )

    order_rows = [
        ("enviado", (today - timedelta(days=1)).isoformat(), "Carlos Silva", 120.0),
        ("processando", today.isoformat(), "Ana Souza", 85.0),
        ("pendente", (today - timedelta(days=2)).isoformat(), "Marcos Lima", 55.0),
        ("entregue", (today - timedelta(days=5)).isoformat(), "Paula Reis", 200.0),
        ("processando", (today - timedelta(days=3)).isoformat(), "Lucas Prado", 30.0),
    ]
    conn.executemany(
        "INSERT INTO orders (status, created_at, customer, total) VALUES (?, ?, ?, ?)",
        order_rows,
    )

    order_item_rows = [
        (1, 1, 2),
        (1, 3, 1),
        (2, 2, 1),
        (3, 4, 1),
        (4, 5, 1),
        (5, 6, 1),
    ]
    conn.executemany(
        "INSERT INTO order_items (order_id, product_id, qty) VALUES (?, ?, ?)",
        order_item_rows,
    )

    # Demo users
    users_rows = [
        ("gestor", "gestor@farmacia.com", _hash_password("farmacia123"), "gestor", 1, "Gestor Principal"),
        ("funcionario", "func@farmacia.com", _hash_password("farmacia456"), "funcionario", 1, "Funcionario Demo"),
    ]
    conn.executemany(
        "INSERT INTO users (username, email, password_hash, role, is_active, nome_completo) VALUES (?, ?, ?, ?, ?, ?)",
        users_rows,
    )

    # Demo customer orders
    customer_order_rows = [
        ("sessao_demo_1", "Maria Silva", "21999001111",
         '[{"sku":"MED001","nome":"Dipirona 500mg","preco":12.90,"quantidade":2}]',
         "retirada", "", 0.0, "confirmado", 25.80, "", (today - timedelta(days=2)).isoformat()),
        ("sessao_demo_2", "João Santos", "21988002222",
         '[{"sku":"HIG001","nome":"Alcool Gel 70%","preco":9.90,"quantidade":1}]',
         "entrega", "Rua das Flores, 100 - Barra", 5.0, "em_preparo", 14.90, "", (today - timedelta(days=1)).isoformat()),
        ("sessao_demo_3", "Ana Oliveira", "21977003333",
         '[{"sku":"SUP001","nome":"Vitamina C 1g","preco":39.90,"quantidade":1},{"sku":"MED002","nome":"Paracetamol 750mg","preco":18.50,"quantidade":2}]',
         "entrega", "Av. das Americas, 500 - Recreio", 8.0, "pendente", 76.90, "", today.isoformat()),
    ]
    conn.executemany(
        """INSERT INTO customer_orders
           (session_id, customer_name, customer_phone, items_json, delivery_type,
            delivery_address, taxa_entrega, status, total, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        customer_order_rows,
    )

    # Delivery settings defaults
    conn.executemany(
        "INSERT INTO delivery_settings (key, value) VALUES (?, ?)",
        [("avg_speed_kmh", "30"), ("stopped_alert_min", "5")],
    )

    # Demo customers
    demo_customers = [
        ("Maria Silva", "maria@email.com", "21999001111",
         _hash_password("senha123"),
         "Rua das Flores", "100", "Apto 201", "Barra da Tijuca", "Rio de Janeiro"),
        ("João Santos", "joao@email.com", "21988002222",
         _hash_password("senha123"),
         "Av. das Américas", "500", "Casa", "Recreio", "Rio de Janeiro"),
    ]
    conn.executemany(
        """INSERT INTO customers (nome, email, telefone, senha_hash,
           endereco_rua, endereco_numero, endereco_complemento, endereco_bairro, endereco_cidade)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        demo_customers,
    )


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        reset_schema(conn)
        seed_data(conn)
        conn.commit()
        print(f"Banco demo criado em {DB_PATH}")
        print("Usuarios demo criados:")
        print("  gestor / farmacia123  (role: gestor)")
        print("  funcionario / farmacia456  (role: funcionario)")
        print("Clientes demo criados:")
        print("  maria@email.com / senha123")
        print("  joao@email.com / senha123")
    finally:
        conn.close()
