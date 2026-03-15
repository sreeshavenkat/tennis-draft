# 🎾 2026 Tennis Draft

Flask web app showing live 2026 ATP/WTA Race standings for your fantasy draft.
Points are scraped daily from the official ATP Race-to-Turin and WTA Race-to-Riyadh
pages using Playwright (headless Chromium).

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chromium browser (one-time)
playwright install chromium

# Run
python app.py
# → open http://localhost:5000
```

## How it works

- On startup the app loads **seed points** from `draft.py` (mid-March 2026 snapshot)
  and immediately triggers a live scrape in the background
- Every 24 hours the scraper re-runs automatically
- Hit the **Refresh** button in the nav to trigger an immediate scrape
- Points and history are persisted in `store.json`

## Files

| File | Purpose |
|------|---------|
| `app.py` | Flask routes + background scheduler |
| `scraper.py` | Playwright scraper for ATP/WTA Race pages |
| `store.py` | JSON persistence + leaderboard logic |
| `draft.py` | Rosters, seed points, tour assignments |
| `templates/index.html` | Full UI |
| `store.json` | Auto-created — live points + history |

## Notes on scraping

The scraper targets:
- ATP: `atptour.com/en/rankings/singles-race-to-turin`
- WTA: `wtatennis.com/rankings/race-to-riyadh`

If a player isn't matched (e.g. page layout changed), the app falls back to seed
points and logs a warning in the Refresh response. Check the terminal for details.
