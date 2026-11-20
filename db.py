"""SQLite schema and loader. Reads the latest raw folder and fills the tables.

Usage:
    python3 db.py     # run twice: the second run should add 0 new price rows
"""
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from sizes import unit_prices

SCHEMA = """
CREATE TABLE IF NOT EXISTS stores (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products_raw (
  id INTEGER PRIMARY KEY,
  store_id INTEGER NOT NULL REFERENCES stores(id),
  external_id TEXT NOT NULL,
  name TEXT NOT NULL,
  category_id TEXT,
  photo_url TEXT,
  pack_grams REAL,
  pack_ml REAL,
  pack_pieces REAL,
  size_source TEXT,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  UNIQUE (store_id, external_id)
);

CREATE TABLE IF NOT EXISTS prices (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products_raw(id),
  regular_price REAL NOT NULL,
  discounted_price REAL,
  effective_price REAL NOT NULL,
  price_per_kg REAL,
  price_per_l REAL,
  price_per_piece REAL,
  scraped_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_product ON prices(product_id, scraped_at);
"""


def init_db(path="whattoeat.db"):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.execute("INSERT OR IGNORE INTO stores(name) VALUES ('yerevan_city'), ('sas')")
    con.commit()
    return con


def load_items(con, store_name, items, category_id, scraped_at):
    """Upsert products and insert a price row only when the price changed."""
    store_id = con.execute("SELECT id FROM stores WHERE name=?", (store_name,)).fetchone()[0]
    new_prices = 0
    for it in items:
        u = unit_prices(it)
        con.execute(
            """
            INSERT INTO products_raw (store_id, external_id, name, category_id, photo_url,
                pack_grams, pack_ml, pack_pieces, size_source, first_seen, last_seen, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(store_id, external_id) DO UPDATE SET
                name=excluded.name, category_id=excluded.category_id, photo_url=excluded.photo_url,
                pack_grams=excluded.pack_grams, pack_ml=excluded.pack_ml,
                pack_pieces=excluded.pack_pieces, size_source=excluded.size_source,
                last_seen=excluded.last_seen, raw_json=excluded.raw_json
            """,
            (store_id, str(it["id"]), it["name"], str(category_id), it.get("photo"),
             u["grams"], u["ml"], u["pieces"], u["source"],
             scraped_at, scraped_at, json.dumps(it, ensure_ascii=False)),
        )
        pid = con.execute(
            "SELECT id FROM products_raw WHERE store_id=? AND external_id=?",
            (store_id, str(it["id"])),
        ).fetchone()[0]

        disc = it.get("discountedPrice") or 0
        discounted = round(disc) if disc > 0 else None
        last = con.execute(
            """SELECT regular_price, discounted_price FROM prices
               WHERE product_id=? ORDER BY scraped_at DESC, id DESC LIMIT 1""",
            (pid,),
        ).fetchone()
        if last != (it["price"], discounted):  # only store changes
            con.execute(
                """INSERT INTO prices (product_id, regular_price, discounted_price,
                   effective_price, price_per_kg, price_per_l, price_per_piece, scraped_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (pid, it["price"], discounted, u["effective_price"],
                 u["price_per_kg"], u["price_per_l"], u["price_per_piece"], scraped_at),
            )
            new_prices += 1
    con.commit()
    return new_prices


if __name__ == "__main__":
    con = init_db()
    folder = sorted(Path("raw/yerevan_city").iterdir())[-1]
    scraped_at = datetime.strptime(folder.name, "%Y%m%d_%H%M").isoformat()

    by_cat = {}
    for f in sorted(folder.glob("cat*_p*.json")):
        cat = re.match(r"cat(\d+)_p", f.name).group(1)
        by_cat.setdefault(cat, []).extend(
            json.loads(f.read_text(encoding="utf-8"))["data"]["list"]
        )

    for cat, items in by_cat.items():
        n = load_items(con, "yerevan_city", items, cat, scraped_at)
        print(f"category {cat}: {len(items)} items, {n} new price rows")
