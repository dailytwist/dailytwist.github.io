#!/usr/bin/env python3
"""Last safety check before publishing. If anything is wrong, the deploy is stopped and the live site stays as it was.

Checks: every language home page exists, the site did not suddenly shrink, all internal links and assets resolve,
every page has a title and closes its HTML, no error text leaked into a page.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"
C = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
problems = []

pages = list(PUB.rglob("*.html"))
if len(pages) < 1000:
    problems.append(f"only {len(pages)} pages were built (expected 1000+)")

for lang in C.get("languages", ["en"]):
    home = PUB / ("index.html" if lang == "en" else f"{lang}/index.html")
    if not home.exists():
        problems.append(f"missing home page for {lang}")
for must in ["sitemap.xml", "robots.txt", "CNAME", "sw.js", "assets/style.css", "assets/app.js"]:
    if not (PUB / must).exists():
        problems.append(f"missing {must}")

broken, bad_pages = {}, []
LEAK = re.compile(r"Traceback \(most recent call last\)|\{[a-z_]+\}|KeyError|None</h1>|>undefined<|>NaN<")
for f in pages:
    s = f.read_text(encoding="utf-8", errors="replace")
    if f.name.startswith("google") and "site-verification" in s:
        continue  # Search Console verification files are plain text on purpose
    if "<title>" not in s or "</html>" not in s:
        bad_pages.append(f"{f.relative_to(PUB)} (incomplete html)")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
    m = LEAK.search(body)
    if m:
        bad_pages.append(f"{f.relative_to(PUB)} (contains '{m.group(0)[:30]}')")
    for u in re.findall(r'(?:href|src)="(/[^"#?]*)', s):
        t = PUB / u.lstrip("/")
        if u.endswith("/"):
            t = t / "index.html"
        if not t.exists():
            broken.setdefault(u, str(f.relative_to(PUB)))
if broken:
    problems.append(f"{len(broken)} broken links, e.g. " + ", ".join(f"{u} on {p}" for u, p in list(broken.items())[:5]))
if bad_pages:
    problems.append(f"{len(bad_pages)} broken pages, e.g. " + ", ".join(bad_pages[:5]))

try:
    import xml.etree.ElementTree as ET
    ET.parse(PUB / "sitemap.xml")
except Exception as e:
    problems.append(f"sitemap.xml is not valid: {e}")

if problems:
    print("::error::Publishing stopped, the live site stays as it was:")
    for p in problems:
        print("::error::" + p)
    sys.exit(1)
print(f"✅ {len(pages)} pages checked: links, assets, titles and sitemap are fine")
