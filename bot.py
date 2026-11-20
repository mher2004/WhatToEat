"""Telegram բոտ մայրիկի համար — օրվա ճաշացանկ, պատրաստման եղանակ և գնումների ցուցակ։

Գործարկում.
    export BOT_TOKEN="123456:ABC..."
    python3 bot.py
"""
import os
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from plan import day_plans, load_recipes
from shop import PANTRY_DEFAULT, build_catalog, fmt_amount, load_info, shopping

DB_PATH = "whattoeat.db"

MEAL_LABELS = {
    "breakfast": "Նախաճաշ",
    "lunch": "Ճաշ",
    "dinner": "Ընթրիք",
}

MEAL_PRESETS = {
    "all3": (["breakfast", "lunch", "dinner"], "Նախաճաշ + Ճաշ + Ընթրիք"),
    "ld": (["lunch", "dinner"], "Ճաշ + Ընթրիք"),
    "l": (["lunch"], "Միայն ճաշ"),
    "d": (["dinner"], "Միայն ընթրիք"),
}


def get_data():
    con = sqlite3.connect(DB_PATH)
    info = load_info(con)
    catalog = build_catalog(con, info)
    return con, info, catalog


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["🍽 Կազմել ճաշացանկ"], ["ℹ️ Ինչպե՞ս օգտվել"]],
        resize_keyboard=True,
    )


def people_keyboard():
    rows = [
        [
            InlineKeyboardButton("1 հոգի", callback_data="ppl:1"),
            InlineKeyboardButton("2 հոգի", callback_data="ppl:2"),
        ],
        [
            InlineKeyboardButton("3 հոգի", callback_data="ppl:3"),
            InlineKeyboardButton("4 հոգի", callback_data="ppl:4"),
        ],
        [
            InlineKeyboardButton("5 հոգի", callback_data="ppl:5"),
            InlineKeyboardButton("6 հոգի", callback_data="ppl:6"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def meals_keyboard():
    rows = [
        [InlineKeyboardButton("🍳🍲🥗 Նախաճաշ + Ճաշ + Ընթրիք", callback_data="meals:all3")],
        [InlineKeyboardButton("🍲🥗 Ճաշ + Ընթրիք", callback_data="meals:ld")],
        [
            InlineKeyboardButton("🍲 Միայն ճաշ", callback_data="meals:l"),
            InlineKeyboardButton("🥗 Միայն ընթրիք", callback_data="meals:d"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def budget_keyboard():
    budgets = [1000, 1500, 2000, 2500, 3000, 4000, 5000, 7000]
    rows = []
    for i in range(0, len(budgets), 2):
        b1, b2 = budgets[i], budgets[i + 1]
        rows.append([
            InlineKeyboardButton(f"{b1:,} ֏".replace(",", " "), callback_data=f"bud:{b1}"),
            InlineKeyboardButton(f"{b2:,} ֏".replace(",", " "), callback_data=f"bud:{b2}"),
        ])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Բարև մամ ջան ❤️\n\n"
        "Ես կօգնեմ ընտրել օրվա ճաշացանկը՝ ըստ ձեր բյուջեի և Երևան Սիթիի իրական գների։\n\n"
        "Սեղմիր ներքևի «🍽 Կազմել ճաշացանկ» կոճակը կամ ընտրիր՝ քանի հոգու համար ենք պատրաստում․",
        reply_markup=main_menu_keyboard(),
    )
    await update.message.reply_text("Քանի՞ հոգու համար է․", reply_markup=people_keyboard())


async def help_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Ինչպե՞ս է աշխատում.\n"
        "1. Ընտրում ես անձանց քանակը\n"
        "2. Ընտրում ես՝ օրվա որ ուտեստներն են պետք\n"
        "3. Ընտրում ես օրվա բյուջեն (դրամով)\n\n"
        "Ես ցույց կտամ 3 տարբերակ՝ իրենց արժեքներով, պատրաստման քայլերով և խանութի գնումների ցուցակով։",
        reply_markup=main_menu_keyboard(),
    )


async def begin_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Քանի՞ հոգու համար ենք պատրաստում․", reply_markup=people_keyboard())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("ppl:"):
        people = int(data.split(":")[1])
        context.user_data["people"] = people
        await query.edit_message_text(
            f"Ընտրված է՝ {people} հոգի։\nՈ՞ր ուտեստներն ենք պլանավորում․",
            reply_markup=meals_keyboard(),
        )

    elif data.startswith("meals:"):
        key = data.split(":")[1]
        meals, label = MEAL_PRESETS[key]
        context.user_data["meals"] = meals
        context.user_data["meals_label"] = label
        people = context.user_data.get("people", 2)
        await query.edit_message_text(
            f"👥 {people} հոգի | 🍽 {label}\n\n"
            "Ինչքա՞ն է օրվա բյուջեն (ամբողջ ընտանիքի համար)․",
            reply_markup=budget_keyboard(),
        )

    elif data.startswith("bud:"):
        budget = int(data.split(":")[1])
        people = context.user_data.get("people", 2)
        meals = context.user_data.get("meals", ["breakfast", "lunch", "dinner"])

        con, info, catalog = get_data()
        recipes = load_recipes(con, people, "p25")
        options = day_plans(recipes, meals, budget, top=3)
        con.close()

        if not options:
            cheapest = sum(min(r["cost"] for r in recipes.values() if m in r["meals"]) for m in meals)
            await query.edit_message_text(
                f"😔 {people} հոգու համար {budget} ֏-ով հարմար տարբերակ չգտնվեց։\n"
                f"Ամենամատչելի տարբերակը կազմում է մոտ {cheapest} ֏։\n\n"
                "Փորձիր ընտրել ավելի մեծ բյուջե․",
                reply_markup=budget_keyboard(),
            )
            return

        context.user_data["options"] = options
        context.user_data["budget"] = budget

        lines = [f"✅ Ահա 3 տարբերակ {people} հոգու համար (բյուջե՝ {budget} ֏)․\n"]
        buttons = []
        for idx, combo in enumerate(options, 1):
            eaten = sum(r["cost"] for r in combo)
            sh = shopping(catalog, info, combo, PANTRY_DEFAULT)
            lines.append(f"🔹 Տարբերակ {idx} — ուտելիքի արժեքը՝ {eaten} ֏ (խանութում՝ ~{sh['pay']} ֏)")
            for m, r in zip(meals, combo):
                lines.append(f"   • {MEAL_LABELS[m]}՝ {r['name']} ({r['cost']} ֏)")
            lines.append("")
            buttons.append([
                InlineKeyboardButton(f"📖 Բաղադրատոմս #{idx}", callback_data=f"steps:{idx-1}"),
                InlineKeyboardButton(f"🛒 Գնումներ #{idx}", callback_data=f"shop:{idx-1}"),
            ])

        buttons.append([InlineKeyboardButton("🔄 Սկսել նորից", callback_data="restart")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("steps:"):
        idx = int(data.split(":")[1])
        options = context.user_data.get("options", [])
        meals = context.user_data.get("meals", [])
        people = context.user_data.get("people", 2)
        if idx >= len(options):
            return
        combo = options[idx]
        text = [f"📖 Պատրաստման եղանակ (Տարբերակ {idx + 1}, {people} հոգու համար)\n"]
        for m, r in zip(meals, combo):
            text.append(f"🔸 {MEAL_LABELS[m]}՝ {r['name']}")
            for step_i, s in enumerate(r["steps"], 1):
                text.append(f"   {step_i}. {s}")
            text.append("")

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🛒 Գնումների ցուցակ #{idx + 1}", callback_data=f"shop:{idx}")],
            [InlineKeyboardButton("🔄 Նոր ճաշացանկ", callback_data="restart")],
        ])
        await query.message.reply_text("\n".join(text), reply_markup=kb)

    elif data.startswith("shop:"):
        idx = int(data.split(":")[1])
        options = context.user_data.get("options", [])
        if idx >= len(options):
            return
        combo = options[idx]
        con, info, catalog = get_data()
        sh = shopping(catalog, info, combo, PANTRY_DEFAULT)
        con.close()

        text = [f"🛒 Գնումների ցուցակ (Տարբերակ {idx + 1})\n"]
        for l in sh["lines"]:
            need_str = fmt_amount(l["need"], l["basis"])
            if l["loose"]:
                buy_str = f"{l['name']} (կշռով)"
            else:
                pack_str = fmt_amount(l["pack"], l["basis"])
                buy_str = f"{l['n']:g} հատ × {l['name']} [{pack_str}]"
            text.append(f"• {l['label']} (պետք է՝ {need_str})\n   ↳ Գնել՝ {buy_str} — {l['cost']:.0f} ֏")

        if sh["pantry"]:
            pantry_names = [info[p][0] for p in sh["pantry"] if p in info]
            text.append(f"\n🏠 Տանը կա (չենք գնում)՝ {', '.join(pantry_names)}")

        text.append(f"\n💰 Ընդհանուր վճարում խանութում՝ {sh['pay']} ֏")
        if sh["leftover_value"] > 0:
            text.append(f"📦 Դրանից մոտ {sh['leftover_value']} ֏-ի մթերք կմնա հաջորդ օրերի համար։")

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📖 Բաղադրատոմս #{idx + 1}", callback_data=f"steps:{idx}")],
            [InlineKeyboardButton("🔄 Նոր ճաշացանկ", callback_data="restart")],
        ])
        await query.message.reply_text("\n".join(text), reply_markup=kb)

    elif data == "restart":
        context.user_data.clear()
        await query.message.reply_text("Քանի՞ հոգու համար ենք պատրաստում․", reply_markup=people_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if "Ինչպե՞ս" in txt:
        await help_msg(update, context)
    else:
        await begin_flow(update, context)


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("Սահմանեք BOT_TOKEN միջավայրի փոփոխականը (export BOT_TOKEN=...)։")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()