"""Most frequent product-name words per category. Used to build the ingredient dictionary
from the real data instead of guessing.

Run after db.py:    python3 words.py     -> writes words_report.txt
"""
import re
import sqlite3
from collections import Counter, defaultdict

from scraper import CORE, OPTIONAL

TOP = 60        # words per category
STEM_LEN = 5    # group inflections: լոլիկ / լոլիկի / լոլիկներ -> one stem

NOT_LETTER = r"(?![а-яёա-ֆa-z])"
SIZE = re.compile(
    rf"\d+(?:[.,]\d+)?\s*(?:%|(?:կգ|գր|գ|մլ|լ|հտ|кг|гр|г|мл|л|шт){NOT_LETTER})?", re.IGNORECASE)
WORD = re.compile(r"[а-яёա-ֆa-z]{3,}")

con = sqlite3.connect("whattoeat.db")
rows = con.execute("SELECT category_id, name FROM products_raw").fetchall()
names = {str(k): v for k, v in {**CORE, **OPTIONAL}.items()}
product_counts = Counter(cat for cat, _ in rows)


def words(name):
    name = re.sub(r"«[^»]*»", " ", name)  # drop brands
    name = SIZE.sub(" ", name)
    return WORD.findall(name.lower())


by_cat = defaultdict(lambda: defaultdict(Counter))  # category -> stem -> full-word counts
for cat, name in rows:
    for w in words(name):
        by_cat[cat][w[:STEM_LEN]][w] += 1

with open("words_report.txt", "w", encoding="utf-8") as f:
    for cat, stems in by_cat.items():
        f.write(f"\n=== {cat} {names.get(cat, '?')} ({product_counts[cat]} products)\n")
        ranked = sorted(stems.values(), key=lambda c: -sum(c.values()))[:TOP]
        f.write(", ".join(f"{c.most_common(1)[0][0]}:{sum(c.values())}" for c in ranked) + "\n")
print("wrote words_report.txt")
