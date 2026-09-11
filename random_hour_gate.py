#!/usr/bin/env python3
"""
GitHub Actions cron can't say "once a day at a random hour" directly, so the
workflow instead runs this check once every hour. For each date, it derives
a pseudo-random target hour (0-23) from a hash of the date (+ a salt you can
change), and exits with status 1 (skip the rest of the job) unless the
current UTC hour matches. Net effect: exactly one real scrape per day, at a
different, unpredictable-looking hour each day.

Exit code 0  -> this IS the hour, proceed with the workflow's remaining steps
Exit code 1  -> not the hour yet today, workflow should stop here
"""

import datetime
import hashlib
import os
import sys

SALT = os.environ.get("RANDOM_HOUR_SALT", "home-audit-v1")


def target_hour_for(date_str: str) -> int:
    digest = hashlib.sha256(f"{SALT}:{date_str}".encode()).hexdigest()
    return int(digest, 16) % 24


def main():
    today = datetime.date.today().isoformat()
    current_hour = datetime.datetime.now(datetime.timezone.utc).hour
    target = target_hour_for(today)
    print(f"Today ({today}) UTC target hour: {target}. Current UTC hour: {current_hour}.")
    if current_hour == target:
        print("-> Match. Proceeding.")
        sys.exit(0)
    print("-> Not yet. Skipping today's run for this hour.")
    sys.exit(1)


if __name__ == "__main__":
    main()
