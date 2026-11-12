"""Buat kartu karakter bergaya RPG (SVG) dari data GitHub.

Data diambil lewat GitHub GraphQL API, lalu digambar sebagai satu file SVG
sehingga tidak bergantung pada layanan pihak ketiga. Semua tech stack
ditampilkan sebagai "Inventory" di bagian bawah kartu.

Variabel lingkungan:
    GITHUB_USERNAME  username GitHub (wajib)
    GITHUB_TOKEN     token untuk GraphQL API (wajib)
    CARD_PATH        lokasi keluaran, default assets/profile-card.svg
"""

import base64
import io
import json
import math
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timezone
from xml.sax.saxutils import escape

USERNAME = os.environ.get("GITHUB_USERNAME", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("CARD_PATH", "assets/profile-card.svg")
ICON_VERSION = "13.21.0"

# ---------------------------------------------------------------- tech stack
# (nama, slug simple-icons atau None, warna tile, kode huruf jika ikon tidak ada)
STACK = [
    ("WEAPONS · FRONT END", [
        ("HTML5", "html5", "E34F26", "H5"),
        ("CSS3", "css3", "1572B6", "C3"),
        ("JavaScript", "javascript", "F7DF1E", "JS"),
        ("TypeScript", "typescript", "3178C6", "TS"),
        ("Tailwind CSS", "tailwindcss", "06B6D4", "TW"),
        ("WXT", None, "67D55E", "WX"),
        ("Lit", "lit", "324FFF", "LI"),
        ("Zustand", None, "433E38", "ZU"),
        ("React Query", "reactquery", "FF4154", "RQ"),
        ("React", "react", "61DAFB", "RE"),
        ("Next.js", "nextdotjs", "111111", "NX"),
        ("TanStack", "tanstack", "EF4444", "TS"),
        ("React Router", "reactrouter", "CA4245", "RR"),
        ("Vite", "vite", "646CFF", "VI"),
        ("Expo", "expo", "000020", "EX"),
        ("React Native", "react", "61DAFB", "RN"),
    ]),
    ("ARMOR · BACK END", [
        ("MySQL", "mysql", "4479A1", "MY"),
        ("PostgreSQL", "postgresql", "4169E1", "PG"),
        ("MongoDB", "mongodb", "47A248", "MG"),
        ("SQLite", "sqlite", "003B57", "SQ"),
        ("Supabase", "supabase", "3ECF8E", "SB"),
        ("TinyBase", None, "D81B60", "TB"),
        ("Qdrant", "qdrant", "DC244C", "QD"),
        ("Redis", "redis", "FF4438", "RD"),
        ("RabbitMQ", "rabbitmq", "FF6600", "RB"),
        ("Node.js", "nodedotjs", "5FA04E", "ND"),
        ("Bun", "bun", "FBF0DF", "BN"),
        ("Express", "express", "111111", "EX"),
        ("Elysia", None, "7C3AED", "EL"),
        ("Hono", "hono", "E36002", "HO"),
        ("Python", "python", "3776AB", "PY"),
        ("FastAPI", "fastapi", "009688", "FA"),
        ("LangChain", "langchain", "1C3C3C", "LC"),
        ("AI SDK", "vercel", "111111", "AI"),
        ("Mastra", None, "0F766E", "MA"),
        ("Prisma", "prisma", "2D3748", "PR"),
        ("Drizzle", "drizzle", "C5F74F", "DZ"),
        ("PHP", "php", "777BB4", "PH"),
        ("Kotlin", "kotlin", "7F52FF", "KT"),
        ("Laravel", "laravel", "FF2D20", "LV"),
        ("C", "c", "A8B9CC", "C"),
        ("Bash", "gnubash", "4EAA25", "SH"),
    ]),
    ("ARTIFACTS · DEV TOOLS & INFRA", [
        ("Google Cloud", "googlecloud", "4285F4", "GC"),
        ("Linear", "linear", "5E6AD2", "LN"),
        ("Kilo Code", None, "F2C94C", "KC"),
        ("CF Pages", "cloudflarepages", "F38020", "CP"),
        ("CF Workers", "cloudflareworkers", "F38020", "CW"),
        ("Railway", "railway", "0B0D0E", "RW"),
        ("Dokploy", None, "2563EB", "DP"),
        ("Docker", "docker", "2496ED", "DK"),
        ("Postman", "postman", "FF6C37", "PM"),
        ("n8n", "n8n", "EA4B71", "N8"),
        ("Figma", "figma", "F24E1E", "FG"),
        ("Sentry", "sentry", "362D59", "SE"),
        ("Biome", "biome", "60A5FA", "BI"),
        ("Oxc", None, "00A3A3", "OX"),
    ]),
]

CLASSES = {
    "JavaScript": "ROGUE", "TypeScript": "WIZARD", "Python": "DRUID",
    "PHP": "CLERIC", "Kotlin": "PALADIN", "C": "BERSERKER", "Go": "RANGER",
    "Rust": "ARTIFICER", "Java": "KNIGHT", "Shell": "MONK",
}

# slug simple-icons dan kode huruf cadangan untuk kartu bahasa
LANG_ICONS = {
    "JavaScript": ("javascript", "JS"), "TypeScript": ("typescript", "TS"),
    "PHP": ("php", "PHP"), "CSS": ("css3", "CSS"), "HTML": ("html5", "H5"),
    "Python": ("python", "PY"), "Blade": ("laravel", "BL"), "C++": ("cplusplus", "C+"),
    "C": ("c", "C"), "Kotlin": ("kotlin", "KT"), "Shell": ("gnubash", "SH"),
    "Dockerfile": ("docker", "DK"), "Java": (None, "JV"), "Go": ("go", "GO"),
}

# ---------------------------------------------------------------- warna/gaya
BG = "#0d1117"
PANEL = "#161b22"
LINE = "#21262d"
GREEN = "#3fb950"
AMBER = "#e3b341"
TEXT = "#e6edf3"
MUTED = "#8b949e"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace"
HEAT = ["#1b2330", "#0e4429", "#006d32", "#26a641", "#39d353"]
W = 900

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    createdAt
    avatarUrl
    followers { totalCount }
    pullRequests(states: OPEN) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch(url, headers=None, data=None):
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "profile-card-generator", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def graphql():
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    raw = fetch(
        "https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        data=body,
    )
    payload = json.loads(raw)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        sys.exit(f"GraphQL gagal: {payload.get('errors')}")
    return payload["data"]["user"]


# ---------------------------------------------------------------- perhitungan
def score(value, top):
    """Skala log 1..20."""
    return max(1, min(20, round(1 + 19 * math.log1p(max(value, 0)) / math.log1p(top))))


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    best = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    recent = list(reversed(counts))
    if recent and recent[0] == 0:
        recent = recent[1:]  # hari ini belum ada kontribusi: mulai hitung dari kemarin
    current = 0
    for c in recent:
        if c == 0:
            break
        current += 1
    return current, best


def languages(user):
    totals, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#8b949e"
    grand = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return [(n, round(100 * s / grand), colors[n]) for n, s in top]


# ---------------------------------------------------------------- gambar
def t(x, y, text, size=12, fill=TEXT, weight="normal", anchor="start", spacing=0):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}" letter-spacing="{spacing}">'
        f"{escape(str(text))}</text>"
    )


def rect(x, y, w, h, fill, rx=0, stroke=None):
    s = f' stroke="{stroke}"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}/>'


def pixel_avatar(url):
    raw = fetch(url)
    mime = "image/jpeg" if raw[:2] == b"\xff\xd8" else "image/png"
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((20, 20), Image.BOX)
        im = im.resize((160, 160), Image.NEAREST)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        raw, mime = buf.getvalue(), "image/png"
    except ImportError:
        pass
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


_icon_cache = {}


def icon_path(slug):
    if not slug:
        return None
    if slug not in _icon_cache:
        try:
            svg = fetch(
                f"https://cdn.jsdelivr.net/npm/simple-icons@{ICON_VERSION}/icons/{slug}.svg"
            ).decode()
            m = re.search(r'<path d="([^"]+)"', svg)
            _icon_cache[slug] = m.group(1) if m else None
        except Exception:
            _icon_cache[slug] = None
    return _icon_cache[slug]


def is_light(hex_color):
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6


def tile(x, y, color, slug, code):
    """Kotak ikon 28x28: glyph simple-icons, atau huruf jika ikon tidak tersedia."""
    ink = "#0d1117" if is_light(color) else "#ffffff"
    out = [rect(x, y, 28, 28, f"#{color}", 4, "#30363d")]
    path = icon_path(slug)
    if path:
        out.append(
            f'<g transform="translate({x + 6},{y + 6}) scale({16 / 24})">'
            f'<path d="{path}" fill="{ink}"/></g>'
        )
    else:
        size = 11 if len(code) <= 2 else 9
        out.append(t(x + 14, y + 18, code, size, ink, "bold", "middle"))
    return "".join(out)


def item_card(x, y, w, h, title, sub, tile_svg):
    return (
        rect(x, y, w, h, PANEL, 4, LINE)
        + tile_svg
        + t(x + 40, y + 16, title, 11, TEXT, "bold")
        + (t(x + 40, y + 29, sub, 9, MUTED) if sub else "")
    )


def build(user):
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, best = streaks(days)
    xp = cal["totalContributions"]

    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    months = max(0, (datetime.now(timezone.utc) - created).days // 30)
    years = months // 12
    langs = languages(user)

    level = int(math.sqrt(xp / 20)) + 1
    start, nxt = 20 * (level - 1) ** 2, 20 * level**2
    progress = (xp - start) / (nxt - start)
    klass = CLASSES.get(langs[0][0], "ADVENTURER") if langs else "ADVENTURER"
    top_lang = langs[0][0].upper() if langs else "CODE"

    followers = user["followers"]["totalCount"]
    commits = cc["totalCommitContributions"]
    prs = cc["totalPullRequestContributions"]
    reviews = cc["totalPullRequestReviewContributions"]
    open_prs = user["pullRequests"]["totalCount"]

    attrs = [
        ("STR", score(commits, 1000), f"{commits} commits"),
        ("DEX", score(prs, 100), f"{prs} pull requests"),
        ("INT", score(reviews, 100), f"{reviews} reviews"),
        ("WIS", score(months, 120), f"{years} years on GitHub" if years else f"{months} months on GitHub"),
        ("CHA", score(followers, 100), f"{followers} followers"),
        ("CON", score(best, 30), f"{best} day best streak"),
    ]

    parts = []

    # --- kartu karakter -------------------------------------------------
    parts.append(rect(20, 20, 860, 270, PANEL, 8, LINE))
    parts.append(f'<rect x="42" y="42" width="164" height="164" fill="none" stroke="{GREEN}" stroke-width="2"/>')
    parts.append(
        f'<image x="44" y="44" width="160" height="160" href="{pixel_avatar(user["avatarUrl"])}" '
        f'image-rendering="pixelated" preserveAspectRatio="xMidYMid slice"/>'
    )
    parts.append(t(44, 232, (user["name"] or user["login"]).upper(), 18, TEXT, "bold", spacing=1))
    parts.append(t(44, 250, f"LEVEL {level} {top_lang} {klass}", 10, GREEN))
    parts.append(t(44, 264, f"class from top language · {langs[0][0] if langs else '-'}", 9, MUTED))

    parts.append(t(240, 48, "ATTRIBUTES", 11, MUTED, spacing=2))
    for i, (label, value, sub) in enumerate(attrs):
        y = 74 + i * 30
        parts.append(t(240, y, label, 16, TEXT, "bold"))
        parts.append(t(300, y, value, 16, TEXT, "bold", "end"))
        for s in range(20):
            parts.append(rect(312 + s * 17, y - 13, 14, 13, GREEN if s < value else "#21262d"))
        parts.append(t(312, y + 11, sub, 8, MUTED))

    parts.append(t(240, 252, f"XP  LV {level} > {level + 1}", 10, MUTED))
    parts.append(t(860, 252, f"{xp - start} / {nxt - start} xp this level", 9, MUTED, anchor="end"))
    parts.append(rect(240, 258, 620, 10, "#21262d"))
    parts.append(rect(240, 258, round(620 * progress), 10, AMBER))

    y = 330

    # --- quest log ---------------------------------------------------------
    parts.append(t(20, y, "QUEST LOG", 20, GREEN, "bold", spacing=2))
    parts.append(t(20, y + 24, f"Open pull requests: {open_prs} in progress, {prs} opened in the last year.", 11, MUTED))
    quest = "No open quests. Resting at the inn." if open_prs == 0 else f"{open_prs} open quests in progress."
    parts.append(t(20, y + 52, quest, 12, TEXT, "bold"))
    y += 100

    # --- inventory ---------------------------------------------------------
    parts.append(t(20, y, "INVENTORY", 20, GREEN, "bold", spacing=2))
    y += 18
    colw = (860 - 16) / 3
    for i, (name, pct, color) in enumerate(langs):
        cx = 20 + (i % 3) * (colw + 8)
        cy = y + (i // 3) * 52
        slug, code = LANG_ICONS.get(name, (None, name[:2].upper()))
        tile_svg = tile(round(cx) + 8, cy + 8, color.lstrip("#"), slug, code)
        parts.append(item_card(round(cx), cy, round(colw), 44, name, f"{pct}% of my code", tile_svg))
    y += math.ceil(len(langs) / 3) * 52 + 14

    seen = {name for name, _, _ in langs}
    cols, gap = 5, 8
    cw = (860 - gap * (cols - 1)) / cols
    for title, items in STACK:
        parts.append(t(20, y + 4, title, 11, AMBER, "bold", spacing=2))
        y += 18
        for i, (name, slug, color, code) in enumerate(items):
            cx = 20 + (i % cols) * (cw + gap)
            cy = y + (i // cols) * 46
            parts.append(item_card(round(cx), cy, round(cw), 38, name, "", tile(round(cx) + 5, cy + 5, color, slug, code)))
        y += math.ceil(len(items) / cols) * 46 + 14

    # --- adventure log -----------------------------------------------------
    y += 14
    parts.append(rect(20, y, 860, 190, PANEL, 8, LINE))
    parts.append(t(44, y + 30, "ADVENTURE LOG", 12, GREEN, spacing=2))
    weeks = cal["weeks"][-20:]
    peak = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=0) or 1
    for wi, w in enumerate(weeks):
        for di, d in enumerate(w["contributionDays"]):
            c = d["contributionCount"]
            ratio = c / peak
            lvl = 0 if c == 0 else 1 if ratio <= 0.25 else 2 if ratio <= 0.5 else 3 if ratio <= 0.75 else 4
            parts.append(rect(44 + wi * 17, y + 48 + di * 17, 14, 14, HEAT[lvl], 2))
    for i, (label, value) in enumerate(
        [("DAYS QUESTING", f"{current} days"), ("LONGEST QUEST", f"{best} days"), ("XP THIS YEAR", str(xp))]
    ):
        parts.append(t(430, y + 62 + i * 46, label, 9, MUTED, spacing=1))
        parts.append(t(430, y + 84 + i * 46, value, 18, TEXT, "bold"))
    y += 190 + 22

    parts.append(
        t(20, y, "Character Sheet · attributes from real GitHub numbers, 1 to 20 on a log scale · style inspired by GitSkins", 9, MUTED)
    )
    height = y + 20

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">'
        f'<title>RPG character sheet for {escape(user["login"])}</title>'
        + rect(0, 0, W, height, BG, 12)
        + "".join(parts)
        + "</svg>"
    )


def main():
    if not USERNAME or not TOKEN:
        sys.exit("Atur GITHUB_USERNAME dan GITHUB_TOKEN terlebih dahulu.")
    svg = build(graphql())
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{OUT} dibuat ({len(svg) // 1024} KB).")


if __name__ == "__main__":
    main()
