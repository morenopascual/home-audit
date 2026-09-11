#!/usr/bin/env python3
"""
Takes one "photo" of the five homepages: for each site, walks its content
modules, classifies every link (own site / streaming page / streaming
player-autoplay / other group brand), sizes each item (hero / image /
text-only) and flags items with a genuinely inline-playable video.

Usage:
    python scrape.py                  # take today's photo, append to history.json
    python scrape.py --force          # take a photo even if one already exists for today
    python scrape.py --dry-run        # print the result, don't touch history.json

Requires: pip install playwright  &&  playwright install chromium
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from sites_config import CONTAINER_JS, DISMISS_COOKIES_JS, EXTRACT_MODULES_JS, SITES, classify_link

HISTORY_PATH = Path(__file__).parent / "history.json"
DEBUG_DIR = Path(__file__).parent / "debug"

SIZE_L, SIZE_M, SIZE_S = 27, 22, 17


def size_for(index_in_module, has_img):
    if index_in_module == 0:
        return "L"
    return "M" if has_img else "S"


def _extract(page, site_key):
    container_handle = page.evaluate_handle(CONTAINER_JS[site_key])
    if container_handle is None:
        return None
    return page.evaluate(EXTRACT_MODULES_JS, container_handle)


def scrape_site(page, site_key, site_cfg):
    page.goto(site_cfg["url"], wait_until="networkidle", timeout=45000)
    try:
        page.evaluate(DISMISS_COOKIES_JS)
    except Exception:
        pass
    page.wait_for_timeout(2000)  # let lazy-loaded modules settle

    raw_modules = _extract(page, site_key)

    if not raw_modules:
        # One retry: reload fresh and give it more time before giving up.
        # Covers both "container selector matched nothing" and "matched an
        # empty/not-yet-hydrated container".
        page.reload(wait_until="networkidle", timeout=45000)
        try:
            page.evaluate(DISMISS_COOKIES_JS)
        except Exception:
            pass
        page.wait_for_timeout(4000)
        raw_modules = _extract(page, site_key)

    if not raw_modules:
        DEBUG_DIR.mkdir(exist_ok=True)
        shot_path = DEBUG_DIR / f"{site_key}.png"
        try:
            page.screenshot(path=str(shot_path), full_page=False)
        except Exception:
            shot_path = None
        title = page.title()
        raise RuntimeError(
            f"[{site_key}] got 0 modules after retry. Page title was: {title!r}. "
            f"{'Screenshot saved to ' + str(shot_path) if shot_path else 'Screenshot failed too.'} "
            f"Likely causes: cookie banner not dismissed, anti-bot page served instead "
            f"of the real homepage, or the site's markup changed."
        )
    return raw_modules


def build_snapshot(raw_modules_by_site):
    """Classify raw extracted modules into the same shape the dashboard
    HTML expects: {site_key: {"modules": [[name, [[cat,size,playable],...]]], ...}}
    """
    snapshot = {}
    for site_key, modules in raw_modules_by_site.items():
        out_modules = []
        playable_total = 0
        for mod in modules:
            name = mod["name"] or "(sin título)"
            items_out = []
            for i, item in enumerate(mod["items"]):
                cat = classify_link(site_key, item["hostname"], item["pathname"])
                if cat is None:
                    continue
                size = size_for(i, item["hasImg"])
                is_playable = 1 if item.get("hasPlayableVideo") else 0
                items_out.append([cat, size, is_playable])
            if not items_out:
                continue
            playable_total += sum(e[2] for e in items_out)
            out_modules.append([name, items_out])
        snapshot[site_key] = {"modules": out_modules, "playable_total": playable_total}
    return snapshot


def run(dry_run=False, force=False):
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC")

    history = []
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text())

    if not force and any(entry["date"] == today for entry in history):
        print(f"Already have a snapshot for {today}, skipping (use --force to override).")
        return

    raw_by_site = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            locale="es-ES",
            timezone_id="Europe/Madrid",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        for site_key, site_cfg in SITES.items():
            print(f"Scraping {site_cfg['label']}...")
            try:
                raw_by_site[site_key] = scrape_site(page, site_key, site_cfg)
            except Exception as exc:
                print(f"  FAILED: {exc}", file=sys.stderr)
                raw_by_site[site_key] = []
        browser.close()

    snapshot = build_snapshot(raw_by_site)

    if dry_run:
        print(json.dumps({"date": today, "time": now, "sites": snapshot}, indent=2, ensure_ascii=False))
        return

    history = [e for e in history if e["date"] != today]  # replace if --force
    history.append({"date": today, "time": now, "sites": snapshot})
    history.sort(key=lambda e: e["date"])
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    print(f"Saved snapshot for {today} {now}. History now has {len(history)} day(s).")

    from generate_dashboard import generate
    generate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)
