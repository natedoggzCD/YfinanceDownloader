import csv
from pathlib import Path

import requests


SCREENER_URL = "https://www.nasdaq.com/market-activity/stocks/screener"
SCREENER_API_URL = (
    "https://api.nasdaq.com/api/screener/stocks?tableonly=false&limit=25&download=true"
)
SCREENER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Origin": "https://www.nasdaq.com",
    "Referer": SCREENER_URL,
}
CSV_COLUMNS = [
    ("symbol", "Symbol"),
    ("name", "Name"),
    ("lastsale", "Last Sale"),
    ("netchange", "Net Change"),
    ("pctchange", "% Change"),
    ("marketCap", "Market Cap"),
    ("country", "Country"),
    ("ipoyear", "IPO Year"),
    ("volume", "Volume"),
    ("sector", "Sector"),
    ("industry", "Industry"),
]


def _download_via_api(output_file: Path) -> int:
    response = requests.get(SCREENER_API_URL, headers=SCREENER_HEADERS, timeout=60)
    response.raise_for_status()

    payload = response.json()
    rows = payload.get("data", {}).get("rows", [])
    if not rows:
        raise ValueError("NASDAQ API returned no screener rows")

    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[label for _, label in CSV_COLUMNS],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({label: row.get(key, "") for key, label in CSV_COLUMNS})

    return len(rows)


def _download_via_playwright(output_file: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"  Playwright fallback unavailable: {exc}")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=SCREENER_HEADERS["User-Agent"],
            accept_downloads=True,
        )
        page = context.new_page()

        try:
            print("  Falling back to browser automation...")
            print("  Navigating to NASDAQ screener page...")
            page.goto(SCREENER_URL, wait_until="domcontentloaded", timeout=60000)
            page.get_by_role("button", name="Download CSV").wait_for(
                state="visible", timeout=30000
            )

            print(f"  Clicking download and saving to {output_file}...")
            with page.expect_download(timeout=60000) as download_info:
                page.get_by_role("button", name="Download CSV").click()

            download_info.value.save_as(str(output_file))
            return True
        finally:
            context.close()
            browser.close()


def download_screener_csv(output_path="nasdaq_screener.csv"):
    """
    Download the latest NASDAQ stock screener CSV.

    Primary path uses Nasdaq's JSON screener endpoint directly because it is
    more reliable than full-page browser navigation. Playwright remains as a
    fallback if the endpoint behavior changes.
    """

    print("\n[NASDAQ SCREENER UPDATER]")
    print("  Downloading latest screener data from NASDAQ...")

    output_file = Path(output_path).resolve()

    try:
        row_count = _download_via_api(output_file)
        print(f"  Successfully updated {output_path} with {row_count} rows.")
        return True
    except Exception as exc:
        print(f"  WARNING: Direct NASDAQ API download failed: {exc}")

    try:
        if _download_via_playwright(output_file):
            print(f"  Successfully updated {output_path} via browser fallback.")
            return True
    except Exception as exc:
        print(f"  ERROR: Playwright fallback failed: {exc}")

    print("  ERROR: Failed to download NASDAQ screener CSV.")
    return False


if __name__ == "__main__":
    download_screener_csv()
