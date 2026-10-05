"""Scrape YouTube video details and append them to a Google Sheet.

Usage:
  python scraper.py <url-or-query> [...] [--sheet NAME] [--limit N]

Inputs can be video URLs, channel/playlist URLs, or "ytsearch10:python tutorial".
Needs a Google service-account key at ./credentials.json (or GOOGLE_CREDS env),
and the target sheet shared with that service account's email.
"""
import argparse
import os
from datetime import datetime

import gspread
import yt_dlp

HEADERS = ["Title", "Channel", "Description", "Publish Date", "Views", "URL", "Scraped At"]


def fmt_date(d):
    return datetime.strptime(d, "%Y%m%d").date().isoformat() if d else ""


def scrape(targets, limit):
    opts = {"quiet": True, "skip_download": True, "ignoreerrors": True, "playlistend": limit}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for t in targets:
            info = ydl.extract_info(t, download=False)
            if not info:
                continue
            # Channels nest tabs -> playlists -> videos; flatten everything down to videos.
            stack = [info]
            while stack:
                e = stack.pop(0)
                if e is None:
                    continue
                if e.get("entries") is not None:
                    stack.extend(e["entries"])
                else:
                    yield e


def to_row(v):
    return [
        v.get("title", ""),
        v.get("channel") or v.get("uploader", ""),
        (v.get("description") or "")[:49000],  # Sheets cell limit is 50k chars
        fmt_date(v.get("upload_date")),
        v.get("view_count") or 0,
        v.get("webpage_url", ""),
        datetime.now().isoformat(timespec="seconds"),
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("targets", nargs="+")
    p.add_argument("--sheet", default="YouTube Scraper")
    p.add_argument("--limit", type=int, default=20, help="max videos per channel/playlist")
    a = p.parse_args()

    rows = [to_row(v) for v in scrape(a.targets, a.limit)]
    print(f"Scraped {len(rows)} videos")

    gc = gspread.service_account(filename=os.getenv("GOOGLE_CREDS", "credentials.json"))
    ws = gc.open(a.sheet).sheet1
    if ws.row_values(1) != HEADERS:
        ws.insert_row(HEADERS, 1)
    ws.append_rows(rows, value_input_option="RAW")
    print(f"Appended to sheet '{a.sheet}': {ws.spreadsheet.url}")


if __name__ == "__main__":
    assert fmt_date("20240131") == "2024-01-31" and fmt_date(None) == ""
    main()
