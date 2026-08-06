# X Scraper

Node.js scraper for X (Twitter) feeds, invoked over SSH from the V3 blog
workflows. Replaces the old paid `twitterapi.io` integration.

## Where it runs

**Not this repo.** This folder mirrors what actually runs on the OVH VPS at:

```
/opt/tcs/scripts/x-scraper/
├── x_scraper.js           # main entry point
├── package.json           # dependencies (rettiwt-api only)
├── package-lock.json
├── node_modules/
└── .rettiwt-auth          # chmod 600, holds the Rettiwt apiKey
```

Sync this repo copy after any prod edit.

## How it's called

The Daily Broadcast V3 workflow (and any V3 workflow that pulls X posts) hits
it via an n8n SSH node with:

```
node /opt/tcs/scripts/x-scraper/x_scraper.js <BASE64_JSON>
```

Input JSON shape:

```json
{
  "feeds": [
    {
      "username":     "elonmusk",
      "display_name": "Elon Musk",
      "key":          "elon_musk",
      "any_words":    ["Starship","Falcon"],
      "exclude_retweets": true
    }
  ],
  "since_days":   7,
  "max_per_feed": 200,
  "run_id":       "568"
}
```

Two output modes matching `article_scraper.py`'s pattern:

- **INLINE** (no `run_id`): full markdown bodies inline in stdout JSON
- **FILE** (with `run_id`): per-feed `tweets-<key>.md` under
  `/opt/tcs/n8n/local_files/scraper-runs/<run_id>/`, slim `index.json` on
  stdout

## Stack

- **[Rettiwt-API](https://github.com/Rishikant181/Rettiwt-API)** 7.1.2 —
  self-hosted Node library that speaks X's undocumented internal API using an
  authenticated session (no paid tier, no rate-limit quota to buy)

That's the entire dependency graph. `package.json`:

```json
{
  "name": "tcs-x-scraper",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "description": "TCS X (Twitter) scraper via Rettiwt-API. Replaces twitterapi.io.",
  "dependencies": {
    "rettiwt-api": "^7.1.2"
  }
}
```

## Auth

The `.rettiwt-auth` file (chmod 600, not committed) holds the Rettiwt session
apiKey. Regenerate via `rettiwt auth login` on the VPS if X invalidates the
session. A `rettiwt_probe.js` script sits alongside `x_scraper.js` for
one-shot connectivity checks.

## Pagination

X caps user-timeline queries at 20 tweets per page. The scraper pages until
one of: empty page, older-than-window, or `max_per_feed` cap. Default window
is 7 days rolling.

## Editing

Edit prod directly on the VPS, test with a manual run, then `cat` back into
this repo. `package.json` diffs should be treated the same way — bump on the
VPS, sync back.
