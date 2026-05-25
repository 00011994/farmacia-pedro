import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

from src.core.db import get_conn


@dataclass
class ProdutoEstoque:
    sku: str
    nome: str
    estoque: int
    reservado: int


@dataclass
class PedidoStatus:
    pedido_id: int
    status: str
    cliente: str


@dataclass
class EstoqueParado:
    sku: str
    nome: str
    ultima_venda: str
    dias_sem_venda: int


@dataclass
class Recompra:
    sku: str
    nome: str
    quantidade_recompra: int


@dataclass
class AlertaBonus:
    sku: str
    nome: str
    markup_pct: float


@dataclass
class ProdutoInfo:
    sku: str
    nome: str
    categoria: str
    preco: float
    estoque: int
    reservado: int


def _normalize(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = unicodedata.normalize("NFD", cleaned)
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _tokenize(text: str) -> List[str]:
    stopwords = {
        "tem",
        "tenho",
        "quero",
        "queria",
        "preciso",
        "um",
        "uma",
        "do",
        "da",
        "de",
        "para",
        "por",
        "favor",
        "separa",
        "separe",
        "manda",
        "me",
        "porfavor",
    }
    tokens = [t for t in _normalize(text).split() if t and t not in stopwords]
    return tokens


class DataGateway:
    def low_stock(self, threshold: int) -> List[ProdutoEstoque]:
        raise NotImplementedError

    def stock_by_sku(self, sku: str) -> Optional[ProdutoEstoque]:
        raise NotImplementedError

    def recent_orders(self, limit: int) -> List[PedidoStatus]:
        raise NotImplementedError

    def order_status(self, order_id: int) -> Optional[PedidoStatus]:
        raise NotImplementedError

    def dead_stock(self, days_no_sales: int) -> List[EstoqueParado]:
        raise NotImplementedError

    def reorder_suggestions(self, safety_days: int) -> List[Recompra]:
        raise NotImplementedError

    def bonus_alerts(self, bonus_markup_pct: float) -> List[AlertaBonus]:
        raise NotImplementedError

    def search_products(self, query: str, limit: int = 5) -> List[ProdutoInfo]:
        raise NotImplementedError

    def get_product(self, sku: str) -> Optional[ProdutoInfo]:
        raise NotImplementedError

    def suggest_alternatives(self, categoria: str, exclude_sku: str, limit: int = 2) -> List[ProdutoInfo]:
        raise NotImplementedError


class SqliteGateway(DataGateway):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def low_stock(self, threshold: int) -> List[ProdutoEstoque]:
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT sku, name, stock
                FROM products
                WHERE stock < ?
                ORDER BY stock ASC
                """,
                (threshold,),
            ).fetchall()
        return [
            ProdutoEstoque(sku=row["sku"], nome=row["name"], estoque=row["stock"], reservado=0)
            for row in rows
        ]

    def stock_by_sku(self, sku: str) -> Optional[ProdutoEstoque]:
        with get_conn(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT sku, name, stock
                FROM products
                WHERE sku = ?
                """,
                (sku,),
            ).fetchone()
        if not row:
            return None
        return ProdutoEstoque(sku=row["sku"], nome=row["name"], estoque=row["stock"], reservado=0)

    def recent_orders(self, limit: int) -> List[PedidoStatus]:
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id AS order_id, status, customer
                FROM orders
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            PedidoStatus(pedido_id=row["order_id"], status=row["status"], cliente=row["customer"])
            for row in rows
        ]

    def order_status(self, order_id: int) -> Optional[PedidoStatus]:
        with get_conn(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id AS order_id, status, customer
                FROM orders
                WHERE id = ?
                """,
                (order_id,),
            ).fetchone()
        if not row:
            return None
        return PedidoStatus(pedido_id=row["order_id"], status=row["status"], cliente=row["customer"])

    def dead_stock(self, days_no_sales: int) -> List[EstoqueParado]:
        from datetime import datetime, timezone

        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.sku, p.name, MAX(s.sale_date) AS last_sale
                FROM products p
                LEFT JOIN sales s ON s.product_id = p.id
                GROUP BY p.id
                """
            ).fetchall()

        today = datetime.now(timezone.utc).date()
        items: List[EstoqueParado] = []
        for row in rows:
            last_sale = row["last_sale"]
            if last_sale is None:
                days = days_no_sales + 1
                last_sale_str = "nunca"
            else:
                last_date = datetime.strptime(last_sale, "%Y-%m-%d").date()
                days = (today - last_date).days
                last_sale_str = last_sale
            if days > days_no_sales:
                items.append(
                    EstoqueParado(
                        sku=row["sku"],
                        nome=row["name"],
                        ultima_venda=last_sale_str,
                        dias_sem_venda=days,
                    )
                )
        return items

    def reorder_suggestions(self, safety_days: int) -> List[Recompra]:
        from datetime import datetime, timedelta, timezone

        since = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT p.id, p.sku, p.name, p.stock, COALESCE(SUM(s.qty), 0) AS qty
                FROM products p
                LEFT JOIN sales s ON s.product_id = p.id AND s.sale_date >= ?
                GROUP BY p.id
                """,
                (since,),
            ).fetchall()
        items: List[Recompra] = []
        for row in rows:
            avg_daily = row["qty"] / 30.0
            target_stock = avg_daily * safety_days
            if target_stock > row["stock"] + 1:
                qty = int(round(target_stock - row["stock"], 0))
                items.append(
                    Recompra(
                        sku=row["sku"],
                        nome=row["name"],
                        quantidade_recompra=max(qty, 1),
                    )
                )
        return items

    def bonus_alerts(self, bonus_markup_pct: float) -> List[AlertaBonus]:
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT sku, name, price, avg_cost
                FROM products
                WHERE avg_cost > 0
                """
            ).fetchall()
        items: List[AlertaBonus] = []
        for row in rows:
            markup = ((row["price"] - row["avg_cost"]) / row["avg_cost"]) * 100
            if markup > bonus_markup_pct:
                items.append(
                    AlertaBonus(sku=row["sku"], nome=row["name"], markup_pct=round(markup, 1))
                )
        return items

    def search_products(self, query: str, limit: int = 5) -> List[ProdutoInfo]:
        sku_match = re.search(r"\b([A-Z]{2,5}\d{2,4})\b", query.upper())
        if sku_match:
            produto = self.get_product(sku_match.group(1))
            return [produto] if produto else []

        tokens = _tokenize(query)
        if not tokens:
            return []
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT sku, name, category, price, stock
                FROM products
                """
            ).fetchall()
        matches: List[ProdutoInfo] = []
        for row in rows:
            name_norm = _normalize(row["name"])
            if all(token in name_norm for token in tokens):
                matches.append(
                    ProdutoInfo(
                        sku=row["sku"],
                        nome=row["name"],
                        categoria=row["category"],
                        preco=float(row["price"]),
                        estoque=int(row["stock"]),
                        reservado=0,
                    )
                )
        return matches[:limit]

    def get_product(self, sku: str) -> Optional[ProdutoInfo]:
        with get_conn(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT sku, name, category, price, stock
                FROM products
                WHERE sku = ?
                """,
                (sku,),
            ).fetchone()
        if not row:
            return None
        return ProdutoInfo(
            sku=row["sku"],
            nome=row["name"],
            categoria=row["category"],
            preco=float(row["price"]),
            estoque=int(row["stock"]),
            reservado=0,
        )

    def suggest_alternatives(self, categoria: str, exclude_sku: str, limit: int = 2) -> List[ProdutoInfo]:
        with get_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT sku, name, category, price, stock
                FROM products
                WHERE category = ? AND sku != ?
                ORDER BY stock DESC
                LIMIT ?
                """,
                (categoria, exclude_sku, limit),
            ).fetchall()
        return [
            ProdutoInfo(
                sku=row["sku"],
                nome=row["name"],
                categoria=row["category"],
                preco=float(row["price"]),
                estoque=int(row["stock"]),
                reservado=0,
            )
            for row in rows
        ]


class MySqlGateway(DataGateway):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _not_ready(self):
        raise RuntimeError(
            "MySqlGateway nao implementado. Crie um adapter usando mysql-connector ou pymysql."
        )

    def low_stock(self, threshold: int):
        self._not_ready()

    def stock_by_sku(self, sku: str):
        self._not_ready()

    def recent_orders(self, limit: int):
        self._not_ready()

    def order_status(self, order_id: int):
        self._not_ready()

    def dead_stock(self, days_no_sales: int):
        self._not_ready()

    def reorder_suggestions(self, safety_days: int):
        self._not_ready()

    def bonus_alerts(self, bonus_markup_pct: float):
        self._not_ready()

    def search_products(self, query: str, limit: int = 5):
        self._not_ready()

    def get_product(self, sku: str):
        self._not_ready()

    def suggest_alternatives(self, categoria: str, exclude_sku: str, limit: int = 2):
        self._not_ready()
