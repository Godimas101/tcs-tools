# Article Scraper

Single-script article extractor invoked over SSH from the V3 blog workflows.
Replaces the older 32-node per-source scrape/cleanup pipeline.

## Where it runs

**Not this repo.** The version in this folder is a mirror of what actually runs
in production. The live copy lives on the OVH VPS at:

```
/opt/tcs/scripts/article_scraper.py
/opt/tcs/scripts/lib_index.py
/opt/tcs/scripts/crawl4ai-env/       # Python venv with Crawl4AI + Playwright
```

Sync this repo copy after any prod edit, so devs can grep the source without
SSH access.

## How it's called

Every V3 blog workflow (Daily Broadcast, NASA Overview, SpaceX Report, Rocket
Lab Roundup, Commercial Space, Bright Blue Origin, Canada From Orbit) invokes
it via an n8n SSH node with:

```
/opt/tcs/scripts/crawl4ai-env/bin/python \
  /opt/tcs/scripts/article_scraper.py <BASE64_JSON> [--run-id=<id>] [--index-prefix=<pref>]
```

Input: base64-encoded JSON array of `{"url", "title"}` objects.

Two output modes:

- **INLINE** (no `--run-id`): full article content emitted on stdout as JSON —
  legacy shape for the prototype workflow.
- **FILE** (with `--run-id`): per-article markdown written under
  `/opt/tcs/n8n/local_files/scraper-runs/<id>/`, with a slim `index.json`
  emitted on stdout. This is what all V3 workflows use — the Write News
  LangChain agent then fetches individual articles on demand via the
  `read_article` tool.

## Stack

- **[Crawl4AI](https://github.com/unclecode/crawl4ai)** 0.8.6 — Playwright-backed
  headless-browser scraper with LLM-ready markdown output
- **Playwright** 1.58.0 (+ `playwright-stealth` 2.0.3) — the browser Crawl4AI
  drives
- **httpx**, **requests**, **beautifulsoup4** — supporting HTTP + parsing libs

The `crawl4ai-env` venv on the VPS is Python 3.12 with the packages above.
Nothing else in this venv — no trafilatura, no Jina Reader.

Separately, some n8n workflows call **paid external services** for pages where
Crawl4AI's self-hosted browser gets caught by anti-bot fingerprinting:
- **[Browserless.io](https://www.browserless.io/)** — SpaceX Report V3 workflow
  hits `chrome.browserless.io/content` for `spacex.com/updates` and
  `starlink.com/updates` (SPA-rendered listings)
- **[ScraperAPI](https://www.scraperapi.com/)** — Bright Blue Origin V3
  workflow hits `api.scraperapi.com` for `blueorigin.com/news`

Those calls happen from n8n HTTP Request nodes, not from `article_scraper.py`.
The scraper itself has no external-service dependencies.

## Per-site config

`SITE_CONFIG` at the top of `article_scraper.py` is a hostname → config dict
covering the ~24 domains we currently ingest from. Each entry can specify:

- `source` — human-readable name for downstream attribution
- `selector` — CSS selector scoping content extraction
- `wait` — extra seconds before extraction (JS-heavy sites)
- `networkidle` — wait for network-idle before extraction
- `strict_scope` — use `target_elements` semantics (prevents overlay stripping)
- `keep_overlays` — disable Crawl4AI's overlay-removal step (breaks Ars, ESA,
  NASA Science, etc. that wrap article images in `<figure>` or `<a>` elements
  the overlay filter classifies as UI)

Sites currently configured: Ars Technica, ESA, European Spaceflight,
NASASpaceflight, Spaceflight Now, SpacePolicyOnline, SpaceNews, Space Daily,
SpaceWar, Space Scout, NASA Science, NASA, Planetary Society, ULA, SpaceQ,
Stoked Space, Firefly Aerospace, Relativity Space, Axiom Space, EIN Presswire,
NordSpace, Maritime Launch Services, Reaction Dynamics, Canada Rocket Company.

## WAF-protected sites (Pattern B)

A handful of sites (CSA `asc-csa.gc.ca` in particular) return
`script_heavy_shell` errors under Crawl4AI's headless browser due to WAF
fingerprinting. Those sites use "Pattern B" in the V3 workflows: a plain n8n
HTTP Request node with browser-like headers, followed by an n8n Code node that
runs regex-based extraction. No external scraping service is involved — it's
just `requests`-equivalent behavior inside n8n itself.

## Editing

Edit prod directly on the VPS, test with a manual run, then `cat` the result
back into this repo so the mirror stays fresh. Rollback backups
(`article_scraper.py.bak.<epoch>`) accumulate in `/opt/tcs/scripts/` on the
VPS but are not synced back here.
