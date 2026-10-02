"""
TMDB Movie Data Cleaning + Metrics
Produces: tmdb_clean.csv ready for Tableau dashboards

Business Questions covered:
  Q1 - Popularity vs Rating (scatter, quadrants, correlation)
  Q2 - Catalog longevity (pre-2010 evergreen titles)
  Q3 - Upcoming 2026+ pre-release buzz
  Q4 - Rating trend over time (2018-2026)
  Q5 - Hidden gems (high-rated, low-popularity)
"""

import csv
import math
import statistics
from collections import defaultdict

from pathlib import Path
HERE   = Path(__file__).resolve().parent
INPUT  = HERE / "tmdb_popular_movies.csv"
OUTPUT = HERE / "tmdb_clean.csv"

# ── 1. LOAD ──────────────────────────────────────────────────────────────────
with open(INPUT, newline="", encoding="utf-8") as f:
    raw = list(csv.DictReader(f))

print(f"Loaded {len(raw)} rows")

# ── 2. CAST TYPES ─────────────────────────────────────────────────────────────
def safe_float(v, default=None):
    try:    return float(v)
    except: return default

def safe_int(v, default=None):
    try:    return int(v)
    except: return default

for r in raw:
    r["popularity"]   = safe_float(r["popularity"], 0.0)
    r["rating"]       = safe_float(r["rating"],     0.0)
    r["votes"]        = safe_int(r["votes"],         0)
    r["year"]         = safe_int(r["year"],          None)
    r["release_date"] = r["release_date"].strip() or None

# ── 3. REMOVE EXACT DUPLICATES ────────────────────────────────────────────────
# Key: title + release_date (keeps different films that share a name)
seen = set()
deduped = []
for r in raw:
    key = (r["title"].strip().lower(), r["release_date"])
    if key not in seen:
        seen.add(key)
        deduped.append(r)

removed_dupes = len(raw) - len(deduped)
print(f"Removed {removed_dupes} exact duplicates → {len(deduped)} rows")

# ── 4. DROP ROWS MISSING YEAR ─────────────────────────────────────────────────
clean = [r for r in deduped if r["year"] is not None]
removed_nullyear = len(deduped) - len(clean)
print(f"Dropped {removed_nullyear} rows with missing year → {len(clean)} rows")

# ── 5. CALCULATED FIELDS ─────────────────────────────────────────────────────

# --- 5a. popularity_tier (based on data distribution)
# p50=5.9  p75=9.0  p90=15.2  p95=22.7  p99≈63  >=50: ~70 titles
def popularity_tier(pop):
    if pop >= 50:   return "Viral"
    if pop >= 20:   return "Very High"
    if pop >= 10:   return "High"
    if pop >= 5:    return "Medium"
    return "Low"

# --- 5b. rating_quality
def rating_quality(rating, votes):
    if votes == 0 or rating == 0:
        return "No Rating"
    if rating >= 8.0: return "Excellent"
    if rating >= 7.0: return "Good"
    if rating >= 6.0: return "Average"
    if rating >= 5.0: return "Below Average"
    return "Poor"

# --- 5c. decade
def decade(year):
    if year is None: return None
    d = (year // 10) * 10
    return f"{d}s"

# --- 5d. Reliability flag (Q1, Q4 — filter noise)
def is_reliable(votes):
    return votes >= 50

# --- 5e. Upcoming flag (Q3)
def is_upcoming(year):
    return year is not None and year >= 2026

# --- 5f. Popularity/Rating quadrant (Q1 scatter)
# Uses median popularity of reliable films as dividing line
reliable_films = [r for r in clean if r["votes"] >= 50 and r["rating"] > 0]
reliable_pops  = [r["popularity"] for r in reliable_films]
pop_median     = statistics.median(reliable_pops)
RATING_LINE    = 7.0   # industry "good" threshold

def quadrant(pop, rating, votes):
    if votes < 50 or rating == 0:
        return "Insufficient Data"
    high_pop    = pop >= pop_median
    high_rating = rating >= RATING_LINE
    if high_pop  and high_rating: return "Viral + Quality"
    if high_pop  and not high_rating: return "Viral + Poor"
    if not high_pop and high_rating: return "Hidden Gem"
    return "Obscure"

# --- 5g. Evergreen flag (Q2)
def is_evergreen(year, pop):
    return year is not None and year < 2010 and pop > 20

# --- 5h. Hidden gem flag (Q5)
# rating >= 8.0, votes >= 100, popularity < median of ALL films
all_pops       = [r["popularity"] for r in clean]
overall_median = statistics.median(all_pops)

def is_hidden_gem(rating, votes, pop):
    return rating >= 8.0 and votes >= 100 and pop < overall_median

# --- 5i. Pearson correlation (Q1)
def pearson(xs, ys):
    n = len(xs)
    if n < 2: return None
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx  = math.sqrt(sum((x-mx)**2 for x in xs))
    dy  = math.sqrt(sum((y-my)**2 for y in ys))
    if dx == 0 or dy == 0: return 0
    return num / (dx * dy)

# Correlation on reliable films
corr_pairs = [(r["popularity"], r["rating"]) for r in reliable_films]
corr = pearson([p for p,_ in corr_pairs], [r for _,r in corr_pairs])
print(f"\nPopularity vs Rating (Pearson r, votes≥50): {corr:.4f}")
print(f"  → {len(reliable_films)} reliable films used")
print(f"  → Median popularity (reliable): {pop_median:.2f}")
print(f"  → Overall median popularity:    {overall_median:.2f}")

# Rank (Spearman) correlation: popularity is extremely skewed (a few titles score in the
# hundreds), and Pearson is sensitive to those outliers. Spearman compares rank order instead.
def ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r

spearman = pearson(ranks([p for p,_ in corr_pairs]), ranks([r for _,r in corr_pairs]))
print(f"Popularity vs Rating (Spearman rank, votes≥50): {spearman:.4f}")

# ── 6. APPLY ALL FIELDS ───────────────────────────────────────────────────────
for r in clean:
    r["popularity_tier"]  = popularity_tier(r["popularity"])
    r["rating_quality"]   = rating_quality(r["rating"], r["votes"])
    r["decade"]           = decade(r["year"])
    r["is_reliable"]      = is_reliable(r["votes"])
    r["is_upcoming"]      = is_upcoming(r["year"])
    r["is_evergreen"]     = is_evergreen(r["year"], r["popularity"])
    r["is_hidden_gem"]    = is_hidden_gem(r["rating"], r["votes"], r["popularity"])
    r["quadrant"]         = quadrant(r["popularity"], r["rating"], r["votes"])
    r["pop_vs_rating_corr"] = round(corr, 4)  # stored as constant for Tableau reference

# ── 7. PRINT SUMMARY STATS ───────────────────────────────────────────────────
print("\n── DATASET SUMMARY ─────────────────────────────────────────────")
print(f"Total clean rows: {len(clean)}")

from collections import Counter
tier_counts = Counter(r["popularity_tier"] for r in clean)
print("\nPopularity tiers:")
for tier in ["Viral","Very High","High","Medium","Low"]:
    print(f"  {tier}: {tier_counts[tier]}")

qual_counts = Counter(r["rating_quality"] for r in clean)
print("\nRating quality:")
for q in ["Excellent","Good","Average","Below Average","Poor","No Rating"]:
    print(f"  {q}: {qual_counts[q]}")

quad_counts = Counter(r["quadrant"] for r in clean)
print("\nQ1 Quadrants (reliable films only):")
for q in ["Viral + Quality","Viral + Poor","Hidden Gem","Obscure","Insufficient Data"]:
    print(f"  {q}: {quad_counts[q]}")

upcoming   = sum(1 for r in clean if r["is_upcoming"])
evergreen  = sum(1 for r in clean if r["is_evergreen"])
hidden     = sum(1 for r in clean if r["is_hidden_gem"])
print(f"\nQ3 Upcoming (2026+):      {upcoming}")
print(f"Q2 Evergreen (<2010, pop>20): {evergreen}")
print(f"Q5 Hidden gems:           {hidden}")

# Q4 – avg rating + popularity by year (2018–2026)
print("\nQ4 – Avg rating + avg popularity by year (votes≥50):")
yearly = defaultdict(list)
for r in clean:
    if r["year"] and 2018 <= r["year"] <= 2026 and r["votes"] >= 50:
        yearly[r["year"]].append(r)
for yr in sorted(yearly):
    entries = yearly[yr]
    avg_r = statistics.mean(e["rating"] for e in entries)
    avg_p = statistics.mean(e["popularity"] for e in entries)
    print(f"  {yr}: avg_rating={avg_r:.2f}  avg_popularity={avg_p:.2f}  n={len(entries)}")

# ── 8. WRITE OUTPUT CSV ───────────────────────────────────────────────────────
fieldnames = [
    "title", "release_date", "year", "decade",
    "popularity", "popularity_tier",
    "rating", "rating_quality",
    "votes", "is_reliable",
    "is_upcoming", "is_evergreen", "is_hidden_gem",
    "quadrant", "pop_vs_rating_corr"
]

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(clean)

print(f"\nExported → {OUTPUT}")
print(f"Rows: {len(clean)}  |  Columns: {len(fieldnames)}")
