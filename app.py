import logging
import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template
import store
from draft import DRAFT, DRAFT_ORDER
from scraper import scrape_race_points

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
ALL_PLAYERS = [p for roster in DRAFT.values() for p in roster]


def do_scrape():
    logger.info("Scraping Race points for %d players…", len(ALL_PLAYERS))
    pts, active_tournaments, undrafted_atp, undrafted_wta, errors = scrape_race_points(ALL_PLAYERS)
    store.apply_scrape(pts, active_tournaments, undrafted_atp, undrafted_wta, errors)
    take_eod_snapshot()
    logger.info("Done — updated %d players. Errors: %d", len(pts), len(errors))
    return pts, errors


def take_eod_snapshot():
    """Save current team totals as an end-of-day history entry."""
    lb = store.leaderboard()
    try:
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        date_str = datetime.now(et).strftime("%Y-%m-%d")
    except Exception:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
    entry = {"date": date_str}
    for row in lb:
        entry[row["name"]] = row["total"]
    store.append_team_history(entry)
    logger.info("EOD snapshot saved for %s", date_str)


def scheduler():
    time.sleep(3)
    while True:
        do_scrape()
        next_run = datetime.now() + timedelta(hours=1)
        logger.info("Next scrape at %s", next_run.strftime("%Y-%m-%d %H:%M"))
        time.sleep(3600)


@app.route("/")
def index():
    d = store.load()
    players = store.all_players()
    player_sparklines = {p["player"]: p.get("sparkline", []) for p in players}
    return render_template(
        "index.html",
        leaderboard=store.leaderboard(),
        players=players,
        draft_order=DRAFT_ORDER,
        team_history=store.get_team_history(),
        active_tournaments=d.get("active_tournaments", {}),
        best_picks=store.best_picks(),
        worst_picks=store.worst_picks(),
        player_sparklines=player_sparklines,
        undrafted_atp=d.get("undrafted_atp", []),
        undrafted_wta=d.get("undrafted_wta", []),
        last_updated=d.get("last_updated"),
        scrape_errors=d.get("scrape_errors", []),
    )


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    pts, errors = do_scrape()
    d = store.load()
    return jsonify({
        "ok": True,
        "updated": len(pts),
        "errors": errors,
        "last_updated": d.get("last_updated"),
        "leaderboard": store.leaderboard(),
    })


@app.route("/api/state")
def api_state():
    d = store.load()
    return jsonify({
        "leaderboard": store.leaderboard(),
        "players": store.all_players(),
        "last_updated": d.get("last_updated"),
        "scrape_errors": d.get("scrape_errors", []),
    })


store.init()
threading.Thread(target=scheduler, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
