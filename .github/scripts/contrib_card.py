#!/usr/bin/env python3
"""
Cosmic-themed contribution card generator.

Fetches the FULL contribution history (all years, PRIVATE contributions included)
straight from the GitHub GraphQL API using the owner's personal token, then renders
dist/contrib-card.svg with three live figures:

    Total Contributions  ·  Current Streak  ·  Longest Streak

Nothing here is hard-coded — every number and date is computed from the API on each
run, so the card always matches what GitHub itself counts (private contributions
require the token; see .github/workflows/contrib-card.yml).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com/graphql"
USER = os.environ.get("USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER", "")
TOKEN = os.environ.get("GH_TOKEN", "").strip()

# palette — matches the README cosmic / tokyonight theme
BG = "#0d1126"
ACCENT = "#a78bfa"
TEXT = "#e6e6f0"
MUTED = "#7a86a8"
RING = "#23284a"

OUT_DIR = "dist"
OUT_FILE = os.path.join(OUT_DIR, "contrib-card.svg")


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(total, cur, longest, total_sub, cur_sub, long_sub) -> str:
    """Build the three-column SVG card."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub contribution stats">
  <style>
    text {{ font-family: 'Segoe UI', Ubuntu, system-ui, -apple-system, sans-serif; }}
    .num {{ font-weight: 800; font-size: 30px; fill: {TEXT}; }}
    .lbl {{ font-weight: 600; font-size: 13px; fill: {ACCENT}; letter-spacing: .3px; }}
    .sub {{ font-weight: 400; font-size: 11px; fill: {MUTED}; }}
    @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    /* fill-mode "both" fades in when animation runs, but leaves content fully
       visible (opacity 1) on any renderer that ignores animations. */
    .col {{ animation: fadein .7s ease both; }}
    .c1 {{ animation-delay: .10s; }}
    .c2 {{ animation-delay: .25s; }}
    .c3 {{ animation-delay: .40s; }}
  </style>

  <rect x="0.5" y="0.5" width="494" height="194" rx="10" fill="{BG}" stroke="{ACCENT}" stroke-opacity="0.25"/>
  <line x1="165" y1="46" x2="165" y2="176" stroke="{ACCENT}" stroke-opacity="0.15"/>
  <line x1="330" y1="46" x2="330" y2="176" stroke="{ACCENT}" stroke-opacity="0.15"/>

  <g class="col c1" text-anchor="middle">
    <text x="82.5" y="84" class="num">{total:,}</text>
    <text x="82.5" y="130" class="lbl">Total Contributions</text>
    <text x="82.5" y="152" class="sub">{esc(total_sub)}</text>
  </g>

  <g class="col c2" text-anchor="middle">
    <circle cx="247.5" cy="74" r="38" fill="none" stroke="{ACCENT}" stroke-opacity="0.12" stroke-width="2"/>
    <circle cx="247.5" cy="74" r="33" fill="none" stroke="{RING}" stroke-width="4.5"/>
    <circle cx="247.5" cy="74" r="33" fill="none" stroke="{ACCENT}" stroke-width="4.5" stroke-linecap="round"
            stroke-dasharray="{_arc(cur, longest)} 999" transform="rotate(-90 247.5 74)"/>
    <text x="247.5" y="84" class="num">{cur:,}</text>
    <text x="247.5" y="130" class="lbl">Current Streak</text>
    <text x="247.5" y="152" class="sub">{esc(cur_sub)}</text>
  </g>

  <g class="col c3" text-anchor="middle">
    <text x="412.5" y="84" class="num">{longest:,}</text>
    <text x="412.5" y="130" class="lbl">Longest Streak</text>
    <text x="412.5" y="152" class="sub">{esc(long_sub)}</text>
  </g>
</svg>
"""


def _arc(cur: int, longest: int) -> float:
    """Length of the purple ring arc — current streak as a fraction of the longest."""
    circumference = 2 * 3.14159265 * 33
    frac = 0.0 if longest <= 0 else min(1.0, cur / longest)
    return round(circumference * frac, 1)


def placeholder(message: str) -> str:
    lines = message.split("\n")
    tspans = "".join(
        f'<tspan x="247.5" dy="{0 if i == 0 else 20}">{esc(l)}</tspan>'
        for i, l in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img">
  <rect x="0.5" y="0.5" width="494" height="194" rx="10" fill="{BG}" stroke="{ACCENT}" stroke-opacity="0.25"/>
  <text x="247.5" y="92" text-anchor="middle" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="14" fill="{MUTED}">{tspans}</text>
</svg>
"""


def write(svg: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(svg)


def gql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{USER}-contrib-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError("GitHub API errors: " + json.dumps(payload["errors"])[:300])
    return payload["data"]


def fmt(d: str, with_year: bool = False) -> str:
    dt = datetime.strptime(d, "%Y-%m-%d")
    # no leading zero on the day, cross-platform (avoid %-d / %#d)
    base = dt.strftime("%b ") + str(dt.day)
    return base + (dt.strftime(", %Y") if with_year else "")


def main() -> None:
    if not USER:
        sys.exit("ERROR: USERNAME (or GITHUB_REPOSITORY_OWNER) env var is required.")

    if not TOKEN:
        # Friendly placeholder so the README never shows a broken image before setup.
        write(placeholder("Add the CONTRIB_TOKEN secret\nto load contribution stats"))
        print("No GH_TOKEN set — wrote placeholder card. See contrib-card.yml setup notes.")
        return

    try:
        created = gql("query($l:String!){user(login:$l){createdAt}}", {"l": USER})
        start_year = int(created["user"]["createdAt"][:4])
        now = datetime.now(timezone.utc)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_year = now.year

        cal_q = """
        query($l:String!, $from:DateTime!, $to:DateTime!){
          user(login:$l){
            contributionsCollection(from:$from, to:$to){
              contributionCalendar{
                weeks{ contributionDays{ date contributionCount } }
              }
            }
          }
        }"""

        days: dict[str, int] = {}
        for yr in range(start_year, end_year + 1):
            # cap the current year at "now" — GitHub rejects a future "to"
            to = now_iso if yr == end_year else f"{yr}-12-31T23:59:59Z"
            data = gql(cal_q, {
                "l": USER,
                "from": f"{yr}-01-01T00:00:00Z",
                "to": to,
            })
            cal = data["user"]["contributionsCollection"]["contributionCalendar"]
            for wk in cal["weeks"]:
                for d in wk["contributionDays"]:
                    days[d["date"]] = d["contributionCount"]

        if not days:
            raise RuntimeError("No contribution data returned for user " + USER)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, KeyError) as e:
        # Leave the previously-published card in place: fail the job loudly.
        sys.exit(f"Failed to fetch contributions: {e}")

    ordered = sorted(days.items())
    dates = [d for d, _ in ordered]
    counts = [c for _, c in ordered]
    total = sum(counts)

    first = next((d for d, c in ordered if c > 0), dates[0])

    # longest streak
    longest = 0
    l_start = l_end = None
    run, run_start = 0, None
    for d, c in ordered:
        if c > 0:
            run_start = d if run == 0 else run_start
            run += 1
            if run > longest:
                longest, l_start, l_end = run, run_start, d
        else:
            run = 0

    # current streak — consecutive days ending today (today may still be 0 = "in progress")
    i = len(ordered) - 1
    if counts[i] == 0:
        i -= 1
    current = 0
    c_start = c_end = None
    while i >= 0 and counts[i] > 0:
        c_end = dates[i] if c_end is None else c_end
        c_start = dates[i]
        current += 1
        i -= 1

    total_sub = f"{fmt(first, with_year=True)} - Present"
    cur_sub = f"{fmt(c_start)} - {fmt(c_end)}" if current > 0 else "Keep it going"
    long_sub = f"{fmt(l_start)} - {fmt(l_end)}" if longest > 0 else "—"

    write(render(total, current, longest, total_sub, cur_sub, long_sub))
    print(f"Wrote {OUT_FILE}: total={total} current={current} longest={longest}")


if __name__ == "__main__":
    main()
