"""Perbarui README profil secara otomatis.

Mengambil aktivitas publik terbaru dari GitHub API (rilis, PR yang digabung,
repo baru) dan, jika BLOG_FEED diisi, artikel terbaru dari feed RSS/Atom.
Hasilnya ditulis ke bagian yang diapit penanda HTML:

    <!-- recent_activity starts --> ... <!-- recent_activity ends -->
    <!-- blog starts -->            ... <!-- blog ends -->   (opsional)
"""

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

USERNAME = os.environ.get("GITHUB_USERNAME", "")
BLOG_FEED = os.environ.get("BLOG_FEED", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
MAX_ITEMS = 5


def fetch(url, headers=None):
    req = urllib.request.Request(
        url, headers={"User-Agent": "profile-readme-updater", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def short_date(value):
    """Ubah tanggal RSS (RFC 2822) atau Atom (ISO 8601) menjadi YYYY-MM-DD."""
    try:
        return parsedate_to_datetime(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")


def github_activity():
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=100"
    events = json.loads(fetch(url, headers))

    items, seen = [], set()
    for ev in events:
        repo = ev["repo"]["name"]
        payload = ev.get("payload", {})
        kind = ev["type"]

        if kind == "ReleaseEvent" and payload.get("action") == "published":
            rel = payload["release"]
            label = f"Rilis [{repo} {rel['tag_name']}]({rel['html_url']})"
        elif kind == "PullRequestEvent" and payload.get("pull_request", {}).get("merged"):
            pr = payload["pull_request"]
            label = f"PR digabung di [{repo}]({pr['html_url']})"
        elif kind == "CreateEvent" and payload.get("ref_type") == "repository":
            label = f"Repo baru [{repo}](https://github.com/{repo})"
        else:
            continue

        if label in seen:
            continue
        seen.add(label)
        items.append(f"- {label} · {ev['created_at'][:10]}")
        if len(items) == MAX_ITEMS:
            break
    return items


def blog_posts():
    root = ET.fromstring(fetch(BLOG_FEED))
    atom = "{http://www.w3.org/2005/Atom}"

    items = []
    # Format RSS: <item><title/><link/><pubDate/></item>
    for item in root.iter("item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub = item.findtext("pubDate", "")
        date = short_date(pub) if pub else ""
        items.append(f"- [{title}]({link}) · {date}".rstrip(" ·"))

    # Format Atom: <entry><title/><link href=""/><updated/></entry>
    for entry in root.iter(f"{atom}entry"):
        title = entry.findtext(f"{atom}title", "").strip()
        link_el = entry.find(f"{atom}link")
        link = link_el.get("href", "") if link_el is not None else ""
        updated = entry.findtext(f"{atom}updated", "")
        date = short_date(updated) if updated else ""
        items.append(f"- [{title}]({link}) · {date}".rstrip(" ·"))

    return items[:MAX_ITEMS]


def replace_section(text, name, lines):
    body = "\n".join(lines) if lines else "_Belum ada data._"
    pattern = re.compile(rf"(<!-- {name} starts -->).*?(<!-- {name} ends -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"Penanda '{name}' tidak ditemukan di {README}")
    # Pakai lambda agar karakter backslash di isi tidak diproses sebagai escape.
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text, count=1)


def main():
    if not USERNAME:
        sys.exit("Atur GITHUB_USERNAME terlebih dahulu.")

    with open(README, encoding="utf-8") as f:
        text = f.read()

    text = replace_section(text, "recent_activity", github_activity())
    if BLOG_FEED:
        text = replace_section(text, "blog", blog_posts())

    with open(README, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{README} diperbarui.")


if __name__ == "__main__":
    main()
