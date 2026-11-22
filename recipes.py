"""Recipe tables + loader.   python3 recipes.py   (re-runnable: it replaces the recipe tables)"""
import json
import sqlite3

from recipes_data import RECIPES
from recipes_hy import RECIPES_HY

SCHEMA = """
DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS recipes;
CREATE TABLE recipes (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, name_hy TEXT,
  meals TEXT NOT NULL,            -- JSON list: breakfast / lunch / dinner
  servings INTEGER NOT NULL, minutes INTEGER, difficulty INTEGER,
  tags TEXT NOT NULL,             -- JSON list
  steps TEXT NOT NULL,            -- JSON list of instruction strings (English)
  steps_hy TEXT                   -- same, Armenian
);
CREATE TABLE recipe_ingredients (
  recipe_id TEXT NOT NULL REFERENCES recipes(id),
  ingredient_id TEXT NOT NULL REFERENCES ingredients(id),
  quantity REAL NOT NULL, unit TEXT NOT NULL CHECK (unit IN ('g','ml','pc')),
  is_staple INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (recipe_id, ingredient_id)
);
"""


def load(db="whattoeat.db"):
    con = sqlite3.connect(db)
    known = {r[0] for r in con.execute("SELECT id FROM ingredients")}
    con.executescript(SCHEMA)
    for r in RECIPES:
        name_hy, steps_hy = RECIPES_HY.get(r["id"], (r["name_hy"] or None, None))
        if steps_hy is not None and len(steps_hy) != len(r["steps"]):
            print(f"WARNING {r['id']}: Armenian steps ({len(steps_hy)}) differ from English ({len(r['steps'])}); "
                  f"using English steps for this recipe until they match")
            steps_hy = None
        con.execute("INSERT INTO recipes VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (r["id"], r["name"], name_hy, json.dumps(r["meals"]), r["servings"],
                     r["minutes"], r["difficulty"], json.dumps(r["tags"]),
                     json.dumps(r["steps"], ensure_ascii=False),
                     json.dumps(steps_hy, ensure_ascii=False) if steps_hy else None))
        for ing, qty, unit, staple in r["ingredients"]:
            if ing not in known:
                raise SystemExit(f"{r['id']}: unknown ingredient id {ing!r} (add it to ingredients.py)")
            con.execute("INSERT INTO recipe_ingredients VALUES (?,?,?,?,?)", (r["id"], ing, qty, unit, int(staple)))
    con.commit()
    print(f"loaded {len(RECIPES)} recipes")


if __name__ == "__main__":
    load()
