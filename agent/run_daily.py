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


def ask_ai(prompt: str, max_tokens: int = 4000, retries: int = 4) -> str:
    """Uses Google Gemini (free tier) if GEMINI_API_KEY is set, otherwise Anthropic Claude."""
    gkey = os.environ.get("GEMINI_API_KEY")
    akey = os.environ.get("ANTHROPIC_API_KEY")
    if not gkey and not akey:
        print("::error::No AI key found. Add the GEMINI_API_KEY secret in the repository settings.")
        sys.exit(1)
    last_error = ""
    for attempt in range(retries):
        try:
            if gkey:
                model = gemini_model(gkey)
                data = _post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    {"contents": [{"parts": [{"text": prompt}]}],
                     "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.9}},
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
    text = ask_ai(prompt + "\n\nReturn ONLY valid JSON, no markdown fences, no comments.", max_tokens)
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
             (make_articles, (today, trending_topics(CONFIG["trends_geo"]), CONFIG["articles_per_day"]))]
    errors = 0
    for fn, a in jobs:
        try:
            fn(*a)
        except Exception as e:
            errors += 1
            print(f"::error::{fn.__name__} failed: {str(e)[:600]}")
    if errors == len(jobs):
        sys.exit(1)
    print("Agent finished.")


if __name__ == "__main__":
    main()
