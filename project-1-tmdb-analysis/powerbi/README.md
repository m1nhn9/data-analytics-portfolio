# TMDB Movie Insights: Power BI dashboard

![TMDB Movie Insights dashboard](dashboard.png)

A Power BI Project (PBIP) on the cleaned TMDB data: a one-page catalogue dashboard for day-to-day use, detail pages, and an Insights page. It uses TMDB's brand colours through a custom report theme.

## Pages

| Page | What it shows |
|---|---|
| Dashboard | Header KPIs (titles, average rating, median votes, 2026+ releases, evergreen titles, hidden gems). Filters for decade, release year, popularity tier, segment and rating band. Releases and average rating by year, popularity vs rating (log scale), catalogue mix, top 10 trending titles, an upcoming releases watchlist and a hidden-gem shortlist. |
| Popularity vs Rating | Scatter of reliably rated films, popularity on a log scale, coloured by segment. |
| Evergreen Titles | Evergreen films by release decade. |
| Upcoming Releases | Top 5 upcoming films by popularity. |
| Ratings Over Time | Average rating and median votes by year, 2018–2026, with a vote-count caveat. |
| Hidden Gems | Highly rated, low-popularity films sorted by rating. |
| Insights | Key findings. |

## Open it

1. Open `TMDB-Movie-Insights.pbip` in Power BI Desktop.
2. Go to **Transform data → Edit parameters** and set `DataFolder` to the folder that holds `tmdb_clean.csv` (the `project-1-tmdb-analysis` folder of this repo), ending with a backslash. Then refresh.

## Main measures

| Measure | DAX |
|---|---|
| Films | `COUNTROWS(tmdb_clean)` |
| Avg Rating | `CALCULATE(AVERAGE(rating), is_reliable = TRUE())`: reliably rated films only |
| Median Votes | `MEDIAN(votes)` |
| Hidden Gems / Evergreen Films | `[Films]` filtered on `is_hidden_gem` / `is_evergreen` |
| Top 10 Popularity | Popularity, kept only for the 10 most popular titles in the current filter context |

Expected totals: 4,682 films, 62 hidden gems, 86 evergreen, 192 released in 2026 or later, and a 6.85 average rating across 3,981 reliably rated films. The popularity–rating correlation (Pearson r 0.079, Spearman ρ 0.230) was computed in Python.
