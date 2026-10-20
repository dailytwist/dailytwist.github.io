"""Tell Bing, Yandex and other IndexNow search engines about new pages right after each publish."""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = "e181b022bc448928dc04bbbaad68aabf"
HOST = "www.mydailytwist.com"
SENT = ROOT / "content" / "indexnow_sent.json"


def main():
    urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "public" / "sitemap.xml").read_text(encoding="utf-8"))
    sent = set(json.loads(SENT.read_text())) if SENT.exists() else set()
    new = [u for u in urls if u not in sent]
    print(f"{len(urls)} pages in sitemap, {len(new)} new")
    for i in range(0, len(new), 9000):
        batch = new[i:i + 9000]
        body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": batch}).encode()
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print(f"  sent {len(batch)} urls -> HTTP {r.status}")
            sent.update(batch)
        except Exception as ex:
            print(f"::warning::IndexNow failed: {ex}")
            break
    SENT.write_text(json.dumps(sorted(sent), indent=0))


if __name__ == "__main__":
    main()
