# AGENTS.md — tcs-tools

**Article scraper + agency search utilities shared across TCS blog workflows.**

> **First-time context:** start with the top-level [AGENTS.md](../AGENTS.md) in the working directory. This file is repo-specific.

## What lives here

- **`article_scraper/`** — The canonical article-scraper implementation. Called via SSH from n8n workflows. Extracts article text from source URLs, handles paywall detection, JavaScript fallbacks, and cleanup.
- **`agency_search/`** — Agency + entity lookup helpers.

Ground truth for scraper behavior is here, not in n8n Code nodes. Code nodes call these via SSH.

## Working principles

1. **Read the current implementation before editing.** Scrapers have accumulated edge cases (Cloudflare-blocked sources like Space Daily, dynamic-JS content requiring browserless, per-source hostname routing). Don't remove a case just because it looks odd — read the commit that added it.
2. **Preserve return shape.** The scraper's output structure is consumed by n8n Code nodes. Adding fields is safe; renaming/removing them breaks callers silently.
3. **Test with a live URL** before committing. `python article_scraper/main.py <url>` from your local machine works for HTTP paths; SSH-only paths need to run on the VPS.
4. **Update the audit results.** Every article-scraper change should be validated against the source-coverage matrix — the overnight audit at `[project_tcs_scraper_overnight_fixes]` memory documents the source-quality tiers.
5. **Update docs.** If you added support for a new source or changed routing behavior, update `tcs-docs/docs/workflows/` for the workflows that use it, and consider whether the source needs a note in `reference_tcs_source_scraping_patterns` memory.

## Common failure modes

- **Cloudflare cookie-wall / SPA JS** — first choice: CRW self-hosted at `http://127.0.0.1:3010/v1/scrape` (deployed 2026-08-08, see `tcs-docs/docs/scrapers.md`). Handles Space Daily, SpaceX, Starlink cleanly. Historically Browserless was used for these — the migration to CRW is in [tcs-workflows#38](https://github.com/The-Canadian-Space/tcs-workflows/issues/38).
- **Cloudflare Turnstile / Vercel Security Checkpoint** — no self-hosted tool bypasses these in 2026. Rocket Lab (Cloudflare UAM) → ScrapingBee (live as of 2026-08-09); Blue Origin (Vercel) → ScraperAPI (staying put).
- **Paywall detection** — heuristic-based; false positives happen. Log them; don't crash.

## How to verify (before flagging In QA or closing)

- **Run it locally.** Whether it's a Python utility or an n8n code node — execute against real (or realistic) input, eyeball the output.
- **For n8n code nodes:** dry-run the node in the n8n Editor with sample input. Check for missing `pairedItem`, wrong data structure, or silent errors that don't propagate.
- **Check the cost side.** If the tool calls an LLM API, note the tokens spent on the test run. Extreme spikes need a comment before closing.
- **Read the log/output for warnings** even when it "worked" — silent warnings often become bugs later.
- **Reversibility.** If the tool writes to WordPress / GitHub / social media, verify you can undo (or that you're running against dev, not prod).

## Related docs

- [Docs site](https://docs.thecanadian.space/)
- Top-level [AGENTS.md](../AGENTS.md) for env access
