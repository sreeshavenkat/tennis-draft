"""
ATP:  live-tennis.eu/en/atp-race  — Playwright with inline stealth patches
WTA:  live-tennis.eu/en/wta-race  — curl_cffi (Chrome TLS) + lxml, no browser needed
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

ATP_URL = "https://live-tennis.eu/en/atp-race"
WTA_URL = "https://live-tennis.eu/en/wta-race"

# Inline stealth JS — patches the signals Cloudflare checks
_STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'permissions', {
        get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
    });
}
"""


def scrape_race_points(all_players: list) -> tuple:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    wanted = set(all_players)
    points = {}
    errors = []

    # ── ATP via Playwright with stealth JS ────────────────────────────────────
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
        page = ctx.new_page()
        page.add_init_script(_STEALTH_JS)
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

            # Extract all data in one JS call instead of row-by-row — much faster
            raw = page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    const results = [];
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 6) {
                            const name = cells[2].innerText.trim();
                            const pts  = cells[5].innerText.trim().replace(/,/g, '');
                            if (name && /^\\d+$/.test(pts)) {
                                results.push([name, parseInt(pts)]);
                            }
                        }
                    });
                    return results;
                }
            """)
            logger.info("[ATP] Extracted %d candidates via JS", len(raw))

            matched = 0
            for name_raw, pts in raw:
                m = _match(name_raw, wanted)
                if m and m not in points:
                    points[m] = pts
                    matched += 1
            atp_pts = points  # already merged above
            logger.info("[ATP] Matched %d players", matched)

            if not matched:
                snippet = page.inner_text("body")[:400]
                logger.warning("[ATP] 0 matched. Snippet:\n%s", snippet)

        except PWTimeout:
            errors.append("ATP page timed out")
        except Exception as e:
            errors.append(f"ATP error: {e}")
        finally:
            page.close()
            browser.close()

    # ── WTA via curl_cffi + lxml (no browser needed) ──────────────────────────
    try:
        from curl_cffi import requests as curl_requests
        from lxml import html as lxml_html

        logger.info("[WTA] Fetching via curl_cffi…")
        session = curl_requests.Session(impersonate="chrome")
        resp = session.get(WTA_URL, timeout=30)
        logger.info("[WTA] Status: %d, length: %d", resp.status_code, len(resp.text))

        tree = lxml_html.fromstring(resp.content)
        rows = tree.xpath("//table/tbody/tr")
        logger.info("[WTA] lxml found %d rows", len(rows))

        if not rows:
            import time as t
            t.sleep(3)
            resp2 = session.get(WTA_URL, timeout=30)
            tree = lxml_html.fromstring(resp2.content)
            rows = tree.xpath("//table/tbody/tr")
            logger.info("[WTA] retry found %d rows", len(rows))

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

    except ImportError as e:
        errors.append(f"WTA missing dependency: {e}")
    except Exception as e:
        errors.append(f"WTA error: {e}")

    missing = wanted - set(points.keys())
    if missing:
        errors.append(f"Not found on Race pages: {', '.join(sorted(missing))}")

    return points, errors


def _parse_rows(rows, wanted: set) -> tuple:
    """Parse live-tennis.eu table: rank | empty | Name | age | country | points"""
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
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _match(name_raw: str, wanted: set) -> str | None:
    name_raw = name_raw.strip()
    if name_raw in wanted:
        return name_raw
    parts = name_raw.split()
    if len(parts) >= 2:
        flipped = f"{' '.join(parts[1:])}, {parts[0]}"
        if flipped in wanted:
            return flipped
    nl = _normalize(name_raw.lower())
    for w in wanted:
        if _normalize(w.lower()) == nl:
            return w
        if "," in w:
            last, first = w.split(",", 1)
            ff = f"{first.strip()} {last.strip()}"
            if _normalize(ff.lower()) == nl:
                return w
    last_scraped = _normalize(parts[-1].lower()) if parts else ""
    if len(last_scraped) > 3:
        for w in wanted:
            if _normalize(w.split(",")[0].strip().lower()) == last_scraped:
                return w
    return None
