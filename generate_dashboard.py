#!/usr/bin/env python3
"""Regenerates home-audit-comparativa.html from history.json."""

import datetime
import json
from pathlib import Path

from sites_config import SITES, SITE_ORDER

ROOT = Path(__file__).parent
HISTORY_PATH = ROOT / "history.json"
TEMPLATE_PATH = ROOT / "dashboard_template.html"
OUTPUT_PATH = ROOT / "home-audit-comparativa.html"


def generate():
    history = json.loads(HISTORY_PATH.read_text()) if HISTORY_PATH.exists() else []
    site_meta = {
        key: {"label": cfg["label"], "own_label": cfg["own_label"], "om_label": cfg["om_label"]}
        for key, cfg in SITES.items()
    }
    template = TEMPLATE_PATH.read_text()
    html = (
        template
        .replace("__HISTORY_JSON__", json.dumps(history, ensure_ascii=False))
        .replace("__SITE_META_JSON__", json.dumps(site_meta, ensure_ascii=False))
        .replace("__SITE_ORDER_JSON__", json.dumps(SITE_ORDER))
        .replace("__N_DAYS__", f"{len(history)} día{'s' if len(history) != 1 else ''}")
        .replace("__GENERATED_AT__", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    )
    OUTPUT_PATH.write_text(html)
    print(f"Wrote {OUTPUT_PATH} ({len(history)} day(s) of history).")


if __name__ == "__main__":
    generate()
