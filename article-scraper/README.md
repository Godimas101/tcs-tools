# 📰 Article Scraper

> **"Fetch the news without breaking the server."**

Lightweight Python article scraper that runs on the TCS droplet via SSH, called from the `Prototype - TCS Python Article Scraper` n8n workflow.

---

## 🧠 How It Works

Takes a base64-encoded JSON array of article URLs, scrapes each one, and returns structured article data as JSON on stdout.

**Two-strategy approach:**
- **Most sites** — `requests` + `trafilatura` (pure Python, no browser, ~30MB RAM)
- **JS-heavy sites** (`nasaspaceflight.com`, `spacepolicyonline.com`) — [Jina Reader API](https://r.jina.ai/) (free external service, handles JS rendering remotely)

No browser. No Playwright. No RAM bomb.

---

## 📥 Input

Passed as a single CLI argument: base64-encoded JSON array.

```json
[
  { "url": "https://spacenews.com/some-article/", "title": "Optional title hint" },
  { "url": "https://nasaspaceflight.com/some-article/", "title": "Optional title hint" }
]
```

---

## 📤 Output

JSON array on stdout, one object per article:

```json
[
  {
    "title": "Article Title",
    "url": "https://...",
    "thumbnail": "https://...image.jpg",
    "images": ["https://...img1.jpg", "https://...img2.jpg"],
    "source": "SpaceNews",
    "content": "Full article text...",
    "word_count": 842,
    "character_count": 4921,
    "has_content": true,
    "date": "April 7, 2026"
  }
]
```

On error, same shape with `has_content: false` and an `error` field.

---

## 🔧 Server Setup

**Location on server:** `/root/n8n-docker-caddy/article_scraper.py`

**Dependencies:**
```bash
pip install trafilatura requests
```

**To deploy a new version**, use the `Tool - SSH Utility` n8n workflow (POST to its webhook with a `base64 -d` deploy command).

---

## 🔗 n8n Integration

| Node | Role |
|---|---|
| `Prepare Scraper Input` | Aggregates upstream items, base64-encodes JSON array |
| `SSH - Article Scraper` | SSHs into droplet, runs `python3 /root/n8n-docker-caddy/article_scraper.py <b64>` |
| `Parse Scraper Output` | Parses stdout JSON, filters `has_content: true`, emits individual items |

---

## 📁 Files

| File | Description |
|---|---|
| `article_scraper.py` | The scraper script — this is what runs on the server |
| `NOTES.md` | Working notes, current status, next steps (gitignored) |
