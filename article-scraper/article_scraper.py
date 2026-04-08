#!/usr/bin/env python3
"""
article_scraper.py - Lightweight article scraper for TCS n8n pipeline.

Strategy:
  - Most sites: requests + trafilatura (pure Python, no browser needed)
  - JS-heavy sites (nasaspaceflight.com etc): Jina Reader API (free external service)

Usage:
    python3 article_scraper.py <base64-encoded-json>

Input (base64 decoded):
    JSON array of {"url": "https://...", "title": "..."} objects

Output (stdout):
    JSON array of scraped article objects matching Article Final Prep schema
"""

import sys
import json
import re
import base64
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
import trafilatura
from trafilatura.settings import use_config


# --- Configuration -----------------------------------------------------------

REQUEST_TIMEOUT = 20  # seconds
JINA_TIMEOUT = 30     # Jina Reader is an external service, can be slower

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Sites that need JS rendering — routed through Jina Reader (no local browser needed)
JINA_SITES = {
    "nasaspaceflight.com",
    "spacepolicyonline.com",
}

# Domain → human-readable source name
SOURCE_MAP = {
    "arstechnica.com": "Ars Technica",
    "esa.int": "ESA",
    "europeanspaceflight.com": "European Spaceflight",
    "science.nasa.gov": "NASA Science",
    "blogs.nasa.gov": "NASA",
    "nasa.gov": "NASA",
    "nasaspaceflight.com": "NASASpaceFlight.com",
    "spacescout.info": "Space Scout",
    "spacedaily.com": "Space Daily",
    "spacenews.com": "SpaceNews",
    "spacepolicyonline.com": "SpacePolicyOnline.com",
    "spaceflightnow.com": "Spaceflight Now",
    "planetary.org": "The Planetary Society",
    "ulalaunch.com": "United Launch Alliance",
    "spaceq.ca": "SpaceQ",
    "spacewar.com": "SpaceWar",
    "thecanadian.space": "The Canadian Space",
}

# Tune trafilatura: no timeout, favour recall over precision
_traf_config = use_config()
_traf_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")


# --- Helpers -----------------------------------------------------------------

def get_domain(url):
    return urlparse(url).netloc.lower().replace("www.", "")


def get_source(url):
    domain = get_domain(url)
    for key, name in SOURCE_MAP.items():
        if key in domain:
            return name
    return domain


def is_jina_site(url):
    domain = get_domain(url)
    return any(s in domain for s in JINA_SITES)


def extract_images_from_html(html):
    images = []
    # og:image is the best thumbnail candidate
    og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if not og:
        og = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
    if og:
        images.append(og.group(1))
    for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I):
        if src.startswith('http') and src not in images:
            clean = src.split('?')[0].lower()
            if any(ext in clean for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                if not any(skip in src.lower() for skip in ['icon', 'logo', 'avatar', 'gravatar', 'pixel', 'badge']):
                    images.append(src)
    seen = set()
    result = []
    for img in images:
        key = img.split('?')[0]
        if key not in seen:
            seen.add(key)
            result.append(img)
    return result[:10]


def extract_images_from_markdown(md):
    pattern = r'!\[.*?\]\((https?://[^\)\s]+)\)'
    images = re.findall(pattern, md or "")
    seen = set()
    result = []
    for img in images:
        clean = img.split('?')[0]
        if clean in seen:
            continue
        if any(skip in img.lower() for skip in ['gravatar', 'avatar', 'icon', 'logo', 'badge', 'pixel']):
            continue
        if not any(ext in clean.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            continue
        seen.add(clean)
        result.append(img)
    return result[:10]


def parse_og_date(html):
    patterns = [
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"publishedTime"\s*:\s*"([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            raw = m.group(1)
            try:
                dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                return dt.strftime("%B %-d, %Y")
            except Exception:
                return raw
    return ""


def parse_jina_date(md):
    m = re.search(r'(?:Published|Date)[:\s]+([A-Z][a-z]+ \d{1,2},?\s+\d{4})', md or "")
    return m.group(1) if m else ""


def word_count_of(text):
    return len(text.split()) if text and text.strip() else 0


# --- Scrapers ----------------------------------------------------------------

def scrape_with_trafilatura(url, title_hint):
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    html = resp.text

    content = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
        config=_traf_config,
    )

    meta = trafilatura.extract_metadata(html, default_url=url)
    title = (meta.title if meta and meta.title else "") or title_hint
    date_str = (meta.date if meta and meta.date else "") or parse_og_date(html)
    if date_str:
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            date_str = dt.strftime("%B %-d, %Y")
        except Exception:
            pass

    images = extract_images_from_html(html)
    wc = word_count_of(content or "")

    return {
        "title": title,
        "url": url,
        "thumbnail": images[0] if images else "",
        "images": images,
        "source": get_source(url),
        "content": content or "",
        "word_count": wc,
        "character_count": len(content) if content else 0,
        "has_content": wc > 50,
        "date": date_str,
    }


def scrape_with_jina(url, title_hint):
    jina_url = "https://r.jina.ai/" + url
    resp = requests.get(
        jina_url,
        headers={**HEADERS, "Accept": "text/markdown"},
        timeout=JINA_TIMEOUT,
    )
    resp.raise_for_status()
    md = resp.text

    title_match = re.search(r'^Title:\s*(.+)$', md, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else title_hint

    date_str = parse_jina_date(md)
    images = extract_images_from_markdown(md)

    # Strip Jina header metadata lines before storing content
    content = re.sub(r'^(Title|URL|Published|Date|Author|Source):.*$', '', md, flags=re.MULTILINE).strip()
    wc = word_count_of(content)

    return {
        "title": title,
        "url": url,
        "thumbnail": images[0] if images else "",
        "images": images,
        "source": get_source(url),
        "content": content,
        "word_count": wc,
        "character_count": len(content),
        "has_content": wc > 50,
        "date": date_str,
    }


# --- Main --------------------------------------------------------------------

def scrape_article(article):
    url = article.get("url", "").strip()
    title_hint = article.get("title", "").strip()

    if not url:
        return {"error": "No URL provided", "has_content": False, "title": title_hint, "url": url}

    try:
        if is_jina_site(url):
            return scrape_with_jina(url, title_hint)
        else:
            return scrape_with_trafilatura(url, title_hint)
    except Exception as e:
        return {
            "title": title_hint,
            "url": url,
            "thumbnail": "",
            "images": [],
            "source": get_source(url),
            "content": "",
            "word_count": 0,
            "character_count": 0,
            "has_content": False,
            "date": "",
            "error": str(e),
        }


def scrape_all(articles):
    results = []
    for i, article in enumerate(articles):
        if i > 0:
            time.sleep(0.5)  # gentle rate limiting between requests
        results.append(scrape_article(article))
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No input provided. Pass base64-encoded JSON array as first argument."}))
        sys.exit(1)

    try:
        raw_input = base64.b64decode(sys.argv[1]).decode('utf-8')
        articles = json.loads(raw_input)
    except Exception as e:
        print(json.dumps({"error": f"Failed to decode input: {str(e))"}))
        sys.exit(1)

    if not isinstance(articles, list):
        print(json.dumps({"error": "Input must be a JSON array of article objects."}))
        sys.exit(1)

    scraped = scrape_all(articles)
    print(json.dumps(scraped, ensure_ascii=False))
