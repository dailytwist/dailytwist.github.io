#!/usr/bin/env python3
"""Sends the morning push notification through OneSignal, once per day.

Each subscriber gets it in their own language; people who chose a zodiac sign get their own sign's horoscope.
Needs the ONESIGNAL_API_KEY secret and "onesignal_app_id" in config.json.
"""
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
C = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
UI_EN = json.loads((ROOT / "site_builder" / "ui_en.json").read_text(encoding="utf-8"))
STATE = CONTENT / "push_sent.json"
URL = C["site_url"].rstrip("/")
SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
EMOJI = dict(zip(SIGNS, "♈♉♊♋♌♍♎♏♐♑♒♓"))


def ui(lang):
    d = dict(UI_EN)
    p = CONTENT / "i18n" / lang / "ui.json"
    if lang != "en" and p.exists():
        d.update(json.loads(p.read_text(encoding="utf-8")))
    return d


def horoscope(lang, day):
    p = (CONTENT if lang == "en" else CONTENT / "i18n" / lang) / "horoscopes" / f"{day}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def short(text, n=150):
    first = re.split(r"(?<=[.!?。！？])\s+", text.strip())[0]
    return first if len(first) <= n else first[: n - 1].rstrip() + "…"


AUTH = ["Key"]


def send(key, app, filters, title, body, url):
    data = json.dumps({"app_id": app, "target_channel": "push", "filters": filters,
                       "headings": {"en": title}, "contents": {"en": body}, "url": url,
                       "chrome_web_icon": f"{URL}/assets/icons/icon-192.png", "ttl": 43200}).encode()
    for scheme in list(AUTH) + [x for x in ("Key", "Basic") if x not in AUTH]:
        req = urllib.request.Request("https://api.onesignal.com/notifications?c=push", data=data, method="POST",
                                     headers={"Authorization": f"{scheme} {key}", "Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                AUTH[:] = [scheme]
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            res = {"error": e.code, "body": e.read().decode()[:300], "auth": scheme}
            if e.code != 401:
                return res
    return res


def main():
    raw = os.environ.get("ONESIGNAL_API_KEY", "")
    found = re.search(r"os_v2_[a-z]+_[A-Za-z0-9_-]+", raw)  # pick the key even if extra text was pasted with it
    key = found.group(0) if found else "".join(raw.split()).strip("'\"")
    app = C.get("onesignal_app_id")
    shape = {"len": len(key), "starts": key[:7], "v2": bool(found)}  # safe hints only, never the key
    if not key or not app:
        print("OneSignal not configured, skipping.")
        return
    today = str(dt.datetime.now(dt.timezone.utc).date())
    sent = json.loads(STATE.read_text()) if STATE.exists() else []
    test = os.environ.get("PUSH_TEST") == "1"
    log = []
    if test:  # one message to every subscriber, to check the setup
        r = send(key, app, [{"field": "session_count", "relation": ">", "value": "0"}], "✅ DailyTwist",
                 "Notifications are working! 🎉", f"{URL}/")
        print("test", r)
        (CONTENT / "push_log.json").write_text(json.dumps({"day": today, "test": r, "key_shape": shape}, ensure_ascii=False, indent=1))
        return
    if today in sent:
        print("Already sent today.")
        return
    ok = 0
    for lang in C.get("languages", ["en"]):
        u, pre = ui(lang), ("" if lang == "en" else f"/{lang}")
        lang_f = {"field": "tag", "key": "lang", "relation": "=", "value": lang}
        h = horoscope(lang, today)
        # everyone in this language without a chosen sign
        r = send(key, app, [lang_f, {"field": "tag", "key": "sign", "relation": "not_exists"}],
                 u.get("push_day_title", UI_EN["push_day_title"]), u.get("push_day_body", UI_EN["push_day_body"]), f"{URL}{pre}/")
        print(lang, "general", r.get("id") or r)
        log.append([lang, "general", r])
        ok += bool(r.get("id"))
        if not h:
            continue
        for s in SIGNS:
            name = u.get("signs", {}).get(s, s.title())
            title = u.get("push_sign_title", UI_EN["push_sign_title"]).replace("{sign}", f"{EMOJI[s]} {name}")
            r = send(key, app, [lang_f, {"field": "tag", "key": "sign", "relation": "=", "value": s}],
                     title, short(h["signs"][s]["overview"]), f"{URL}{pre}/horoscope/{s}/")
            ok += bool(r.get("id"))
            log.append([lang, s, r])
            if r.get("error"):
                print(lang, s, r)
    print("notifications created:", ok)
    (CONTENT / "push_log.json").write_text(json.dumps({"day": today, "created": ok, "results": log}, ensure_ascii=False, indent=1))
    sent = (sent + [today])[-60:]
    STATE.write_text(json.dumps(sent))


if __name__ == "__main__":
    main()
