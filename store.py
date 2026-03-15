import json
import os
from datetime import datetime, timezone, timedelta
from draft import DRAFT, DRAFT_ORDER

_FILE = os.path.join(os.path.dirname(__file__), "store.json")

def _now_et() -> str:
    utc_now = datetime.now(timezone.utc)
    try:
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        return datetime.now(et).strftime("%b %-d, %Y %-I:%M %p ET")
    except Exception:
        et_time = utc_now + timedelta(hours=-5)
        return et_time.strftime("%b %d, %Y %I:%M %p ET")


def _defaults():
    return {
        "player_points": {},
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


def apply_scrape(new_points: dict, active_tournaments: dict, undrafted_atp: list, undrafted_wta: list, errors: list):
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
    d["active_tournaments"] = active_tournaments
    d["undrafted_atp"] = undrafted_atp
    d["undrafted_wta"] = undrafted_wta
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
        sparkline = [e["points"] for e in h[-14:]] if h else []
        rows.append({"player": player, "owner": owner, "points": p, "delta": delta, "sparkline": sparkline})
    rows.sort(key=lambda x: x["points"], reverse=True)
    return rows


def best_picks() -> dict:
    """
    Best pick = highest opportunity cost outperformance.
    For each pick, compare the player's current points against the
    best available player at that pick slot (i.e. the highest-scoring
    player who was still undrafted at that point in the draft).
    A positive value means you outperformed the best alternative.
    """
    d = load()
    pts = d["player_points"]

    # Build set of all drafted players with their points
    all_drafted = {pick["player"]: pts.get(pick["player"], 0) for pick in DRAFT_ORDER}

    result = {}
    already_picked = set()

    for pick in DRAFT_ORDER:
        p = pick["player"]
        owner = pick["owner"]
        player_pts = pts.get(p, 0)
        already_picked.add(p)

        if player_pts == 0:
            continue

        # Best available at this pick = highest scoring player NOT yet picked
        # excluding the current player (they weren't available to themselves)
        available = {
            name: points for name, points in all_drafted.items()
            if name not in already_picked
        }
        best_available_pts = max(available.values()) if available else 0

        # Outperformance = how much better this pick is vs best remaining option
        outperformance = player_pts - best_available_pts

        if owner not in result or outperformance > result[owner]["outperformance"]:
            best_available_name = max(available, key=available.get) if available else "—"
            result[owner] = {
                "player": p,
                "points": player_pts,
                "round": pick["round"],
                "overall_pick": pick["overall_pick"],
                "outperformance": outperformance,
                "best_available": best_available_name,
                "best_available_pts": best_available_pts,
            }

    return result


def append_team_history(entry: dict):
    d = load()
    history = d.setdefault("team_history", [])
    if not history or history[-1]["date"] != entry["date"]:
        history.append(entry)
        d["team_history"] = history
        save(d)


def get_team_history() -> list:
    from draft import TEAM_HISTORY
    d = load()
    live = {e["date"]: e for e in d.get("team_history", [])}
    seed = {e["date"]: e for e in TEAM_HISTORY}
    merged = {**seed, **live}
    return sorted(merged.values(), key=lambda x: x["date"])
