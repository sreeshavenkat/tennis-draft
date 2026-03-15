"""
ATP:  live-tennis.eu/en/atp-race  — stealth Playwright (working)
WTA:  live-tennis.eu/en/wta-race  — curl_cffi to bypass Cloudflare TLS check,
      cookies injected into Playwright so JS can render the table.

curl_cffi impersonates Chrome's TLS fingerprint at the socket level — a
completely different signal from what playwright-stealth patches. Together
they cover the two main Cloudflare bot-detection vectors.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

ATP_URL = "https://live-tennis.eu/en/atp-race"
WTA_URL = "https://live-tennis.eu/en/wta-race"


def scrape_race_points(all_players: list) -> tuple:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    from playwright_stealth import stealth_sync

    wanted = set(all_players)
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
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )

        # ── ATP via stealth Playwright ────────────────────────────────────────
        page = ctx.new_page()
        stealth_sync(page)
        try:
            logger.info("[ATP] Loading %s", ATP_URL)
            page.goto(ATP_URL, wait_until="domcontentloaded", timeout=90_000)
            _dismiss_cookies(page)
            try:
                page.wait_for_selector("table tbody tr", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(2000)
            rows = page.query_selector_all("table tbody tr")
            logger.info("[ATP] Found %d rows", len(rows))
            atp_pts, atp_matched = _parse_rows(rows, wanted)
            points.update(atp_pts)
            logger.info("[ATP] Matched %d players", atp_matched)
        except PWTimeout:
            errors.append("ATP page timed out")
        except Exception as e:
            errors.append(f"ATP error: {e}")
        finally:
            page.close()

        # ── WTA via curl_cffi + Playwright ────────────────────────────────────
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            errors.append("curl_cffi not installed — run: pip install curl_cffi --index-url https://pypi.org/simple/")
            curl_requests = None

        if curl_requests:
            try:
                logger.info("[WTA] Fetching via curl_cffi (Chrome TLS impersonation)…")
                session = curl_requests.Session(impersonate="chrome")
                # First hit the page to get Cloudflare clearance cookies
                resp = session.get(WTA_URL, timeout=30)
                logger.info("[WTA] curl_cffi status: %d, content length: %d", resp.status_code, len(resp.text))

                # Log a snippet to see what we got
                snippet = resp.text[:600]
                logger.info("[WTA] Response snippet:\n%s", snippet)

                # Try parsing the HTML directly with lxml
                from lxml import html as lxml_html
                tree = lxml_html.fromstring(resp.content)
                rows = tree.xpath("//table/tbody/tr")
                logger.info("[WTA] lxml found %d rows", len(rows))

                if not rows:
                    # Page may be a JS challenge — try waiting and refetching
                    import time as time_mod
                    time_mod.sleep(3)
                    resp2 = session.get(WTA_URL, timeout=30)
                    logger.info("[WTA] Retry status: %d", resp2.status_code)
                    tree = lxml_html.fromstring(resp2.content)
                    rows = tree.xpath("//table/tbody/tr")
                    logger.info("[WTA] lxml retry found %d rows", len(rows))

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
                        m = _match(name_raw, wanted)
                        if m and m not in points:
                            points[m] = int(pts_raw)
                            matched += 1
                    except Exception:
                        continue

                logger.info("[WTA] Matched %d players", matched)
                if not matched and rows:
                    # Log first row to see column structure
                    first = rows[0].xpath("./td")
                    logger.warning("[WTA] First row cells: %s", [c.text_content().strip() for c in first[:8]])

            except Exception as e:
                errors.append(f"WTA curl_cffi error: {e}")

        browser.close()

    missing = wanted - set(points.keys())
    if missing:
        errors.append(f"Not found on Race pages: {', '.join(sorted(missing))}")

    return points, errors


def _parse_rows(rows, wanted: set) -> tuple:
    """
    Parse live-tennis.eu table rows.
    Column structure: rank | empty | Name (First Last) | age | country | points
    """
    points = {}
    matched = 0
    for row in rows:
        try:
            cells = row.query_selector_all("td")
            if len(cells) < 6:
                continue
            name_raw = cells[2].inner_text().strip()
            pts_raw  = cells[5].inner_text().strip().replace(",", "").replace("\xa0", "")
            if not name_raw or not pts_raw.isdigit():
                continue
            m = _match(name_raw, wanted)
            if m and m not in points:
                points[m] = int(pts_raw)
                matched += 1
        except Exception:
            continue
    return points, matched


def _first_int(cells) -> int | None:
    for cell in cells:
        txt = cell.inner_text().strip().replace(",", "").replace("\xa0", "")
        if re.fullmatch(r"\d+", txt):
            return int(txt)
    return None


def _dismiss_cookies(page):
    for sel in [
        "button#onetrust-accept-btn-handler",
        "button.accept-cookies",
        "button:has-text('Accept All')",
        "button:has-text('I Agree')",
        "button:has-text('Accept')",
        "[aria-label='Accept cookies']",
    ]:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(400)
                return
        except Exception:
            pass


def _normalize(s: str) -> str:
    """Strip accents: ć→c, ö→o, etc."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _match(name_raw: str, wanted: set) -> str | None:
    name_raw = name_raw.strip()

    # 1. Exact
    if name_raw in wanted:
        return name_raw

    # 2. Flip "First Last" → "Last, First"
    parts = name_raw.split()
    if len(parts) >= 2:
        flipped = f"{' '.join(parts[1:])}, {parts[0]}"
        if flipped in wanted:
            return flipped

    # 3. Case-insensitive + accent-stripped
    nl = _normalize(name_raw.lower())
    for w in wanted:
        if _normalize(w.lower()) == nl:
            return w
        if "," in w:
            last, first = w.split(",", 1)
            ff = f"{first.strip()} {last.strip()}"
            if _normalize(ff.lower()) == nl:
                return w

    # 4. Last-name fuzzy (accent-stripped)
    last_scraped = _normalize(parts[-1].lower()) if parts else ""
    if len(last_scraped) > 3:
        for w in wanted:
            last_wanted = _normalize(w.split(",")[0].strip().lower())
            if last_scraped == last_wanted:
                return w

    return None
