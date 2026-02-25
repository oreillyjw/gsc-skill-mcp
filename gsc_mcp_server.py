#!/usr/bin/env python3
"""
MCP server wrapping the GSC query tool for Claude Desktop.
"""

import os
import sys
import subprocess
from mcp.server.fastmcp import FastMCP

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GSC_SCRIPT = os.path.join(SCRIPT_DIR, "gsc_query.py")
PYTHON = sys.executable

mcp = FastMCP("gsc-skill-mcp")


def run_gsc(args: list[str]) -> str:
    """Run gsc_query.py with the given arguments and return output."""
    result = subprocess.run(
        [PYTHON, GSC_SCRIPT] + args,
        capture_output=True, text=True, timeout=60,
        env={**os.environ},
    )
    if result.returncode != 0:
        return f"Error: {result.stderr.strip()}"
    return result.stdout.strip()


@mcp.tool()
def gsc_properties() -> str:
    """List all Search Console properties the service account can access."""
    return run_gsc(["--report", "properties"])


@mcp.tool()
def gsc_search(days: int = 28, limit: int = 20, dimensions: str = "query", site_url: str = "") -> str:
    """Top search queries with clicks, impressions, CTR, and position."""
    args = ["--report", "search", "--days", str(days), "--limit", str(limit), "--dimensions", dimensions]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_pages(days: int = 28, limit: int = 20, site_url: str = "") -> str:
    """Top pages by clicks with impressions, CTR, and position."""
    args = ["--report", "pages", "--days", str(days), "--limit", str(limit)]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_performance(days: int = 28, site_url: str = "") -> str:
    """Performance overview with totals and daily trend."""
    args = ["--report", "performance", "--days", str(days)]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_page_queries(page_url: str, days: int = 28, limit: int = 20, site_url: str = "") -> str:
    """Queries driving traffic to a specific page URL."""
    args = ["--report", "page-queries", "--page-url", page_url, "--days", str(days), "--limit", str(limit)]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_compare(p1_start: str, p1_end: str, p2_start: str, p2_end: str, dimensions: str = "query", limit: int = 20, site_url: str = "") -> str:
    """Compare search performance between two time periods (dates as YYYY-MM-DD)."""
    args = [
        "--report", "compare",
        "--p1-start", p1_start, "--p1-end", p1_end,
        "--p2-start", p2_start, "--p2-end", p2_end,
        "--dimensions", dimensions, "--limit", str(limit),
    ]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_inspect(page_url: str, site_url: str = "") -> str:
    """URL inspection: indexing status, crawl info, canonical, rich results."""
    args = ["--report", "inspect", "--page-url", page_url]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_sitemaps(site_url: str = "") -> str:
    """List submitted sitemaps with status, URL count, and errors."""
    args = ["--report", "sitemaps"]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


@mcp.tool()
def gsc_indexing(urls: str, site_url: str = "") -> str:
    """Batch check indexing status for multiple URLs (comma-separated, max 10)."""
    args = ["--report", "indexing", "--urls", urls]
    if site_url:
        args += ["--site-url", site_url]
    return run_gsc(args)


if __name__ == "__main__":
    mcp.run()
