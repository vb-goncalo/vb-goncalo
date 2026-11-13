#!/usr/bin/env python3
"""Render the GitHub contribution calendar as a dark-theme SVG with a blue scale."""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "vb-goncalo")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "contributions.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

COLORS = {
    "NONE": "#151b23",
    "FIRST_QUARTILE": "#0c2d6b",
    "SECOND_QUARTILE": "#1f4fa3",
    "THIRD_QUARTILE": "#3b82f6",
    "FOURTH_QUARTILE": "#79b8ff",
}
LEVELS = list(COLORS)

FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'
MUTED = "#9198a1"
BRIGHT = "#f0f6fc"
CELL, STEP = 10, 13
WIDTH = 760
LEFT = 46
TOP = 48
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch(token, login):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "contributions-svg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"error: GitHub API returned HTTP {e.code}: {e.read()[:300]!r}")
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        sys.exit(f"error: request failed: {e}")
    if data.get("errors"):
        sys.exit(f"error: GraphQL errors: {json.dumps(data['errors'])[:500]}")
    try:
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (KeyError, TypeError):
        sys.exit("error: unexpected API response (user not found?)")
    if not cal.get("weeks"):
        sys.exit("error: API returned an empty calendar")
    return cal


def render(cal):
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    n = len(weeks)
    out = []
    grid_h = 7 * STEP - 3
    height = TOP + grid_h + 38
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="{total} contributions in the last year" '
        f'font-family=\'{FONT}\' fill="{MUTED}">'
    )
    out.append(f'<text x="16" y="18" font-size="14" fill="{BRIGHT}">{total:,} contributions in the last year</text>')

    # month labels: first week of each month, skipping labels too close to the previous one
    last_col, last_month = -10, None
    for i, w in enumerate(weeks):
        days = w["contributionDays"]
        if not days:
            continue
        d = datetime.date.fromisoformat(days[0]["date"])
        if d.month == last_month:
            continue
        last_month = d.month
        if i - last_col < 3:
            continue
        last_col = i
        out.append(f'<text x="{LEFT + i * STEP}" y="{TOP - 8}" font-size="10">{MONTHS[d.month - 1]}</text>')

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="16" y="{TOP + row * STEP + 9}" font-size="10">{label}</text>')

    for i, w in enumerate(weeks):
        for d in w["contributionDays"]:
            x = LEFT + i * STEP
            y = TOP + d["weekday"] * STEP
            color = COLORS.get(d["contributionLevel"], COLORS["NONE"])
            c = d["contributionCount"]
            word = "contribution" if c == 1 else "contributions"
            out.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
                f'fill="{color}" stroke="rgba(255,255,255,0.05)" stroke-width="1">'
                f'<title>{c} {word} on {d["date"]}</title></rect>'
            )

    # legend, right-aligned to the grid end
    grid_end = LEFT + n * STEP - 3
    ly = TOP + grid_h + 14
    lx = grid_end - (5 * STEP - 3) - 4 - 28 - 4 - 24
    out.append(f'<text x="{lx}" y="{ly + 9}" font-size="10">Less</text>')
    sx = lx + 28
    for k, lvl in enumerate(LEVELS):
        out.append(
            f'<rect x="{sx + k * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
            f'fill="{COLORS[lvl]}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>'
        )
    out.append(f'<text x="{sx + 5 * STEP + 1}" y="{ly + 9}" font-size="10">More</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("error: GITHUB_TOKEN is not set")
    cal = fetch(token, LOGIN)
    svg = render(cal)
    path = os.path.normpath(OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(svg)
    os.replace(tmp, path)
    print(f"wrote {path}: totalContributions={cal['totalContributions']}")


if __name__ == "__main__":
    main()
