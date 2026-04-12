"""
ATP + WTA: try curl_cffi first (fast, no browser, ~1 sec).
If ATP is Cloudflare-blocked, fall back to Playwright.
ATP and WTA players are matched ONLY against their respective tour pages.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

ATP_URL = "https://live-tennis.eu/en/atp-race"
WTA_URL = "https://live-tennis.eu/en/wta-race"

# Players to exclude from undrafted/missed picks
BLOCKLIST = {"Alexander Zverev"}

# Substrings that indicate a non-player row (cut lines, qualification markers)
_SKIP_SUBSTRINGS = {"qualification", "cut", "alternates", "alternate", "qualifier"}

_STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins',   { get: () => [1,2,3,4,5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
    window.chrome = { runtime: {} };
}
"""


def scrape_race_points(all_players: list) -> tuple:
    from curl_cffi import requests as curl_requests
    from lxml import html as lxml_html
    from draft import PLAYER_TOUR

    atp_wanted = {p for p in all_players if PLAYER_TOUR.get(p) == "atp"}
    wta_wanted = {p for p in all_players if PLAYER_TOUR.get(p) == "wta"}

    points = {}
    active_tournaments = {}
    undrafted_atp = []
    undrafted_wta = []
    errors = []

    # ── ATP ───────────────────────────────────────────────────────────────────
    logger.info("[ATP] Fetching via curl_cffi…")
    try:
        session = curl_requests.Session(impersonate="chrome")
        resp = session.get(ATP_URL, timeout=30)
        logger.info("[ATP] Status: %d, length: %d", resp.status_code, len(resp.text))
        tree = lxml_html.fromstring(resp.content)
        rows = tree.xpath("//table/tbody/tr")
        logger.info("[ATP] lxml found %d rows", len(rows))

        matched = _parse_lxml_rows(rows, atp_wanted, points, active_tournaments, undrafted_atp)
        logger.info("[ATP] matched %d players", matched)

        if not matched:
            logger.warning("[ATP] curl_cffi got 0 — falling back to Playwright")
            atp_pts, atp_err = _scrape_playwright(ATP_URL, "ATP", atp_wanted)
            points.update(atp_pts)
            errors.extend(atp_err)
    except Exception as e:
        errors.append(f"ATP curl_cffi failed ({e}), trying Playwright…")
        atp_pts, atp_err = _scrape_playwright(ATP_URL, "ATP", atp_wanted)
        points.update(atp_pts)
        errors.extend(atp_err)

    # ── WTA ───────────────────────────────────────────────────────────────────
    logger.info("[WTA] Fetching via curl_cffi…")
    try:
        session = curl_requests.Session(impersonate="chrome")
        resp = session.get(WTA_URL, timeout=30)
        logger.info("[WTA] Status: %d, length: %d", resp.status_code, len(resp.text))
        tree = lxml_html.fromstring(resp.content)
        rows = tree.xpath("//table/tbody/tr")
        logger.info("[WTA] lxml found %d rows", len(rows))

        if not rows:
            import time as t; t.sleep(3)
            resp2 = session.get(WTA_URL, timeout=30)
            tree = lxml_html.fromstring(resp2.content)
            rows = tree.xpath("//table/tbody/tr")
            logger.info("[WTA] retry found %d rows", len(rows))

        matched = _parse_lxml_rows(rows, wta_wanted, points, active_tournaments, undrafted_wta)
        logger.info("[WTA] matched %d players", matched)
    except Exception as e:
        errors.append(f"WTA error: {e}")

    missing = set(all_players) - set(points.keys())
    if missing:
        errors.append(f"Not found on Race pages: {', '.join(sorted(missing))}")

    return points, active_tournaments, undrafted_atp, undrafted_wta, errors


def _clean_name(name: str) -> str:
    """Strip status symbols like ✗, ✓, ★ etc from player names."""
    # Remove non-letter, non-space, non-comma, non-hyphen, non-apostrophe chars
    cleaned = re.sub(r'[^\w\s,.\'\-]', '', name, flags=re.UNICODE).strip()
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', cleaned).strip()


def _parse_lxml_rows(rows, wanted: set, points: dict, active_tournaments: dict = None, undrafted: list = None, max_undrafted: int = 20) -> int:
    matched = 0
    for row in rows:
        try:
            cells = row.xpath("./td")
            if len(cells) < 6:
                continue
            name_raw = (cells[2].text_content() or "").strip()
            pts_raw  = (cells[5].text_content() or "").strip().replace(",", "").replace("\xa0", "")
            if not name_raw or not pts_raw.isdigit():
                continue

            # Skip non-player rows (qualification cuts etc)
            if any(s in name_raw.lower() for s in _SKIP_SUBSTRINGS):
                continue

            # Clean name (strip ✗ and other symbols)
            name_clean = _clean_name(name_raw)

            # Skip blocklisted players
            if any(_normalize(name_clean.lower()) == _normalize(b.lower()) for b in BLOCKLIST):
                continue

            m = _match(name_clean, wanted)
            if m and m not in points:
                points[m] = int(pts_raw)
                matched += 1
                # Active = col8 non-empty AND col9 empty
                if active_tournaments is not None and len(cells) > 8:
                    col8 = cells[8].text_content().strip().replace("\xa0", " ").strip()
                    col9 = cells[9].text_content().strip() if len(cells) > 9 else ""
                    if col8 and not col9:
                        active_tournaments[m] = col8
            elif m is None and undrafted is not None and len(undrafted) < max_undrafted:
                pts = int(pts_raw)
                if pts > 0:
                    undrafted.append({"player": name_clean, "points": pts})
        except Exception:
            continue
    return matched


def _scrape_playwright(url: str, label: str, wanted: set) -> tuple:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    points = {}
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = ctx.new_page()
        page.add_init_script(_STEALTH_JS)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            _dismiss_cookies(page)
            try:
                page.wait_for_selector("table tbody tr", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(2000)
            raw = page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    const out = [];
                    rows.forEach(r => {
                        const c = r.querySelectorAll('td');
                        if (c.length >= 6) {
                            const name = c[2].innerText.trim();
                            const pts  = c[5].innerText.trim().replace(/,/g,'');
                            if (name && /^\\d+$/.test(pts)) out.push([name, parseInt(pts)]);
                        }
                    });
                    return out;
                }
            """)
            logger.info("[%s] Playwright extracted %d rows", label, len(raw))
            for name_raw, pts in raw:
                name_clean = _clean_name(name_raw)
                m = _match(name_clean, wanted)
                if m and m not in points:
                    points[m] = pts
            logger.info("[%s] Playwright matched %d players", label, len(points))
        except PWTimeout:
            errors.append(f"{label} Playwright timed out")
        except Exception as e:
            errors.append(f"{label} Playwright error: {e}")
        finally:
            page.close()
            browser.close()
    return points, errors


def _dismiss_cookies(page):
    for sel in [
        "button#onetrust-accept-btn-handler", "button.accept-cookies",
        "button:has-text('Accept All')", "button:has-text('Accept')",
    ]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click(); page.wait_for_timeout(400); return
        except Exception:
            pass


def _normalize(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _match(name_raw, wanted):
    name_raw = name_raw.strip()
    if name_raw in wanted: return name_raw
    parts = name_raw.split()
    if len(parts) >= 2:
        flipped = f"{' '.join(parts[1:])}, {parts[0]}"
        if flipped in wanted: return flipped
    nl = _normalize(name_raw.lower())
    for w in wanted:
        if _normalize(w.lower()) == nl: return w
        if "," in w:
            last, first = w.split(",", 1)
            if _normalize(f"{first.strip()} {last.strip()}".lower()) == nl: return w
    # Multi-word last name matching (e.g. "Davidovich Fokina")
    if len(parts) >= 3:
        for w in wanted:
            if "," in w:
                last = w.split(",")[0].strip()
                if _normalize(last.lower()) == _normalize(" ".join(parts[1:]).lower()):
                    return w
    last_s = _normalize(parts[-1].lower()) if parts else ""
    if len(last_s) > 3:
        for w in wanted:
            if _normalize(w.split(",")[0].strip().lower()) == last_s: return w
    return None
