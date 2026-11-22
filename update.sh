#!/usr/bin/env bash
# Refresh all data: scrape Yerevan City -> load DB -> match ingredients/prices -> load recipes.
# Shows an overall progress bar, a live scraping counter and the time each step took.
#
#   ./update.sh                 full update
#   ./update.sh --skip-scrape   rebuild the DB from the latest raw/ folder without hitting the website
#   ./update.sh --check         also run check.py (sanity checks on the raw scrape)
#
# Safe to run from cron. Plain output is also appended to logs/update.log.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
SKIP_SCRAPE=0
RUN_CHECK=0
for arg in "$@"; do
  case "$arg" in
    --skip-scrape) SKIP_SCRAPE=1 ;;
    --check)       RUN_CHECK=1 ;;
    -h|--help)     sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

mkdir -p logs
LOG=logs/update.log
TOTAL=4
[ "$RUN_CHECK" -eq 1 ] && TOTAL=5
CUR=0
START=$(date +%s)

bar() {  # bar <done> <total>  -> [#####-----]  50%
  local d=$1 t=$2 w=30 f p i out=""
  f=$(( d * w / t )); p=$(( d * 100 / t ))
  for ((i=0;i<w;i++)); do if [ $i -lt $f ]; then out+="#"; else out+="-"; fi; done
  printf "[%s] %3d%%" "$out" "$p"
}

log() { echo "$*" >> "$LOG"; }

begin() {  # begin "<title>"
  STEP_START=$(date +%s)
  echo
  echo "$(bar "$CUR" "$TOTAL")  step $((CUR+1))/$TOTAL: $1"
  log ""; log "--> step $((CUR+1))/$TOTAL: $1 ($(date '+%F %T'))"
}

finish() {
  CUR=$((CUR+1))
  local secs=$(( $(date +%s) - STEP_START ))
  echo "$(bar "$CUR" "$TOTAL")  done in ${secs}s (total $(( $(date +%s) - START ))s)"
  log "    done in ${secs}s"
}

# Run a command, show its output and copy it to the log.
run() { "$PY" -u "$@" 2>&1 | tee -a "$LOG"; }

log ""; log "===== update started $(date '+%F %T') ====="
echo "WhatToEat update started $(date '+%F %T')"

# ---- step: scraping with a live counter ----
if [ "$SKIP_SCRAPE" -eq 0 ]; then
  begin "scraping Yerevan City (a few minutes)"
  NCAT=$("$PY" -c "from scraper import CORE; print(len(CORE))")
  "$PY" -u scraper.py 2>&1 | tee -a "$LOG" | awk -v ncat="$NCAT" -v tty="$([ -t 1 ] && echo 1 || echo 0)" '
    /^category /  { cat++; name=$0; sub(/^category [0-9]+: /, "", name); items=0; next }
    /^  page /    { split($2, a, "/"); pg=a[1]; pages=a[2]; items+=$3
                    if (tty) printf "\r   category %d/%d  page %s/%s  %-35.35s", cat, ncat, pg, pages, name
                    next }
    /^raw folder/ { print "   " $0; next }
    /^Summary:/   { if (tty) printf "\r%80s\r", ""; print; show=1; next }
    show          { print; next }
    { if (tty) printf "\r%80s\r", ""; print }
  '
  finish
else
  echo
  echo "(scraping skipped: using the latest folder in raw/yerevan_city)"
  log "scraping skipped"
  TOTAL=$((TOTAL-1))
fi

if [ ! -d raw/yerevan_city ] || [ -z "$(ls -A raw/yerevan_city 2>/dev/null)" ]; then
  echo "ERROR: no raw data found in raw/yerevan_city. Run without --skip-scrape first."
  exit 1
fi

if [ "$RUN_CHECK" -eq 1 ]; then
  begin "sanity checks (check.py)"
  run check.py > /dev/null
  finish
fi

begin "loading products and prices into whattoeat.db"
run db.py | awk '{ printf "\r   %-60.60s", $0 } END { print "" }'
finish

begin "matching products to ingredients, computing ingredient prices"
run match.py | awk 'NR<=3'
finish

begin "loading recipes"
run recipes.py
finish

echo
echo "All done in $(( $(date +%s) - START ))s."
echo "Latest price date in DB: $("$PY" -c "import sqlite3;print(sqlite3.connect('whattoeat.db').execute('select max(scraped_at) from prices').fetchone()[0])")"
log "===== update finished $(date '+%F %T') ====="
