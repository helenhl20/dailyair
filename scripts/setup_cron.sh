#!/bin/bash
# DailyAir — Cron setup script
# Adds a daily 6:30 AM cron job to run DailyAir

DAILYAIR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$(which python3)"
CRON_CMD="30 6 * * * cd $DAILYAIR_DIR && $PYTHON -m dailyair run >> $DAILYAIR_DIR/dailyair.log 2>&1"

echo "Setting up DailyAir cron job..."
echo "  Directory: $DAILYAIR_DIR"
echo "  Time: 6:30 AM daily"

(crontab -l 2>/dev/null | grep -v "dailyair run"; echo "$CRON_CMD") | crontab -

echo "✅ Done! DailyAir will run every day at 6:30 AM."
echo "   Logs: $DAILYAIR_DIR/dailyair.log"
