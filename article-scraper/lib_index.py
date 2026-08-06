"""Shared helper for atomically upserting entries into a run's index.json.

Used by every per-source writer (article_scraper.py, write_events.py,
write_sd_article.py, write_indexed_article.py, append_to_index.py). All
writers share the same flock-based lock file so the read-modify-write
cycle is safe under parallel n8n branches.

Entries are keyed by their `index` field (string or int). Existing entries
with a matching index are replaced, so each writer is idempotent on its
own indices.
"""
import fcntl
import json
import os


def upsert_entries(run_dir, entries):
    """Upsert a list of entries into <run_dir>/index.json.

    Args:
        run_dir: absolute path to the run directory (created if missing)
        entries: iterable of dicts; each must have an 'index' field

    Returns:
        The updated index dict (also written to disk).
    """
    os.makedirs(run_dir, exist_ok=True)
    index_path = os.path.join(run_dir, "index.json")
    lock_path = index_path + ".lock"

    # Touch lock file (we hold an exclusive flock on it for the whole RMW).
    # Lock file is intentionally never removed — keeps things simple, and
    # the whole run dir is rm -rf'd at the end of the workflow anyway.
    with open(lock_path, "a") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            if os.path.exists(index_path):
                try:
                    with open(index_path, "r", encoding="utf-8") as f:
                        index = json.load(f)
                except Exception:
                    index = {}
            else:
                index = {}

            articles = index.get("articles", []) or []
            new_indices = {str(e.get("index")) for e in entries}
            # Drop any prior entry with the same index (true upsert)
            articles = [a for a in articles if str(a.get("index")) not in new_indices]
            articles.extend(entries)

            run_id = os.path.basename(os.path.normpath(run_dir))
            index.update({
                "run_id": index.get("run_id") or run_id,
                "run_dir": run_dir,
                "article_count": len(articles),
                "success_count": sum(1 for a in articles if a.get("has_content")),
                "unknown_count": sum(1 for a in articles if a.get("unknown_site")),
                "articles": articles,
            })

            # Atomic write: temp file + rename to avoid a partial write
            # being visible to a concurrent reader.
            tmp = index_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, index_path)

            return index
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)
