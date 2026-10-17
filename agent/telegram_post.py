#!/usr/bin/env python3
"""Posts today's highlights to the Telegram channel once per day.

Needs the TELEGRAM_BOT_TOKEN secret and "telegram_channel" in config.json (channel username without @).
The bot must be an admin of the channel with permission to post messages.
"""
import datetime as dt
import html
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
C = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
STATE = CONTENT / "telegram_sent.json"


def main():
    token = "".join((os.environ.get("TELEGRAM_BOT_TOKEN") or "").split())  # remove spaces/newlines from copy-paste
    channel = C.get("telegram_channel", "").lstrip("@")
    if not token or not channel:
        print("Telegram not configured, skipping.")
        return
    import re
    if "--check" in sys.argv:
        ok_format = bool(re.fullmatch(r"\d{6,12}:[A-Za-z0-9_-]{30,40}", token))
        print(f"::warning::token length {len(token)}, looks like a bot token: {ok_format}")
        try:
            with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=30) as r:
                me = json.loads(r.read())["result"]
            print(f"::warning::token works for bot @{me.get('username')}")
        except Exception as ex:
            print(f"::warning::getMe failed: {ex}")
        return
    today = str(dt.datetime.now(dt.timezone.utc).date())
    sent = json.loads(STATE.read_text()) if STATE.exists() else []
    if today in sent:
        print("Already posted today.")
        return
    url = C["site_url"].rstrip("/")
    e = html.escape
    lines = [f"✨ <b>{e(C['site_name'])}</b> — {dt.date.fromisoformat(today):%A, %B %-d}", ""]
    if (CONTENT / "horoscopes" / f"{today}.json").exists():
        lines.append(f"🔮 <a href=\"{url}/horoscope/\">Today's horoscope for every sign</a>")
    trivia = CONTENT / "trivia" / f"{today}.json"
    if trivia.exists():
        t = json.loads(trivia.read_text(encoding="utf-8"))
        lines.append(f"🧠 <a href=\"{url}/trivia/\">{e(t.get('title', 'Daily trivia'))}</a>")
    lines.append(f"🧩 <a href=\"{url}/puzzle/\">Today's word puzzle</a>")
    new = []
    for f in (CONTENT / "articles").glob("*.json"):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("date") == today:
            new.append(a)
    if new:
        lines += ["", "📖 <b>New explainers</b>"]
        lines += [f"• <a href=\"{url}/articles/{a['slug']}/\">{e(a['title'])}</a>" for a in new]
    body = urllib.parse.urlencode({"chat_id": f"@{channel}", "text": "\n".join(lines), "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=body, timeout=30) as r:
            ok = json.loads(r.read()).get("ok")
    except Exception as ex:
        detail = ex.read().decode()[:300] if hasattr(ex, "read") else ""
        print(f"::warning::Telegram post failed: {ex} {detail}")
        return
    if ok:
        sent = (sent + [today])[-30:]
        STATE.write_text(json.dumps(sent))
        print("Posted to Telegram.")


if __name__ == "__main__":
    sys.exit(main())
