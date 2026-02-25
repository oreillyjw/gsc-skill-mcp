---
name: gsc-skill-mcp
description: Query Google Search Console data. Use when the user asks about search rankings, impressions, clicks, CTR, indexed pages, sitemaps, URL inspection, or SEO performance. Trigger on keywords like "search console", "GSC", "rankings", "impressions", "clicks", "CTR", "indexed", "sitemaps", "SEO", "search queries", "position", "indexing".
---

# Google Search Console Skill

Query GSC property data using the Search Console API with a service account.

## Setup

### 1. Environment Variables

Set these before using the skill:

| Variable | Required | Description |
|----------|----------|-------------|
| `GSC_CREDENTIALS_PATH` | Yes | Absolute path to your Google service account JSON key file |
| `GSC_SITE_URL` | No | Default GSC property URL (can be overridden per-query with `--site-url`) |

### 2. Python Virtual Environment

These skills require a Python venv with their dependencies installed. Set `SKILLS_PYTHON` to the venv's Python binary:

```bash
# Create a venv (or use an existing one)
python3 -m venv ~/.claude/venv

# Install dependencies
~/.claude/venv/bin/pip install -r PATH_TO_SKILL/requirements.txt
```

Then add to your Claude Code settings:

```json
{
  "env": {
    "SKILLS_PYTHON": "/path/to/your/venv/bin/python3"
  }
}
```

### 3. Service Account Permissions

The service account must be added as a **user** in Google Search Console for each property you want to query. Add it via GSC Settings > Users and permissions using the service account email.

### 4. Multi-Domain Usage

To query different properties, either:
- Set `GSC_SITE_URL` to your most-used property and override with `--site-url` as needed
- Use `--report properties` to list all properties the service account has access to

## How to Use

Run the query script using the venv Python:

```bash
$SKILLS_PYTHON PATH_TO_SKILL/gsc_query.py --report <report_type> [options]
```

## Available Reports

### 1. `properties` — List all GSC properties
```bash
python gsc_query.py --report properties
```
Returns: site URLs and permission levels. Useful for discovering available properties.

### 2. `search` — Top search queries
```bash
python gsc_query.py --report search --days 28 --limit 20
python gsc_query.py --report search --dimensions "query,page" --limit 10
```
Returns: queries, clicks, impressions, CTR, position.

### 3. `pages` — Top pages by clicks
```bash
python gsc_query.py --report pages --days 28 --limit 20
```
Returns: page URLs, clicks, impressions, CTR, position.

### 4. `performance` — Performance overview with daily trend
```bash
python gsc_query.py --report performance --days 28
```
Returns: totals (clicks, impressions, CTR, position) + daily breakdown.

### 5. `page-queries` — Queries for a specific page
```bash
python gsc_query.py --report page-queries --page-url "https://example.com/blog" --days 28
```
Returns: which queries drive traffic to a specific page.

### 6. `compare` — Compare two time periods
```bash
python gsc_query.py --report compare --p1-start 2026-01-01 --p1-end 2026-01-31 --p2-start 2026-02-01 --p2-end 2026-02-28
```
Returns: side-by-side clicks, position changes between periods.

### 7. `inspect` — URL inspection (indexing status)
```bash
python gsc_query.py --report inspect --page-url "https://example.com/about"
```
Returns: indexing verdict, coverage, crawl status, canonical, rich results.

### 8. `sitemaps` — List submitted sitemaps
```bash
python gsc_query.py --report sitemaps
```
Returns: sitemap paths, last downloaded, type, URL count, errors.

### 9. `indexing` — Batch check indexing issues
```bash
python gsc_query.py --report indexing --urls "https://example.com/,https://example.com/about,https://example.com/blog"
```
Returns: indexed/not-indexed summary, robots blocked, fetch issues.

## Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `--site-url` | `$GSC_SITE_URL` | GSC property URL (overrides env var) |
| `--days` | `28` | Lookback period in days |
| `--limit` | `20` | Max rows returned |
| `--start` | — | Explicit start date (YYYY-MM-DD), overrides --days |
| `--end` | — | Explicit end date (YYYY-MM-DD), defaults to today |
| `--output` | `table` | Output format: `table`, `json`, or `csv` |
| `--dimensions` | `query` | Dimensions for search/compare (query, page, device, country, date) |
| `--page-url` | — | Page URL for page-queries and inspect reports |
| `--urls` | — | Comma-separated URLs for indexing report (max 10) |

## GSC Dimension Reference

**Dimensions**: query, page, device, country, date

**Site URL formats**:
- Domain property: `sc-domain:example.com`
- URL prefix: `https://example.com/`
