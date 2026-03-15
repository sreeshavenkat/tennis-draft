import logging
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
    pts, errors = scrape_race_points(ALL_PLAYERS)
    store.apply_scrape(pts, errors)
    logger.info("Done — updated %d players. Errors: %d", len(pts), len(errors))
    return pts, errors


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
    return render_template(
        "index.html",
        leaderboard=store.leaderboard(),
        players=store.all_players(),
        draft_order=DRAFT_ORDER,
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


if __name__ == "__main__":
    store.init()
    threading.Thread(target=scheduler, daemon=True).start()
    app.run(debug=False, port=5000)
