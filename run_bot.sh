#!/usr/bin/env bash
# Start the Telegram bot.
#
#   ./run_bot.sh            run the bot (stop with Ctrl+C)
#   ./run_bot.sh --forever  restart automatically if it crashes (waits 10 s between restarts)
#
# The token is read from the BOT_TOKEN environment variable, or from a file named .env
# in this folder containing one line:   BOT_TOKEN=123456:ABC...
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"

if [ -z "${BOT_TOKEN:-}" ] && [ -f .env ]; then
  set -a; . ./.env; set +a
fi
if [ -z "${BOT_TOKEN:-}" ]; then
  echo "ERROR: BOT_TOKEN is not set."
  echo "  Option 1:  export BOT_TOKEN=\"123456:ABC...\" && ./run_bot.sh"
  echo "  Option 2:  put  BOT_TOKEN=123456:ABC...  in a file named .env next to this script"
  exit 1
fi

if [ ! -f whattoeat.db ]; then
  echo "ERROR: whattoeat.db not found. Run ./update.sh first."
  exit 1
fi
if ! "$PY" -c "import telegram" 2>/dev/null; then
  echo "ERROR: python-telegram-bot is not installed.  Run:  pip install \"python-telegram-bot>=20.0\""
  exit 1
fi
if [ "$("$PY" -c "import sqlite3;print(sqlite3.connect('whattoeat.db').execute('select count(*) from recipes').fetchone()[0])" 2>/dev/null || echo 0)" = "0" ]; then
  echo "ERROR: no recipes in the database. Run ./update.sh (or python3 recipes.py) first."
  exit 1
fi

if [ "${1:-}" = "--forever" ]; then
  while true; do
    "$PY" bot.py || echo "Bot stopped with an error."
    echo "Restarting in 10 seconds (Ctrl+C to quit)..."
    sleep 10
  done
else
  exec "$PY" bot.py
fi
