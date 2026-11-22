# WhatToEat (Ի՞նչ եփել այսօր) 🍲🛒

A budget-aware daily meal planner and grocery cost optimizer built on supermarket prices in Yerevan, Armenia (AMD).

**WhatToEat** scrapes the Yerevan City product catalog, normalizes noisy Armenian/Russian product names into canonical ingredients, computes both the proportional *eaten* cost of a meal and the real *checkout* cost (whole packs), and serves it through an **Armenian CLI planner** and an **Armenian Telegram bot**.

---

## ✨ Features

- **Price ingestion:** scrapes Yerevan City with rate limiting and resume support; the SQLite history stores a new price row only when a price changes. Discounts are used as the real price.
- **Ingredient matching:** maps product names (`«brands»`, pack sizes) to ~120 canonical ingredients with word-anchored regex rules (Armenian / Russian / Latin).
- **Size and outlier QA:** untrusted pack sizes and absurd unit prices are dropped (`p25` and `median` price per kg / litre / piece).
- **Eaten cost vs. real shop bill:** proportional cost of what is eaten, versus the whole-pack bill (loose items in 100 g steps), with leftover value shown.
- **Menu planner:** best varied menus for breakfast / lunch / dinner within a daily budget, 1 or many days.
- **Armenian by default:** all CLI and bot texts, ingredient names, recipe names and cooking steps (`--lang en` for English).
- **Telegram bot:** buttons for people, meals and budget, then 3 menu options, recipes and a shopping list.

> Prices are **not** checked live. Everything uses the last scrape stored in `whattoeat.db`. Run `./update.sh` to refresh (see below).

---

## 🗂 Project structure

```text
WhatToEat/
├── update.sh         # refresh all data (scrape -> db -> match -> recipes)
├── run_bot.sh        # start the Telegram bot
├── scraper.py        # fetches raw category JSON from the Yerevan City API -> raw/
├── check.py          # read-only sanity checks of the latest raw scrape
├── sizes.py          # parses pack sizes (g / ml / pcs) and unit prices (python3 sizes.py = tests)
├── db.py             # SQLite schema + incremental price loader (whattoeat.db)
├── words.py          # word-frequency report used to build the ingredient dictionary
├── ingredients.py    # canonical ingredients + regex matching rules
├── match.py          # products -> ingredients, ingredient price stats (p25 / median)
├── names_hy.py       # Armenian ingredient names
├── recipes_data.py   # recipes (English): ingredients, quantities, steps
├── recipes_hy.py     # recipes (Armenian): names and steps
├── recipes.py        # loads recipes into the DB
├── cost.py           # eaten cost of recipes
├── shop.py           # pack-aware shopping lists
├── i18n.py           # interface texts (hy / en) and meal-name parsing
├── plan.py           # CLI planner
└── bot.py            # Telegram bot
```

---

## 🚀 Setup (once)

Requirements: Python 3.10+.

```bash
pip install httpx "python-telegram-bot>=20.0"
chmod +x update.sh run_bot.sh
./update.sh          # builds whattoeat.db (first run takes a few minutes)
```

## 🔄 Updating the data

```bash
./update.sh                 # full update: scrape + db + match + recipes
./update.sh --skip-scrape   # rebuild from the latest saved scrape, no website access
./update.sh --check         # also run check.py sanity checks
```

It runs, in order: `scraper.py` -> `db.py` -> `match.py` -> `recipes.py`, stops on the first error, and appends output to `logs/update.log`.
Run it daily to keep prices fresh. Example cron entry (every day at 06:00):

```cron
0 6 * * * cd /path/to/WhatToEat && ./update.sh >/dev/null 2>&1
```

Run `./update.sh` again whenever you edit `ingredients.py`, `recipes_data.py`, `recipes_hy.py` or `names_hy.py`
(use `--skip-scrape` to avoid re-downloading).

## 🤖 Running the Telegram bot

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Give the token to the script, either way:
   ```bash
   export BOT_TOKEN="123456:ABC..."
   ./run_bot.sh
   ```
   or create a file `.env` in the project folder with one line `BOT_TOKEN=123456:ABC...` and run `./run_bot.sh`.
3. Open your bot in Telegram and send `/start`.

```bash
./run_bot.sh --forever      # restart automatically if it crashes
```

Keep `.env` private (do not commit it; add it to `.gitignore`). The bot reads `whattoeat.db` on every request, so after `./update.sh` it uses new prices without a restart.

## 🍽 Running the CLI planner

```bash
# 2 people, 3 meals, 2500 AMD per day (Armenian output)
python3 plan.py --people 2 --meals նախաճաշ,ճաշ,ընթրիք --budget 2500

# English meal names and interface
python3 plan.py --people 2 --meals breakfast,lunch,dinner --budget 2500 --lang en

# show option 2 with cooking steps and its real shopping list; the shop bill must fit the budget
python3 plan.py --people 2 --budget 2500 --pick 2 --steps --real

# 3-day plan, bought together
python3 plan.py --people 4 --meals ճաշ,ընթրիք --budget 4000 --days 3 --steps

# every dinner that fits 900 AMD
python3 plan.py --people 2 --meals ընթրիք --budget 900 --all
```

| Flag | Meaning |
|---|---|
| `--people N` | number of people (required) |
| `--meals` | `նախաճաշ,ճաշ,ընթրիք` (also Russian or English names), default all three |
| `--budget N` | per day, whole group, in AMD (required) |
| `--days N` | plan several days without repeating dishes |
| `--top N` | number of options shown (default 3) |
| `--pick N` | option whose steps and shopping list are printed |
| `--real` | the real shop bill (whole packs) must fit the budget (single day) |
| `--pantry a,b` | ingredient ids already at home (default salt, black_pepper, sunflower_oil; `none`) |
| `--prices p25\|median` | which ingredient price to use |
| `--steps` | print cooking instructions |
| `--all` | list every recipe that fits each meal's share |
| `--sides` | allow side dishes as a main |
| `--lang hy\|en` | interface language (default hy) |

"Eaten" cost is the normal price of the food used; "shop" is what you pay for whole packs. The difference is leftover you can use later.

---

## 🛠 Extending the project

- **Recipes:** add to `recipes_data.py` (English) and `recipes_hy.py` (Armenian, same number of steps), using ingredient ids from `ingredients.py`; then `./update.sh --skip-scrape`. A step-count mismatch prints a WARNING and that recipe falls back to English steps.
- **Matching quality:** `python3 match.py --unmapped` writes `unmapped_report.txt`; `python3 match.py --samples` writes `match_samples.txt` to eyeball matches. Edit rules in `ingredients.py` and re-run `python3 match.py && python3 recipes.py`.
- **New ingredient:** add it to `ingredients.py` and its Armenian name to `names_hy.py`.
- **Another supermarket:** `db.py` already supports several stores; add a scraper and `shop.py` can compare packs.

## ⚠️ Known limits

- No live price check, no stock information, one store (Yerevan City).
- The planner leans cheap and has no nutrition data yet.
- Loose items are rounded up to 100 g; fresh vegetables have few price points, so their cost can drift.
- Herbs and spices are not in recipes (sold per bunch / pack without a per-kg price).
