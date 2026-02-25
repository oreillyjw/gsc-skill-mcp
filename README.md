# Google Search Console — Claude Code Skill + MCP Server

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) and [MCP server](https://modelcontextprotocol.io/) that lets Claude query your Google Search Console data using natural language. Works with Claude Code (skill mode) and Claude Desktop / any MCP client (server mode).

## Inspiration

This skill was inspired by Amin Foroutan's [mcp-gsc](https://github.com/AminForou/mcp-gsc) project, an MCP server for querying Google Search Console data. We adapted the approach into a Claude Code skill using a direct Python query script.

## Prerequisites

- Python 3.9+
- A Google Cloud project with the **Search Console API** enabled
- A service account with a JSON key file
- The service account added as a **user** in Google Search Console for each property you want to query

## Installation

### 1. Copy the skill into your Claude Code skills directory

```bash
# Global (all projects)
cp -r gsc-skill-mcp ~/.claude/skills/gsc-skill-mcp

# Or project-level (single repo)
cp -r gsc-skill-mcp .claude/skills/gsc-skill-mcp
```

### 2. Set up a Python virtual environment

Create a venv (or use an existing one) and install dependencies:

```bash
# Create the venv
python3 -m venv ~/.claude/venv

# Install dependencies
~/.claude/venv/bin/pip install -r ~/.claude/skills/gsc-skill-mcp/requirements.txt
```

This installs:

- `google-api-python-client` — Google API client
- `google-auth` — Google authentication library

### 3. Configure environment variables

Add to `~/.claude/settings.json` (global) or `.claude/settings.local.json` (project-level):

```json
{
  "env": {
    "SKILLS_PYTHON": "/path/to/your/venv/bin/python3",
    "GSC_CREDENTIALS_PATH": "/absolute/path/to/service-account.json",
    "GSC_SITE_URL": "sc-domain:example.com"
  }
}
```

- `SKILLS_PYTHON` — path to the venv's Python binary. Claude uses this to run the query scripts.
- `GSC_SITE_URL` — optional if you always pass `--site-url` or only use the `properties` report.

**Site URL formats:**

- Domain property: `sc-domain:example.com`
- URL prefix property: `https://example.com/`

## Verify It Works

Run these commands to confirm the skill is set up correctly. Each test builds on the previous one. Replace the venv path below with your actual path.

### Test 1: Check dependencies are installed

```bash
~/.claude/venv/bin/python3 -c "from googleapiclient.discovery import build; print('OK: google-api-python-client')"
~/.claude/venv/bin/python3 -c "from google.oauth2 import service_account; print('OK: google-auth')"
```

Both should print `OK`. If not, re-run the pip install step.

### Test 2: Check credentials file exists

```bash
~/.claude/venv/bin/python3 -c "
import os, json
path = os.environ.get('GSC_CREDENTIALS_PATH', '')
assert path, 'GSC_CREDENTIALS_PATH not set'
assert os.path.exists(path), f'File not found: {path}'
with open(path) as f:
    data = json.load(f)
print(f'OK: service account = {data.get(\"client_email\", \"UNKNOWN\")}')
"
```

Should print the service account email. If it says `not set`, check your `settings.json` env block.

### Test 3: List accessible properties (no site URL needed)

```bash
~/.claude/venv/bin/python3 ~/.claude/skills/gsc-skill-mcp/gsc_query.py --report properties
```

Should return a table of site URLs and permission levels. If you see `No Search Console properties found`, the service account doesn't have access — add it via GSC Settings > Users and permissions using the service account email from Test 2.

### Test 4: Pull a real report

```bash
~/.claude/venv/bin/python3 ~/.claude/skills/gsc-skill-mcp/gsc_query.py --report search --days 28 --limit 10
```

Should return top search queries with clicks, impressions, CTR, and position. If you get a permissions error, confirm the service account has access to the property.

### Test 5: Verify multi-domain support

```bash
# Query a different property without changing env vars
~/.claude/venv/bin/python3 ~/.claude/skills/gsc-skill-mcp/gsc_query.py --report search --site-url "sc-domain:other-site.com" --days 28
```

### Test 6: URL inspection (optional, requires URL Inspection API access)

```bash
~/.claude/venv/bin/python3 ~/.claude/skills/gsc-skill-mcp/gsc_query.py --report inspect --page-url "https://example.com/"
```

Should return indexing verdict, coverage state, and crawl info.

## Usage with Claude Code

Once installed, just ask Claude naturally:

- "What are my top search queries this month?"
- "Show me the top pages by clicks in the last 28 days"
- "Is my homepage indexed?"
- "Compare search performance: January vs February"
- "List all my Search Console properties"
- "What queries drive traffic to /blog?"
- "Check indexing status for these URLs: /about, /pricing, /blog"
- "Show me sitemaps for sc-domain:other-site.com"

## Available Reports

| Report | Description |
|--------|-------------|
| `properties` | List all GSC properties the service account can access |
| `search` | Top search queries (clicks, impressions, CTR, position) |
| `pages` | Top pages by clicks |
| `performance` | Performance overview with totals + daily trend |
| `page-queries` | Queries driving traffic to a specific page |
| `compare` | Side-by-side comparison of two time periods |
| `inspect` | URL inspection (indexing status, crawl info, rich results) |
| `sitemaps` | List submitted sitemaps |
| `indexing` | Batch check indexing issues for multiple URLs (max 10) |

## Multi-Domain Usage

Set a default site via env var, override per-query:

```bash
# Uses GSC_SITE_URL from env
$SKILLS_PYTHON gsc_query.py --report search

# Override for a different property
$SKILLS_PYTHON gsc_query.py --report search --site-url "sc-domain:other-site.com"
```

Or skip setting a default entirely and always pass `--site-url`.

## Output Formats

All reports support `--output table` (default), `--output json`, and `--output csv`.

## MCP Server Setup

The MCP server (`gsc_mcp_server.py`) wraps the same query logic as individual tools, so any MCP-compatible client (Claude Desktop, Cursor, etc.) can call them directly.

### 1. Install the additional dependency

```bash
~/.claude/venv/bin/pip install "mcp>=1.0.0"
```

This is already included in `requirements.txt`.

### 2. Configure your MCP client

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "gsc-skill-mcp": {
      "command": "/path/to/your/venv/bin/python3",
      "args": ["/path/to/gsc-skill-mcp/gsc_mcp_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/absolute/path/to/service-account.json",
        "GSC_SITE_URL": "sc-domain:example.com"
      }
    }
  }
}
```

**Claude Code** — add to `~/.claude/settings.json` or `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "gsc-skill-mcp": {
      "command": "/path/to/your/venv/bin/python3",
      "args": ["/path/to/gsc-skill-mcp/gsc_mcp_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/absolute/path/to/service-account.json",
        "GSC_SITE_URL": "sc-domain:example.com"
      }
    }
  }
}
```

### 3. Verify the server starts

```bash
~/.claude/venv/bin/python3 /path/to/gsc-skill-mcp/gsc_mcp_server.py
```

The server runs over stdio — you should see no output (it's waiting for MCP messages). Press `Ctrl+C` to stop.

### Available MCP Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `gsc_properties` | — | List all Search Console properties |
| `gsc_search` | `days`, `limit`, `dimensions`, `site_url` | Top search queries with clicks, impressions, CTR, position |
| `gsc_pages` | `days`, `limit`, `site_url` | Top pages by clicks |
| `gsc_performance` | `days`, `site_url` | Performance overview with totals + daily trend |
| `gsc_page_queries` | `page_url`, `days`, `limit`, `site_url` | Queries driving traffic to a specific page |
| `gsc_compare` | `p1_start`, `p1_end`, `p2_start`, `p2_end`, `dimensions`, `limit`, `site_url` | Compare two time periods |
| `gsc_inspect` | `page_url`, `site_url` | URL inspection: indexing status, crawl info, rich results |
| `gsc_sitemaps` | `site_url` | List submitted sitemaps |
| `gsc_indexing` | `urls`, `site_url` | Batch check indexing for multiple URLs (comma-separated, max 10) |

All parameters are optional unless noted — defaults: `days=28`, `limit=20`.

## File Structure

```text
gsc-skill-mcp/
├── SKILL.md           # Claude Code skill definition (auto-loaded by Claude)
├── README.md          # This file
├── gsc_query.py       # Query script (CLI)
├── gsc_mcp_server.py  # MCP server (wraps gsc_query as tools)
└── requirements.txt   # Python dependencies
```

## License

MIT
