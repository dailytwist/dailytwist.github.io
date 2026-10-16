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
Requires the environment variable ANTHROPIC_API_KEY. No extra packages needed.
"""
import argparse
import datetime as dt
import json
import os
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
def ask_ai(prompt: str, max_tokens: int = 4000, retries: int = 3) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY is not set.")
    body = json.dumps({
        "model": CONFIG["ai_model"],
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=body, headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
            return "".join(b.get("text", "") for b in data["content"])
        except Exception as e:  # network / rate limit
            print(f"  AI call failed ({e}), retry {attempt + 1}/{retries}")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("AI call failed after retries")


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
Reject anything about deaths, crimes, accidents, politics, health scares, gambling, adult content, or that only makes sense as breaking news.
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

    for i in range(args.backfill, 0, -1):
        d = today - dt.timedelta(days=i)
        make_horoscopes(d)
        make_trivia(d)
        make_articles(d, [], 2)

    topics = trending_topics(CONFIG["trends_geo"])
    make_horoscopes(today)
    make_trivia(today)
    make_articles(today, topics, CONFIG["articles_per_day"])
    print("Agent finished.")


if __name__ == "__main__":
    main()
