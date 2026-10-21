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
HOLIDAY_EMOJI = {"ramadan": "🌙", "eid-al-fitr": "🌙", "eid-al-adha": "🐑", "islamic-new-year": "🕌", "mawlid": "✨", "chinese-new-year": "🧧", "christmas": "🎄", "new-year": "🎆", "halloween": "🎃", "valentines-day": "💝",
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


SIGN_KEYS = ("aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces")


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
        "guides": {g["sign"]: g for g in load(base / "signs") if g.get("sign") in SIGN_KEYS},
        "pairs": {x["slug"]: x for x in load(base / "pairs") if x.get("slug")},
        "yearly": {(x["year"], x["sign"]): x for x in load(base / "yearly") if x.get("sign") in SIGN_KEYS},
        "chinese": {x["animal"]: x for x in load(base / "chinese") if x.get("animal")},
        "numerology": {int(x["number"]): x for x in load(base / "numerology") if x.get("number")},
        "dreams": {x["symbol"]: x for x in load(base / "dreams") if x.get("symbol")},
        "guides2": load(base / "guides"),
        "names": {x["slug"]: x for x in load(base / "names") if x.get("slug") and x.get("nm")},
        "english": {x["slug"]: x for x in load(base / "english") if x.get("slug") and x.get("quiz")},
    }


DEFAULT_IMG = "/assets/sections/games.webp"
SECTION_IMG = {"dreams": "dreams", "tarot": "tarot", "tarot-meanings": "tarot", "compatibility": "compatibility",
               "love-calculator": "compatibility", "love-messages": "compatibility", "numerology": "numerology",
               "angel-numbers": "angel", "chinese-zodiac": "chinese", "moon-phase": "moon", "birthday": "birthday",
               "birthstones": "birthday", "age-calculator": "birthday", "games": "games", "trivia": "trivia", "zodiac-quiz": "trivia"}


def section_img(path):
    """Illustration for a page path ('dreams/snake/' -> /assets/sections/dreams.webp), or None."""
    parts = [x for x in path.split("/") if x]
    if not parts:
        return None
    if parts[0] in SECTION_IMG:
        return f"/assets/sections/{SECTION_IMG[parts[0]]}.webp"
    if parts[0] == "learn-english":
        return "/assets/english/hero.webp"
    if parts[0] in ("horoscope", "zodiac") and len(parts) > 1 and (HERE / "assets" / "signs" / f"{parts[1]}.webp").exists():
        return f"/assets/signs/{parts[1]}.webp"
    return None


CITIES = json.loads((Path(__file__).parent / "data" / "cities.json").read_text(encoding="utf-8"))
PRAYER_METHODS = {"morocco": {"f": 19, "i": 17, "mg": 5}, "algeria": {"f": 18, "i": 17}, "tunisia": {"f": 18, "i": 18},
                  "egypt": {"f": 19.5, "i": 17.5}, "ummalqura": {"f": 18.5, "i": "90"}, "uae": {"f": 18.2, "i": 18.2},
                  "qatar": {"f": 18, "i": "90"}, "kuwait": {"f": 18, "i": 17.5}, "jordan": {"f": 18, "i": 18},
                  "mwl": {"f": 18, "i": 17}, "turkey": {"f": 18, "i": 17}, "karachi": {"f": 18, "i": 18, "asr": 2},
                  "sea": {"f": 20, "i": 18}, "france": {"f": 12, "i": 12}, "isna": {"f": 15, "i": 15}}
EN_ORDER = json.loads((Path(__file__).parent / "data" / "english_lessons.json").read_text(encoding="utf-8"))
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
    if (HERE / "assets" / "signs" / f"{sign}.webp").exists():  # painted artwork when we have it
        return (f'<img class="medal pic" src="/assets/signs/{sign}.webp" width="{size}" height="{size}" '
                f'alt="" loading="lazy" decoding="async">')
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


GAMES = {  # slug: (title key, desc key, how key, colors, emoji, js name, best-score storage key)
    "block-puzzle": ("game_blocks", "game_blocks_desc", "how_blocks", ("#7c5cff", "#ff5e7e"), "🟪", "blocks", "dt-blocks-best"),
    "mahjong": ("game_mj", "game_mj_desc", "how_mj", ("#2f6b4f", "#c9b98f"), "🀄", "mahjong", None),
    "word-search": ("game_ws", "game_ws_desc", "how_ws", ("#2563eb", "#22c1c3"), "🔤", "wordsearch", None),
    "solitaire": ("game_solitaire", "game_solitaire_desc", "how_solitaire", ("#1f7a4f", "#3fc1c9"), "🃏", "solitaire", None),
    "chess": ("game_chess", "game_chess_desc", "how_chess", ("#5b3df5", "#1e1b2b"), "♟️", "chess", None),
    "ludo": ("game_ludo", "game_ludo_desc", "how_ludo", ("#e5484d", "#f5b301"), "🎲", "ludo", None),
    "sudoku": ("game_sudoku", "game_sudoku_desc", "how_sudoku", ("#3a4bd8", "#8f7bff"), "🧩", "sudoku", "dt-sdk-best-easy"),
    "math-rush": ("game_math", "game_math_desc", "how_math", ("#ff5e7e", "#ff8a3d"), "⚡", "math", "dt-math-best"),
    "memory": ("game_memory", "game_memory_desc", "how_memory", ("#d36bff", "#ffb3d9"), "🃏", "memory", "dt-mem-best-medium"),
    "color-memory": ("game_simon", "game_simon_desc", "how_simon", ("#1fb5a8", "#7dd3fc"), "🎨", "simon", "dt-simon-best"),
    "2048": ("game_2048", "game_2048_desc", "how_2048", ("#ff8a3d", "#ffd166"), "🔢", "2048", "dt-2048-best"),
    "tictactoe": ("game_ttt", "game_ttt_desc", "how_ttt", ("#2f9e6e", "#c4e86b"), "⭕", "ttt", None),
}
WS = json.loads((HERE / "data" / "wordsearch.json").read_text(encoding="utf-8"))
EXTERNAL_JS = ("chess", "ludo", "blocks", "solitaire", "wordsearch", "mahjong")
GAME_LABELS = ["new_game", "moves", "score", "best", "you_won", "you_lost", "draw", "your_turn", "easy", "medium", "hard",
               "time", "undo", "hint", "mistakes", "start", "play_again", "game_over", "new_record", "times_up", "combo",
               "wins", "losses", "draws", "level", "level_up", "day_streak", "too_many_mistakes", "math_intro", "watch",
               "your_turn_repeat", "simon_intro", "quick", "classic", "computer_turn", "captured", "try_again",
               "thinking", "check", "your_move", "checkmate_win", "checkmate_lose",
               "nice", "great", "amazing", "no_moves", "draw_1", "draw_3", "auto_finish", "ws_theme", "ws_found", "mj_pairs", "mj_shuffle", "mj_stuck", "badges", "badge_new",
               "daily", "b_first", "b_10", "b_50", "b_s3", "b_s7", "b_s30", "b_l5", "b_l10"]


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
<script>try{{var t=localStorage.getItem('dt-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<meta name="p:domain_verify" content="35643b0df7034260a8368e9d58182cfd"/>
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
<meta property="og:image" content="{URL}{e(section_img(path) or DEFAULT_IMG)}">
<meta name="twitter:card" content="summary_large_image">
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
      <a href="{pre}/search/" aria-label="{e(T(lang, 'search_title'))}">🔍</a>
      <a href="{pre}/horoscope/">🔮 {e(T(lang, 'nav_horoscopes'))}</a>
      <a href="{pre}/games/">🎮 {e(T(lang, 'nav_games'))}</a>
      <a href="{pre}/trivia/">🧠 {e(T(lang, 'nav_trivia'))}</a>
      <a href="/puzzle/">🧩 {e(T(lang, 'nav_puzzle'))}</a>
      <a href="{pre}/articles/">📖 {e(T(lang, 'nav_articles'))}</a>
      <a href="{pre}/countdown/">⏳ {e(T(lang, 'nav_countdowns'))}</a>
    </nav>
    <button class="themebtn" type="button" aria-label="{e(T(lang, 'theme_toggle'))}" onclick="var d=document.documentElement,n=(d.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'))==='dark'?'light':'dark';d.dataset.theme=n;try{{localStorage.setItem('dt-theme',n)}}catch(e){{}}"><span class="th-moon">🌙</span><span class="th-sun">☀️</span></button>
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


# expected dates (astronomical calendar); the real day can move by one depending on the moon sighting
ISLAMIC = {
    "ramadan": {2026: dt.date(2026, 2, 18), 2027: dt.date(2027, 2, 8), 2028: dt.date(2028, 1, 28), 2029: dt.date(2029, 1, 16), 2030: dt.date(2030, 1, 6)},
    "eid-al-fitr": {2026: dt.date(2026, 3, 20), 2027: dt.date(2027, 3, 10), 2028: dt.date(2028, 2, 27), 2029: dt.date(2029, 2, 15), 2030: dt.date(2030, 2, 5)},
    "eid-al-adha": {2026: dt.date(2026, 5, 27), 2027: dt.date(2027, 5, 17), 2028: dt.date(2028, 5, 6), 2029: dt.date(2029, 4, 25), 2030: dt.date(2030, 4, 14)},
    "islamic-new-year": {2026: dt.date(2026, 6, 16), 2027: dt.date(2027, 6, 6), 2028: dt.date(2028, 5, 25), 2029: dt.date(2029, 5, 15), 2030: dt.date(2030, 5, 4)},
    "mawlid": {2026: dt.date(2026, 8, 26), 2027: dt.date(2027, 8, 15), 2028: dt.date(2028, 8, 4), 2029: dt.date(2029, 7, 24), 2030: dt.date(2030, 7, 13)},
}
CNY = json.loads((HERE / "data" / "cny.json").read_text())
HOLIDAYS = {
    "christmas": lambda y: dt.date(y, 12, 25), "new-year": lambda y: dt.date(y, 1, 1),
    "halloween": lambda y: dt.date(y, 10, 31), "valentines-day": lambda y: dt.date(y, 2, 14),
    "thanksgiving": lambda y: nth_weekday(y, 11, 3, 4), "easter": easter,
    "fourth-of-july": lambda y: dt.date(y, 7, 4), "mothers-day": lambda y: nth_weekday(y, 5, 6, 2),
    "fathers-day": lambda y: nth_weekday(y, 6, 6, 3), "st-patricks-day": lambda y: dt.date(y, 3, 17),
    "memorial-day": lambda y: last_weekday(y, 5, 0), "labor-day": lambda y: nth_weekday(y, 9, 0, 1),
    "black-friday": lambda y: nth_weekday(y, 11, 3, 4) + dt.timedelta(days=1),
    "ramadan": lambda y: ISLAMIC["ramadan"].get(y, dt.date(9999, 1, 1)),
    "eid-al-fitr": lambda y: ISLAMIC["eid-al-fitr"].get(y, dt.date(9999, 1, 1)),
    "eid-al-adha": lambda y: ISLAMIC["eid-al-adha"].get(y, dt.date(9999, 1, 1)),
    "islamic-new-year": lambda y: ISLAMIC["islamic-new-year"].get(y, dt.date(9999, 1, 1)),
    "mawlid": lambda y: ISLAMIC["mawlid"].get(y, dt.date(9999, 1, 1)),
    "chinese-new-year": lambda y: dt.date(y, *divmod(CNY[str(y)], 100)) if str(y) in CNY else dt.date(9999, 1, 1),
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
    title, desc, _, (c1, c2), emoji, _, best = GAMES[slug]
    return (f'<a class="gcard" href="{P(lang)}/games/{slug}/" style="--c1:{c1};--c2:{c2}">'
            f'<span class="gc-icon">{emoji}</span><span class="gc-body"><b>{e(T(lang, title))}</b>'
            f'<small>{e(T(lang, desc))}</small>{f"<em data-best={chr(34)}{best}{chr(34)}></em>" if best else ""}</span>'
            f'<span class="gc-play">▶</span></a>')


def games_grid(lang, only=None):
    return f'<div class="ggrid">{"".join(game_card(lang, g) for g in (only or GAMES))}</div>'


def labels_json(lang):
    data = {k: T(lang, k) for k in GAME_LABELS}
    return '<script type="application/json" id="game-l">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + '</script>'


def profile_box(lang):
    return f'<div class="profile" data-profile></div>'



def more_fun(lang):
    quiz = (f'<a class="card art" href="{P(lang)}/trivia/">{art("quiz", "#5b3df5", "#8f7bff", "🧠")}'
            f'<div class="card-body"><span class="tag">❓ {e(T(lang, "daily_trivia"))}</span><h3>{e(T(lang, "start_quiz"))}</h3>'
            f'<p>{e(T(lang, "trivia_teaser", n=10))}</p></div></a>') if DATA[lang]["trivia"] else ""
    return (f'<section class="more-fun"><h2>✨ {e(T(lang, "more_fun"))}</h2>{games_grid(lang, list(GAMES)[:4])}'
            f'<div class="grid" style="margin-top:14px">{quiz}</div></section>'
            f'{labels_json(lang)}<script src="/assets/games.js" defer></script>')


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
    latest = "".join(article_card(lang, a) for a in AR[:6]) or f"<p class='muted'>{e(T(lang, 'new_daily'))}</p>"
    n_games = len(GAMES)
    tiles = [
        (f"{pre}/horoscope/", "🔮", "nav_horoscopes", "tile_horoscope", "#7c5cff", "#c084fc"),
        (f"{pre}/games/", "🎮", "nav_games", "tile_games", "#ff5e7e", "#ff8a3d"),
        (f"{pre}/trivia/", "🧠", "nav_trivia", "tile_trivia", "#3a6ff7", "#22c1c3"),
        ("/puzzle/", "🧩", "nav_puzzle", "tile_puzzle", "#2fa36b", "#a3e635"),
        (f"{pre}/articles/", "📖", "nav_articles", "tile_articles", "#f59e0b", "#f97316"),
        (f"{pre}/countdown/", "⏳", "nav_countdowns", "tile_countdown", "#0ea5e9", "#6366f1"),
        (f"{pre}/compatibility/", "💕", "compat_title", "tile_compat", "#ff5e7e", "#d36bff"),
        (f"{pre}/tarot/", "🃏", "tarot_title", "tile_tarot", "#3b2a8c", "#c084fc"),
        (f"{pre}/zodiac/", "♈", "zodiac_title", "tile_zodiac", "#b8793b", "#f5b301"),
        (f"{pre}/chinese-zodiac/", "🐉", "chinese_title", "tile_chinese", "#d62828", "#f77f00"),
        (f"{pre}/numerology/", "🔢", "num_title", "tile_num", "#0f766e", "#22c1c3"),
        (f"{pre}/love-calculator/", "💘", "love_calc_title", "tile_lovecalc", "#e11d48", "#fb7185"),
        *([(f"{pre}/dreams/", "💤", "dreams_title", "tile_dreams", "#312e81", "#a78bfa")] if D["dreams"] else []),
        *([(f"{pre}/angel-numbers/", "👼", "ang_title", "tile_ang", "#0369a1", "#7dd3fc")] if any(x.get("kind") == "angel" for x in D["guides2"]) else []),
        *([(f"{pre}/birthday/", "🎁", "bdp_title", "tile_bdp", "#be185d", "#fbbf24")] if any(x.get("kind") == "birthday" for x in D["guides2"]) else []),
        (f"{pre}/prayer-times/", "🕌", "pt_title", "tile_pt", "#065f46", "#10b981"),
        (f"{pre}/hijri-calendar/", "🌙", "hj_title", "tile_hj", "#047857", "#34d399"),
        *([(f"{pre}/names/", "👶", "nm_title", "tile_nm", "#0891b2", "#f472b6")] if D["names"] else []),
        *([(f"{pre}/learn-english/", "🇬🇧", "en_title", "tile_en", "#1d4ed8", "#ef4444")] if D["english"] else []),
        (f"{pre}/zodiac-quiz/", "🧠", "pq_title", "tile_pq", "#7c3aed", "#ec4899"),
        (f"{pre}/love-messages/", "💌", "lm_title", "tile_lm", "#db2777", "#f9a8d4"),
        (f"{pre}/age-calculator/", "🎂", "bday_title", "tile_bday", "#ea580c", "#facc15"),
        (f"{pre}/moon-phase/", "🌙", "moon_title", "tile_moon", "#1e1b4b", "#6366f1"),
    ]
    yrs = sorted({y for (y, _) in D["yearly"]})
    if yrs:
        tiles.insert(1, (f"{pre}/horoscope-{yrs[-1]}/", "🎆", "yearly_title", "tile_yearly", "#7c3aed", "#f59e0b"))
    def tile_ic(u, ic):
        im = section_img(u[len(pre):].lstrip("/") if pre and u.startswith(pre) else u.lstrip("/"))
        return f'<img src="{im}" width="48" height="48" alt="" loading="lazy">' if im and "/signs/" not in im else ic
    def tile_img(u, ic, c1, c2):
        path = u[len(pre):].lstrip("/") if pre and u.startswith(pre) else u.lstrip("/")
        im = section_img(path)
        if path.startswith(("horoscope", "zodiac")) and not im:
            im = "/assets/signs/leo.webp"
        return (f'<img src="{im}" width="320" height="320" alt="" loading="lazy">' if im
                else f'<span class="rc-emo" style="--c1:{c1};--c2:{c2}">{ic}</span>')
    by_path = {}
    for tl in tiles:
        by_path[tl[0][len(pre):].strip("/") if pre else tl[0].strip("/")] = tl
    CATS = [("cat_popular", "⭐", ["horoscope", "prayer-times", "names", "learn-english", "games", "compatibility"]),
            ("cat_spirit", "🔮", [k for k in by_path if k.startswith("horoscope-")] + ["zodiac", "tarot", "dreams", "chinese-zodiac", "numerology", "angel-numbers", "moon-phase", "zodiac-quiz"]),
            ("cat_islamic", "🕌", ["prayer-times", "hijri-calendar", "countdown"]),
            ("cat_play", "🎮", ["games", "trivia", "puzzle", "zodiac-quiz", "love-calculator"]),
            ("cat_life", "💡", ["names", "learn-english", "birthday", "love-messages", "age-calculator", "articles", "countdown"])]
    used = set(k for _, _, ks in CATS for k in ks)
    CATS[-1][2].extend(k for k in by_path if k not in used)
    def rail(title, emo, keys):
        cards = "".join(
            f'<a class="rcard" href="{by_path[k][0]}">{tile_img(by_path[k][0], by_path[k][1], by_path[k][4], by_path[k][5])}'
            f'<b>{e(T(lang, by_path[k][2], year=yrs[-1] if yrs else ""))}</b><small>{e(T(lang, by_path[k][3]))}</small></a>'
            for k in keys if k in by_path)
        return f'<section class="rail"><h2>{emo} {e(T(lang, title))}</h2><div class="rtrack">{cards}</div></section>' if cards else ""
    tiles_html = "".join(rail(*c) for c in CATS)
    strip = "".join(
        f'<a class="sg" href="{pre}/horoscope/{s}/" data-sign="{s}">{sign_art(s, 50)}<b>{e(sign_name(lang, s))}</b></a>'
        for s in SIGNS)
    body = f"""
<section class="hero2">
  <div class="hero2-in">
    <p class="kicker">{e(fdate(lang, TODAY))}</p>
    <h1>{e(T(lang, 'hero_short'))}</h1>
    <p class="hero2-sub">{e(T(lang, 'tagline'))}.</p>
    <form class="hsearch" action="{pre}/search/" method="get" role="search"><input type="search" name="q" placeholder="{e(T(lang, 'search_hero'))}" aria-label="{e(T(lang, 'search_title'))}"><button type="submit" aria-label="{e(T(lang, 'search_title'))}">🔍</button></form>
    <div class="hero2-cta">
      <a class="btn light" href="{pre}/games/">🎮 {e(T(lang, 'cta_play'))}</a>
      <a class="btn glass" href="{pre}/horoscope/" data-mysign>🔮 {e(T(lang, 'cta_horoscope'))}</a>
    </div>
    <ul class="hero2-badges"><li>🎮 {e(T(lang, 'badge_games', n=n_games))}</li><li>♈ {e(T(lang, 'badge_signs'))}</li><li>✨ {e(T(lang, 'badge_daily'))}</li></ul>
  </div>
  <img class="hero-img" src="/assets/sections/hero.webp" width="560" height="600" alt="">
</section>
<div class="explore">{tiles_html}</div>
<section>
  <div class="sec-head"><h2>🔮 {e(T(lang, 'daily_horoscope'))}</h2><a href="{pre}/horoscope/">{e(T(lang, 'see_all'))} →</a></div>
  <p class="muted small hint">{e(T(lang, 'pick_sign'))}</p>
  <div class="sgstrip" data-your="{e(T(lang, 'your_sign'))}">{strip}</div>
</section>
<section>
  <div class="sec-head"><h2>🎮 {e(T(lang, 'games_title'))}</h2><a href="{pre}/games/">{e(T(lang, 'see_all'))} →</a></div>
  {games_grid(lang, list(GAMES)[:6])}
</section>
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
{facts(lang)}
<section>
  <div class="sec-head"><h2>📖 {e(T(lang, 'latest_explainers'))}</h2><a href="{pre}/articles/">{e(T(lang, 'see_all'))} →</a></div>
  <div class="grid">{latest}</div>
</section>
<script>(function(){{try{{var m=localStorage.getItem('dt-sign'),st=document.querySelector('.sgstrip');if(!st)return;
st.querySelectorAll('.sg').forEach(function(a){{a.addEventListener('click',function(){{try{{localStorage.setItem('dt-sign',a.dataset.sign)}}catch(x){{}}}})}});
if(m){{var a=st.querySelector('[data-sign="'+m+'"]');if(a){{a.classList.add('mine');a.setAttribute('data-your',st.dataset.your);st.prepend(a);
var c=document.querySelector('[data-mysign]');if(c)c.href=a.getAttribute('href');}}}}}}catch(x){{}}}})();</script>
{labels_json(lang)}<script src="/assets/games.js" defer></script>"""
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
  {f'<img class="sign-hero" src="/assets/signs/{s}-tall.webp" width="512" height="768" alt="{e(sign_name(lang, s))}">' if (HERE / "assets" / "signs" / f"{s}-tall.webp").exists() else ""}
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
  {f'<a class="btn ghost guide-link" href="{pre}/zodiac/{s}/">📖 {e(T(lang, "read_guide", sign=sign_name(lang, s)))}</a>' if s in D["guides"] else ""}
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
  <p class="small muted">{e(T(lang, 'timer_note'))}{(" " + e(T(lang, "moon_note"))) if slug in ISLAMIC else ""}</p>
  <h2>{e(T(lang, 'more_countdowns'))}</h2><div class="chips">{more}</div>
</article>
<script src="/assets/countdown.js" defer></script>"""
        add(lang, f"countdown/{slug}/", f"{T(lang, 'how_many_days', name=name)} ({days})",
            re.sub("<[^>]+>", "", T(lang, "falls_on", name=name, date=fdate(lang, d), days=days)), body, priority="0.7")
    rows = sorted(HOLIDAYS, key=lambda s: next_date(HOLIDAYS[s]))
    add(lang, "countdown/", T(lang, "countdowns_title"), T(lang, "countdowns_desc"),
        f'<h1>{e(T(lang, "countdowns_title"))}</h1><div class="cds big">{"".join(cd_card(lang, s) for s in rows)}</div>', priority="0.7")

    # games
    add(lang, "games/", T(lang, "games_title"), T(lang, "games_desc"),
        f'<section class="games-hero"><p class="kicker">🎮 {e(T(lang, "brain_games"))}</p><h1>{e(T(lang, "games_title"))}</h1>'
        f'<p class="lead">{e(T(lang, "games_desc"))}</p>{profile_box(lang)}</section>{games_grid(lang)}'
        f'{labels_json(lang)}<script src="/assets/games.js" defer></script>', priority="0.8")
    for slug, (title, desc, how, (c1, c2), emoji, js, _) in GAMES.items():
        body = f"""
<article class="gamepage" style="--c1:{c1};--c2:{c2}">
  <div class="game-head"><span class="gc-icon">{emoji}</span><div><p class="kicker">🎮 {e(T(lang, 'brain_games'))}</p>
  <h1>{e(T(lang, title))}</h1></div></div>
  <p class="lead">{e(T(lang, desc))}</p>
  {profile_box(lang)}
  <div id="game" data-game="{js}"></div>
  {f'<script type="application/json" id="ws-data">{json.dumps(WS.get(lang, WS["en"]), ensure_ascii=False)}</script>' if js == "wordsearch" else ""}
  <details class="howto"><summary>{e(T(lang, 'how_to_play'))}</summary><p>{e(T(lang, how))}</p></details>
</article>
<section><h2>✨ {e(T(lang, 'more_fun'))}</h2>{games_grid(lang, [g for g in GAMES if g != slug])}</section>
{labels_json(lang)}
<script src="/assets/games.js" defer></script>{f'<script src="/assets/{js}.js" defer></script>' if js in EXTERNAL_JS else ""}"""
        add(lang, f"games/{slug}/", f"{T(lang, title)} – {T(lang, 'games_title')}", T(lang, desc), body,
            {"@context": "https://schema.org", "@type": "VideoGame", "name": T(lang, title), "inLanguage": lang,
             "gamePlatform": "Web browser", "applicationCategory": "Game"}, "0.7")

    # zodiac sign guides + pair compatibility guides
    G, PR = D["guides"], D["pairs"]
    EL = lambda s: T(lang, "el_" + SIGNS[s][1])
    pair_slug = lambda a, b: "-".join(sorted([a, b], key=SIGN_KEYS.index))
    def sign_link(s):
        return f'<a class="mchip" href="{pre}/zodiac/{s}/">{sign_art(s, 28)} {e(sign_name(lang, s))}</a>' if s in G else \
               f'<a class="mchip" href="{pre}/horoscope/{s}/">{sign_art(s, 28)} {e(sign_name(lang, s))}</a>'
    if G:
        cards = "".join(
            f'<a class="zcard" href="{pre}/zodiac/{s}/" data-sign="{s}">'
            f'<img src="/assets/signs/{s}.webp" alt="" width="160" height="160" loading="lazy">'
            f'<b>{SIGNS[s][0]} {e(sign_name(lang, s))}</b><small>{e(sign_range(lang, s))} · {e(EL(s))}</small></a>'
            for s in SIGNS if s in G)
        ranges = {s: [SIGNS[s][2], SIGNS[s][3]] for s in SIGNS}
        names = {s: sign_name(lang, s) for s in SIGNS}
        add(lang, "zodiac/", T(lang, "zodiac_title"), T(lang, "zodiac_desc"), f"""
<section class="zhub">
  <p class="kicker">♈ {e(T(lang, 'zodiac_title'))}</p><h1>{e(T(lang, 'zodiac_title'))}</h1>
  <p class="lead">{e(T(lang, 'zodiac_desc'))}</p>
  <div class="finder" id="finder">
    <h2>🔍 {e(T(lang, 'zodiac_finder'))}</h2>
    <label>{e(T(lang, 'birthday'))}<input type="date" name="bd" value="2000-01-01"></label>
    <button class="btn">{e(T(lang, 'find_sign'))}</button>
    <div class="finder-out" aria-live="polite"></div>
  </div>
  <div class="zgrid">{cards}</div>
</section>
<script type="application/json" id="finder-data">{json.dumps({"r": ranges, "n": names, "pre": pre, "you": T(lang, "you_are"), "read": T(lang, "read_guide")}, ensure_ascii=False).replace("</", "<\\/")}</script>
<script src="/assets/finder.js" defer></script>""", priority="0.9")
    for s, g in G.items():
        f = g.get("facts", {})
        kf = [("🪐", T(lang, "ruling_planet"), f.get("planet", "")), ("🔥", T(lang, "element"), EL(s)),
                 ("🧭", T(lang, "modality"), f.get("modality", "")), ("📅", T(lang, "lucky_day"), f.get("day", "")),
                 ("🎨", T(lang, "lucky_color"), f.get("color", "")), ("💎", T(lang, "lucky_stone"), f.get("stone", "")),
                 ("🍀", T(lang, "lucky_number"), str(g.get("lucky_number", "")))]
        facts_html = "".join(f'<div><span>{ic}</span><small>{e(k)}</small><b>{e(v)}</b></div>' for ic, k, v in kf if v)
        li = lambda xs: "".join(f"<li>{e(x)}</li>" for x in xs)
        match = lambda xs: "".join(
            (f'<a class="mchip" href="{pre}/compatibility/{pair_slug(s, o)}/">{sign_art(o, 28)} {e(sign_name(lang, o))}</a>'
             if pair_slug(s, o) in PR else sign_link(o)) for o in xs)
        guides = "".join(f'<a class="mchip" href="{pre}/compatibility/{pair_slug(s, o)}/">{sign_art(o, 28)} {e(sign_name(lang, o))}</a>'
                         for o in SIGNS if pair_slug(s, o) in PR)
        faq = g.get("faq", [])
        faq_html = "".join(f"<details class='faq'><summary>{e(x['q'])}</summary><p>{e(x['ans'])}</p></details>" for x in faq)
        body = f"""
<article class="guide">
  <img class="sign-hero" src="/assets/signs/{s}-tall.webp" width="512" height="768" alt="{e(sign_name(lang, s))}">
  <p class="kicker">{SIGNS[s][0]} {e(sign_range(lang, s))} · {e(EL(s))}</p>
  <h1>{e(g['title'])}</h1>
  <p class="lead">{e(g['intro'])}</p>
  <div class="facts">{facts_html}</div>
  <h2>✨ {e(T(lang, 'personality'))}</h2><p>{e(g['personality'])}</p>
  <div class="sw"><div><h3>💪 {e(T(lang, 'strengths'))}</h3><ul>{li(g['strengths'])}</ul></div>
  <div><h3>⚠️ {e(T(lang, 'weaknesses'))}</h3><ul>{li(g['weaknesses'])}</ul></div></div>
  <h2>❤️ {e(T(lang, 'love'))}</h2><p>{e(g['love'])}</p>
  <h2>💼 {e(T(lang, 'career'))}</h2><p>{e(g['career'])}</p>
  <h2>🤝 {e(T(lang, 'friendship'))}</h2><p>{e(g['friendship'])}</p>
  <h2>💞 {e(T(lang, 'best_matches'))}</h2><div class="chips">{match(g['best'])}</div>
  <h3>🌗 {e(T(lang, 'hard_matches'))}</h3><div class="chips">{match(g['hard'])}</div>
  {f'<h2>💕 {e(T(lang, "compat_guides"))}</h2><div class="chips">{guides}</div>' if guides else ''}
  <a class="btn" href="{pre}/horoscope/{s}/">🔮 {e(T(lang, 'horoscope_today', sign=sign_name(lang, s)))}</a>
  {f'<h2>❓ {e(T(lang, "faq_title"))}</h2>{faq_html}' if faq else ''}
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <h2>{e(T(lang, 'other_signs'))}</h2><div class="chips">{"".join(sign_link(o) for o in SIGNS if o != s)}</div>
</article>"""
        schema = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang,
                  "mainEntity": [{"@type": "Question", "name": x["q"], "acceptedAnswer": {"@type": "Answer", "text": x["ans"]}} for x in faq]} if faq else None
        add(lang, f"zodiac/{s}/", g["title"], g["intro"], body, schema, priority="0.8")
    for slug, x in PR.items():
        a, b = x["a"], x["b"]
        tips = "".join(f"<li>{e(t)}</li>" for t in x.get("tips", []))
        body = f"""
<article class="guide pair">
  <div class="pair-head">{sign_art(a, 96)}<span class="pair-heart">❤</span>{sign_art(b, 96)}</div>
  <p class="kicker">💕 {e(sign_name(lang, a))} + {e(sign_name(lang, b))}</p>
  <h1>{e(x['title'])}</h1>
  <div class="cc-ring big" style="--p:{int(x['score'])}"><b>{int(x['score'])}%</b></div>
  <p class="center muted small">{e(T(lang, 'harmony'))}</p>
  <p class="lead">{e(x['summary'])}</p>
  <h2>❤️ {e(T(lang, 'love'))}</h2><p>{e(x['love'])}</p>
  <h2>🤝 {e(T(lang, 'friendship'))}</h2><p>{e(x['friendship'])}</p>
  <h2>💼 {e(T(lang, 'compat_work'))}</h2><p>{e(x['work'])}</p>
  <h2>🌗 {e(T(lang, 'challenges'))}</h2><p>{e(x['challenges'])}</p>
  <h2>💡 {e(T(lang, 'compat_tip'))}</h2><ul>{tips}</ul>
  <a class="btn" href="{pre}/compatibility/">💘 {e(T(lang, 'compat_check'))}</a>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <div class="chips">{sign_link(a)}{sign_link(b) if b != a else ''}</div>
</article>"""
        add(lang, f"compatibility/{slug}/", x["title"], x["summary"], body, priority="0.7")

    # yearly horoscope
    Y = D["yearly"]
    for year in sorted({y for (y, _) in Y}):
        have = [s for s in SIGNS if (year, s) in Y]
        cards = "".join(f'<a class="zcard" href="{pre}/horoscope-{year}/{s}/"><img src="/assets/signs/{s}.webp" alt="" width="160" height="160" loading="lazy">'
                        f'<b>{SIGNS[s][0]} {e(sign_name(lang, s))}</b><small>{e(Y[(year, s)]["theme"])}</small></a>' for s in have)
        add(lang, f"horoscope-{year}/", T(lang, "yearly_title", year=year), T(lang, "yearly_desc", year=year),
            f'<section class="zhub"><p class="kicker">🎆 {year}</p><h1>{e(T(lang, "yearly_title", year=year))}</h1>'
            f'<p class="lead">{e(T(lang, "yearly_desc", year=year))}</p><div class="zgrid">{cards}</div></section>', priority="0.9")
        for s in have:
            x = Y[(year, s)]
            li = "".join(f"<li>{e(t)}</li>" for t in x.get("tips", []))
            body = f"""
<article class="guide">
  <img class="sign-hero" src="/assets/signs/{s}-tall.webp" width="512" height="768" alt="{e(sign_name(lang, s))}">
  <p class="kicker">🎆 {year} · {SIGNS[s][0]} {e(sign_name(lang, s))}</p>
  <h1>{e(x['title'])}</h1>
  <p class="lead">{e(x['summary'])}</p>
  <div class="facts"><div><span>✨</span><small>{e(T(lang, 'theme_year'))}</small><b>{e(x['theme'])}</b></div>
  <div><span>🍀</span><small>{e(T(lang, 'best_months'))}</small><b>{e(', '.join(map(str, x['best_months'])))}</b></div></div>
  <h2>❤️ {e(T(lang, 'love'))}</h2><p>{e(x['love'])}</p>
  <h2>💼 {e(T(lang, 'career'))}</h2><p>{e(x['career'])}</p>
  <h2>💰 {e(T(lang, 'money'))}</h2><p>{e(x['money'])}</p>
  <h2>🌿 {e(T(lang, 'wellness'))}</h2><p>{e(x['wellness'])}</p>
  <h2>💡 {e(T(lang, 'yearly_tips'))}</h2><ul>{li}</ul>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <div class="chips">{"".join(f'<a class="mchip" href="{pre}/horoscope-{year}/{o}/">{sign_art(o, 28)} {e(sign_name(lang, o))}</a>' for o in have if o != s)}</div>
</article>"""
            add(lang, f"horoscope-{year}/{s}/", x["title"], x["summary"], body, priority="0.8")

    # chinese zodiac
    CZ = D["chinese"]
    ANIMALS = ["rat", "ox", "tiger", "rabbit", "dragon", "snake", "horse", "goat", "monkey", "rooster", "dog", "pig"]
    AEMO = dict(zip(ANIMALS, "🐀 🐂 🐅 🐇 🐉 🐍 🐎 🐐 🐒 🐓 🐕 🐖".split()))
    def animal_art(a, size=110):
        if (HERE / "assets" / "chinese" / f"{a}.webp").exists():
            return f'<img class="medal pic" src="/assets/chinese/{a}.webp" width="{size}" height="{size}" alt="" loading="lazy">'
        return f'<span class="aemo" style="width:{size}px;height:{size}px;font-size:{size * .55:.0f}px">{AEMO[a]}</span>'
    acards = "".join(f'<a class="zcard" href="{pre}/chinese-zodiac/{a}/" data-animal="{a}">{animal_art(a)}<b>{e(T(lang, "an_" + a))}</b>'
                     f'<small>{", ".join(str(y) for y in range(1936 + ANIMALS.index(a), 2032, 12)[-4:])}</small></a>' for a in ANIMALS)
    cny = json.loads((HERE / "data" / "cny.json").read_text())
    add(lang, "chinese-zodiac/", T(lang, "chinese_title"), T(lang, "chinese_desc"), f"""
<section class="zhub">
  <p class="kicker">🐉 {e(T(lang, 'chinese_title'))}</p><h1>{e(T(lang, 'chinese_title'))}</h1>
  <p class="lead">{e(T(lang, 'chinese_desc'))}</p>
  <div class="finder red" id="cfinder">
    <h2>🔍 {e(T(lang, 'chinese_finder'))}</h2>
    <label>{e(T(lang, 'birth_date'))}<input type="date" name="bd" value="2000-06-15" min="1924-02-05" max="2032-01-30"></label>
    <button class="btn">{e(T(lang, 'find_sign'))}</button>
    <div class="finder-out" aria-live="polite"></div>
  </div>
  <div class="zgrid">{acards}</div>
</section>
<script type="application/json" id="cfinder-data">{json.dumps({"cny": cny, "a": ANIMALS, "emo": AEMO, "n": {a: T(lang, "an_" + a) for a in ANIMALS}, "pre": pre, "you": T(lang, "you_are_animal"), "has": sorted(CZ)}, ensure_ascii=False).replace("</", "<\\/")}</script>
<script src="/assets/chinese.js" defer></script>""", priority="0.9")
    for a, x in CZ.items():
        li = lambda xs: "".join(f"<li>{e(str(t))}</li>" for t in xs)
        faq = x.get("faq", [])
        body = f"""
<article class="guide">
  <div class="pair-head">{animal_art(a, 140)}</div>
  <p class="kicker">🐉 {e(T(lang, 'chinese_title'))} · {e(T(lang, 'an_' + a))}</p>
  <h1>{e(x['title'])}</h1>
  <p class="lead">{e(x['intro'])}</p>
  <div class="facts"><div><span>📅</span><small>{e(T(lang, 'years_label'))}</small><b>{e(', '.join(str(y) for y in x.get('years', [])))}</b></div>
  <div><span>🎨</span><small>{e(T(lang, 'lucky_colors'))}</small><b>{e(', '.join(map(str, x['lucky_colors'])))}</b></div>
  <div><span>🍀</span><small>{e(T(lang, 'lucky_numbers'))}</small><b>{e(str(x['lucky_numbers']))}</b></div></div>
  <h2>✨ {e(T(lang, 'personality'))}</h2><p>{e(x['personality'])}</p>
  <div class="sw"><div><h3>💪 {e(T(lang, 'strengths'))}</h3><ul>{li(x['strengths'])}</ul></div><div><h3>⚠️ {e(T(lang, 'weaknesses'))}</h3><ul>{li(x['weaknesses'])}</ul></div></div>
  <h2>❤️ {e(T(lang, 'love'))}</h2><p>{e(x['love'])}</p>
  <h2>💼 {e(T(lang, 'career'))}</h2><p>{e(x['career'])}</p>
  <h2>💞 {e(T(lang, 'best_matches'))}</h2><div class="chips">{"".join(f'<a class="mchip" href="{pre}/chinese-zodiac/{m}/">{AEMO[m]} {e(T(lang, "an_" + m))}</a>' for m in x.get('best_matches', []) if m in AEMO)}</div>
  {f'<h2>❓ {e(T(lang, "faq_title"))}</h2>' + "".join(f"<details class='faq'><summary>{e(q['q'])}</summary><p>{e(q['ans'])}</p></details>" for q in faq) if faq else ''}
  <a class="btn" href="{pre}/chinese-zodiac/">🔍 {e(T(lang, 'chinese_finder'))}</a>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
</article>"""
        schema = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang,
                  "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["ans"]}} for q in faq]} if faq else None
        add(lang, f"chinese-zodiac/{a}/", x["title"], x["intro"], body, schema, priority="0.8")

    # numerology
    NU = D["numerology"]
    if NU:
        ncards = "".join(f'<a class="ncard" href="{pre}/numerology/{n}/"><b>{n}</b><small>{e(NU[n]["name"])}</small></a>' for n in sorted(NU))
        add(lang, "numerology/", T(lang, "num_title"), T(lang, "num_desc"), f"""
<section class="zhub">
  <p class="kicker">🔢 {e(T(lang, 'num_title'))}</p><h1>{e(T(lang, 'num_title'))}</h1>
  <p class="lead">{e(T(lang, 'num_desc'))}</p>
  <div class="finder teal" id="nfinder">
    <label>{e(T(lang, 'birth_date'))}<input type="date" name="bd" value="1995-07-14"></label>
    <button class="btn">{e(T(lang, 'num_calc'))}</button>
    <div class="finder-out" aria-live="polite"></div>
    <p class="small">{e(T(lang, 'num_how'))}</p>
  </div>
  <div class="ngrid">{ncards}</div>
</section>
<script type="application/json" id="nfinder-data">{json.dumps({"pre": pre, "res": T(lang, "num_result"), "names": {n: NU[n]["name"] for n in NU}, "read": T(lang, "compat_open")}, ensure_ascii=False).replace("</", "<\\/")}</script>
<script src="/assets/numerology.js" defer></script>""", priority="0.8")
        for n, x in NU.items():
            li = lambda xs: "".join(f"<li>{e(t)}</li>" for t in xs)
            add(lang, f"numerology/{n}/", x["title"], x["intro"], f"""
<article class="guide">
  <div class="pair-head"><span class="bignum">{n}</span></div>
  <p class="kicker">🔢 {e(T(lang, 'num_title'))}</p><h1>{e(x['title'])}</h1>
  <p class="lead">{e(x['intro'])}</p>
  <div class="sw"><div><h3>💪 {e(T(lang, 'strengths'))}</h3><ul>{li(x['strengths'])}</ul></div><div><h3>⚠️ {e(T(lang, 'weaknesses'))}</h3><ul>{li(x['weaknesses'])}</ul></div></div>
  <h2>❤️ {e(T(lang, 'love'))}</h2><p>{e(x['love'])}</p>
  <h2>💼 {e(T(lang, 'career'))}</h2><p>{e(x['career'])}</p>
  <a class="btn" href="{pre}/numerology/">🔢 {e(T(lang, 'num_calc'))}</a>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <div class="chips">{"".join(f'<a class="mchip num" href="{pre}/numerology/{m}/"><b>{m}</b> {e(NU[m]["name"])}</a>' for m in sorted(NU) if m != n)}</div>
</article>""", priority="0.7")

    # moon phase
    mdata = {"p": [T(lang, f"moon_p{i}") for i in range(8)], "m": [T(lang, f"moon_m{i}") for i in range(8)], "lang": lang,
             "l": {k: T(lang, k) for k in ("moon_illum", "moon_next_full", "moon_next_new", "moon_age", "days")}}
    add(lang, "moon-phase/", T(lang, "moon_title"), T(lang, "moon_desc"), f"""
<section class="moonpage">
  <p class="kicker">🌙 {e(T(lang, 'moon_title'))}</p><h1>{e(T(lang, 'moon_title'))}</h1>
  <p class="lead">{e(T(lang, 'moon_desc'))}</p>
  <div id="moon" class="moon"></div>
</section>
<script type="application/json" id="moon-data">{json.dumps(mdata, ensure_ascii=False).replace("</", "<\\/")}</script>
<script src="/assets/moon.js" defer></script>""", priority="0.8")

    # fun tools: love calculator, birthday/age, personality quiz, love message cards
    jd = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    names = {s: sign_name(lang, s) for s in SIGNS}
    add(lang, "love-calculator/", T(lang, "love_calc_title"), T(lang, "love_calc_desc"), f"""
<article class="compat-page">
  <p class="kicker">💘 {e(T(lang, 'love_calc_title'))}</p><h1>{e(T(lang, 'love_calc_title'))}</h1>
  <p class="lead">{e(T(lang, 'love_calc_desc'))}</p>
  <div id="lovecalc" class="compat lc">
    <label><span>{e(T(lang, 'your_name'))}</span><input name="a" maxlength="40" autocomplete="off"></label>
    <span class="compat-plus">❤</span>
    <label><span>{e(T(lang, 'their_name'))}</span><input name="b" maxlength="40" autocomplete="off"></label>
    <button class="btn compat-go">💘 {e(T(lang, 'calc_love'))}</button>
    <div class="compat-out" aria-live="polite"></div>
  </div>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
</article>
<script type="application/json" id="tools-data">{jd({"r": [T(lang, f"love_r{i}") for i in range(5)], "share": T(lang, "compat_share"), "title": T(lang, "love_calc_title")})}</script>
<script src="/assets/tools.js" defer></script>""", priority="0.9")
    add(lang, "age-calculator/", T(lang, "bday_title"), T(lang, "bday_desc"), f"""
<article class="compat-page">
  <p class="kicker">🎂 {e(T(lang, 'bday_title'))}</p><h1>{e(T(lang, 'bday_title'))}</h1>
  <p class="lead">{e(T(lang, 'bday_desc'))}</p>
  <div id="bday" class="finder orange"><label>{e(T(lang, 'birth_date'))}<input type="date" name="bd" value="2000-01-01"></label>
  <button class="btn">{e(T(lang, 'bday_calc'))}</button><div class="finder-out bday-out" aria-live="polite"></div></div>
</article>
<script type="application/json" id="tools-data">{jd({"lang": lang, "pre": pre, "names": names, "ranges": {s: [SIGNS[s][2], SIGNS[s][3]] for s in SIGNS}, "glyph": {s: SIGNS[s][0] for s in SIGNS},
    "cny": json.loads((HERE / "data" / "cny.json").read_text()), "animals": ["rat", "ox", "tiger", "rabbit", "dragon", "snake", "horse", "goat", "monkey", "rooster", "dog", "pig"],
    "an": {a: T(lang, "an_" + a) for a in ["rat", "ox", "tiger", "rabbit", "dragon", "snake", "horse", "goat", "monkey", "rooster", "dog", "pig"]},
    "l": {k: T(lang, k) for k in ("age", "age_exact", "days_lived", "next_bday", "born_on", "in_days", "today_bday", "heartbeats", "your_zodiac", "your_animal", "your_number")}})}</script>
<script src="/assets/tools.js" defer></script>""", priority="0.9")
    pq = {"q": [{"t": T(lang, f"pq_q{i}"), "o": [T(lang, f"pq_q{i}_{j}") for j in range(3 if i == 7 else 4)]} for i in range(8)],
          "names": names, "pre": pre, "res": T(lang, "pq_result"), "again": T(lang, "pq_again"), "share": T(lang, "pq_share"),
          "of": T(lang, "pq_of"), "read": T(lang, "read_guide"), "title": T(lang, "pq_title")}
    add(lang, "zodiac-quiz/", T(lang, "pq_title"), T(lang, "pq_desc"), f"""
<article class="compat-page">
  <p class="kicker">🧠 {e(T(lang, 'pq_title'))}</p><h1>{e(T(lang, 'pq_title'))}</h1>
  <p class="lead">{e(T(lang, 'pq_desc'))}</p>
  <div id="pquiz" class="pquiz"><button class="btn pq-start">✨ {e(T(lang, 'pq_start'))}</button></div>
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
</article>
<script type="application/json" id="tools-data">{jd(pq)}</script>
<script src="/assets/tools.js" defer></script>""", priority="0.9")
    lm = {"m": {s: [T(lang, f"lm_{s}_{i}") for i in range(3)] for s in SIGNS}, "names": names, "glyph": {s: SIGNS[s][0] for s in SIGNS},
          "save": T(lang, "lm_save"), "share": T(lang, "lm_share"), "next": T(lang, "lm_next"), "rtl": lang == "ar", "site": "mydailytwist.com"}
    add(lang, "love-messages/", T(lang, "lm_title"), T(lang, "lm_desc"), f"""
<article class="compat-page">
  <p class="kicker">💌 {e(T(lang, 'lm_title'))}</p><h1>{e(T(lang, 'lm_title'))}</h1>
  <p class="lead">{e(T(lang, 'lm_desc'))}</p>
  <div id="lovemsg" class="lovemsg">
    <p class="muted">{e(T(lang, 'lm_pick'))}</p>
    <div class="lm-signs">{"".join(f'<button class="mchip" data-s="{s}">{sign_art(s, 28)} {e(sign_name(lang, s))}</button>' for s in SIGNS)}</div>
    <canvas width="1080" height="1080" hidden></canvas>
    <div class="lm-actions" hidden><button class="btn small lm-share">📤 {e(T(lang, 'lm_share'))}</button>
    <button class="btn small ghost lm-save">⬇ {e(T(lang, 'lm_save'))}</button><button class="btn small ghost lm-next">🔄 {e(T(lang, 'lm_next'))}</button></div>
  </div>
</article>
<script type="application/json" id="tools-data">{jd(lm)}</script>
<script src="/assets/tools.js" defer></script>""", priority="0.8")

    # dream dictionary
    DR = D["dreams"]
    if DR:
        dcards = "".join(f'<a class="dcard" href="{pre}/dreams/{k}/" data-q="{e(x["title"].lower())}"><span>{e(x.get("emoji", "🌙"))}</span><b>{e(x["title"].split(":")[0])}</b></a>'
                         for k, x in sorted(DR.items(), key=lambda kv: kv[1]["title"]))
        add(lang, "dreams/", T(lang, "dreams_title"), T(lang, "dreams_desc"), f"""
<section class="zhub">
  <p class="kicker">🌙 {e(T(lang, 'dreams_title'))}</p><h1>{e(T(lang, 'dreams_title'))}</h1>
  <p class="lead">{e(T(lang, 'dreams_desc'))}</p>
  <input class="dsearch" type="search" placeholder="🔍 {e(T(lang, 'dreams_search'))}" oninput="var q=this.value.toLowerCase();document.querySelectorAll('.dcard').forEach(function(c){{c.hidden=q&&c.dataset.q.indexOf(q)<0}})">
  <div class="dgrid">{dcards}</div>
</section>""", priority="0.9")
        for k, x in DR.items():
            v = x.get("variations", [])
            others = sorted(DR, key=lambda o: hashlib.md5((k + o).encode()).hexdigest())[:8]
            body = f"""
<article class="guide">
  <div class="pair-head"><span class="aemo dream" style="width:120px;height:120px;font-size:62px">{e(x.get('emoji', '🌙'))}</span></div>
  <p class="kicker">🌙 {e(T(lang, 'dreams_title'))}</p><h1>{e(x['title'])}</h1>
  <p class="lead">{e(x['summary'])}</p>
  <h2>🔮 {e(T(lang, 'dream_meaning'))}</h2><p>{e(x['meaning'])}</p>
  <div class="sw"><div><h3>✨ {e(T(lang, 'dream_positive'))}</h3><p>{e(x['positive'])}</p></div><div><h3>⚠️ {e(T(lang, 'dream_warning'))}</h3><p>{e(x['warning'])}</p></div></div>
  {f'<h2>❓ {e(T(lang, "dream_variations"))}</h2>' + "".join(f"<details class='faq'><summary>{e(q['q'])}</summary><p>{e(q['ans'])}</p></details>" for q in v) if v else ''}
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <h2>🌙 {e(T(lang, 'dreams_more'))}</h2><div class="chips">{"".join(f'<a class="mchip" href="{pre}/dreams/{o}/">{e(DR[o].get("emoji", "🌙"))} {e(DR[o]["title"].split(":")[0])}</a>' for o in others if o != k)}</div>
  <a class="btn" href="{pre}/dreams/">📖 {e(T(lang, 'dreams_title'))}</a>
</article>"""
            schema = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang,
                      "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["ans"]}} for q in v]} if v else None
            add(lang, f"dreams/{k}/", x["title"], x["summary"], body, schema, priority="0.8")

    # evergreen guide collections (written by the agent): tarot meanings, angel numbers, birthdays, birthstones
    TAROT_KEYS = ["the-fool", "the-magician", "the-high-priestess", "the-empress", "the-emperor", "the-hierophant", "the-lovers",
                  "the-chariot", "strength", "the-hermit", "wheel-of-fortune", "justice", "the-hanged-man", "death", "temperance",
                  "the-devil", "the-tower", "the-star", "the-moon", "the-sun", "judgement", "the-world"]
    MONTH_KEYS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    GD = {}
    for x in D["guides2"]:
        GD.setdefault(x.get("kind"), {})[x.get("key")] = x
    COLL = {"tarot": ("tarot-meanings", "tm", "🃏"), "angel": ("angel-numbers", "ang", "👼"),
            "birthday": ("birthday", "bdp", "🎂"), "birthstone": ("birthstones", "bst", "💎")}
    def short_title(x):
        return x["title"].split(":")[0]
    def label(kind, k):
        if kind == "birthday":
            m, d = k.split("-"); return fdate(lang, dt.date(2024, MONTH_KEYS.index(m) + 1, int(d)), True)
        return short_title(GD[kind][k])
    def month_name(m):
        return re.sub(r"\s*15日|\s*15\s*", " ", fdate(lang, dt.date(2024, MONTH_KEYS.index(m) + 1, 15), True)).strip(" ,.")
    def order(kind, ks):
        if kind == "tarot": return sorted(ks, key=TAROT_KEYS.index)
        if kind == "angel": return sorted(ks, key=lambda v: (len(v), v))
        if kind == "birthday": return sorted(ks, key=lambda v: (MONTH_KEYS.index(v.split("-")[0]), int(v.split("-")[1])))
        return sorted(ks, key=MONTH_KEYS.index)
    for kind, items in GD.items():
        if kind not in COLL:
            continue
        path, pfx, emo = COLL[kind]
        ks = order(kind, list(items))
        if kind == "birthday":
            groups = {}
            for k in ks:
                groups.setdefault(k.split("-")[0], []).append(k)
            grid = "".join(f'<h2>🎂 {e(month_name(m))}</h2>'
                           f'<div class="chips">' + "".join(f'<a class="mchip daychip" href="{pre}/{path}/{k}/">{e(label(kind, k))}</a>' for k in g) + '</div>'
                           for m, g in groups.items())
        else:
            grid = '<div class="dgrid">' + "".join(f'<a class="dcard" href="{pre}/{path}/{k}/"><span>{e(items[k].get("emoji", emo))}</span><b>{e(label(kind, k))}</b></a>' for k in ks) + '</div>'
        add(lang, f"{path}/", T(lang, pfx + "_title"), T(lang, pfx + "_desc"),
            f'<section class="zhub"><p class="kicker">{emo} {e(T(lang, pfx + "_title"))}</p><h1>{e(T(lang, pfx + "_title"))}</h1>'
            f'<p class="lead">{e(T(lang, pfx + "_desc"))}</p>{grid}</section>', priority="0.9")
        for i, k in enumerate(ks):
            x = items[k]
            nb = [ks[j] for j in (i - 1, i + 1) if 0 <= j < len(ks)]
            secs = "".join(f"<h2>{e(sc['h'])}</h2><p>{e(sc['p'])}</p>" for sc in x.get("sections", []))
            faq = x.get("faq", [])
            body = f"""
<article class="guide">
  <div class="pair-head"><span class="aemo dream" style="width:120px;height:120px;font-size:62px">{e(x.get('emoji', emo))}</span></div>
  <p class="kicker">{emo} {e(T(lang, pfx + '_title'))}</p><h1>{e(x['title'])}</h1>
  <p class="lead">{e(x['summary'])}</p>
  {secs}
  {f'<h2>❓ {e(T(lang, "faq_title"))}</h2>' + "".join(f"<details class='faq'><summary>{e(q['q'])}</summary><p>{e(q['ans'])}</p></details>" for q in faq) if faq else ''}
  <p class="small muted">{e(T(lang, 'entertainment_only'))}</p>
  <div class="chips">{"".join(f'<a class="mchip" href="{pre}/{path}/{o}/">{e(items[o].get("emoji", emo))} {e(label(kind, o))}</a>' for o in nb)}</div>
  <a class="btn" href="{pre}/{path}/">{emo} {e(T(lang, pfx + '_title'))}</a>
</article>"""
            schema = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang,
                      "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["ans"]}} for q in faq]} if faq else None
            add(lang, f"{path}/{k}/", x["title"], x["summary"], body, schema, priority="0.7")
    TAROT_LINKS = [f"{pre}/tarot-meanings/{k}/" if k in GD.get("tarot", {}) else "" for k in TAROT_KEYS]

    sj = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    # site search (the index is written after every page is known)
    add(lang, "search/", T(lang, "search_title"), T(lang, "search_desc"), f"""
<section class="zhub srch">
  <p class="kicker">🔍 {e(T(lang, 'search_title'))}</p><h1>{e(T(lang, 'search_title'))}</h1>
  <input class="dsearch" type="search" id="q" placeholder="🔍 {e(T(lang, 'search_ph'))}" autofocus>
  <p class="muted small" id="sn"></p>
  <div id="sr" class="sr"></div>
</section>
<script>(function(){{var I=[],q=document.getElementById('q'),r=document.getElementById('sr'),n=document.getElementById('sn');
function nz(s){{return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'')}}
function go(){{var v=nz(q.value.trim());if(v.length<2){{r.innerHTML='';n.textContent='';return}}var w=v.split(/\\s+/),out=I.filter(function(x){{return w.every(function(t){{return x.k.indexOf(t)>-1}})}}).slice(0,60);
n.textContent=out.length?'':{json.dumps(T(lang, 'search_none'), ensure_ascii=False)};
r.innerHTML=out.map(function(x){{return '<a class="sres" href="'+x.u+'"><b>'+x.t.replace(/</g,'&lt;')+'</b><small>'+x.d.replace(/</g,'&lt;')+'</small></a>'}}).join('')}}
fetch('/search-{lang}.json').then(function(x){{return x.json()}}).then(function(d){{I=d.map(function(x){{return {{t:x[0],u:x[1],d:x[2],k:nz(x[0]+' '+x[2])}}}});var s=new URLSearchParams(location.search).get('q');if(s)q.value=s;go()}});
q.oninput=go}})();</script>""", priority="0.3")

    # prayer times: calculated in the browser for each city
    ci = {"en": 1, "ar": 2, "fr": 3, "es": 4}.get(lang, 1)
    flag = lambda cc: "".join(chr(0x1F1E6 + ord(c) - 65) for c in cc)
    pnames = {n: T(lang, "pt_" + n) for n in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")}
    ptl = {**pnames, "next": T(lang, "pt_next"), "here": T(lang, "pt_here")}
    icons = {"fajr": "🌄", "sunrise": "🌅", "dhuhr": "☀️", "asr": "🌤️", "maghrib": "🌇", "isha": "🌙"}
    loc = {"ar": "ar-MA", "pt": "pt-BR"}.get(lang, lang)
    citylist = "".join(f'<a class="mchip ptchip" href="{pre}/prayer-times/{c[0]}/">{flag(c[5])} {e(c[ci])}</a>' for c in CITIES)
    def pt_widget(city, slug):
        d = {"city": city, "methods": PRAYER_METHODS, "l": ptl, "icons": icons, "locale": loc}
        return f"""<div id="prayer" class="prayer">
    <div class="pt-head"><b class="pt-city">{e(city.get("name", ""))}</b><small class="pt-date"></small></div>
    <p class="pt-next"></p><div class="pt-grid"></div>
    {'' if slug else f'<button class="btn small pt-locate" type="button">📍 {e(T(lang, "pt_locate"))}</button>'}
    <h2>📅 {e(T(lang, 'pt_month'))}</h2><div class="pt-scroll"><table class="pt-month"></table></div>
  </div>
<script type="application/json" id="prayer-data">{json.dumps(d, ensure_ascii=False)}</script>
<script src="/assets/prayer.js" defer></script>"""
    home_city = next(c for c in CITIES if c[0] == ("cairo" if lang == "ar" else "casablanca" if lang == "fr" else "mecca"))
    add(lang, "prayer-times/", T(lang, "pt_title"), T(lang, "pt_desc"), f"""
<article class="pt-page">
  <p class="kicker">🕌 {e(T(lang, 'pt_title'))}</p><h1>{e(T(lang, 'pt_title'))}</h1>
  <p class="lead">{e(T(lang, 'pt_desc'))}</p>
  <h2>🏙️ {e(T(lang, 'pt_cities'))}</h2><div class="chips">{citylist}</div>
  {pt_widget({"name": home_city[ci], "lat": home_city[6], "lng": home_city[7], "tz": home_city[8], "m": home_city[9]}, "")}
  <p class="small muted">ℹ️ {e(T(lang, 'pt_note'))}</p>
</article>""", priority="0.9")
    for c in CITIES:
        name = c[ci]
        others = [o for o in CITIES if o[5] == c[5] and o[0] != c[0]][:12] or [o for o in CITIES if o[0] != c[0]][:12]
        add(lang, f"prayer-times/{c[0]}/", T(lang, "pt_city_title", city=name), T(lang, "pt_city_desc", city=name), f"""
<article class="pt-page">
  <p class="kicker">🕌 <a href="{pre}/prayer-times/">{e(T(lang, 'pt_title'))}</a></p><h1>{flag(c[5])} {e(T(lang, 'pt_city_title', city=name))}</h1>
  <p class="lead">{e(T(lang, 'pt_city_desc', city=name))}</p>
  {pt_widget({"name": name, "lat": c[6], "lng": c[7], "tz": c[8], "m": c[9]}, c[0])}
  <p class="small muted">ℹ️ {e(T(lang, 'pt_note'))}</p>
  <h2>🏙️ {e(T(lang, 'pt_other'))}</h2><div class="chips">{"".join(f'<a class="mchip ptchip" href="{pre}/prayer-times/{o[0]}/">{flag(o[5])} {e(o[ci])}</a>' for o in others)}</div>
  <a class="btn light" href="{pre}/hijri-calendar/">🌙 {e(T(lang, 'hj_title'))}</a>
</article>""", priority="0.8")

    # Hijri calendar: today's date and converter (computed in the browser)
    hol = DATA[lang]["ui"].get("holidays", {})
    evs = sorted((d, k) for k, ys in ISLAMIC.items() for d in ys.values() if d >= TODAY)[:8]
    evrows = "".join(f'<li><b>{e(hol.get(k, UI_EN["holidays"].get(k, k)))}</b><span>{e(fdate(lang, d))}</span><small data-iso="{d}"></small>'
                     + (f' <a href="{pre}/countdown/{k}/">⏳</a>' if (lang, f"countdown/{k}/") in PAGES else "") + '</li>' for d, k in evs)
    hjd = {"locale": {"ar": "ar-MA", "pt": "pt-BR"}.get(lang, lang), "l": {k: e(T(lang, "hj_" + k)) for k in ("unsupported", "invalid")}}
    add(lang, "hijri-calendar/", T(lang, "hj_title"), T(lang, "hj_desc"), f"""
<article class="hijri-page">
  <p class="kicker">🌙 {e(T(lang, 'hj_title'))}</p><h1>{e(T(lang, 'hj_title'))}</h1>
  <p class="lead">{e(T(lang, 'hj_desc'))}</p>
  <div id="hijri" class="hijri">
    <div class="hj-today"><small class="hj-k">{e(T(lang, 'hj_today'))}</small><b>…</b><small></small></div>
    <div class="hj-box"><h2>📅 → 🌙 {e(T(lang, 'hj_g2h'))}</h2><input type="date" name="g"><p class="hj-g2h-out"></p></div>
    <div class="hj-box"><h2>🌙 → 📅 {e(T(lang, 'hj_h2g'))}</h2>
      <div class="hj-sel"><select name="hd" aria-label="{e(T(lang, 'hj_day'))}"></select><select name="hm" aria-label="{e(T(lang, 'hj_month'))}"></select><input type="number" name="hy" min="1300" max="1600" aria-label="{e(T(lang, 'hj_year'))}"></div>
      <p class="hj-h2g-out"></p></div>
  </div>
  <h2>🕌 {e(T(lang, 'hj_events'))}</h2><ul class="hj-events">{evrows}</ul>
  <p class="small muted">ℹ️ {e(T(lang, 'hj_note'))}</p>
</article>
<script type="application/json" id="hijri-data">{json.dumps(hjd, ensure_ascii=False)}</script>
<script src="/assets/hijri.js" defer></script>""", priority="0.9")

    # baby names: meaning pages written by the agent
    NM = D["names"]
    if NM:
        def name_number(n):
            import unicodedata as ud
            t = sum((ord(c) - 97) % 9 + 1 for c in ud.normalize("NFKD", n.lower()) if "a" <= c <= "z")
            while t > 9 and t not in (11, 22, 33):
                t = sum(int(d) for d in str(t))
            return t
        gl = lambda g: T(lang, "nm_boy" if g == "boy" else "nm_girl")
        keys = sorted(NM, key=lambda k: NM[k]["nm"].lower())
        scr = lambda k: f'<i>{e(NM[k]["script"])}</i>' if NM[k].get("script") else ""
        cards = []
        for letter in sorted({NM[k]["nm"][0].upper() for k in keys}):
            cards.append(f'<h2 class="nmletter" id="l-{letter}">{letter}</h2><div class="nmgrid">' + "".join(
                f'<a class="nmcard {NM[k]["gender"]}" href="{pre}/names/{k}/" data-q="{e((NM[k]["nm"] + " " + NM[k].get("script", "") + " " + NM[k]["meaning"]).lower())}" data-g="{NM[k]["gender"]}">'
                f'<b>{e(NM[k]["nm"])}</b>{scr(k)}<small>{e(NM[k]["meaning"])}</small></a>'
                for k in keys if NM[k]["nm"][0].upper() == letter) + '</div>')
        add(lang, "names/", T(lang, "nm_title"), T(lang, "nm_desc"), f"""
<section class="zhub nmhub">
  <p class="kicker">👶 {e(T(lang, 'nm_title'))}</p><h1>{e(T(lang, 'nm_title'))}</h1>
  <p class="lead">{e(T(lang, 'nm_desc'))}</p>
  <input class="dsearch" type="search" placeholder="🔍 {e(T(lang, 'nm_search'))}">
  <div class="nmfilter"><button class="on" data-g="">{e(T(lang, 'nm_all'))}</button><button data-g="boy">👦 {e(T(lang, 'nm_boys'))}</button><button data-g="girl">👧 {e(T(lang, 'nm_girls'))}</button></div>
  {"".join(cards)}
  <p class="muted small">✨ {e(T(lang, 'nm_new'))}</p>
</section>
<script>(function(){{var q='',g='',inp=document.querySelector('.nmhub .dsearch');function f(){{document.querySelectorAll('.nmcard').forEach(function(c){{c.hidden=(q&&c.dataset.q.indexOf(q)<0)||(g&&c.dataset.g!==g)}});document.querySelectorAll('.nmgrid').forEach(function(d){{var any=[].some.call(d.children,function(c){{return !c.hidden}});d.hidden=!any;d.previousElementSibling.hidden=!any}})}}inp.oninput=function(){{q=this.value.toLowerCase().trim();f()}};document.querySelectorAll('.nmfilter button').forEach(function(b){{b.onclick=function(){{document.querySelectorAll('.nmfilter button').forEach(function(x){{x.classList.remove('on')}});b.classList.add('on');g=b.dataset.g;f()}}}})}})();</script>""", priority="0.9")
        by_slug = {NM[k]["nm"].lower(): k for k in NM}
        for k in keys:
            x = NM[k]
            num = name_number(x["nm"])
            numlink = f'<a href="{pre}/numerology/{num}/">{num}</a>' if num in D["numerology"] else str(num)
            def chips(lst, link=False):
                return "".join((f'<a class="mchip nmchip" href="{pre}/names/{by_slug[v.lower()]}/">{e(v)}</a>' if link and v.lower() in by_slug and by_slug[v.lower()] != k
                                else f'<span class="mchip nmchip">{e(v)}</span>') for v in lst)
            same = [o for o in keys if o != k and NM[o]["nm"][0].upper() == x["nm"][0].upper()][:10]
            faq = x.get("faq", [])
            body = f"""
<article class="guide nmpage">
  <p class="kicker">👶 <a href="{pre}/names/">{e(T(lang, 'nm_title'))}</a></p>
  <div class="nmhead {x['gender']}"><span class="nmbig">{e(x['nm'])}</span>{f'<span class="nmscript">{e(x["script"])}</span>' if x.get('script') else ''}
    <div class="nmtags"><span>{'👦' if x['gender'] == 'boy' else '👧'} {e(gl(x['gender']))}</span><span>💬 {e(x['meaning'])}</span><span>🔢 {e(T(lang, 'nm_number'))}: {numlink}</span></div></div>
  <h1>{e(x['title'])}</h1>
  <p class="lead">{e(x['summary'])}</p>
  <h2>🌍 {e(T(lang, 'nm_origin'))}</h2><p>{e(x['origin'])}</p>
  <h2>✨ {e(T(lang, 'nm_personality'))}</h2><p>{e(x['personality'])}</p>
  <h2>📈 {e(T(lang, 'nm_popularity'))}</h2><p>{e(x['popularity'])}</p>
  {f'<h2>🔤 {e(T(lang, "nm_variants"))}</h2><div class="chips">{chips(x["variants"], True)}</div>' if x.get('variants') else ''}
  {f'<h2>💕 {e(T(lang, "nm_nicknames"))}</h2><div class="chips">{chips(x["nicknames"])}</div>' if x.get('nicknames') else ''}
  {f'<h2>👶 {e(T(lang, "nm_similar"))}</h2><div class="chips">{chips(x["similar"], True)}</div>' if x.get('similar') else ''}
  {f'<h2>❓ {e(T(lang, "faq_title"))}</h2>' + "".join(f"<details class='faq'><summary>{e(q['q'])}</summary><p>{e(q['ans'])}</p></details>" for q in faq) if faq else ''}
  {f'<h2>🔠 {e(T(lang, "nm_same_letter", letter=x["nm"][0].upper()))}</h2><div class="chips">' + "".join(f'<a class="mchip nmchip" href="{pre}/names/{o}/">{e(NM[o]["nm"])}</a>' for o in same) + '</div>' if same else ''}
  <a class="btn" href="{pre}/names/">👶 {e(T(lang, 'nm_all_names'))}</a>
</article>"""
            schema = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang,
                      "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["ans"]}} for q in faq]} if faq else None
            add(lang, f"names/{k}/", x["title"], x["summary"], body, schema, priority="0.8")

    # learn English: lessons written by the agent, explanations translated, English examples kept
    EN = D["english"]
    if EN:
        order = [x[0] for x in EN_ORDER if x[0] in EN]
        order += sorted(k for k in EN if k not in order)
        LV = ("A1", "A2", "B1", "B2")
        def ecard(k):
            x = EN[k]
            return (f'<a class="encard" href="{pre}/learn-english/{k}/" data-k="{k}"><span class="enemo"><img src="/assets/english/{x.get('cat', 'grammar')}.webp" width="60" height="60" alt="" loading="lazy"><em>{e(x.get("emoji", "📘"))}</em></span>'
                    f'<span class="entx"><b>{e(x["title"])}</b><small>{e(T(lang, "en_cat_" + x.get("cat", "grammar")))}</small></span><i class="enok">✓</i></a>')
        levels = "".join(f'<h2 class="enlv"><span class="cefr">{lv}</span> {e(T(lang, "en_lv_" + lv))}</h2><div class="engrid">' + "".join(ecard(k) for k in order if EN[k].get("cefr") == lv) + '</div>'
                         for lv in LV if any(EN[k].get("cefr") == lv for k in order))
        wod = [[w["en"], w["mean"], k] for k in order for w in EN[k].get("words", [])]
        edata = {"words": wod, "total": len(order), "l": {k: e(T(lang, "en_" + k)) for k in ("progress", "listen")}, "pre": pre}
        add(lang, "learn-english/", T(lang, "en_title"), T(lang, "en_desc"), f"""
<section class="zhub enhub">
  <p class="kicker">🇬🇧 {e(T(lang, 'en_title'))}</p><h1>{e(T(lang, 'en_title'))}</h1>
  <p class="lead">{e(T(lang, 'en_desc'))}</p>
  <img class="enhero" src="/assets/english/hero.webp" width="768" height="576" alt="{e(T(lang, 'en_title'))}">
  <div class="enwod"><small>⭐ {e(T(lang, 'en_wod'))}</small><div class="enwod-w"><b lang="en" dir="ltr"></b><button class="say" type="button" aria-label="{e(T(lang, 'en_listen'))}">🔊</button></div><p></p><a class="small" href="#"></a></div>
  <div class="enprog"><div class="enbar"><i></i></div><span></span></div>
  {levels}
  <p class="muted small">✨ {e(T(lang, 'en_new'))}</p>
</section>
<script type="application/json" id="en-data">{sj(edata)}</script>
<script src="/assets/english.js" defer></script>""", priority="0.9")
        for i, k in enumerate(order):
            x = EN[k]
            say = lambda t: f'<button class="say" type="button" data-t="{e(t)}" aria-label="{e(T(lang, "en_listen"))}">🔊</button>'
            secs = "".join(
                f"<h2>{e(sc['h'])}</h2><p>{e(sc['p'])}</p>" + "".join(
                    f'<div class="enex">{say(z["en"])}<div><b lang="en" dir="ltr">{e(z["en"])}</b><small>{e(z["mean"])}</small></div></div>' for z in sc.get("ex", []))
                for sc in x.get("sections", []))
            words = "".join(f'<div class="enw">{say(w["en"])}<b lang="en" dir="ltr">{e(w["en"])}</b><small>{e(w["mean"])}</small></div>' for w in x.get("words", []))
            qd = {"q": [{"ask": q["ask"], "en": q["en"], "c": q["choices"], "a": q["answer_index"]} for q in x["quiz"]], "k": k,
                  "l": {kk: e(T(lang, "en_" + kk)) for kk in ("score", "retry", "done", "listen")}}
            prv = order[i - 1] if i else None
            nxt = order[i + 1] if i + 1 < len(order) else None
            nav = (f'<a class="btn small ghost" href="{pre}/learn-english/{prv}/">← {e(EN[prv]["title"])}</a>' if prv else "") + \
                  (f'<a class="btn small" href="{pre}/learn-english/{nxt}/">{e(T(lang, "en_next"))}: {e(EN[nxt]["title"])} →</a>' if nxt else "")
            body = f"""
<article class="guide enles">
  <p class="kicker">🇬🇧 <a href="{pre}/learn-english/">{e(T(lang, 'en_title'))}</a> · <span class="cefr">{e(x.get('cefr', ''))}</span> {e(T(lang, 'en_cat_' + x.get('cat', 'grammar')))}</p>
  <img class="enles-img" src="/assets/english/{x.get('cat', 'grammar')}.webp" width="480" height="480" alt="{e(T(lang, 'en_cat_' + x.get('cat', 'grammar')))}">
  <h1>{e(x.get('emoji', '📘'))} {e(x['title'])}</h1>
  <p class="lead">{e(x['summary'])}</p>
  {secs}
  {f'<h2>📝 {e(T(lang, "en_words"))}</h2><div class="enwords">{words}</div>' if words else ''}
  {f'<div class="entip">💡 {e(x["tip"])}</div>' if x.get('tip') else ''}
  <h2>✅ {e(T(lang, 'en_quiz'))}</h2>
  <div id="enquiz" class="enquiz"></div>
  <div class="ennav">{nav}</div>
  <a class="btn light" href="{pre}/learn-english/">📚 {e(T(lang, 'en_all'))}</a>
</article>
<script type="application/json" id="enq-data">{sj(qd)}</script>
<script src="/assets/english.js" defer></script>"""
            schema = {"@context": "https://schema.org", "@type": "LearningResource", "name": x["title"], "description": x["summary"],
                      "inLanguage": lang, "educationalLevel": x.get("cefr", ""), "learningResourceType": "Lesson",
                      "teaches": x["title"], "isAccessibleForFree": True}
            add(lang, f"learn-english/{k}/", x["title"], x["summary"], body, schema, priority="0.8")

    # love compatibility
    sj = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
    elems = ["fire", "earth", "air", "water"]
    pairs = [f"{x}_{y}" for i, x in enumerate(elems) for y in elems[i:]]
    cdata = {"signs": {s: [SIGNS[s][0], SIGNS[s][1], e(sign_name(lang, s))] for s in SIGNS},
             "t": {k: e(T(lang, "compat_" + k)) for k in pairs},
             "l": {k: e(T(lang, "compat_" + k)) for k in ("love", "friend", "work", "tip", "share", "open")} | {"title": e(T(lang, "compat_title"))},
             "pairs": sorted(D["pairs"]), "pre": pre}
    opts = lambda sel: "".join(f'<option value="{s}"{" selected" if s == sel else ""}>{SIGNS[s][0]} {e(sign_name(lang, s))}</option>' for s in SIGNS)
    add(lang, "compatibility/", T(lang, "compat_title"), T(lang, "compat_desc"), f"""
<article class="compat-page">
  <p class="kicker">💕 {e(T(lang, 'compat_title'))}</p><h1>{e(T(lang, 'compat_title'))}</h1>
  <p class="lead">{e(T(lang, 'compat_desc'))}</p>
  <div id="compat" class="compat">
    <label><span>{e(T(lang, 'your_sign'))}</span><select name="a">{opts("aries")}</select></label>
    <span class="compat-plus">❤</span>
    <label><span>{e(T(lang, 'compat_partner'))}</span><select name="b">{opts("leo")}</select></label>
    <button class="btn compat-go">💘 {e(T(lang, 'compat_check'))}</button>
    <div class="compat-out" aria-live="polite"></div>
  </div>
  {f'<h2>💕 {e(T(lang, "compat_guides"))}</h2><div class="chips">' + "".join(f'<a class="mchip" href="{pre}/compatibility/{k}/">{SIGNS[v["a"]][0]}{SIGNS[v["b"]][0]} {e(sign_name(lang, v["a"]))} + {e(sign_name(lang, v["b"]))}</a>' for k, v in sorted(D["pairs"].items())) + '</div>' if D["pairs"] else ''}
</article>
<script type="application/json" id="compat-data">{sj(cdata)}</script>
<script src="/assets/compat.js" defer></script>""", priority="0.8")

    # tarot card of the day
    tdata = {"cards": [[e(T(lang, f"tarot_{i}")), e(T(lang, f"tarot_{i}_m"))] for i in range(22)],
             "l": {k: e(T(lang, "tarot_" + k)) for k in ("tap", "back", "again", "note")} | {"more": e(T(lang, "compat_open"))},
             "links": TAROT_LINKS}
    add(lang, "tarot/", T(lang, "tarot_title"), T(lang, "tarot_desc"), f"""
<article class="tarot-page">
  <p class="kicker">🔮 {e(T(lang, 'tarot_title'))}</p><h1>{e(T(lang, 'tarot_title'))}</h1>
  <p class="lead">{e(T(lang, 'tarot_desc'))}</p>
  <div id="tarot" class="tarot">
    <p class="tarot-msg"></p>
    <div class="tarot-deck">{''.join('<button class="tc" aria-label="card"><div class="tc-in"><div class="tc-back"></div></div></button>' for _ in range(3))}</div>
    <div class="tarot-out" hidden></div>
  </div>
</article>
<script type="application/json" id="tarot-data">{sj(tdata)}</script>
<script src="/assets/tarot.js" defer></script>""", priority="0.7")

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


def build_delete_page():
    body = f"""
<article class="post"><h1>Delete your data — {e(SITE)}</h1>
<p class="muted">Applies to the {e(SITE)} website ({e(URL)}) and the {e(SITE)} Android app (com.mydailytwist.app) by the {e(SITE)} developer.</p>
<h2>What data we have</h2>
<p>{e(SITE)} has no accounts. The only personal data we can hold is what you send us yourself through the contact form:
your <b>name</b>, your <b>email address</b> and your <b>message</b>.</p>
<p>Your game scores, levels, streaks and language choice are stored <b>only on your own device</b> (browser/app storage). We never receive them.</p>
<h2>How to request deletion</h2>
<ol>
<li>Open our <a href="/contact/">contact page</a>.</li>
<li>Write “Delete my data” in the message and enter the same email address you used before.</li>
<li>Send the form. We delete your name, email address and messages within <b>30 days</b> and confirm by email.</li>
</ol>
<h2>Delete data stored on your device</h2>
<p>Clear the site data in your browser settings, or in Android go to <b>Settings → Apps → {e(SITE)} → Storage → Clear storage</b>, or simply uninstall the app.</p>
<h2>What we keep</h2>
<p>Nothing. After deletion we keep no copy of your contact messages.</p>
</article>"""
    add("en", "delete-data/", f"Delete your data – {SITE}", f"How to request deletion of your data from {SITE}.", body, priority="0.2")


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
    build_delete_page()
    for (l, p), pg in PAGES.items():  # section illustration under the title of each hub page
        im = section_img(p)
        if im and p.count("/") == 1 and "/sections/" in im and "</h1>" in pg["body"] and "sechero" not in pg["body"]:
            i = pg["body"].index("</h1>") + 5
            pg["body"] = pg["body"][:i] + f'<img class="sechero" src="{im}" width="640" height="640" alt="{e(pg["title"])}">' + pg["body"][i:]
    for lang in LANGS:  # small per-language search index: title, url, short description
        idx = [[html.unescape(pg["title"]), f"{P(l)}/{p}", html.unescape(pg["desc"])[:110]]
               for (l, p), pg in PAGES.items() if l == lang and p not in ("search/", "")]
        (OUT / f"search-{lang}.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
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
