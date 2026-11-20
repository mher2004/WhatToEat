# WhatToEat (Ի՞նչ եփել այսօր) 🍲🛒

A budget-aware daily meal planner and grocery cost optimizer built on live supermarket prices in Yerevan, Armenia (AMD). 

**WhatToEat** scrapes real product catalogs, normalizes noisy Armenian/Russian/English product names into canonical ingredients, computes both proportional *eaten* meal costs and real *checkout* whole-pack grocery bills, and provides an interactive **Armenian Telegram bot** alongside a CLI planner.

---

## ✨ Features

- **Live Supermarket Price Ingestion:** Scrapes Yerevan City product categories with rate-limiting, resume support, and append-only SQLite price history (storing rows only when prices change).
- **Multilingual Ingredient Matching:** Maps raw supermarket product names (`«brands»`, weights, pack sizes) to canonical ingredients using word-anchored regex rules across Armenian, Russian, and Latin scripts.
- **Outlier & Size QA:** Filters unreliable package weights and price outliers (`p25` and `median` per-unit pricing in AMD/kg, AMD/L, or AMD/piece).
- **Eaten Cost vs. Real Checkout Cost:** Distinguishes between the proportional cost of ingredients actually consumed in a recipe and the real supermarket bill rounded up to whole packs (or 100 g steps for loose produce), tracking leftover ingredient value.
- **Smart Menu Optimization:** Generates varied daily menus (Breakfast, Lunch, Dinner) within a target daily AMD budget while avoiding repetitive staple ingredients.
- **Armenian Telegram Bot (`bot.py`):** Simple button-driven interface in Armenian for selecting household size, meal combinations, and daily budget—returning menu options, step-by-step Armenian recipes, and itemized shopping lists.

---

## 🗂 Project Structure

```text
WhatToEat/
├── scraper.py        # Fetches raw category JSONs from Yerevan City API
├── check.py          # Read-only sanity checks for scraped weights & unit prices
├── sizes.py          # Parses product weights/volumes/pieces and unit prices
├── db.py             # SQLite schema & incremental price loader (whattoeat.db)
├── ingredients.py    # Canonical ingredient dictionary (EN/HY) & regex matching rules
├── match.py          # Maps products_raw -> ingredients and computes p25/median prices
├── recipes_data.py   # Recipe catalog with Armenian titles, ingredients, and steps
├── recipes.py        # Loads recipes into SQLite
├── cost.py           # Calculates proportional (eaten) recipe costs
├── shop.py           # Optimizes whole-pack supermarket shopping lists
├── plan.py           # CLI meal planner & menu scorer
└── bot.py            # Interactive Armenian Telegram bot
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- SQLite3

Install dependencies:
```bash
pip install httpx "python-telegram-bot>=20.0"
```

### 2. Scrape & Build the Database
```bash
# 1. Scrape core food categories from Yerevan City
python3 scraper.py

# 2. Run sanity checks on the raw scrape (optional)
python3 check.py

# 3. Load products and price deltas into whattoeat.db
python3 db.py

# 4. Match products to canonical ingredients & compute unit prices
python3 match.py

# 5. Load recipes into the database
python3 recipes.py
```

### 3. Run the CLI Meal Planner
```bash
# Plan breakfast, lunch, and dinner for 2 people within 2,500 AMD/day
python3 plan.py --people 2 --meals breakfast,lunch,dinner --budget 2500 --steps

# Enforce that the real whole-pack checkout bill fits the budget
python3 plan.py --people 4 --meals lunch,dinner --budget 4000 --real
```

### 4. Run the Armenian Telegram Bot
Create a bot via [@BotFather](https://t.me/BotFather), set your token, and start the bot:
```bash
export BOT_TOKEN="your_telegram_bot_token"
python3 bot.py
```

---

## 🛠 Extending the Project

- **Adding Recipes:** Edit `recipes_data.py` using existing ingredient IDs from `ingredients.py`, then run `python3 recipes.py`.
- **Tuning Ingredient Matching:** Run `python3 match.py --unmapped` to inspect frequent unmatched words or `--samples` to audit matched products, update regex rules in `ingredients.py`, and re-run `python3 match.py`.
- **Adding More Supermarkets:** `db.py` already supports multiple stores (`yerevan_city`, `sas`); adding a new scraper will automatically let `shop.py` compare and pick the cheapest packs across stores.