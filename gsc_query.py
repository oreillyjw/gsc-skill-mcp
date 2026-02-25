#!/usr/bin/env python3
"""
Google Search Console query tool.
Queries GSC property data using a service account.
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============================================================
# CONFIGURATION — Set via environment variables:
#   GSC_CREDENTIALS_PATH  - path to service account JSON key
#   GSC_SITE_URL          - default site URL (e.g. sc-domain:example.com)
# ============================================================
GSC_CREDENTIALS_PATH = os.environ.get("GSC_CREDENTIALS_PATH", "")
GSC_SITE_URL = os.environ.get("GSC_SITE_URL", "")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def get_service():
    """Create and return an authorized Search Console service."""
    if not GSC_CREDENTIALS_PATH or not os.path.exists(GSC_CREDENTIALS_PATH):
        print(
            "Error: GSC_CREDENTIALS_PATH not set or file not found.\n"
            "Set the environment variable to your service account JSON key path.",
            file=sys.stderr,
        )
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(
        GSC_CREDENTIALS_PATH, scopes=SCOPES
    )
    return build("searchconsole", "v1", credentials=creds)


def get_site_url(args):
    """Get site URL from args or env var."""
    url = getattr(args, "site_url", None) or GSC_SITE_URL
    if not url:
        print(
            "Error: No site URL provided. Use --site-url or set GSC_SITE_URL env var.",
            file=sys.stderr,
        )
        sys.exit(1)
    return url


def format_table(headers, rows):
    """Format data as an ASCII table."""
    if not rows:
        return "No data found."

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = "|" + "|".join(f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)) + "|"

    lines = [separator, header_row, separator]
    for row in rows:
        line = "|" + "|".join(f" {str(v):<{col_widths[i]}} " for i, v in enumerate(row)) + "|"
        lines.append(line)
    lines.append(separator)
    lines.append(f"\nTotal rows: {len(rows)}")
    return "\n".join(lines)


def format_output(headers, rows, output="table"):
    """Format output in the requested format."""
    if output == "json":
        result = [dict(zip(headers, row)) for row in rows]
        return json.dumps(result, indent=2)
    elif output == "csv":
        lines = [",".join(headers)]
        for row in rows:
            lines.append(",".join(str(v) for v in row))
        return "\n".join(lines)
    else:
        return format_table(headers, rows)


# ============================================================
# Report Functions
# ============================================================


def report_properties(service, args):
    """List all Search Console properties."""
    site_list = service.sites().list().execute()
    sites = site_list.get("siteEntry", [])

    if not sites:
        return "No Search Console properties found."

    headers = ["siteUrl", "permissionLevel"]
    rows = [[s.get("siteUrl", ""), s.get("permissionLevel", "")] for s in sites]
    return format_output(headers, rows, args.output)


def report_search(service, args):
    """Search analytics — top queries."""
    site_url = get_site_url(args)
    end_date = args.end or datetime.now().date().strftime("%Y-%m-%d")
    start_date = args.start or (datetime.now().date() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    dims = [d.strip() for d in args.dimensions.split(",")] if args.dimensions else ["query"]

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dims,
        "rowLimit": args.limit,
    }

    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    rows_data = response.get("rows", [])

    if not rows_data:
        return f"No search data found for {site_url} ({start_date} to {end_date})."

    headers = [d.capitalize() for d in dims] + ["Clicks", "Impressions", "CTR", "Position"]
    rows = []
    for row in rows_data:
        values = [k[:80] for k in row.get("keys", [])]
        values.extend([
            str(row.get("clicks", 0)),
            str(row.get("impressions", 0)),
            f"{row.get('ctr', 0) * 100:.2f}%",
            f"{row.get('position', 0):.1f}",
        ])
        rows.append(values)

    return format_output(headers, rows, args.output)


def report_pages(service, args):
    """Top pages by clicks."""
    site_url = get_site_url(args)
    end_date = args.end or datetime.now().date().strftime("%Y-%m-%d")
    start_date = args.start or (datetime.now().date() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "rowLimit": args.limit,
    }

    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    rows_data = response.get("rows", [])

    if not rows_data:
        return f"No page data found for {site_url} ({start_date} to {end_date})."

    headers = ["Page", "Clicks", "Impressions", "CTR", "Position"]
    rows = []
    for row in rows_data:
        page = row.get("keys", [""])[0][:80]
        rows.append([
            page,
            str(row.get("clicks", 0)),
            str(row.get("impressions", 0)),
            f"{row.get('ctr', 0) * 100:.2f}%",
            f"{row.get('position', 0):.1f}",
        ])

    return format_output(headers, rows, args.output)


def report_performance(service, args):
    """Performance overview with daily trend."""
    site_url = get_site_url(args)
    end_date = args.end or datetime.now().date().strftime("%Y-%m-%d")
    start_date = args.start or (datetime.now().date() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    # Totals
    total_req = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": [],
        "rowLimit": 1,
    }
    total_resp = service.searchanalytics().query(siteUrl=site_url, body=total_req).execute()

    lines = [f"Performance Overview for {site_url} ({start_date} to {end_date}):", "-" * 60]

    if total_resp.get("rows"):
        row = total_resp["rows"][0]
        lines.append(f"Total Clicks:      {row.get('clicks', 0):,}")
        lines.append(f"Total Impressions: {row.get('impressions', 0):,}")
        lines.append(f"Average CTR:       {row.get('ctr', 0) * 100:.2f}%")
        lines.append(f"Average Position:  {row.get('position', 0):.1f}")
    else:
        lines.append("No data available for the selected period.")
        return "\n".join(lines)

    # Daily trend
    date_req = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["date"],
        "rowLimit": args.days or 28,
    }
    date_resp = service.searchanalytics().query(siteUrl=site_url, body=date_req).execute()

    if date_resp.get("rows"):
        sorted_rows = sorted(date_resp["rows"], key=lambda x: x["keys"][0])
        lines.append("")
        headers = ["Date", "Clicks", "Impressions", "CTR", "Position"]
        table_rows = []
        for row in sorted_rows:
            table_rows.append([
                row["keys"][0],
                str(row.get("clicks", 0)),
                str(row.get("impressions", 0)),
                f"{row.get('ctr', 0) * 100:.2f}%",
                f"{row.get('position', 0):.1f}",
            ])
        lines.append(format_table(headers, table_rows))

    return "\n".join(lines)


def report_page_queries(service, args):
    """Queries driving traffic to a specific page."""
    site_url = get_site_url(args)
    if not args.page_url:
        return "Error: --page-url is required for the page-queries report."

    end_date = args.end or datetime.now().date().strftime("%Y-%m-%d")
    start_date = args.start or (datetime.now().date() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "page",
                "operator": "equals",
                "expression": args.page_url,
            }]
        }],
        "rowLimit": args.limit,
    }

    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    rows_data = response.get("rows", [])

    if not rows_data:
        return f"No search data found for page {args.page_url}."

    headers = ["Query", "Clicks", "Impressions", "CTR", "Position"]
    rows = []
    for row in rows_data:
        rows.append([
            row.get("keys", [""])[0][:80],
            str(row.get("clicks", 0)),
            str(row.get("impressions", 0)),
            f"{row.get('ctr', 0) * 100:.2f}%",
            f"{row.get('position', 0):.1f}",
        ])

    return format_output(headers, rows, args.output)


def report_compare(service, args):
    """Compare search analytics between two periods."""
    site_url = get_site_url(args)
    if not all([args.p1_start, args.p1_end, args.p2_start, args.p2_end]):
        return "Error: --p1-start, --p1-end, --p2-start, --p2-end are all required for compare."

    dims = [d.strip() for d in args.dimensions.split(",")] if args.dimensions else ["query"]

    def fetch_period(start, end):
        req = {
            "startDate": start,
            "endDate": end,
            "dimensions": dims,
            "rowLimit": 1000,
        }
        return service.searchanalytics().query(siteUrl=site_url, body=req).execute().get("rows", [])

    p1_rows = fetch_period(args.p1_start, args.p1_end)
    p2_rows = fetch_period(args.p2_start, args.p2_end)

    if not p1_rows and not p2_rows:
        return "No data found for either period."

    p1_data = {tuple(r.get("keys", [])): r for r in p1_rows}
    p2_data = {tuple(r.get("keys", [])): r for r in p2_rows}

    all_keys = set(p1_data.keys()) | set(p2_data.keys())
    comparisons = []

    for key in all_keys:
        p1 = p1_data.get(key, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})
        p2 = p2_data.get(key, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})
        diff = p2.get("clicks", 0) - p1.get("clicks", 0)
        comparisons.append((key, p1, p2, diff))

    comparisons.sort(key=lambda x: abs(x[3]), reverse=True)

    dim_headers = [d.capitalize() for d in dims]
    headers = dim_headers + ["P1 Clicks", "P2 Clicks", "Change", "P1 Pos", "P2 Pos"]
    rows = []
    for key, p1, p2, diff in comparisons[:args.limit]:
        row = [str(k)[:60] for k in key]
        row.extend([
            str(p1.get("clicks", 0)),
            str(p2.get("clicks", 0)),
            f"{diff:+d}",
            f"{p1.get('position', 0):.1f}",
            f"{p2.get('position', 0):.1f}",
        ])
        rows.append(row)

    title = (
        f"Comparison for {site_url}\n"
        f"Period 1: {args.p1_start} to {args.p1_end}\n"
        f"Period 2: {args.p2_start} to {args.p2_end}\n"
    )
    return title + "\n" + format_output(headers, rows, args.output)


def report_inspect(service, args):
    """URL inspection for indexing status."""
    site_url = get_site_url(args)
    if not args.page_url:
        return "Error: --page-url is required for the inspect report."

    request = {"inspectionUrl": args.page_url, "siteUrl": site_url}
    response = service.urlInspection().index().inspect(body=request).execute()

    if not response or "inspectionResult" not in response:
        return f"No inspection data for {args.page_url}."

    inspection = response["inspectionResult"]
    index_status = inspection.get("indexStatusResult", {})

    lines = [f"URL Inspection: {args.page_url}", "-" * 60]

    if "inspectionResultLink" in inspection:
        lines.append(f"GSC Link: {inspection['inspectionResultLink']}")

    lines.append(f"Verdict:       {index_status.get('verdict', 'UNKNOWN')}")

    field_map = {
        "coverageState": "Coverage",
        "pageFetchState": "Page Fetch",
        "robotsTxtState": "Robots.txt",
        "indexingState": "Indexing",
        "crawledAs": "Crawled As",
        "googleCanonical": "Google Canonical",
        "userCanonical": "User Canonical",
    }

    for field, label in field_map.items():
        if field in index_status:
            lines.append(f"{label + ':':15s}{index_status[field]}")

    if "lastCrawlTime" in index_status:
        try:
            ct = datetime.fromisoformat(index_status["lastCrawlTime"].replace("Z", "+00:00"))
            lines.append(f"{'Last Crawled:':15s}{ct.strftime('%Y-%m-%d %H:%M')}")
        except ValueError:
            lines.append(f"{'Last Crawled:':15s}{index_status['lastCrawlTime']}")

    if "referringUrls" in index_status and index_status["referringUrls"]:
        lines.append("\nReferring URLs:")
        for url in index_status["referringUrls"][:5]:
            lines.append(f"  - {url}")

    if "richResultsResult" in inspection:
        rich = inspection["richResultsResult"]
        lines.append(f"\nRich Results:  {rich.get('verdict', 'UNKNOWN')}")
        for item in rich.get("detectedItems", []):
            lines.append(f"  - {item.get('richResultType', 'Unknown')}")

    return "\n".join(lines)


def report_sitemaps(service, args):
    """List sitemaps for a property."""
    site_url = get_site_url(args)
    sitemaps = service.sitemaps().list(siteUrl=site_url).execute()

    if not sitemaps.get("sitemap"):
        return f"No sitemaps found for {site_url}."

    headers = ["Path", "Last Downloaded", "Type", "URLs", "Errors"]
    rows = []
    for sm in sitemaps.get("sitemap", []):
        last_dl = sm.get("lastDownloaded", "Never")
        if last_dl != "Never":
            try:
                dt = datetime.fromisoformat(last_dl.replace("Z", "+00:00"))
                last_dl = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass

        sm_type = "Index" if sm.get("isSitemapsIndex", False) else "Sitemap"
        url_count = "N/A"
        for content in sm.get("contents", []):
            if content.get("type") == "web":
                url_count = str(content.get("submitted", 0))
                break

        rows.append([
            sm.get("path", "Unknown"),
            last_dl,
            sm_type,
            url_count,
            str(sm.get("errors", 0)),
        ])

    return format_output(headers, rows, args.output)


def report_indexing(service, args):
    """Check indexing issues for multiple URLs."""
    site_url = get_site_url(args)
    if not args.urls:
        return "Error: --urls is required (comma-separated list of URLs to check)."

    url_list = [u.strip() for u in args.urls.split(",") if u.strip()]
    if len(url_list) > 10:
        return "Error: Max 10 URLs per batch to avoid API quota issues."

    summary = {"indexed": [], "not_indexed": [], "fetch_issues": [], "robots_blocked": []}

    for page_url in url_list:
        try:
            request = {"inspectionUrl": page_url, "siteUrl": site_url}
            response = service.urlInspection().index().inspect(body=request).execute()

            if not response or "inspectionResult" not in response:
                summary["not_indexed"].append(f"{page_url} — no data")
                continue

            idx = response["inspectionResult"].get("indexStatusResult", {})
            verdict = idx.get("verdict", "UNKNOWN")
            coverage = idx.get("coverageState", "Unknown")

            if verdict != "PASS" or "not indexed" in coverage.lower() or "excluded" in coverage.lower():
                summary["not_indexed"].append(f"{page_url} — {coverage}")
            else:
                summary["indexed"].append(page_url)

            if idx.get("robotsTxtState") == "BLOCKED":
                summary["robots_blocked"].append(page_url)
            if idx.get("pageFetchState", "SUCCESSFUL") != "SUCCESSFUL":
                summary["fetch_issues"].append(f"{page_url} — {idx.get('pageFetchState')}")

        except Exception as e:
            summary["not_indexed"].append(f"{page_url} — Error: {e}")

    lines = [f"Indexing Report for {site_url}", "-" * 60]
    lines.append(f"Checked:        {len(url_list)}")
    lines.append(f"Indexed:        {len(summary['indexed'])}")
    lines.append(f"Not indexed:    {len(summary['not_indexed'])}")
    lines.append(f"Robots blocked: {len(summary['robots_blocked'])}")
    lines.append(f"Fetch issues:   {len(summary['fetch_issues'])}")

    for category, label in [
        ("not_indexed", "Not Indexed"),
        ("robots_blocked", "Robots Blocked"),
        ("fetch_issues", "Fetch Issues"),
    ]:
        if summary[category]:
            lines.append(f"\n{label}:")
            for item in summary[category]:
                lines.append(f"  - {item}")

    return "\n".join(lines)


REPORTS = {
    "properties": report_properties,
    "search": report_search,
    "pages": report_pages,
    "performance": report_performance,
    "page-queries": report_page_queries,
    "compare": report_compare,
    "inspect": report_inspect,
    "sitemaps": report_sitemaps,
    "indexing": report_indexing,
}


def main():
    parser = argparse.ArgumentParser(description="Query Google Search Console data")
    parser.add_argument("--report", required=True, choices=REPORTS.keys(), help="Report type")
    parser.add_argument("--site-url", help="GSC site URL (overrides GSC_SITE_URL env var)")
    parser.add_argument("--days", type=int, default=28, help="Lookback period in days (default: 28)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD), overrides --days")
    parser.add_argument("--end", help="End date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--limit", type=int, default=20, help="Max rows (default: 20)")
    parser.add_argument("--output", choices=["table", "json", "csv"], default="table", help="Output format")
    parser.add_argument("--dimensions", help="Comma-separated dimensions (for search/compare)")
    parser.add_argument("--page-url", help="Page URL (for page-queries and inspect)")
    parser.add_argument("--urls", help="Comma-separated URLs (for indexing report)")
    parser.add_argument("--p1-start", help="Period 1 start date (for compare)")
    parser.add_argument("--p1-end", help="Period 1 end date (for compare)")
    parser.add_argument("--p2-start", help="Period 2 start date (for compare)")
    parser.add_argument("--p2-end", help="Period 2 end date (for compare)")

    args = parser.parse_args()

    # Allow --site-url to override env var
    if args.site_url:
        global GSC_SITE_URL
        GSC_SITE_URL = args.site_url

    try:
        service = get_service()
        result = REPORTS[args.report](service, args)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
