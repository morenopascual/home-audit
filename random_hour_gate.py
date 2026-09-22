#!/usr/bin/env python3
"""
GitHub Actions cron can't say "once a day at a random hour" directly, so the
workflow instead runs this check once every hour. For each date, it derives
a pseudo-random target hour (0-23) from a hash of the date (+ a salt you can
change).

It proceeds (exit 0) once the current UTC hour has REACHED that target hour
AND today doesn't have a snapshot yet. Using ">=" instead of "==" makes this
self-healing: GitHub Actions can and does occasionally skip/delay a specific
scheduled trigger under high load, and with an exact-hour match that silently
loses the whole day. With ">=", the very next hourly tick after a missed one
just catches up instead.

Exit code 0  -> proceed with the workflow's remaining steps
Exit code 1  -> already have today's photo, or not the hour yet -- skip
"""

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

SALT = os.environ.get("RANDOM_HOUR_SALT", "home-audit-v1")
HISTORY_PATH = Path(__file__).parent / "history.json"


def target_hour_for(date_str: str) -> int:
    digest = hashlib.sha256(f"{SALT}:{date_str}".encode()).hexdigest()
    return int(digest, 16) % 24


def already_have_snapshot_for(date_str: str) -> bool:
    if not HISTORY_PATH.exists():
        return False
    try:
        history = json.loads(HISTORY_PATH.read_text())
    except json.JSONDecodeError:
        return False
    return any(entry.get("date") == date_str for entry in history)


def main():
    today = datetime.date.today().isoformat()
    current_hour = datetime.datetime.now(datetime.timezone.utc).hour
    target = target_hour_for(today)

    if already_have_snapshot_for(today):
        print(f"Already have a snapshot for {today}. Skipping.")
        sys.exit(1)

    print(f"Today ({today}) UTC target hour: {target}. Current UTC hour: {current_hour}.")
    if current_hour >= target:
        print("-> Target hour reached (or we're catching up on a missed tick). Proceeding.")
        sys.exit(0)
    print("-> Not yet. Skipping this hour.")
    sys.exit(1)


if __name__ == "__main__":
    main()
