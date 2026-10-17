#!/usr/bin/env python3
"""Builds the multilingual static website from content/ into public/. No extra packages needed.

English lives at the site root, every other language under /<code>/ (for example /fr/).
A language is published only once its interface strings exist in content/i18n/<code>/ui.json
(the daily agent creates them), and only the content that has been translated is shown in it.
"""
import datetime as dt
import hashlib
import html
import json
import random
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = ROOT / "public"
C = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SITE = C["site_name"]
URL = C["site_url"].rstrip("/")
BASE = "/" + URL.split("://", 1)[-1].split("/", 1)[1] if "/" in URL.split("://", 1)[-1] else ""
TODAY = dt.datetime.now(dt.timezone.utc).date()
UI_EN = json.loads((HERE / "ui_en.json").read_text(encoding="utf-8"))
RTL = {"ar", "he", "fa", "ur"}
NATIVE = {"en": "English", "es": "Español", "fr": "Français", "de": "Deutsch", "pt": "Português", "it": "Italiano",
          "ja": "日本語", "ar": "العربية", "nl": "Nederlands", "pl": "Polski", "tr": "Türkçe", "id": "Bahasa Indonesia",
          "hi": "हिन्दी", "ko": "한국어", "ru": "Русский", "sv": "Svenska", "zh": "中文", "vi": "Tiếng Việt", "th": "ไทย",
          "uk": "Українська"}
e = html.escape

SIGNS = {  # glyph, element, (start month, day), (end month, day)
    "aries": ("♈", "fire", (3, 21), (4, 19)), "taurus": ("♉", "earth", (4, 20), (5, 20)),
    "gemini": ("♊", "air", (5, 21), (6, 20)), "cancer": ("♋", "water", (6, 21), (7, 22)),
    "leo": ("♌", "fire", (7, 23), (8, 22)), "virgo": ("♍", "earth", (8, 23), (9, 22)),
    "libra": ("♎", "air", (9, 23), (10, 22)), "scorpio": ("♏", "water", (10, 23), (11, 21)),
    "sagittarius": ("♐", "fire", (11, 22), (12, 21)), "capricorn": ("♑", "earth", (12, 22), (1, 19)),
    "aquarius": ("♒", "air", (1, 20), (2, 18)), "pisces": ("♓", "water", (2, 19), (3, 20)),
}
ELEMENT_COLORS = {"fire": ("#ff7a45", "#ffb347"), "earth": ("#3fa36b", "#a3c76d"),
                  "air": ("#5b8def", "#9fc3ff"), "water": ("#6a4cf5", "#3fc1c9")}
CATEGORY_STYLE = {  # two colors + emoji used for generated cover art
    "Entertainment": ("#ff5e7e", "#ffb26b", "🎬"), "Science": ("#4b6cff", "#3fd0c9", "🔬"),
    "Food": ("#ff8a3d", "#ffd166", "🍳"), "Travel": ("#1fb5a8", "#7dd3fc", "✈️"),
    "Sports": ("#22a95b", "#c4e86b", "🏆"), "Lifestyle": ("#d36bff", "#ffb3d9", "🌿"),
    "Tech": ("#3a4bd8", "#8f7bff", "💡"), "History": ("#b8793b", "#f2c98a", "🏛️"),
    "Animals": ("#2f9e6e", "#ffd36b", "🐾"), "Explainer": ("#6b4eff", "#ff8a3d", "✨"),
}
HOLIDAY_EMOJI = {"christmas": "🎄", "new-year": "🎆", "halloween": "🎃", "valentines-day": "💝",
                 "thanksgiving": "🦃", "easter": "🐣", "fourth-of-july": "🎇", "mothers-day": "💐",
                 "fathers-day": "👔", "st-patricks-day": "☘️", "memorial-day": "🇺🇸", "labor-day": "🛠️",
                 "black-friday": "🛍️"}


# ---------------------------------------------------------------- data
def load(folder):
    items = []
    for f in sorted(folder.glob("*.json")):
        try:
            items.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception as ex:
            print(f"skip broken file {f}: {ex}")
    return [i for i in items if i.get("date", "") <= str(TODAY)]  # never publish future-dated content


def lang_data(lang):
    base = CONTENT if lang == "en" else CONTENT / "i18n" / lang
    ui = dict(UI_EN)
    if lang != "en":
        ui.update(json.loads((base / "ui.json").read_text(encoding="utf-8")))
    return {
        "ui": ui,
        "horoscopes": sorted(load(base / "horoscopes"), key=lambda x: x["date"]),
        "trivia": sorted(load(base / "trivia"), key=lambda x: x["date"]),
        "articles": sorted(load(base / "articles"), key=lambda x: (x["date"], x["title"]), reverse=True),
    }


LANGS = ["en"] + [l for l in C.get("languages", []) if l != "en" and (CONTENT / "i18n" / l / "ui.json").exists()]
DATA = {l: lang_data(l) for l in LANGS}


# ---------------------------------------------------------------- helpers
def P(lang):
    return "" if lang == "en" else f"/{lang}"


def T(lang, key, **kw):
    s = DATA[lang]["ui"].get(key, UI_EN.get(key, key))
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def fdate(lang, iso, short=False):
    d = dt.date.fromisoformat(iso) if isinstance(iso, str) else iso
    ui = DATA[lang]["ui"]
    fmt = ui.get("short_date_format" if short else "date_format", UI_EN["date_format"])
    months = ui.get("months_short", UI_EN["months_short"]) if short else ui["months"]
    return (fmt.replace("{weekday}", ui["weekdays"][d.weekday()]).replace("{month}", months[d.month - 1])
            .replace("{day}", str(d.day)).replace("{year}", str(d.year)))


def sign_name(lang, s):
    return DATA[lang]["ui"].get("signs", {}).get(s, s.title())


def sign_range(lang, s):
    (m1, d1), (m2, d2) = SIGNS[s][2], SIGNS[s][3]
    return f"{fdate(lang, dt.date(2024, m1, d1), True)} – {fdate(lang, dt.date(2024, m2, d2), True)}"


def cat_name(lang, c):
    return DATA[lang]["ui"].get("categories", {}).get(c, c)


def rng(seed):
    return random.Random(int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))


# ---------------------------------------------------------------- original illustrations (inline SVG)
def sign_art(sign, size=64):
    glyph, element, _, _ = SIGNS[sign]
    c1, c2 = ELEMENT_COLORS[element]
    r = rng(sign)
    pts = [(r.uniform(14, 86), r.uniform(14, 86)) for _ in range(6)]
    lines = "".join(f'<line x1="{a[0]:.0f}" y1="{a[1]:.0f}" x2="{b[0]:.0f}" y2="{b[1]:.0f}"/>' for a, b in zip(pts, pts[1:]))
    stars = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.uniform(1.4, 2.6):.1f}"/>' for x, y in pts)
    gid = f"g-{sign}"
    return (f'<svg class="medal" width="{size}" height="{size}" viewBox="0 0 100 100" aria-hidden="true">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
            f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
            f'<circle cx="50" cy="50" r="48" fill="url(#{gid})"/>'
            f'<g stroke="#fff" stroke-opacity=".35" stroke-width="1">{lines}</g><g fill="#fff" fill-opacity=".8">{stars}</g>'
            f'<text x="50" y="52" text-anchor="middle" dominant-baseline="central" font-size="40" fill="#fff">{glyph}</text></svg>')


def cover_art(seed, category, cls="cover"):
    c1, c2, emoji = CATEGORY_STYLE.get(category, CATEGORY_STYLE["Explainer"])
    return art(seed, c1, c2, emoji, cls)


GAMES = {  # slug: (ui title key, ui desc key, ui how key, colors, emoji)
    "memory": ("game_memory", "game_memory_desc", "how_memory", ("#ff5e7e", "#ffb26b"), "🧠"),
    "2048": ("game_2048", "game_2048_desc", "how_2048", ("#ff8a3d", "#ffd166"), "🔢"),
    "tictactoe": ("game_ttt", "game_ttt_desc", "how_ttt", ("#4b6cff", "#3fd0c9"), "❌⭕"),
}


def art(seed, c1, c2, emoji, cls="cover"):
    r = rng(seed)
    blobs = "".join(
        f'<circle cx="{r.uniform(0, 400):.0f}" cy="{r.uniform(0, 200):.0f}" r="{r.uniform(30, 110):.0f}" '
        f'fill="#fff" fill-opacity="{r.uniform(.07, .2):.2f}"/>' for _ in range(5))
    rings = "".join(
        f'<circle cx="{r.uniform(40, 360):.0f}" cy="{r.uniform(20, 180):.0f}" r="{r.uniform(10, 40):.0f}" '
        f'fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>' for _ in range(3))
    gid = "c" + hashlib.md5(seed.encode()).hexdigest()[:8]
    return (f'<svg class="{cls}" viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
            f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
            f'<rect width="400" height="200" fill="url(#{gid})"/>{blobs}{rings}'
            f'<text x="200" y="104" text-anchor="middle" dominant-baseline="central" font-size="64">{emoji}</text></svg>')


HERO_ART = """<svg class="hero-art" viewBox="0 0 320 260" aria-hidden="true">
<defs><linearGradient id="hs" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb347"/><stop offset="1" stop-color="#ff5e7e"/></linearGradient>
<linearGradient id="hm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8f7bff"/><stop offset="1" stop-color="#5b3df5"/></linearGradient></defs>
<ellipse cx="160" cy="135" rx="150" ry="58" fill="none" stroke="currentColor" stroke-opacity=".18" stroke-width="2" stroke-dasharray="4 8" transform="rotate(-14 160 135)"/>
<circle cx="150" cy="130" r="70" fill="url(#hs)"/>
<circle cx="250" cy="70" r="34" fill="url(#hm)"/><circle cx="262" cy="62" r="30" fill="var(--bg)"/>
<circle cx="56" cy="210" r="16" fill="#3fc1c9"/>
<g fill="#ffb347"><path d="M40 52l4 10 10 4-10 4-4 10-4-10-10-4 10-4z"/><path d="M286 180l3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/></g>
<g fill="currentColor" fill-opacity=".5"><circle cx="96" cy="40" r="2.5"/><circle cx="210" cy="24" r="2"/><circle cx="300" cy="128" r="2.5"/><circle cx="24" cy="130" r="2"/><circle cx="230" cy="232" r="2.5"/></g>
<text x="150" y="132" text-anchor="middle" dominant-baseline="central" font-size="56">✨</text></svg>"""


# ---------------------------------------------------------------- page registry
PAGES = {}  # (lang, path) -> dict


def add(lang, path, title, desc, body, schema=None, priority="0.6"):
    PAGES[(lang, path)] = dict(title=title, desc=desc, body=body, schema=schema, priority=priority)


def lang_menu(lang, path):
    items = []
    for l in LANGS:
        target = (P(l) + "/" + path) if (l, path) in PAGES else (P(l) + "/")
        cur = ' aria-current="true"' if l == lang else ""
        items.append(f'<a href="{e(target)}" data-l="{l}" hreflang="{l}" lang="{l}"{cur}>{e(NATIVE.get(l, l))}</a>')
    return items


def render(lang, path, pg):
    canonical = f"{URL}{P(lang)}/{path}"
    alts = {l: f"{URL}{P(l)}/{path}" for l in LANGS if (l, path) in PAGES}
    hreflang = "".join(f'<link rel="alternate" hreflang="{l}" href="{e(u)}">' for l, u in alts.items())
    if "en" in alts:
        hreflang += f'<link rel="alternate" hreflang="x-default" href="{e(alts["en"])}">'
    rel_alts = {l: f"{P(l)}/{path}" for l in alts}
    ads = ""
    if C.get("adsense_client"):
        ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(C["adsense_client"])}" '
               'crossorigin="anonymous"></script>')
    ld = f'<script type="application/ld+json">{json.dumps(pg["schema"], ensure_ascii=False)}</script>' if pg["schema"] else ""
    title = pg["title"] if SITE in pg["title"] else f'{pg["title"]} | {SITE}'
    extra_font = {"ar": "&family=Noto+Kufi+Arabic:wght@400;600;800", "ja": "&family=Noto+Sans+JP:wght@400;700"}.get(lang, "")
    menu = "".join(lang_menu(lang, path))
    auto = (f"<script>(function(){{try{{if(/bot|crawl|spider|slurp|lighthouse|inspection/i.test(navigator.userAgent))return;"
            f"var L={json.dumps(LANGS)},cur={json.dumps(lang)},alt={json.dumps(rel_alts)},p=null;"
            f"try{{p=localStorage.getItem('dt-lang')}}catch(x){{}}"
            f"if(!p&&cur==='en'){{var n=(navigator.languages||[navigator.language||'en']);"
            f"for(var i=0;i<n.length;i++){{var c=(n[i]||'').slice(0,2).toLowerCase();if(L.indexOf(c)>-1){{p=c;break}}}}}}"
            f"if(p&&p!==cur&&alt[p]&&location.pathname.indexOf('/puzzle/')<0)location.replace({json.dumps(BASE)}+alt[p]+location.search);"
            f"}}catch(x){{}}}})();</script>")
    pre = P(lang)
    tg = f'<a href="https://t.me/{e(C["telegram_channel"])}" rel="noopener">Telegram</a>' if C.get("telegram_channel") else ""
    doc = f"""<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang in RTL else 'ltr'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(pg['desc'])}">
<link rel="canonical" href="{e(canonical)}">
{hreflang}
<meta property="og:title" content="{e(pg['title'])}">
<meta property="og:description" content="{e(pg['desc'])}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:site_name" content="{e(SITE)}">
<meta property="og:locale" content="{lang}">
<meta name="theme-color" content="#5b3df5">
{auto}
<link rel="alternate" type="application/rss+xml" title="{e(SITE)} ({lang})" href="{pre}/feed.xml">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{e(SITE)}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="mobile-web-app-capable" content="yes">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Inter:wght@400;500;600{extra_font}&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
{ads}
{ld}
</head>
<body class="lang-{lang}">
<header class="top">
  <div class="wrap nav">
    <a class="brand" href="{pre}/"><span class="logo">✦</span>{e(SITE)}</a>
    <nav>
      <a href="{pre}/horoscope/">{e(T(lang, 'nav_horoscopes'))}</a>
      <a href="{pre}/trivia/">{e(T(lang, 'nav_trivia'))}</a>
      <a href="{pre}/games/">{e(T(lang, 'nav_games'))}</a>
      <a href="/puzzle/">{e(T(lang, 'nav_puzzle'))}</a>
      <a href="{pre}/articles/">{e(T(lang, 'nav_articles'))}</a>
      <a href="{pre}/countdown/">{e(T(lang, 'nav_countdowns'))}</a>
    </nav>
    <button id="install" class="install" hidden>📲 {e(T(lang, 'install_app'))}</button>
    <details class="langs"><summary aria-label="{e(T(lang, 'language_label'))}">🌐 {e(NATIVE.get(lang, lang))}</summary>
      <div class="menu">{menu}</div></details>
  </div>
</header>
<main class="wrap">
{pg['body']}
</main>
<footer class="foot">
  <div class="wrap">
    <p class="brand small-brand"><span class="logo">✦</span>{e(SITE)}</p>
    <p>{e(T(lang, 'tagline'))}.</p>
    <p class="links"><a href="{pre}/about/">{e(T(lang, 'about'))}</a><a href="{pre}/contact/">{e(T(lang, 'contact'))}</a><a href="{pre}/privacy/">{e(T(lang, 'privacy'))}</a><a href="{pre}/terms/">{e(T(lang, 'terms'))}</a><a href="{pre}/feed.xml">RSS</a>{tg}<a href="/sitemap.xml">Sitemap</a></p>
    <p class="small">{e(T(lang, 'footer_note'))} © {TODAY.year} {e(SITE)}</p>
  </div>
</footer>
<div id="appbanner" class="appbanner" hidden role="dialog" aria-label="{e(T(lang, 'banner_title'))}"
  data-play="{e(C.get('play_store_url', ''))}" data-how="{e(T(lang, 'banner_how'))}">
  <img src="/assets/icons/icon-192.png" alt="" width="52" height="52">
  <div class="ab-text"><b>{e(T(lang, 'banner_title'))}</b><span>{e(T(lang, 'banner_text'))}</span></div>
  <div class="ab-actions"><button class="btn small" id="ab-install">{e(T(lang, 'banner_install'))}</button>
  <button class="ab-later" id="ab-later">{e(T(lang, 'banner_later'))}</button></div>
  <ol class="ios-steps" hidden>
    <li><span class="ios-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12"/><path d="M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg></span>{e(T(lang, 'ios_step1'))}</li>
    <li><span class="ios-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4"/><path d="M12 8v8M8 12h8"/></svg></span>{e(T(lang, 'ios_step2'))}</li>
    <li><span class="ios-ic">✓</span>{e(T(lang, 'ios_step3'))}</li>
  </ol>
</div>
<script src="/assets/app.js" defer></script>
<script>document.querySelectorAll('.langs a').forEach(function(a){{a.addEventListener('click',function(){{try{{localStorage.setItem('dt-lang',a.dataset.l)}}catch(x){{}}}})}});</script>
</body>
</html>"""
    if BASE:
        doc = doc.replace('href="/', f'href="{BASE}/').replace('src="/', f'src="{BASE}/')
    out = OUT / (pre.lstrip("/")) / path / "index.html" if not path.endswith(".html") else OUT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return canonical, pg["priority"], alts


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
    return dt.date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


HOLIDAYS = {
    "christmas": lambda y: dt.date(y, 12, 25), "new-year": lambda y: dt.date(y, 1, 1),
    "halloween": lambda y: dt.date(y, 10, 31), "valentines-day": lambda y: dt.date(y, 2, 14),
    "thanksgiving": lambda y: nth_weekday(y, 11, 3, 4), "easter": easter,
    "fourth-of-july": lambda y: dt.date(y, 7, 4), "mothers-day": lambda y: nth_weekday(y, 5, 6, 2),
    "fathers-day": lambda y: nth_weekday(y, 6, 6, 3), "st-patricks-day": lambda y: dt.date(y, 3, 17),
    "memorial-day": lambda y: last_weekday(y, 5, 0), "labor-day": lambda y: nth_weekday(y, 9, 0, 1),
    "black-friday": lambda y: nth_weekday(y, 11, 3, 4) + dt.timedelta(days=1),
}


def next_date(fn):
    d = fn(TODAY.year)
    return d if d >= TODAY else fn(TODAY.year + 1)


def hname(lang, slug):
    return DATA[lang]["ui"].get("holidays", {}).get(slug, UI_EN["holidays"][slug])


def cd_card(lang, slug, big=False):
    d = next_date(HOLIDAYS[slug])
    return (f'<a class="cd" href="{P(lang)}/countdown/{slug}/"><span class="cd-emoji">{HOLIDAY_EMOJI.get(slug, "📅")}</span>'
            f'<b>{(d - TODAY).days}</b><span>{e(T(lang, "days_to", name=hname(lang, slug)))}</span></a>')


# ---------------------------------------------------------------- sections
def article_card(lang, a):
    cat = a.get("category", "Explainer")
    return (f'<a class="card art" href="{P(lang)}/articles/{e(a["slug"])}/">{cover_art(a["slug"], cat)}'
            f'<div class="card-body"><span class="tag">{e(cat_name(lang, cat))}</span>'
            f'<h3>{e(a["title"])}</h3><p>{e(a["description"])}</p></div></a>')


def game_card(lang, slug):
    title, desc, _, (c1, c2), emoji = GAMES[slug]
    return (f'<a class="card art" href="{P(lang)}/games/{slug}/">{art("game-" + slug, c1, c2, emoji)}'
            f'<div class="card-body"><span class="tag">🎮 {e(T(lang, "play"))}</span><h3>{e(T(lang, title))}</h3>'
            f'<p>{e(T(lang, desc))}</p></div></a>')


def more_fun(lang):
    quiz = (f'<a class="card art" href="{P(lang)}/trivia/">{art("quiz", "#5b3df5", "#8f7bff", "🧠")}'
            f'<div class="card-body"><span class="tag">❓ {e(T(lang, "daily_trivia"))}</span><h3>{e(T(lang, "start_quiz"))}</h3>'
            f'<p>{e(T(lang, "trivia_teaser", n=10))}</p></div></a>') if DATA[lang]["trivia"] else ""
    return (f'<section class="more-fun"><h2>✨ {e(T(lang, "more_fun"))}</h2><div class="grid">'
            f'{quiz}{"".join(game_card(lang, g) for g in GAMES)}</div></section>')


def facts(lang, n=3):
    pool = [q.get("fun_fact", "") for t in DATA[lang]["trivia"][-14:] for q in t["questions"] if q.get("fun_fact")]
    if not pool:
        return ""
    r = random.Random(str(TODAY) + lang)
    pick = r.sample(pool, min(n, len(pool)))
    cards = "".join(f'<div class="fact-card"><span class="fact-emoji">{em}</span><p>{e(f)}</p></div>'
                    for em, f in zip(["💡", "🌍", "🔭", "🐾", "🎨"], pick))
    return f'<section><h2>🤔 {e(T(lang, "did_you_know"))}</h2><div class="facts">{cards}</div></section>'


def sign_grid(lang):
    return "".join(
        f'<a class="sign" href="{P(lang)}/horoscope/{s}/">{sign_art(s, 56)}<b>{e(sign_name(lang, s))}</b>'
        f'<small>{e(sign_range(lang, s))}</small></a>' for s in SIGNS)


def build_lang(lang):
    D = DATA[lang]
    pre = P(lang)
    H, TR, AR = D["horoscopes"], D["trivia"], D["articles"]

    # home
    h, t = (H[-1] if H else None), (TR[-1] if TR else None)
    upcoming = sorted(HOLIDAYS, key=lambda s: next_date(HOLIDAYS[s]))[:4]
    latest = "".join(article_card(lang, a) for a in AR[:9]) or f"<p class='muted'>{e(T(lang, 'new_daily'))}</p>"
    body = f"""
<section class="hero-top">
  <div class="hero-head">
    <div><p class="kicker">{e(fdate(lang, TODAY))}</p>
    <h1>{e(T(lang, 'hero_title'))}</h1></div>
  </div>
  <div class="sec-head"><h2>🔮 {e(T(lang, 'daily_horoscope'))}</h2>{f'<span class="muted">{e(T(lang, "updated_on", date=fdate(lang, h["date"])))}</span>' if h else ''}</div>
  <div class="signs">{sign_grid(lang)}</div>
</section>
{facts(lang)}
<section class="split">
  <div class="panel quiz-panel">
    <span class="panel-emoji">🧠</span>
    <h2>{e(t["title"]) if t else e(T(lang, 'daily_trivia'))}</h2>
    <p>{e(T(lang, 'trivia_teaser', n=len(t["questions"]) if t else 10))}</p>
    <a class="btn" href="{pre}/trivia/">{e(T(lang, 'start_quiz'))}</a>
  </div>
  <div class="panel">
    <h2>⏳ {e(T(lang, 'upcoming_countdowns'))}</h2>
    <div class="cds">{''.join(cd_card(lang, s) for s in upcoming)}</div>
  </div>
</section>
<section>
  <div class="sec-head"><h2>🎮 {e(T(lang, 'games_title'))}</h2><a href="{pre}/games/">{e(T(lang, 'see_all'))} →</a></div>
  <div class="grid">{''.join(game_card(lang, g) for g in GAMES)}<a class="card art" href="/puzzle/">{art("puzzle", "#2f9e6e", "#c4e86b", "🔤")}<div class="card-body"><span class="tag">🎮 {e(T(lang, 'play'))}</span><h3>{e(T(lang, 'nav_puzzle'))}</h3><p>{e(T(lang, 'hero_cta_puzzle'))}</p></div></a></div>
</section>
<section>
  <div class="sec-head"><h2>📖 {e(T(lang, 'latest_explainers'))}</h2><a href="{pre}/articles/">{e(T(lang, 'see_all'))} →</a></div>
  <div class="grid">{latest}</div>
</section>"""
    add(lang, "", f"{SITE} — {T(lang, 'home_title')}", T(lang, "tagline"), body,
        {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": f"{URL}{pre}/", "inLanguage": lang}, "1.0")

    # horoscopes
    if H:
        latest_h = H[-1]
        cards = "".join(
            f'<a class="card hcard" href="{pre}/horoscope/{s}/">{sign_art(s, 52)}<div><h3>{e(sign_name(lang, s))}</h3>'
            f'<p>{e(latest_h["signs"][s]["overview"][:140])}…</p></div></a>' for s in SIGNS)
        archive = "".join(f'<a href="{pre}/horoscope/archive/{x["date"]}/">{e(fdate(lang, x["date"]))}</a>' for x in reversed(H[-60:]))
        add(lang, "horoscope/", T(lang, "horoscopes_title"), T(lang, "horoscopes_desc", date=fdate(lang, latest_h["date"])),
            f'<h1>{e(T(lang, "horoscopes_title"))}</h1><p class="muted">{e(fdate(lang, latest_h["date"]))}</p>'
            f'<div class="grid">{cards}</div><h2>{e(T(lang, "past_days"))}</h2><div class="chips">{archive}</div>', priority="0.9")
        for s in SIGNS:
            dd = latest_h["signs"][s]
            others = "".join(f'<a href="{pre}/horoscope/{o}/">{SIGNS[o][0]} {e(sign_name(lang, o))}</a>' for o in SIGNS if o != s)
            body = f"""
<article class="reading">
  <div class="reading-head">{sign_art(s, 96)}<div>
    <p class="kicker">{e(fdate(lang, latest_h["date"]))} · {e(sign_range(lang, s))}</p>
    <h1>{e(T(lang, 'horoscope_today', sign=sign_name(lang, s)))}</h1></div></div>
  <p class="lead">{e(dd["overview"])}</p>
  <div class="facets">
    <div><h3>❤️ {e(T(lang, 'love'))}</h3><p>{e(dd["love"])}</p></div>
    <div><h3>💼 {e(T(lang, 'career'))}</h3><p>{e(dd["career"])}</p></div>
    <div><h3>🌿 {e(T(lang, 'wellness'))}</h3><p>{e(dd["wellness"])}</p></div>
  </div>
  <div class="lucky">
    <span>🍀 {e(T(lang, 'lucky_number'))} <b>{e(str(dd["lucky_number"]))}</b></span>
    <span>🎨 {e(T(lang, 'lucky_color'))} <b>{e(str(dd["lucky_color"]))}</b></span>
    <span>✨ {e(T(lang, 'mood'))} <b>{e(str(dd["mood"]))}</b></span>
  </div>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <h2>{e(T(lang, 'other_signs'))}</h2>
  <div class="chips">{others}</div>
</article>
{more_fun(lang)}"""
            add(lang, f"horoscope/{s}/", f'{T(lang, "horoscope_today", sign=sign_name(lang, s))} – {fdate(lang, latest_h["date"])}',
                dd["overview"][:150], body, priority="0.9")
        for x in H:
            links = "".join(f'<a class="card hcard" href="{pre}/horoscope/{s}/">{sign_art(s, 52)}<div><h3>{e(sign_name(lang, s))}</h3>'
                            f'<p>{e(x["signs"][s]["overview"])}</p></div></a>' for s in SIGNS)
            add(lang, f"horoscope/archive/{x['date']}/", T(lang, "horoscopes_for", date=fdate(lang, x["date"])),
                T(lang, "horoscopes_for", date=fdate(lang, x["date"])),
                f'<h1>{e(T(lang, "horoscopes_for", date=fdate(lang, x["date"])))}</h1><div class="grid">{links}</div>', priority="0.4")
    elif lang == "en":
        add(lang, "horoscope/", T(lang, "horoscopes_title"), T(lang, "tagline"),
            f'<h1>{e(T(lang, "horoscopes_title"))}</h1><p>{e(T(lang, "being_prepared"))}</p>')

    # trivia
    def trivia_body(t):
        qs = []
        for i, q in enumerate(t["questions"]):
            opts = "".join(f'<button class="opt" data-i="{j}"><span class="opt-l">{"ABCD"[j]}</span>{e(o)}</button>'
                           for j, o in enumerate(q["options"]))
            qs.append(f'<div class="q" data-answer="{q["answer_index"]}"><p class="qcat">{e(T(lang, "question_n", n=i + 1))} · '
                      f'{e(str(q.get("category", "")))}</p><h3>{e(q["question"])}</h3><div class="opts">{opts}</div>'
                      f'<p class="fact" hidden>💡 {e(q.get("fun_fact", ""))}</p></div>')
        past = "".join(f'<a href="{pre}/trivia/{x["date"]}/">{e(fdate(lang, x["date"]))}</a>' for x in reversed(TR[-60:]) if x is not t)
        return f"""
<article class="quiz">
  <div class="quiz-head"><span class="panel-emoji">🧠</span><div>
  <p class="kicker">{e(T(lang, 'trivia_kicker', date=fdate(lang, t["date"])))}</p>
  <h1>{e(t["title"])}</h1></div></div>
  <p class="lead">{e(T(lang, 'trivia_lead'))}</p>
  <div class="progress"><span id="bar"></span></div>
  {"".join(qs)}
  <div class="score" hidden><h2>{e(T(lang, 'you_scored'))} <span id="sc">0</span>/{len(t["questions"])}</h2><p>{e(T(lang, 'come_back'))}</p></div>
  {f'<h2>{e(T(lang, "previous_quizzes"))}</h2><div class="chips">{past}</div>' if past else ''}
</article>
{more_fun(lang)}
<script src="/assets/quiz.js" defer></script>"""
    for t in TR:
        add(lang, f"trivia/{t['date']}/", f"{t['title']} – {fdate(lang, t['date'])}",
            T(lang, "trivia_desc", date=fdate(lang, t["date"]), n=len(t["questions"])), trivia_body(t),
            {"@context": "https://schema.org", "@type": "Quiz", "name": t["title"], "datePublished": t["date"], "inLanguage": lang}, "0.5")
    if TR:
        t = TR[-1]
        add(lang, "trivia/", f"{T(lang, 'daily_trivia')} – {fdate(lang, t['date'])}",
            T(lang, "trivia_desc", date=fdate(lang, t["date"]), n=len(t["questions"])), trivia_body(t), priority="0.9")
    elif lang == "en":
        add(lang, "trivia/", T(lang, "daily_trivia"), T(lang, "tagline"), f'<h1>{e(T(lang, "daily_trivia"))}</h1><p>{e(T(lang, "being_prepared"))}</p>')

    # articles
    for a in AR:
        cat = a.get("category", "Explainer")
        secs = "".join(f'<h2>{e(s["heading"])}</h2>' + "".join(f"<p>{e(p)}</p>" for p in s.get("paragraphs", [])) for s in a["sections"])
        faq = "".join(f'<details><summary>{e(f["q"])}</summary><p>{e(f["a"])}</p></details>' for f in a.get("faq", []))
        rel = [x for x in AR if x is not a and x.get("category") == cat][:3] or [x for x in AR if x is not a][:3]
        schema = [{"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": a["description"],
                   "datePublished": a["date"], "inLanguage": lang,
                   "author": {"@type": "Organization", "name": f"{SITE} Editorial Team"}, "publisher": {"@type": "Organization", "name": SITE}}]
        if a.get("faq"):
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in a["faq"]]})
        body = f"""
<article class="post">
  {cover_art(a["slug"], cat, "banner")}
  <p class="kicker">{e(cat_name(lang, cat))} · {e(fdate(lang, a["date"]))}</p>
  <h1>{e(a["title"])}</h1>
  <p class="lead">{e(a["description"])}</p>
  {secs}
  {f'<h2>{e(T(lang, "faq"))}</h2><div class="faq">{faq}</div>' if faq else ''}
  <p class="small muted">{T(lang, 'written_by', site=e(SITE), contact_url=pre + '/contact/')}</p>
</article>
{f'<section><h2>{e(T(lang, "keep_reading"))}</h2><div class="grid">{"".join(article_card(lang, x) for x in rel)}</div></section>' if rel else ''}
{more_fun(lang)}"""
        add(lang, f"articles/{a['slug']}/", a["title"], a["description"], body, schema, "0.7")
    if AR or lang == "en":
        cats = sorted({cat_name(lang, a.get("category", "Explainer")) for a in AR})
        cards = "".join(article_card(lang, a) for a in AR) or f"<p class='muted'>{e(T(lang, 'new_daily'))}</p>"
        add(lang, "articles/", T(lang, "explainers_title"), T(lang, "explainers_desc"),
            f'<h1>{e(T(lang, "explainers_title"))}</h1><p class="muted">{e(T(lang, "articles_count", n=len(AR)))} · {e(", ".join(cats))}</p>'
            f'<div class="grid">{cards}</div>', priority="0.8")

    # countdowns
    for slug, fn in HOLIDAYS.items():
        d = next_date(fn)
        days = (d - TODAY).days
        name = hname(lang, slug)
        more = "".join(f'<a href="{pre}/countdown/{s}/">{HOLIDAY_EMOJI.get(s, "")} {e(hname(lang, s))}</a>' for s in HOLIDAYS if s != slug)
        body = f"""
<article class="countdown" data-target="{d.isoformat()}T00:00:00">
  <div class="cd-hero"><span class="cd-big">{HOLIDAY_EMOJI.get(slug, "📅")}</span><div>
  <p class="kicker">{e(T(lang, 'countdown'))}</p>
  <h1>{e(T(lang, 'how_many_days', name=name))}</h1></div></div>
  <p class="lead">{T(lang, 'falls_on', name=e(name), date=e(fdate(lang, d)), days=days)}</p>
  <div class="ticker"><div><b id="d">{days}</b><span>{e(T(lang, 'days'))}</span></div><div><b id="h">0</b><span>{e(T(lang, 'hours'))}</span></div>
  <div><b id="m">0</b><span>{e(T(lang, 'minutes'))}</span></div><div><b id="s">0</b><span>{e(T(lang, 'seconds'))}</span></div></div>
  <p class="small muted">{e(T(lang, 'timer_note'))}</p>
  <h2>{e(T(lang, 'more_countdowns'))}</h2><div class="chips">{more}</div>
</article>
<script src="/assets/countdown.js" defer></script>"""
        add(lang, f"countdown/{slug}/", f"{T(lang, 'how_many_days', name=name)} ({days})",
            re.sub("<[^>]+>", "", T(lang, "falls_on", name=name, date=fdate(lang, d), days=days)), body, priority="0.7")
    rows = sorted(HOLIDAYS, key=lambda s: next_date(HOLIDAYS[s]))
    add(lang, "countdown/", T(lang, "countdowns_title"), T(lang, "countdowns_desc"),
        f'<h1>{e(T(lang, "countdowns_title"))}</h1><div class="cds big">{"".join(cd_card(lang, s) for s in rows)}</div>', priority="0.7")

    # games
    labels = {"data-new-game": T(lang, "new_game"), "data-moves": T(lang, "moves"), "data-score": T(lang, "score"),
              "data-best": T(lang, "best"), "data-won": T(lang, "you_won"), "data-lost": T(lang, "you_lost"),
              "data-draw": T(lang, "draw"), "data-turn": T(lang, "your_turn")}
    attrs = " ".join(f'{k}="{e(v)}"' for k, v in labels.items())
    add(lang, "games/", T(lang, "games_title"), T(lang, "games_desc"),
        f'<h1>🎮 {e(T(lang, "games_title"))}</h1><p class="lead">{e(T(lang, "games_desc"))}</p>'
        f'<div class="grid">{"".join(game_card(lang, g) for g in GAMES)}</div>', priority="0.8")
    for slug, (title, desc, how, _, emoji) in GAMES.items():
        others = "".join(game_card(lang, g) for g in GAMES if g != slug)
        body = f"""
<article class="gamepage">
  <p class="kicker">🎮 {e(T(lang, 'games_title'))}</p>
  <h1>{emoji} {e(T(lang, title))}</h1>
  <p class="lead">{e(T(lang, desc))}</p>
  <div id="game" data-game="{'ttt' if slug == 'tictactoe' else slug}" {attrs}></div>
  <h2>{e(T(lang, 'how_to_play'))}</h2><p>{e(T(lang, how))}</p>
</article>
<section><h2>✨ {e(T(lang, 'more_fun'))}</h2><div class="grid">{others}</div></section>
<script src="/assets/games.js" defer></script>"""
        add(lang, f"games/{slug}/", f"{T(lang, title)} – {T(lang, 'games_title')}", T(lang, desc), body,
            {"@context": "https://schema.org", "@type": "VideoGame", "name": T(lang, title), "inLanguage": lang,
             "gamePlatform": "Web browser", "applicationCategory": "Game"}, "0.7")

    # legal & contact
    fill = lambda s: s.replace("{site}", e(SITE)).replace("{url}", e(URL)).replace("{contact_url}", pre + "/contact/")
    add(lang, "about/", T(lang, "about_title", site=SITE), T(lang, "tagline"),
        f'<article class="post"><h1>{e(T(lang, "about_title", site=SITE))}</h1>{fill(T(lang, "about_html"))}</article>', priority="0.3")
    upd = e(T(lang, "last_updated", date=fdate(lang, TODAY)))
    add(lang, "privacy/", T(lang, "privacy"), f"{T(lang, 'privacy')} – {SITE}",
        f'<article class="post"><h1>{e(T(lang, "privacy"))}</h1><p class="muted">{upd}</p>{fill(T(lang, "privacy_html"))}</article>', priority="0.2")
    add(lang, "terms/", T(lang, "terms"), f"{T(lang, 'terms')} – {SITE}",
        f'<article class="post"><h1>{e(T(lang, "terms"))}</h1><p class="muted">{upd}</p>{fill(T(lang, "terms_html"))}</article>', priority="0.2")
    key = C.get("web3forms_key", "")
    if key:
        box = f"""
<form id="cf" class="cform" data-sending="{e(T(lang, 'form_sending'))}" data-ok="{e(T(lang, 'form_ok'))}" data-err="{e(T(lang, 'form_error'))}">
  <input type="hidden" name="access_key" value="{e(key)}">
  <input type="hidden" name="subject" value="New message from {e(SITE)} ({lang})">
  <input type="checkbox" name="botcheck" style="display:none" tabindex="-1" autocomplete="off">
  <label>{e(T(lang, 'form_name'))}<input name="name" required maxlength="100"></label>
  <label>{e(T(lang, 'form_email'))}<input name="email" type="email" required maxlength="150"></label>
  <label>{e(T(lang, 'form_message'))}<textarea name="message" required rows="6" maxlength="4000"></textarea></label>
  <button class="btn" type="submit">{e(T(lang, 'form_send'))}</button>
  <p id="cf-msg" class="msg" aria-live="polite"></p>
</form>
<script src="/assets/contact.js" defer></script>"""
    else:
        enc = C["contact_email"][::-1]
        box = (f'<p class="lead"><a id="em" href="#">{e(T(lang, "show_email"))}</a></p>'
               f'<script>(function(){{var a=document.getElementById("em");a.addEventListener("click",function(ev){{'
               f'var x={json.dumps(enc)}.split("").reverse().join("");if(a.dataset.on){{return}}ev.preventDefault();'
               f'a.dataset.on=1;a.href="mailto:"+x;a.textContent=x;}})}})();</script>')
    add(lang, "contact/", T(lang, "contact_title"), T(lang, "contact_lead"),
        f'<article class="post"><h1>{e(T(lang, "contact_title"))}</h1><p>{e(T(lang, "contact_lead"))}</p>{box}'
        f'<p class="muted">{e(T(lang, "contact_reply"))}</p></article>', priority="0.3")


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
    add("en", "puzzle/", "Daily Word Puzzle – Guess the 5-Letter Word",
        "A free daily five-letter word guessing game. Six tries, new word every day.", body, priority="0.9")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for lang in LANGS:
        build_lang(lang)
    build_puzzle()
    sitemap = [render(l, p, pg) for (l, p), pg in PAGES.items()]

    shutil.copytree(HERE / "assets", OUT / "assets", dirs_exist_ok=True)
    if (HERE / "root").exists():
        shutil.copytree(HERE / "root", OUT, dirs_exist_ok=True)
    home = (OUT / "index.html").read_text(encoding="utf-8")
    (OUT / "404.html").write_text(home.replace('<p class="kicker">', f'<p class="kicker">{e(UI_EN["not_found"])} · ', 1), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n", encoding="utf-8")
    if C.get("adsense_client"):
        (OUT / "ads.txt").write_text(f"google.com, {C['adsense_client'].replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    host = URL.split("://", 1)[-1]
    if "example.com" not in host and "github.io" not in host:
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    manifest = {
        "name": f"{SITE} – Horoscopes, Trivia & Games", "short_name": SITE, "id": "/", "start_url": "/?source=pwa",
        "scope": "/", "display": "standalone", "orientation": "portrait", "background_color": "#fbf8f3",
        "theme_color": "#5b3df5", "description": UI_EN["tagline"], "lang": "en", "dir": "ltr",
        "categories": ["entertainment", "games", "lifestyle"],
        "icons": [{"src": "/assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                  {"src": "/assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                  {"src": "/assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
        "shortcuts": [{"name": "Daily horoscope", "url": "/horoscope/"}, {"name": "Daily trivia", "url": "/trivia/"},
                      {"name": "Games", "url": "/games/"}],
    }
    (OUT / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    sw = (HERE / "sw.js").read_text(encoding="utf-8").replace("__VERSION__", dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M"))
    (OUT / "sw.js").write_text(sw, encoding="utf-8")
    offline = (OUT / "index.html").read_text(encoding="utf-8")
    start, end = offline.index("<main"), offline.index("</main>")
    (OUT / "offline.html").write_text(offline[:start] + f'<main class="wrap"><section class="hero-top" style="text-align:center;margin-top:30px">'
                                      f'<p style="font-size:3rem;margin:0">📡</p><h1>{e(UI_EN["offline_title"])}</h1><p class="lead">{e(UI_EN["offline_text"])}</p>'
                                      f'</section>' + offline[end:], encoding="utf-8")
    links = [{"relation": ["delegate_permission/common.handle_all_urls"],
              "target": {"namespace": "android_app", "package_name": C["android_package"],
                         "sha256_cert_fingerprints": sorted(set(C.get("android_sha256", []) + (
                             json.loads((ROOT / "android" / "fingerprints.json").read_text())
                             if (ROOT / "android" / "fingerprints.json").exists() else [])))}}] if C.get("android_package") else []
    if links:
        (OUT / ".well-known").mkdir(exist_ok=True)
        (OUT / ".well-known" / "assetlinks.json").write_text(json.dumps(links, indent=1), encoding="utf-8")
    for lang in LANGS:
        D = DATA[lang]
        items = []
        for a in D["articles"][:20]:
            link = f"{URL}{P(lang)}/articles/{a['slug']}/"
            pub = dt.datetime.fromisoformat(a["date"]).replace(hour=6, tzinfo=dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
            items.append(f"<item><title>{e(a['title'])}</title><link>{e(link)}</link><guid>{e(link)}</guid>"
                         f"<pubDate>{pub}</pubDate><description>{e(a['description'])}</description></item>")
        (OUT / P(lang).lstrip("/") / "feed.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{e(SITE)}</title><link>{e(URL)}{P(lang)}/</link><description>{e(T(lang, 'tagline'))}</description>"
            f"<language>{lang}</language>{''.join(items)}</channel></rss>", encoding="utf-8")
    urls = []
    for loc, pri, alts in sitemap:
        links = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{e(u)}"/>' for l, u in alts.items()) if len(alts) > 1 else ""
        urls.append(f"<url><loc>{e(loc)}</loc><lastmod>{TODAY}</lastmod><priority>{pri}</priority>{links}</url>")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        f'xmlns:xhtml="http://www.w3.org/1999/xhtml">{"".join(urls)}</urlset>', encoding="utf-8")
    counts = ", ".join(f"{l}: {len(DATA[l]['articles'])} articles" for l in LANGS)
    print(f"Built {len(PAGES)} pages in {len(LANGS)} language(s) ({counts})")


if __name__ == "__main__":
    main()
