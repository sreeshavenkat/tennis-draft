"""
Thin JSON store. Persists scraped points and a per-player history
so we can show point deltas over time.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from draft import DRAFT

_FILE = os.path.join(os.path.dirname(__file__), "store.json")
_ET = timezone(timedelta(hours=-5))  # ET (UTC-5); EDT is UTC-4, EST is UTC-5
# We use the system clock to determine DST automatically
def _now_et() -> str:
    import time as _time
    # Use local-aware conversion: get UTC, convert to ET accounting for DST
    utc_now = datetime.now(timezone.utc)
    # ET is UTC-4 in summer (EDT), UTC-5 in winter (EST)
    # Python's astimezone handles DST correctly when the system timezone is set
    try:
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        return datetime.now(et).strftime("%b %-d, %Y %-I:%M %p ET")
    except Exception:
        # Fallback: simple UTC-5 offset
        et_time = utc_now + timedelta(hours=-5)
        return et_time.strftime("%b %d, %Y %I:%M %p ET")


def _defaults():
    return {
        "player_points": {},   # only live scraped data — no seeds
        "history": {},
        "last_updated": None,
        "scrape_errors": [],
    }


def load():
    try:
        with open(_FILE) as f:
            d = json.load(f)
        for k, v in _defaults().items():
            d.setdefault(k, v)
        return d
    except (FileNotFoundError, json.JSONDecodeError):
        return _defaults()


def save(d):
    with open(_FILE, "w") as f:
        json.dump(d, f, indent=2)


def init():
    if not os.path.exists(_FILE):
        save(_defaults())


def apply_scrape(new_points: dict, errors: list):
    d = load()
    now = _now_et()
    for player, pts in new_points.items():
        d["player_points"][player] = pts
        hist = d["history"].setdefault(player, [])
        if not hist or hist[-1]["points"] != pts:
            hist.append({"date": now, "points": pts})
            d["history"][player] = hist[-200:]
    d["last_updated"] = now
    d["scrape_errors"] = errors
    save(d)


def leaderboard():
    d = load()
    pts = d["player_points"]
    rows = []
    for participant, roster in DRAFT.items():
        breakdown = {p: pts.get(p, 0) for p in roster}
        rows.append({
            "name": participant,
            "total": sum(breakdown.values()),
            "breakdown": breakdown,
        })
    rows.sort(key=lambda x: x["total"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def all_players():
    d = load()
    pts = d["player_points"]
    hist = d["history"]
    owner_map = {p: owner for owner, roster in DRAFT.items() for p in roster}
    rows = []
    for player, owner in owner_map.items():
        p = pts.get(player, 0)
        h = hist.get(player, [])
        delta = (h[-1]["points"] - h[0]["points"]) if len(h) >= 2 else None
        rows.append({"player": player, "owner": owner, "points": p, "delta": delta})
    rows.sort(key=lambda x: x["points"], reverse=True)
    return rows
