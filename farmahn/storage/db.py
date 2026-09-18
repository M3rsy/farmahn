from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import os
import sqlite3

from farmahn.core.models import Product
from farmahn.core.normalize import canonical_product_key, normalize_text


def default_db_path() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "farmahn" / "farmahn.db"


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init_schema(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    provider_slug TEXT NOT NULL,
                    query_norm TEXT NOT NULL,
                    city_norm TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_slug TEXT NOT NULL,
                    pharmacy TEXT NOT NULL,
                    canonical_key TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    concentration TEXT,
                    presentation TEXT,
                    quantity INTEGER,
                    price REAL NOT NULL,
                    regular_price REAL,
                    available INTEGER,
                    url TEXT NOT NULL,
                    city TEXT,
                    observed_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_history_key_time
                    ON price_history(canonical_key, observed_at DESC);

                CREATE INDEX IF NOT EXISTS idx_history_provider_time
                    ON price_history(provider_slug, observed_at DESC);
                """
            )

    @staticmethod
    def _cache_key(provider_slug: str, query: str, city: str | None) -> str:
        raw = "|".join((provider_slug, normalize_text(query), normalize_text(city or "")))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_cached_search(self, provider_slug: str, query: str, city: str | None) -> list[Product] | None:
        key = self._cache_key(provider_slug, query, city)
        now = datetime.now(timezone.utc)
        with self.connect() as con:
            row = con.execute(
                "SELECT payload, expires_at FROM search_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()

            if row is None:
                return None

            if datetime.fromisoformat(row["expires_at"]) <= now:
                con.execute("DELETE FROM search_cache WHERE cache_key = ?", (key,))
                return None

            payload = json.loads(row["payload"])
            return [Product.model_validate(item) for item in payload]

    def set_cached_search(
        self,
        provider_slug: str,
        query: str,
        city: str | None,
        products: list[Product],
        ttl_minutes: int = 10,
    ) -> None:
        key = self._cache_key(provider_slug, query, city)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=max(1, ttl_minutes))
        payload = json.dumps([p.model_dump(mode="json") for p in products], ensure_ascii=False)
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO search_cache
                    (cache_key, provider_slug, query_norm, city_norm, payload, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload=excluded.payload,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at
                """,
                (
                    key,
                    provider_slug,
                    normalize_text(query),
                    normalize_text(city or ""),
                    payload,
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )

    def record_prices(self, provider_slug: str, products: list[Product], city: str | None = None) -> None:
        if not products:
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for product in products:
            rows.append(
                (
                    provider_slug,
                    product.pharmacy,
                    product.canonical_key or canonical_product_key(product.name),
                    product.name,
                    product.concentration,
                    product.presentation,
                    product.quantity,
                    product.price,
                    product.regular_price,
                    None if product.available is None else int(product.available),
                    product.url,
                    city or product.city,
                    now,
                )
            )
        with self.connect() as con:
            con.executemany(
                """
                INSERT INTO price_history (
                    provider_slug, pharmacy, canonical_key, product_name,
                    concentration, presentation, quantity, price, regular_price,
                    available, url, city, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def history(self, query: str, limit: int = 30) -> list[dict]:
        query_norm = normalize_text(query)
        tokens = [token for token in query_norm.split() if len(token) > 1]
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT pharmacy, product_name, concentration, presentation, quantity,
                       price, regular_price, available, url, city, observed_at
                FROM price_history
                ORDER BY observed_at DESC
                LIMIT 1000
                """
            ).fetchall()

        matches = []
        for row in rows:
            haystack = normalize_text(f"{row['product_name']} {row['concentration'] or ''}")
            if not tokens or all(token in haystack for token in tokens):
                item = dict(row)
                if item["available"] is not None:
                    item["available"] = bool(item["available"])
                matches.append(item)
                if len(matches) >= limit:
                    break
        return matches

    def clear_cache(self) -> int:
        with self.connect() as con:
            count = con.execute("SELECT COUNT(*) AS n FROM search_cache").fetchone()["n"]
            con.execute("DELETE FROM search_cache")
        return int(count)

    def stats(self) -> dict:
        with self.connect() as con:
            cache = con.execute("SELECT COUNT(*) AS n FROM search_cache").fetchone()["n"]
            history = con.execute("SELECT COUNT(*) AS n FROM price_history").fetchone()["n"]
        return {"cache_entries": int(cache), "history_entries": int(history), "path": str(self.path)}


default_database = Database()
