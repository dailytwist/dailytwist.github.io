#!/usr/bin/env python3
"""Builds the static website from content/*.json into public/. No extra packages needed."""
import datetime as dt
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "public"
ASSETS = Path(__file__).resolve().parent / "assets"
C = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SITE = C["site_name"]
URL = C["site_url"].rstrip("/")
BASE = "/" + URL.split("://", 1)[-1].split("/", 1)[1] if "/" in URL.split("://", 1)[-1] else ""
TODAY = dt.datetime.now(dt.timezone.utc).date()

SIGNS = {
    "aries": ("♈", "Mar 21 – Apr 19"), "taurus": ("♉", "Apr 20 – May 20"),
    "gemini": ("♊", "May 21 – Jun 20"), "cancer": ("♋", "Jun 21 – Jul 22"),
    "leo": ("♌", "Jul 23 – Aug 22"), "virgo": ("♍", "Aug 23 – Sep 22"),
    "libra": ("♎", "Sep 23 – Oct 22"), "scorpio": ("♏", "Oct 23 – Nov 21"),
    "sagittarius": ("♐", "Nov 22 – Dec 21"), "capricorn": ("♑", "Dec 22 – Jan 19"),
    "aquarius": ("♒", "Jan 20 – Feb 18"), "pisces": ("♓", "Feb 19 – Mar 20"),
}
e = html.escape
sitemap = []


# ---------------------------------------------------------------- data
def load_dir(name):
    items = []
    for f in sorted((CONTENT / name).glob("*.json")):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception as ex:
            print(f"skip broken file {f.name}: {ex}")
    return items


horoscopes = sorted(load_dir("horoscopes"), key=lambda x: x["date"])
trivia = sorted(load_dir("trivia"), key=lambda x: x["date"])
articles = sorted(load_dir("articles"), key=lambda x: (x["date"], x["title"]), reverse=True)
# never publish future-dated content
horoscopes = [h for h in horoscopes if h["date"] <= str(TODAY)]
trivia = [t for t in trivia if t["date"] <= str(TODAY)]
articles = [a for a in articles if a["date"] <= str(TODAY)]


# ---------------------------------------------------------------- layout
def page(path, title, desc, body, schema=None, priority="0.6"):
    """path like 'horoscope/aries/' or 'about/' or '' for home."""
    canonical = f"{URL}/{path}"
    ads = ""
    if C.get("adsense_client"):
        ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(C["adsense_client"])}" '
               'crossorigin="anonymous"></script>')
    ld = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>' if schema else ""
    full_title = title if title.endswith(SITE) else f"{title} | {SITE}"
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:site_name" content="{e(SITE)}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
{ads}
{ld}
</head>
<body>
<header class="top">
  <div class="wrap nav">
    <a class="brand" href="/"><span class="dot"></span>{e(SITE)}</a>
    <nav>
      <a href="/horoscope/">Horoscopes</a>
      <a href="/trivia/">Trivia</a>
      <a href="/puzzle/">Puzzle</a>
      <a href="/articles/">Explainers</a>
      <a href="/countdown/">Countdowns</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="foot">
  <div class="wrap">
    <p><strong>{e(SITE)}</strong> — {e(C["tagline"])}.</p>
    <p class="links"><a href="/about/">About</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy Policy</a><a href="/terms/">Terms of Use</a><a href="/sitemap.xml">Sitemap</a></p>
    <p class="small">Horoscopes, quizzes and explainers are for entertainment and general information only. © {TODAY.year} {e(SITE)}</p>
  </div>
</footer>
</body>
</html>"""
    if BASE:
        doc = doc.replace('href="/', f'href="{BASE}/').replace('src="/', f'src="{BASE}/')
    target = OUT / path / "index.html" if not path.endswith(".html") else OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")
    sitemap.append((canonical, priority))


def nice_date(d):
    return dt.date.fromisoformat(d).strftime("%A, %B %-d, %Y")


def article_card(a):
    return (f'<a class="card art" href="/articles/{e(a["slug"])}/"><span class="tag">{e(a.get("category", "Explainer"))}</span>'
            f'<h3>{e(a["title"])}</h3><p>{e(a["description"])}</p></a>')


# ---------------------------------------------------------------- holidays
def nth_weekday(year, month, weekday, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def last_weekday(year, month, weekday):
    d = dt.date(year, month + 1, 1) - dt.timedelta(days=1) if month < 12 else dt.date(year, 12, 31)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, ee = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * ee + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(y, month, day)


HOLIDAYS = {
    "christmas": ("Christmas", lambda y: dt.date(y, 12, 25)),
    "new-year": ("New Year's Day", lambda y: dt.date(y, 1, 1)),
    "halloween": ("Halloween", lambda y: dt.date(y, 10, 31)),
    "valentines-day": ("Valentine's Day", lambda y: dt.date(y, 2, 14)),
    "thanksgiving": ("Thanksgiving (US)", lambda y: nth_weekday(y, 11, 3, 4)),
    "easter": ("Easter Sunday", easter),
    "fourth-of-july": ("Fourth of July", lambda y: dt.date(y, 7, 4)),
    "mothers-day": ("Mother's Day (US)", lambda y: nth_weekday(y, 5, 6, 2)),
    "fathers-day": ("Father's Day (US)", lambda y: nth_weekday(y, 6, 6, 3)),
    "st-patricks-day": ("St. Patrick's Day", lambda y: dt.date(y, 3, 17)),
    "memorial-day": ("Memorial Day (US)", lambda y: last_weekday(y, 5, 0)),
    "labor-day": ("Labor Day (US)", lambda y: nth_weekday(y, 9, 0, 1)),
    "black-friday": ("Black Friday", lambda y: nth_weekday(y, 11, 3, 4) + dt.timedelta(days=1)),
}


def next_date(fn):
    d = fn(TODAY.year)
    return d if d >= TODAY else fn(TODAY.year + 1)


# ---------------------------------------------------------------- pages
def build_home():
    h = horoscopes[-1] if horoscopes else None
    t = trivia[-1] if trivia else None
    signs = "".join(
        f'<a class="sign" href="/horoscope/{s}/"><span class="glyph">{g}</span><b>{s.title()}</b><small>{r}</small></a>'
        for s, (g, r) in SIGNS.items())
    upcoming = sorted(((next_date(fn), slug, name) for slug, (name, fn) in HOLIDAYS.items()))[:4]
    cds = "".join(f'<a class="cd" href="/countdown/{slug}/"><b>{(d - TODAY).days}</b><span>days to {e(name)}</span></a>'
                  for d, slug, name in upcoming)
    latest = "".join(article_card(a) for a in articles[:9]) or "<p class='muted'>New explainers arrive every day.</p>"
    body = f"""
<section class="hero">
  <p class="kicker">{TODAY.strftime("%A, %B %-d, %Y")}</p>
  <h1>Today's horoscopes, a fresh trivia quiz and a new word puzzle — every single day.</h1>
  <div class="hero-cta">
    <a class="btn" href="/trivia/">Play today's trivia</a>
    <a class="btn ghost" href="/puzzle/">Solve the daily puzzle</a>
  </div>
</section>
<section>
  <div class="sec-head"><h2>Daily horoscope</h2>{f'<span class="muted">Updated {nice_date(h["date"])}</span>' if h else ''}</div>
  <div class="signs">{signs}</div>
</section>
<section class="split">
  <div class="panel">
    <h2>{e(t["title"]) if t else "Daily trivia"}</h2>
    <p>{len(t["questions"]) if t else 10} brand-new questions across science, history, movies, geography and more. How many can you get right?</p>
    <a class="btn" href="/trivia/">Start the quiz</a>
  </div>
  <div class="panel">
    <h2>Upcoming countdowns</h2>
    <div class="cds">{cds}</div>
  </div>
</section>
<section>
  <div class="sec-head"><h2>Latest explainers</h2><a href="/articles/">See all →</a></div>
  <div class="grid">{latest}</div>
</section>"""
    schema = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": URL + "/"}
    page("", f"{SITE} — Daily Horoscopes, Trivia & Puzzles", C["tagline"], body, schema, "1.0")


def horoscope_body(sign, data, date):
    g, r = SIGNS[sign]
    others = "".join(f'<a href="/horoscope/{s}/">{SIGNS[s][0]} {s.title()}</a>' for s in SIGNS if s != sign)
    return f"""
<article class="reading">
  <p class="kicker">{nice_date(date)} · {r}</p>
  <h1><span class="glyph big">{g}</span> {sign.title()} Horoscope Today</h1>
  <p class="lead">{e(data["overview"])}</p>
  <div class="facets">
    <div><h3>❤ Love</h3><p>{e(data["love"])}</p></div>
    <div><h3>💼 Career</h3><p>{e(data["career"])}</p></div>
    <div><h3>🌿 Wellness</h3><p>{e(data["wellness"])}</p></div>
  </div>
  <div class="lucky">
    <span>Lucky number <b>{e(str(data["lucky_number"]))}</b></span>
    <span>Lucky color <b>{e(str(data["lucky_color"]))}</b></span>
    <span>Mood <b>{e(str(data["mood"]))}</b></span>
  </div>
  <p class="small muted">For entertainment only.</p>
  <h2>Other signs today</h2>
  <div class="chips">{others}</div>
</article>"""


def build_horoscopes():
    if not horoscopes:
        page("horoscope/", "Daily Horoscopes", "Free daily horoscopes for all 12 zodiac signs.",
             "<h1>Daily horoscopes</h1><p>Today's readings are being prepared. Check back soon!</p>")
        return
    latest = horoscopes[-1]
    cards = "".join(
        f'<a class="card hcard" href="/horoscope/{s}/"><span class="glyph">{g}</span><h3>{s.title()}</h3>'
        f'<p>{e(latest["signs"][s]["overview"][:140])}…</p></a>' for s, (g, r) in SIGNS.items())
    archive = "".join(f'<a href="/horoscope/archive/{h["date"]}/">{nice_date(h["date"])}</a>' for h in reversed(horoscopes[-60:]))
    page("horoscope/", "Daily Horoscopes for All 12 Signs",
         f"Free horoscopes for {nice_date(latest['date'])}: love, career and wellness for every zodiac sign.",
         f'<h1>Daily horoscopes</h1><p class="muted">{nice_date(latest["date"])}</p><div class="grid">{cards}</div>'
         f'<h2>Past days</h2><div class="chips">{archive}</div>', priority="0.9")
    for s in SIGNS:
        page(f"horoscope/{s}/", f"{s.title()} Horoscope Today – {nice_date(latest['date'])}",
             latest["signs"][s]["overview"][:150], horoscope_body(s, latest["signs"][s], latest["date"]), priority="0.9")
    for h in horoscopes:
        links = "".join(f'<a class="card hcard" href="/horoscope/{s}/"><span class="glyph">{g}</span><h3>{s.title()}</h3>'
                        f'<p>{e(h["signs"][s]["overview"])}</p></a>' for s, (g, r) in SIGNS.items())
        page(f"horoscope/archive/{h['date']}/", f"Horoscopes for {nice_date(h['date'])}",
             f"All 12 zodiac horoscopes for {nice_date(h['date'])}.",
             f'<h1>Horoscopes for {nice_date(h["date"])}</h1><div class="grid">{links}</div>', priority="0.4")


def trivia_body(t):
    qs = []
    for i, q in enumerate(t["questions"]):
        opts = "".join(f'<button class="opt" data-i="{j}">{e(o)}</button>' for j, o in enumerate(q["options"]))
        qs.append(f"""<div class="q" data-answer="{q["answer_index"]}">
  <p class="qcat">Question {i + 1} · {e(q.get("category", "General"))}</p>
  <h3>{e(q["question"])}</h3>
  <div class="opts">{opts}</div>
  <p class="fact" hidden>💡 {e(q.get("fun_fact", ""))}</p>
</div>""")
    past = "".join(f'<a href="/trivia/{x["date"]}/">{nice_date(x["date"])}</a>' for x in reversed(trivia[-60:]) if x is not t)
    return f"""
<article class="quiz">
  <p class="kicker">Daily trivia · {nice_date(t["date"])}</p>
  <h1>{e(t["title"])}</h1>
  <p class="lead">Tap an answer to lock it in. Your score appears at the end — share it with friends!</p>
  {"".join(qs)}
  <div class="score" hidden><h2>You scored <span id="sc">0</span>/{len(t["questions"])}</h2>
  <p>A new quiz drops every day. Come back tomorrow!</p></div>
  <h2>Previous quizzes</h2><div class="chips">{past}</div>
</article>
<script src="/assets/quiz.js" defer></script>"""


def build_trivia():
    if not trivia:
        page("trivia/", "Daily Trivia Quiz", "A new free trivia quiz every day.",
             "<h1>Daily trivia</h1><p>Today's quiz is being prepared. Check back soon!</p>")
        return
    for t in trivia:
        schema = {"@context": "https://schema.org", "@type": "Quiz", "name": t["title"],
                  "about": "General knowledge", "datePublished": t["date"]}
        page(f"trivia/{t['date']}/", f"{t['title']} – Trivia for {nice_date(t['date'])}",
             f"Play the free daily trivia quiz for {nice_date(t['date'])}: {len(t['questions'])} questions.",
             trivia_body(t), schema, "0.5")
    t = trivia[-1]
    page("trivia/", f"Daily Trivia Quiz – {nice_date(t['date'])}",
         f"Today's free trivia quiz: {len(t['questions'])} questions on science, history, movies and more.",
         trivia_body(t), priority="0.9")


def build_articles():
    for a in articles:
        secs = "".join(f'<h2>{e(s["heading"])}</h2>' + "".join(f"<p>{e(p)}</p>" for p in s.get("paragraphs", []))
                       for s in a["sections"])
        faq = "".join(f'<details><summary>{e(f["q"])}</summary><p>{e(f["a"])}</p></details>' for f in a.get("faq", []))
        rel = [x for x in articles if x is not a and x.get("category") == a.get("category")][:3] or [x for x in articles if x is not a][:3]
        related = "".join(article_card(x) for x in rel)
        schema = [{"@context": "https://schema.org", "@type": "Article", "headline": a["title"],
                   "description": a["description"], "datePublished": a["date"],
                   "author": {"@type": "Organization", "name": f"{SITE} Editorial Team"},
                   "publisher": {"@type": "Organization", "name": SITE}}]
        if a.get("faq"):
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in a["faq"]]})
        body = f"""
<article class="post">
  <p class="kicker">{e(a.get("category", "Explainer"))} · {nice_date(a["date"])}</p>
  <h1>{e(a["title"])}</h1>
  <p class="lead">{e(a["description"])}</p>
  {secs}
  {f'<h2>Frequently asked questions</h2><div class="faq">{faq}</div>' if faq else ''}
  <p class="small muted">Written by the {e(SITE)} editorial team for general information. Spotted an error? <a href="/contact/">Tell us</a>.</p>
</article>
{f'<section><h2>Keep reading</h2><div class="grid">{related}</div></section>' if related else ''}"""
        page(f"articles/{a['slug']}/", a["title"], a["description"], body, schema, "0.7")
    cats = sorted({a.get("category", "Explainer") for a in articles})
    cards = "".join(article_card(a) for a in articles) or "<p class='muted'>New explainers arrive every day.</p>"
    page("articles/", "Explainers & Fun Facts", "Easy, fun explainers about the topics everyone is searching for.",
         f'<h1>Explainers</h1><p class="muted">{len(articles)} articles · {e(", ".join(cats))}</p><div class="grid">{cards}</div>',
         priority="0.8")


def build_countdowns():
    rows = []
    for slug, (name, fn) in HOLIDAYS.items():
        d = next_date(fn)
        days = (d - TODAY).days
        rows.append((d, slug, name, days))
        body = f"""
<article class="countdown" data-target="{d.isoformat()}T00:00:00">
  <p class="kicker">Countdown</p>
  <h1>How many days until {e(name)}?</h1>
  <p class="lead">{e(name)} falls on <b>{d.strftime("%A, %B %-d, %Y")}</b>. That's <b>{days} days</b> from today ({TODAY.strftime("%B %-d")}).</p>
  <div class="ticker"><div><b id="d">{days}</b><span>days</span></div><div><b id="h">0</b><span>hours</span></div>
  <div><b id="m">0</b><span>minutes</span></div><div><b id="s">0</b><span>seconds</span></div></div>
  <p class="small muted">The live timer counts down to midnight in your own time zone.</p>
  <h2>More countdowns</h2>
  <div class="chips">{"".join(f'<a href="/countdown/{s}/">{e(n)}</a>' for s, (n, _) in HOLIDAYS.items() if s != slug)}</div>
</article>
<script src="/assets/countdown.js" defer></script>"""
        page(f"countdown/{slug}/", f"How Many Days Until {name}? ({days} days)",
             f"Live countdown: {days} days until {name} on {d.strftime('%B %-d, %Y')}.", body, priority="0.7")
    rows.sort()
    cds = "".join(f'<a class="cd" href="/countdown/{s}/"><b>{n}</b><span>days to {e(name)}</span></a>' for d, s, name, n in rows)
    page("countdown/", "Holiday Countdowns", "Live countdowns to Christmas, Halloween, Thanksgiving and every big holiday.",
         f'<h1>Holiday countdowns</h1><div class="cds big">{cds}</div>', priority="0.7")


def build_puzzle():
    body = """
<article class="puzzle">
  <p class="kicker">Daily word puzzle</p>
  <h1>Guess today's five-letter word</h1>
  <p class="lead">You have six tries. Green = right letter, right spot. Yellow = right letter, wrong spot. Grey = not in the word. A new word every day at midnight.</p>
  <div id="board" class="board" aria-live="polite"></div>
  <p id="msg" class="msg"></p>
  <div id="kb" class="kb"></div>
  <h2>How to play</h2>
  <p>Type any five-letter word and press Enter. Use the colour clues to narrow it down. Everybody gets the same word on the same day, so you can compare results with friends.</p>
</article>
<script src="/assets/puzzle.js" defer></script>"""
    page("puzzle/", "Daily Word Puzzle – Guess the 5-Letter Word",
         "A free daily five-letter word guessing game. Six tries, new word every day.", body, priority="0.9")


def build_legal():
    email = e(C["contact_email"])
    page("about/", f"About {SITE}", f"Who we are and what {SITE} publishes.", f"""
<article class="post"><h1>About {e(SITE)}</h1>
<p>{e(SITE)} is a light-hearted daily destination for curious people. Every day we publish fresh horoscopes for all twelve zodiac signs, a new general-knowledge trivia quiz, a five-letter word puzzle, live holiday countdowns, and easy-to-read explainers about the subjects people are curious about.</p>
<h2>How we create content</h2>
<p>Our editorial process uses AI-assisted drafting under strict guidelines: evergreen, family-friendly topics only; no news reporting, no medical, legal or financial advice; and only well-established facts. Horoscopes and quizzes are entertainment. If you spot a mistake, please <a href="/contact/">contact us</a> and we will correct it quickly.</p>
<h2>Contact</h2><p>Email: <a href="mailto:{email}">{email}</a></p></article>""", priority="0.3")
    page("contact/", "Contact Us", f"How to reach the {SITE} team.", f"""
<article class="post"><h1>Contact us</h1>
<p>Questions, corrections, partnership ideas or feedback? We read every message.</p>
<p class="lead"><a href="mailto:{email}">{email}</a></p>
<p>We usually reply within 2–3 business days.</p></article>""", priority="0.3")
    page("privacy/", "Privacy Policy", f"Privacy policy for {SITE}.", f"""
<article class="post"><h1>Privacy Policy</h1><p class="muted">Last updated: {TODAY.strftime("%B %-d, %Y")}</p>
<p>This policy explains what information is collected when you visit {e(SITE)} ({e(URL)}).</p>
<h2>Information we collect</h2>
<p>We do not ask you to create an account and we do not collect your name, address or other personal details through forms. If you email us, we use your email address only to reply.</p>
<p>Game progress (for example, your daily puzzle guesses) is stored only in your own browser and is never sent to us.</p>
<h2>Advertising and cookies</h2>
<p>We use Google AdSense to show advertising. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this website or other websites. Google's use of advertising cookies enables it and its partners to serve ads to you based on your visit to this site and/or other sites on the Internet.</p>
<p>You may opt out of personalised advertising by visiting <a href="https://www.google.com/settings/ads" rel="nofollow">Google Ads Settings</a>, or opt out of some third-party vendors' use of cookies for personalised advertising at <a href="https://www.aboutads.info/choices/" rel="nofollow">www.aboutads.info</a>. Learn more about <a href="https://policies.google.com/technologies/partner-sites" rel="nofollow">how Google uses information from sites that use its services</a>.</p>
<p>Visitors in the European Economic Area, the UK and Switzerland are asked for consent through a consent message before personalised ads are shown.</p>
<h2>Children</h2><p>This site is not directed to children under 13 and we do not knowingly collect information from them.</p>
<h2>Changes and contact</h2><p>We may update this policy; the date above shows the latest version. Questions: <a href="mailto:{email}">{email}</a>.</p></article>""", priority="0.2")
    page("terms/", "Terms of Use", f"Terms of use for {SITE}.", f"""
<article class="post"><h1>Terms of Use</h1><p class="muted">Last updated: {TODAY.strftime("%B %-d, %Y")}</p>
<p>By using {e(SITE)} you agree to these terms.</p>
<h2>Entertainment and general information</h2><p>Horoscopes, quizzes and puzzles are provided for entertainment. Articles are general information and are not professional advice of any kind. We work to keep content accurate but cannot guarantee it is complete or error-free.</p>
<h2>Intellectual property</h2><p>All content on this site is owned by {e(SITE)} unless stated otherwise. You may share links freely; please do not republish full pages without permission.</p>
<h2>External links and ads</h2><p>We are not responsible for the content of third-party websites or advertisements.</p>
<h2>Contact</h2><p><a href="mailto:{email}">{email}</a></p></article>""", priority="0.2")


def build_misc():
    shutil.copytree(ASSETS, OUT / "assets", dirs_exist_ok=True)
    (OUT / "404.html").write_text((OUT / "index.html").read_text(encoding="utf-8").replace(
        '<section class="hero">', '<section class="hero"><p class="kicker">Page not found — but here is today\'s fun:</p>', 1), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n", encoding="utf-8")
    if C.get("adsense_client"):
        pub = C["adsense_client"].replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    host = URL.split("://", 1)[-1]
    if "example.com" not in host and "github.io" not in host:
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    urls = "".join(f"<url><loc>{e(u)}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority></url>" for u, p in sitemap)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
        encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    build_home()
    build_horoscopes()
    build_trivia()
    build_puzzle()
    build_articles()
    build_countdowns()
    build_legal()
    build_misc()
    print(f"Built {len(sitemap)} pages into {OUT} "
          f"({len(horoscopes)} horoscope days, {len(trivia)} quizzes, {len(articles)} articles)")


if __name__ == "__main__":
    main()
