"""Yerevan City scraper: fetches all products of the chosen categories, saves raw JSON.

Usage:
    python3 scraper.py                       # core food categories
    python3 scraper.py --optional            # core + optional (sweets, ready food, drinks...)
    python3 scraper.py --only 1923           # just these category ids (comma separated)
    python3 scraper.py --resume raw/yerevan_city/20261121_1530   # continue a stopped run
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

URL = "https://apishopv2.yerevan-city.am/api/Product/GetByLastCategory"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (research project)",
    "Content-Type": "application/json",
    "Origin": "https://yerevan-city.am",
    "Referer": "https://yerevan-city.am/",
}

PAGE_SIZE = 30
DELAY_SECONDS = 1.5

# Top-level category ids from GetParentCategories (names as the site returns them).
# Asking for a parent id returns all products under it.
CORE = {
    1923: "Пекарня",
    22: "Молочные продукты, мороженое и лед",
    6: "Колбаса и деликатесы",
    1927: "Мясо",
    7: "Мясо птицы и яйца",
    29: "Полуфабрикаты",
    27: "Рыба и морепродукты",
    1928: "Рыба живая и свежая",
    1926: "Свежие овощи и фрукты",
    25: "Консервы",
    26: "Бакалея",
}
OPTIONAL = {
    2: "Сладости",
    40: "Диетическое, здоровое и детское питание",
    1924: "Готовая еда",
    38: "Горячие напитки",
    33: "Снэки, семена, кукуруза, сладкая вата",
    39: "Безалкогольные напитки",
}


def make_body(category_id, page, count=PAGE_SIZE):
    # The site itself sends null for priceFrom/priceTo, so no price filtering.
    return {
        "categoryId": category_id,
        "count": count,
        "page": page,
        "priceFrom": None,
        "priceTo": None,
        "countries": [],
        "tags": [],
        "categories": [],
        "brands": [],
        "search": None,
        "parentId": category_id,
        "isDiscounted": False,
        "sortBy": 0,
    }


def post_with_retry(client, body, attempts=4):
    for n in range(1, attempts + 1):
        try:
            r = client.post(URL, json=body, timeout=30)
            r.raise_for_status()
            return r
        except httpx.HTTPError as e:
            if n == attempts:
                raise
            wait = 5 * n
            print(f"  retry {n}/{attempts - 1} after {e!r}; waiting {wait}s")
            time.sleep(wait)


def scrape_category(client, category_id, raw_dir):
    """Fetch every page of a category. Pages already on disk are reused (resume)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    page, page_count = 1, 1
    item_count = saved = 0
    while page <= page_count:
        path = raw_dir / f"cat{category_id}_p{page}.json"
        fetched = not path.exists()
        if fetched:
            payload = post_with_retry(client, make_body(category_id, page)).json()
            # Save the raw response BEFORE parsing anything.
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
        data = payload["data"]
        page_count = data["pageCount"]
        item_count = data["itemCount"]
        saved += len(data["list"])
        note = "" if fetched else " (already saved)"
        print(f"  page {page}/{page_count}: {len(data['list'])} items{note}")
        page += 1
        if fetched:
            time.sleep(DELAY_SECONDS)  # be gentle with the server
    return item_count, saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated category ids")
    ap.add_argument("--optional", action="store_true", help="also scrape OPTIONAL categories")
    ap.add_argument("--resume", help="existing raw run folder to continue")
    args = ap.parse_args()

    names = {**CORE, **OPTIONAL}
    if args.only:
        ids = [int(x) for x in args.only.split(",")]
    else:
        ids = list(CORE) + (list(OPTIONAL) if args.optional else [])

    if args.resume:
        raw_dir = Path(args.resume)
        if not raw_dir.is_dir():
            sys.exit(f"Resume folder not found: {raw_dir}")
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        raw_dir = Path("raw") / "yerevan_city" / stamp
    print("raw folder:", raw_dir)

    results = []
    with httpx.Client(headers=HEADERS) as client:
        for cid in ids:
            print(f"category {cid}: {names.get(cid, '?')}")
            count, saved = scrape_category(client, cid, raw_dir)
            if count != saved:
                print(f"  WARNING: site says {count} items, saved {saved}")
            results.append({"id": cid, "name": names.get(cid, "?"),
                            "itemCount": count, "saved": saved})

    print("\nSummary:")
    for r in results:
        print(f"  {r['id']:>5}  {r['saved']:>6} / {r['itemCount']:<6}  {r['name']}")
    print("  total items saved:", sum(r["saved"] for r in results))
    (raw_dir / "summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
