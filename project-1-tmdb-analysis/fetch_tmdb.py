"""
TMDB Movie Data - Extraction step (reconstructed, October 2026)

The original script that pulled tmdb_popular_movies.csv (April 2026) was never committed to
this repo. This file re-creates that step so the pipeline is complete and repeatable:
it calls TMDB's "popular movies" endpoint page by page and writes the same six columns that
clean_tmdb.py expects.

Note: running it today pulls TODAY's popular list, so the numbers will differ from the
April 2026 snapshot that the analysis and report are based on. The April CSV stays as the
source of record; this script documents how it was produced and lets anyone refresh it.

Setup:
  1. Create a free account at themoviedb.org -> Settings -> API -> request an API key.
  2. In Terminal:   export TMDB_API_KEY="your-key-here"      (never paste the key into code)
  3. Run:           python3 fetch_tmdb.py

Writes: tmdb_popular_movies_<YYYYMMDD>.csv  (title, release_date, popularity, rating, votes, year)
"""

import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date

API_KEY = os.environ.get("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3/movie/popular"
PAGES = 250            # 20 films per page -> 5,000 rows (TMDB allows up to page 500)
PAUSE_SECONDS = 0.1    # be polite to the API


def get_page(page):
    query = urllib.parse.urlencode({"api_key": API_KEY, "language": "en-US", "page": page})
    with urllib.request.urlopen(f"{BASE}?{query}", timeout=30) as resp:
        return json.load(resp)


def main(fetch=get_page):
    if fetch is get_page and not API_KEY:
        raise SystemExit("Set TMDB_API_KEY first (see the instructions at the top of this file).")

    rows, seen_ids, repeats = [], set(), 0
    for page in range(1, PAGES + 1):
        for m in fetch(page).get("results", []):
            # The popular list re-ranks while we page through it, so a film can appear on two
            # pages. Count those repeats here; clean_tmdb.py removes them later.
            if m["id"] in seen_ids:
                repeats += 1
            seen_ids.add(m["id"])
            release = (m.get("release_date") or "").strip()
            rows.append({
                "title": m.get("title", ""),
                "release_date": release,
                "popularity": m.get("popularity", 0),
                "rating": m.get("vote_average", 0),
                "votes": m.get("vote_count", 0),
                "year": release[:4] if len(release) >= 4 else "",
            })
        if page % 25 == 0:
            print(f"  page {page}/{PAGES}: {len(rows):,} rows so far")
        time.sleep(PAUSE_SECONDS if fetch is get_page else 0)

    out = f"tmdb_popular_movies_{date.today():%Y%m%d}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "release_date", "popularity", "rating", "votes", "year"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows):,} rows to {out}")
    print(f"Films returned more than once while paging: {repeats:,}")
    if repeats:
        print("  -> the list re-ranked mid-pull; clean_tmdb.py's de-duplication step removes these")
    return out


if __name__ == "__main__":
    main()
