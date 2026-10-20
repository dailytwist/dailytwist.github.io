#!/usr/bin/env python3
"""
DailyTwist daily AI agent.

Every run it:
  1. Pulls today's trending searches (Google Trends RSS) for the configured country.
  2. Filters out sensitive / news-only topics (deaths, crimes, politics, disasters...).
  3. Writes evergreen "fun explainer" articles about the safe trending topics.
  4. Writes the 12 daily horoscopes.
  5. Writes the daily trivia quiz.
Everything is saved as JSON under content/, then site_builder/build.py turns it into HTML.

Usage:
  python agent/run_daily.py                 # generate content for today
  python agent/run_daily.py --backfill 14   # also fill the last 14 days (horoscopes + trivia + evergreen articles)
Requires GEMINI_API_KEY (free, Google AI Studio) or ANTHROPIC_API_KEY. No extra packages needed.
"""
import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
         "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]

# Topics the agent never writes about: news events, tragedies, politics, adult, gambling, health claims.
BLOCKED = re.compile(
    r"\b(dies|died|death|dead|killed|kill|shooting|shot|murder|arrest|arrested|charged|crash|"
    r"accident|fire|earthquake|hurricane|flood|tornado|war|attack|bomb|election|vote|senate|"
    r"congress|president|trump|biden|harris|politic|lawsuit|trial|court|sentenced|suicide|"
    r"overdose|cancer|disease|outbreak|virus|porn|nude|onlyfans|leak|casino|betting|odds|"
    r"lottery|powerball|mega millions|stock|crypto|bitcoin)\b", re.I)

API_URL = "https://api.anthropic.com/v1/messages"


# ---------------------------------------------------------------- helpers
def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


_GEMINI_MODEL = None


def gemini_model(key: str) -> str:
    """Pick a working Gemini model: the configured one if it exists, otherwise the newest Flash-Lite / Flash."""
    global _GEMINI_MODEL
    if _GEMINI_MODEL:
        return _GEMINI_MODEL
    wanted = CONFIG.get("gemini_model", "")
    try:
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                                     headers={"x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=60) as r:
            models = json.loads(r.read()).get("models", [])
        names = [m["name"].split("/", 1)[1] for m in models
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
        print(f"::warning::Gemini models available: {', '.join(names[:40])}")
        if wanted in names:
            _GEMINI_MODEL = wanted
        else:
            def score(n):
                bad = any(x in n for x in ("preview", "exp", "tts", "image", "live", "audio", "embedding", "robotics", "thinking"))
                kind = 2 if "flash-lite" in n else 1 if "flash" in n else 0
                ver = [int(x) for x in re.findall(r"\d+", n)[:2]] + [0, 0]
                return (not bad, kind > 0, "latest" in n, kind, ver[0], ver[1])
            _GEMINI_MODEL = max(names, key=score) if names else (wanted or "gemini-flash-lite-latest")
    except Exception as e:
        body = " ".join(e.read().decode().split())[:300] if hasattr(e, "read") else ""
        print(f"::warning::could not list Gemini models ({e} {body})")
        _GEMINI_MODEL = "gemini-flash-lite-latest"
    print(f"::warning::using Gemini model: {_GEMINI_MODEL}")
    return _GEMINI_MODEL


def ask_ai(prompt: str, max_tokens: int = 4000, retries: int = 4, json_mode: bool = False) -> str:
    """Uses Google Gemini (free tier) if GEMINI_API_KEY is set, otherwise Anthropic Claude."""
    gkey = os.environ.get("GEMINI_API_KEY")
    akey = os.environ.get("ANTHROPIC_API_KEY")
    if not gkey and not akey:
        print("::error::No AI key found. Add the GEMINI_API_KEY secret in the repository settings.")
        sys.exit(1)
    last_error = ""
    time.sleep(CONFIG.get("ai_delay_seconds", 4))  # stay under free-tier per-minute limits
    for attempt in range(retries):
        try:
            if gkey:
                model = gemini_model(gkey)
                data = _post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    {"contents": [{"parts": [{"text": prompt}]}],
                     "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.9,
                                          **({"responseMimeType": "application/json"} if json_mode else {})}},
                    {"x-goog-api-key": gkey, "content-type": "application/json"})
                return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            data = _post(API_URL, {"model": CONFIG["ai_model"], "max_tokens": max_tokens,
                                   "messages": [{"role": "user", "content": prompt}]},
                         {"x-api-key": akey, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            return "".join(b.get("text", "") for b in data["content"])
        except Exception as e:  # network / rate limit
            if hasattr(e, "read"):
                try:
                    e = f"{e} " + " ".join(e.read().decode().split())[:300]
                except Exception:
                    pass
            last_error = str(e)
            wait = 65 if "429" in str(e) else 10 * (attempt + 1)
            print(f"  AI call failed ({e}), retry {attempt + 1}/{retries} in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"AI call failed after retries: {last_error}")


def ask_json(prompt: str, max_tokens: int = 4000):
    text = ask_ai(prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no comments.", max_tokens, json_mode=True)
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=0)
    return json.loads(text[start:])


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:70] or "article"


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved {path.relative_to(ROOT)}")


def existing_article_titles() -> list:
    out = []
    for f in (CONTENT / "articles").glob("*.json"):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8"))["title"])
        except Exception:
            pass
    return out


# ---------------------------------------------------------------- trends
def trending_topics(geo: str) -> list:
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
        topics = [i.findtext("title", "").strip() for i in root.iter("item")]
        topics = [t for t in topics if t and not BLOCKED.search(t)]
        print(f"  {len(topics)} trending topics after filtering")
        return topics[:25]
    except Exception as e:
        print(f"  could not read Google Trends ({e}); using evergreen ideas only")
        return []


# ---------------------------------------------------------------- generators
def make_horoscopes(day: dt.date) -> None:
    path = CONTENT / "horoscopes" / f"{day}.json"
    if path.exists():
        return
    print(f"- horoscopes {day}")
    data = ask_json(f"""You write the daily horoscope column for an entertainment website.
Date: {day:%A, %B %d, %Y}.
Write a fresh horoscope for each of the 12 zodiac signs: {", ".join(SIGNS)}.
For each sign give:
 "overview": 90-120 words, warm, specific, playful, second person,
 "love": 1-2 sentences, "career": 1-2 sentences, "wellness": 1 sentence (light lifestyle tips only, never medical advice),
 "lucky_number": integer 1-99, "lucky_color": a color word, "mood": one word.
Make every sign clearly different. No financial or medical advice. No gambling.
Format: {{"aries": {{...}}, "taurus": {{...}}, ...}}""", max_tokens=8000)
    if set(data) >= set(SIGNS):
        save(path, {"date": str(day), "signs": {s: data[s] for s in SIGNS}})


def make_trivia(day: dt.date) -> None:
    path = CONTENT / "trivia" / f"{day}.json"
    if path.exists():
        return
    print(f"- trivia {day}")
    n = CONFIG["trivia_questions_per_day"]
    recent = []
    for f in sorted((CONTENT / "trivia").glob("*.json"))[-7:]:
        recent += [q["question"] for q in json.loads(f.read_text(encoding="utf-8"))["questions"]]
    data = ask_json(f"""Create a daily general-knowledge trivia quiz of {n} multiple-choice questions for {day:%B %d, %Y}.
Mix categories: geography, science, history, movies & pop culture, food, animals, sports, language, space.
Difficulty: 3 easy, 4 medium, 3 hard. Only use facts that are stable and certain; avoid anything that may have changed recently.
Do not repeat these recent questions: {json.dumps(recent[-40:])}
Format: {{"title": "a catchy quiz title", "questions": [{{"category": "...", "question": "...",
"options": ["...","...","...","..."], "answer_index": 0, "fun_fact": "one-sentence explanation"}}]}}""", max_tokens=5000)
    qs = [q for q in data.get("questions", []) if len(q.get("options", [])) == 4 and 0 <= q.get("answer_index", -1) < 4]
    rnd = random.Random(str(day))
    for q in qs:  # shuffle so the right answer is not always in the same spot
        right = q["options"][q["answer_index"]]
        rnd.shuffle(q["options"])
        q["answer_index"] = q["options"].index(right)
    if len(qs) >= 5:
        save(path, {"date": str(day), "title": data.get("title", "Daily Trivia"), "questions": qs})


def write_article(topic: str, day: dt.date, trending: bool) -> None:
    angle = ("This topic is trending in searches today. Write an EVERGREEN explainer about the subject itself "
             "(what it is, background, interesting facts, why people are curious) — do NOT report breaking news, "
             "scores, rumors or anything that happened in the last few days, because you cannot verify it."
             if trending else "Write an evergreen, genuinely useful and fun article on this topic.")
    data = ask_json(f"""You are a senior editor of a light, high-quality entertainment & curiosity website.
Topic: "{topic}"
{angle}
Rules:
- Original, helpful, people-first content; 700-1000 words; clear structure.
- Only state facts you are highly confident are true. If unsure, leave it out. Never invent quotes, statistics or dates.
- Never write about unreleased products, rumors, leaks or upcoming events you cannot verify.
- No medical, legal or financial advice; nothing sexual, violent, political or hateful; no clickbait lies.
- If the topic cannot be written safely and accurately as an evergreen piece, return {{"skip": true}}.
Format: {{"title": "SEO-friendly title (max 65 chars)", "description": "meta description (max 155 chars)",
"category": "one of: Entertainment, Science, Food, Travel, Sports, Lifestyle, Tech, History, Animals",
"sections": [{{"heading": "...", "paragraphs": ["...", "..."]}}],
"faq": [{{"q": "...", "a": "..."}}]}}  (4-6 sections, 3 FAQ items)""", max_tokens=5000)
    if data.get("skip") or not data.get("sections"):
        print(f"  skipped: {topic}")
        return
    slug = slugify(data["title"])
    path = CONTENT / "articles" / f"{slug}.json"
    if path.exists():
        return
    data.update({"slug": slug, "date": str(day), "topic": topic, "trending": trending})
    save(path, data)


def make_articles(day: dt.date, topics: list, count: int) -> None:
    done = existing_article_titles()
    if topics:
        print(f"- choosing articles from trends for {day}")
        picks = ask_json(f"""Here are today's trending search terms: {json.dumps(topics)}
Pick up to {count} that make a great EVERGREEN, family-friendly explainer article (celebrities' careers, movies, TV shows,
games, products, sports teams' history, places, holidays, food, science...).
Reject unreleased products, rumors and anything about deaths, crimes, accidents, politics, health scares, gambling, adult content, or that only makes sense as breaking news.
Avoid subjects already covered: {json.dumps(done[-60:])}
Format: {{"picks": ["topic", ...]}}""", max_tokens=500).get("picks", [])
    else:
        picks = []
    if len(picks) < count:
        print("- adding evergreen ideas")
        extra = ask_json(f"""Suggest {count - len(picks)} evergreen article ideas people search for every day
(curiosities, "why do...", "how does...", fun facts, food, animals, space, history, pop culture, holidays near {day:%B %d}).
Avoid subjects already covered: {json.dumps(done[-80:])}
Format: {{"ideas": ["...", ...]}}""", max_tokens=500).get("ideas", [])
        trending_set = set(picks)
        picks += extra
    else:
        trending_set = set(picks)
    for t in picks[:count]:
        try:
            write_article(t, day, t in trending_set)
        except Exception as e:
            print(f"  article failed for {t}: {e}")


# ---------------------------------------------------------------- translations
LANG_NAMES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese (Brazil)",
              "it": "Italian", "ja": "Japanese", "ar": "Modern Standard Arabic", "nl": "Dutch", "pl": "Polish",
              "tr": "Turkish", "id": "Indonesian", "hi": "Hindi", "ko": "Korean", "ru": "Russian",
              "sv": "Swedish", "zh": "Simplified Chinese", "vi": "Vietnamese", "th": "Thai", "uk": "Ukrainian"}
UI_EN = json.loads((ROOT / "site_builder" / "ui_en.json").read_text(encoding="utf-8"))
I18N = CONTENT / "i18n"
KEEP = {"slug", "date", "topic", "trending", "answer_index", "lucky_number", "category", "sign", "best", "hard", "a", "b", "score", "year", "animal", "number", "years", "symbol"}


def _keep(k, d) -> bool:
    return k in KEEP and not (k == "category" and "question" in d)  # quiz categories get translated


def _shape(o):
    if isinstance(o, dict):
        return {k: _shape(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_shape(v) for v in o]
    return type(o).__name__


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if not _keep(k, o)}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _merge(orig, tr):
    if isinstance(orig, dict):
        return {k: (v if _keep(k, orig) else _merge(v, tr.get(k, v))) for k, v in orig.items()}
    if isinstance(orig, list):
        return [_merge(a, b) for a, b in zip(orig, tr)] if len(orig) == len(tr) else orig
    return tr if isinstance(tr, type(orig)) else orig


def translate_json(obj, lang: str, max_tokens: int = 8000, tries: int = 2):
    src = _strip(obj)
    last = None
    for _ in range(tries):
        try:
            out = ask_json(f"""Translate every string value in this JSON into natural, fluent {LANG_NAMES.get(lang, lang)}
written for a native reader (not word-for-word). Rules:
- Keep the JSON structure, keys, list lengths and order EXACTLY the same: one translated string for every source string.
  Never merge, split, add or remove list items or paragraphs.
- Keep HTML tags, {{placeholders}} in curly braces, URLs, numbers and brand/person names unchanged.
- For horoscope and quiz text keep the same playful tone.
JSON:
{json.dumps(src, ensure_ascii=False)}""", max_tokens=max_tokens)
            if _shape(out) != _shape(src):
                raise ValueError("translated JSON has a different structure")
            return _merge(obj, out)
        except Exception as ex:
            last = ex
    raise last


def ensure_ui(lang: str) -> None:
    path = I18N / lang / "ui.json"
    have = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = {k: v for k, v in UI_EN.items() if k not in have}
    if not missing:
        return
    print(f"- UI strings -> {lang} ({len(missing)} keys)")
    html_keys = [k for k in missing if k.endswith("_html")]
    plain = [k for k in missing if k not in html_keys]
    groups = [{k: missing[k] for k in plain[i:i + 25]} for i in range(0, len(plain), 25)] + [{k: missing[k]} for k in html_keys]
    for g in groups:
        if not g:
            continue
        try:
            t = translate_json(g, lang)
        except Exception as ex:
            print(f"::warning::UI translation {lang} failed: {str(ex)[:200]}")
            continue
        for k, v in t.items():
            if isinstance(v, str) and set(re.findall(r"{\w+}", v)) != set(re.findall(r"{\w+}", UI_EN[k])):
                continue  # placeholders broken -> keep English for this key
            have[k] = v
    have["language_name"] = LANG_NAMES.get(lang, lang)
    save(path, have)


def translate_content(lang: str, budget: list, today: dt.date) -> None:
    jobs = []
    for kind in ("horoscopes", "trivia", "articles", "signs", "pairs", "yearly", "chinese", "numerology", "dreams"):
        for f in (CONTENT / kind).glob("*.json"):
            if not (I18N / lang / kind / f.name).exists():
                jobs.append((kind, f))
    # newest first (today's items come first), horoscopes/trivia before articles on the same day
    def newest(j):
        d = json.loads(j[1].read_text(encoding="utf-8")).get("date", "")
        return (d, j[0] != "articles")
    jobs.sort(key=newest, reverse=True)
    for kind, f in jobs:
        if budget[0] <= 0:
            return
        budget[0] -= 1
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            save(I18N / lang / kind / f.name, translate_json(data, lang))
        except Exception as ex:
            print(f"::warning::translate {kind}/{f.name} -> {lang} failed: {str(ex)[:200]}")


PAIR_ELEMENT = {"aries": "fire", "leo": "fire", "sagittarius": "fire", "taurus": "earth", "virgo": "earth", "capricorn": "earth",
                "gemini": "air", "libra": "air", "aquarius": "air", "cancer": "water", "scorpio": "water", "pisces": "water"}


def make_pairs(day: dt.date, count: int) -> None:
    """Evergreen love-compatibility guides, a few per day until all 78 sign pairs exist."""
    signs = list(PAIR_ELEMENT)
    todo = [(a, b) for i, a in enumerate(signs) for b in signs[i:]
            if not (CONTENT / "pairs" / f"{a}-{b}.json").exists()]
    for a, b in todo[:count]:
        print(f"- compatibility {a} + {b}")
        data = ask_json(f"""You write evergreen zodiac compatibility guides for an entertainment website.
Write an original, warm and specific guide for {a.title()} ({PAIR_ELEMENT[a]}) and {b.title()} ({PAIR_ELEMENT[b]}).
{"It is a pair of the same sign, so talk about two " + a.title() + "s together." if a == b else ""}
Use classic astrology ideas (elements, ruling planets, modalities) but keep it fun, kind and for entertainment.
Never claim a pair is doomed; give practical, positive advice. No medical, legal or financial advice.
Format: {{"title": "{a.title()} and {b.title()} Compatibility: Love, Friendship & Work",
"summary": "2-3 sentences", "love": "110-150 words", "friendship": "60-90 words", "work": "60-90 words",
"challenges": "60-90 words", "tips": ["3 short practical tips"], "score": an integer 40-98 for overall harmony}}""", max_tokens=3000)
        need = ("title", "summary", "love", "friendship", "work", "challenges", "tips", "score")
        if all(k in data for k in need) and isinstance(data["tips"], list) and len(data["tips"]) >= 3:
            data["tips"] = [str(t) for t in data["tips"][:3]]
            data["score"] = max(40, min(98, int(data["score"])))
            save(CONTENT / "pairs" / f"{a}-{b}.json",
                 {"date": str(day), "slug": f"{a}-{b}", "a": a, "b": b, **{k: data[k] for k in need}})


def make_yearly(day: dt.date, count: int) -> None:
    """Next-year forecast per sign, written from October on, a few per run."""
    year = day.year + 1 if day.month >= 10 else day.year
    todo = [s for s in SIGNS if not (CONTENT / "yearly" / f"{year}-{s}.json").exists()]
    for s in todo[:count]:
        print(f"- yearly {year} {s}")
        data = ask_json(f"""Write the {year} yearly horoscope for {s.title()} for an entertainment website.
Warm, specific, optimistic but honest, second person. Use classic astrology ideas (ruling planet, element) loosely.
No medical, legal, financial or gambling advice.
Format: {{"title": "{s.title()} Horoscope {year}: Love, Career, Money & Luck", "summary": "2-3 sentences",
"love": "100-130 words", "career": "100-130 words", "money": "60-90 words (general habits only)", "wellness": "60-90 words (light lifestyle tips)",
"best_months": ["3 month names"], "theme": "a 2-4 word theme for the year", "tips": ["3 short tips"]}}""", max_tokens=3000)
        need = ("title", "summary", "love", "career", "money", "wellness", "best_months", "theme", "tips")
        if all(k in data for k in need):
            save(CONTENT / "yearly" / f"{year}-{s}.json", {"date": str(day), "year": year, "sign": s, **{k: data[k] for k in need}})


CHINESE = ["rat", "ox", "tiger", "rabbit", "dragon", "snake", "horse", "goat", "monkey", "rooster", "dog", "pig"]


def make_chinese(day: dt.date, count: int) -> None:
    todo = [a for a in CHINESE if not (CONTENT / "chinese" / f"{a}.json").exists()]
    for a in todo[:count]:
        years = [y for y in range(1936, 2032) if (y - 1936) % 12 == CHINESE.index(a)]
        print(f"- chinese zodiac {a}")
        data = ask_json(f"""Write an evergreen guide to the Chinese zodiac animal {a.title()} for an entertainment website.
Accurate to traditional Chinese astrology, warm and specific. Years: {years}.
Format: {{"title": "Year of the {a.title()}: Personality, Love, Career & Compatibility", "intro": "2-3 sentences",
"personality": "110-150 words", "love": "70-100 words", "career": "60-90 words",
"strengths": ["5 short items"], "weaknesses": ["4 short items"], "lucky_colors": ["2-3 colors"], "lucky_numbers": "e.g. 2 and 3",
"best_matches": ["3 animal names in English, lowercase"], "faq": [{{"q": "question", "ans": "short answer"}}, 3 items]}}""", max_tokens=3000)
        need = ("title", "intro", "personality", "love", "career", "strengths", "weaknesses", "lucky_colors", "lucky_numbers", "best_matches", "faq")
        if all(k in data for k in need):
            data["best_matches"] = [m for m in (str(x).lower() for x in data["best_matches"]) if m in CHINESE][:3]
            data["faq"] = [{"q": str(x.get("q", "")), "ans": str(x.get("ans", ""))} for x in data["faq"] if isinstance(x, dict)][:4]
            save(CONTENT / "chinese" / f"{a}.json", {"date": str(day), "animal": a, "years": years, **{k: data[k] for k in need}})


DREAM_SYMBOLS = """snake teeth-falling-out falling flying being-chased water ocean fish baby pregnancy wedding ex-partner death
cat dog spider house car-crash fire money gold exam being-late naked-in-public school hair-loss blood rain flood storm
mirror moon sun stars bird horse lion wolf bear rat mouse cockroach shark crocodile scorpion bees butterfly flowers
tree garden mountain bridge stairs elevator door key lost-phone shoes clothes dress white-dress ring kiss hug crying
laughing dancing singing food bread eggs fruit grapes dates milk honey coffee meat cooking eating-with-family
mother father grandmother deceased-relative friend stranger celebrity king prayer mosque church quran angel
travel airplane train bus ship lost-in-a-city prison police running fighting war gun knife wound hospital doctor
illness shower bathroom toilet urine rainbow lightning earthquake snow desert river well green-grass camel sheep
cow goat chicken frog turtle owl crow pigeon peacock eagle wedding-ring gift party birthday moving-house new-house
old-house buying-a-car shopping lottery losing-money finding-money cheating breakup proposal twins children-playing""".split()


def make_dreams(day: dt.date, count: int) -> None:
    """Dream dictionary: a few dream symbols per day."""
    todo = [x for x in DREAM_SYMBOLS if not (CONTENT / "dreams" / f"{x}.json").exists()]
    for sym in todo[:count]:
        name = sym.replace("-", " ")
        print(f"- dream {name}")
        data = ask_json(f"""Write an evergreen dream-meaning guide: "Dream about {name}" for an entertainment website.
Kind, clear and specific. Mention common psychological interpretations and popular traditional/cultural readings
(including well-known interpretations from Arab and Islamic dream traditions where relevant), without religious rulings.
Never frightening, never medical advice. Format:
{{"title": "Dream About {name.title()}: Meaning and Interpretation", "summary": "2 sentences",
"meaning": "130-170 words", "positive": "60-80 words: hopeful meanings", "warning": "60-80 words: what it may ask you to watch",
"variations": [{{"q": "Dreaming of ... (a common variation)", "ans": "2-3 sentences"}}, 5 items],
"emoji": "one emoji"}}""", max_tokens=3000)
        need = ("title", "summary", "meaning", "positive", "warning", "variations")
        if all(k in data for k in need) and isinstance(data["variations"], list):
            data["variations"] = [{"q": str(v.get("q", "")), "ans": str(v.get("ans", ""))} for v in data["variations"] if isinstance(v, dict)][:6]
            save(CONTENT / "dreams" / f"{sym}.json", {"date": str(day), "symbol": sym, "emoji": str(data.get("emoji", "🌙"))[:4],
                                                     **{k: data[k] for k in need}})


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, default=0, help="also generate N previous days")
    args = ap.parse_args()
    today = dt.datetime.now(dt.timezone.utc).date()

    jobs = []
    for i in range(args.backfill, 0, -1):
        d = today - dt.timedelta(days=i)
        jobs += [(make_horoscopes, (d,)), (make_trivia, (d,)), (make_articles, (d, [], 2))]
    jobs += [(make_horoscopes, (today,)), (make_trivia, (today,)),
             (make_articles, (today, trending_topics(CONFIG["trends_geo"]), CONFIG["articles_per_day"])),
             (make_pairs, (today, CONFIG.get("pairs_per_day", 6))),
             (make_yearly, (today, 6)), (make_chinese, (today, 6)),
             (make_dreams, (today, CONFIG.get("dreams_per_day", 6)))]
    errors = 0
    for fn, a in jobs:
        try:
            fn(*a)
        except Exception as e:
            errors += 1
            print(f"::error::{fn.__name__} failed: {str(e)[:600]}")
    if errors == len(jobs):
        sys.exit(1)

    budget = [CONFIG.get("max_translations_per_run", 60)]
    langs = [l for l in CONFIG.get("languages", ["en"]) if l != "en"]
    for lang in langs:
        try:
            ensure_ui(lang)
        except Exception as ex:
            print(f"::warning::UI {lang}: {str(ex)[:200]}")
    # round-robin so every language gets today's content before any backlog
    for _ in range(100):
        used_round = 0
        for lang in langs:
            if budget[0] <= 0:
                break
            chunk = [min(3, budget[0])]
            start = chunk[0]
            translate_content(lang, chunk, today)
            used = start - chunk[0]
            budget[0] -= used
            used_round += used
        if used_round == 0:
            break
    print("Agent finished.")


if __name__ == "__main__":
    main()
