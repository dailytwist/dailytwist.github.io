#!/usr/bin/env python3
"""DailyTwist guard ("العساس"): checks the live site, the domain and the repo.

Runs on GitHub Actions every few hours. If something looks wrong it opens (or
updates) one GitHub issue titled "🚨 Guard alert", so the owner gets an email,
and the job fails. When everything is fine again it closes that issue.

Checks:
  1. Site is up (www + apex) over HTTPS.
  2. TLS certificate is not about to expire.
  3. DNS still points at GitHub Pages.
  4. Domain registration: not expiring soon, not on hold.
  5. Live files match what the repository builds (no injected code).
  6. Pages load scripts/iframes only from allowed hosts; no miner/obfuscation.
  7. Recent commits come only from known authors.

Usage:
  python agent/guard.py                 # full live check
  python agent/guard.py --local public  # only scan a local build (for testing)
"""
import datetime as dt
import json
import subprocess
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SITE = CONFIG["site_url"].rstrip("/")            # https://www.mydailytwist.com
HOST = SITE.split("://", 1)[1]                    # www.mydailytwist.com
APEX = HOST[4:] if HOST.startswith("www.") else HOST
GITHUB_PAGES_IPS = {"185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"}
PAGES_TARGET = "dailytwist.github.io"

# Files whose live copy must be byte-identical to the repository build.
STATIC_FILES = ["sw.js", "manifest.webmanifest", ".well-known/assetlinks.json", "CNAME", "robots.txt"]
PAGES_TO_SCAN = ["", "games/", "horoscope/", "trivia/", "contact/", "ar/", "es/"]

# Hosts that pages may load scripts / iframes from (AdSense + contact form).
ALLOWED_HOSTS = (
    "pagead2.googlesyndication.com", "googleads.g.doubleclick.net", "tpc.googlesyndication.com",
    "ep2.adtrafficquality.google", "fundingchoicesmessages.google.com", "www.google.com",
    "www.gstatic.com", "api.web3forms.com", "cdn.onesignal.com", "onesignal.com",
)
SUSPICIOUS = re.compile(
    r"coinhive|cryptonight|coin-hive|webminer|miner\.start|crypto-loot|"
    r"eval\(atob|eval\(unescape|String\.fromCharCode\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+|"
    r"document\.write\(unescape",
    re.I,
)
KNOWN_EMAILS = {
    "sosomalika95@gmail.com",
    "noreply@anthropic.com",  # changes made by Claude for the owner
    "dailytwist@users.noreply.github.com",
    "bot@users.noreply.github.com",
    "noreply@github.com",
    "noreply@anthropic.com",
    "41898282+github-actions[bot]@users.noreply.github.com",
}
UA = {"User-Agent": "DailyTwist-Guard/1.0 (+https://www.mydailytwist.com)"}

problems: list[str] = []
notes: list[str] = []


def bad(msg):
    problems.append(msg)
    print("❌", msg)
    print("::error::" + str(msg)[:900].replace("\n", " "))  # shows up as a run annotation


def ok(msg):
    notes.append(msg)
    print("✅", msg)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.read()


def bust(url):
    return f"{url}{'&' if '?' in url else '?'}guard={int(time.time())}"


# ---------------------------------------------------------------- checks
def check_up():
    try:
        status, final, body = fetch(bust(SITE + "/"))
        if status == 200 and b"DailyTwist" in body:
            ok(f"site is up ({SITE})")
        else:
            bad(f"site answered {status} without the DailyTwist page")
    except Exception as e:
        bad(f"site is DOWN: {SITE} ({e})")
    try:
        status, final, _ = fetch(f"https://{APEX}/")
        if HOST in final:
            ok(f"{APEX} redirects to {HOST}")
        else:
            bad(f"https://{APEX}/ ended at {final} instead of {HOST}")
    except Exception as e:
        bad(f"https://{APEX}/ is not reachable ({e})")


def check_tls():
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((HOST, 443), timeout=20) as s:
            with ctx.wrap_socket(s, server_hostname=HOST) as t:
                cert = t.getpeercert()
        end = dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        days = (end - dt.datetime.utcnow()).days
        if days < 10:
            bad(f"HTTPS certificate expires in {days} days")
        else:
            ok(f"HTTPS certificate valid ({days} days left)")
    except Exception as e:
        bad(f"HTTPS certificate problem: {e}")


def doh(name, rtype):
    url = f"https://dns.google/resolve?name={name}&type={rtype}"
    _, _, body = fetch(url)
    data = json.loads(body)
    return [a["data"].rstrip(".") for a in data.get("Answer", []) if a.get("type") in (1, 5)]


def check_dns():
    try:
        a = set(x for x in doh(APEX, "A") if re.match(r"^\d+\.\d+\.\d+\.\d+$", x))
        if a and a <= GITHUB_PAGES_IPS:
            ok(f"DNS {APEX} -> GitHub Pages")
        else:
            bad(f"DNS for {APEX} points to {sorted(a) or 'nothing'} (expected GitHub Pages IPs)")
        cname = doh(HOST, "CNAME")
        if cname and cname[0].lower() == PAGES_TARGET:
            ok(f"DNS {HOST} -> {PAGES_TARGET}")
        else:
            bad(f"DNS for {HOST} points to {cname or 'nothing'} (expected {PAGES_TARGET})")
    except Exception as e:
        bad(f"could not check DNS: {e}")


def check_domain():
    try:
        _, _, body = fetch(f"https://rdap.verisign.com/com/v1/domain/{APEX.upper()}")
        data = json.loads(body)
        status = [s.lower() for s in data.get("status", [])]
        held = [s for s in status if "hold" in s]
        if held:
            bad(f"domain {APEX} is ON HOLD ({', '.join(held)}) — check Namecheap email verification")
        exp = next((e["eventDate"] for e in data.get("events", []) if e.get("eventAction") == "expiration"), None)
        if exp:
            end = dt.datetime.fromisoformat(exp.replace("Z", "+00:00"))
            days = (end - dt.datetime.now(dt.timezone.utc)).days
            if days < 30:
                bad(f"domain {APEX} expires in {days} days — make sure auto-renew works")
            else:
                ok(f"domain registered, {days} days left")
    except Exception as e:
        print("⚠️ could not read domain registry data:", e)  # registry hiccups are not alerts


def build_locally():
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "site_builder" / "build.py")], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise RuntimeError("local build failed")
    return ROOT / "public"


def same(rel, live, local):
    if rel == "sw.js":  # the cache name holds the build time; ignore it
        norm = lambda b: re.sub(rb"dailytwist-\d{12}", b"dailytwist-V", b)
        return norm(live) == norm(local)
    return live == local


def check_integrity(public: Path):
    files = STATIC_FILES + ["assets/" + p.name for p in sorted((public / "assets").glob("*.js"))]
    files += ["assets/" + p.name for p in sorted((public / "assets").glob("*.css"))]
    mismatched = []
    for rel in files:
        local = public / rel
        if not local.exists():
            continue
        try:
            _, _, live = fetch(bust(f"{SITE}/{rel}"))
        except Exception as e:
            mismatched.append(f"{rel} (not reachable: {e})")
            continue
        if not same(rel, live, local.read_bytes()):
            mismatched.append(rel)
    if mismatched:
        # a deploy may be in progress: wait and look once more before alerting
        time.sleep(300)
        still = []
        for rel in mismatched:
            rel = rel.split(" ")[0]
            try:
                _, _, live = fetch(bust(f"{SITE}/{rel}"))
                if not same(rel, live, (public / rel).read_bytes()):
                    still.append(rel)
            except Exception:
                still.append(rel)
        if still and deploy_pending():
            ok("a new version is still being published, live files will match after the deploy: " + ", ".join(still))
            return
        if still:
            bad("live files differ from the repository (possible tampering): " + ", ".join(still))
            return
    ok(f"{len(files)} live code files match the repository")


def scan_html(name, html):
    found = []
    for tag, src in re.findall(r"<(script|iframe)\b[^>]*\bsrc=[\"']([^\"']+)", html, re.I):
        if src.startswith("/") and not src.startswith("//"):
            continue
        host = re.sub(r"^(https?:)?//", "", src).split("/")[0].lower()
        if host in (HOST, APEX) or host.endswith(ALLOWED_HOSTS):
            continue
        found.append(f"{name}: unknown {tag} from {host}")
    m = SUSPICIOUS.search(html)
    if m:
        found.append(f"{name}: suspicious code '{m.group(0)[:40]}'")
    return found


def check_pages_live():
    issues = []
    for p in PAGES_TO_SCAN:
        try:
            _, _, body = fetch(bust(f"{SITE}/{p}"))
            issues += scan_html("/" + p, body.decode("utf-8", "replace"))
        except Exception as e:
            issues.append(f"/{p}: not reachable ({e})")
    for i in issues:
        bad(i)
    if not issues:
        ok(f"{len(PAGES_TO_SCAN)} pages scanned, no foreign scripts")


def check_pages_local(public: Path):
    issues = []
    n = 0
    for f in public.rglob("*.html"):
        n += 1
        issues += scan_html(str(f.relative_to(public)), f.read_text(encoding="utf-8", errors="replace"))
    for f in public.rglob("*.js"):
        m = SUSPICIOUS.search(f.read_text(encoding="utf-8", errors="replace"))
        if m:
            issues.append(f"{f.relative_to(public)}: suspicious code '{m.group(0)[:40]}'")
    for i in issues:
        bad(i)
    if not issues:
        ok(f"{n} local pages scanned, no foreign scripts")


def deploy_pending():
    """True while the newest commit is not live yet (a publish run is queued or running)."""
    try:
        for st in ("in_progress", "queued", "waiting", "pending"):
            runs = gh(f"/actions/runs?status={st}&per_page=20") or {}
            if any(r.get("name", "").startswith(("Daily", "pages")) for r in runs.get("workflow_runs", [])):
                return True
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        deps = gh("/deployments?environment=github-pages&per_page=1") or []
        return bool(head and deps and deps[0].get("sha") != head)
    except Exception as ex:
        print(f"  could not check deploy status: {ex}")
        return False


def gh(path, method="GET", payload=None):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    url = f"https://api.github.com/repos/{repo}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", **UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body else {}


def check_commits():
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        commits = gh(f"/commits?since={since}&per_page=100")
    except Exception as e:
        print("⚠️ could not list commits:", e)
        return
    if commits is None:
        print("(no GitHub token: commit check skipped)")
        return
    strangers = []
    for c in commits:
        for who in ("author", "committer"):
            email = (c["commit"].get(who) or {}).get("email", "").lower()
            if email and email not in KNOWN_EMAILS:
                strangers.append(f"{c['sha'][:7]} by {email}")
    if strangers:
        bad("commits from UNKNOWN people: " + "; ".join(sorted(set(strangers))))
    else:
        ok(f"{len(commits)} recent commits, all from known authors")


# ---------------------------------------------------------------- alerting
TITLE = "🚨 Guard alert"


def report():
    try:
        issues = gh("/issues?state=open&per_page=50")
    except Exception as e:
        print("⚠️ could not read issues:", e)
        issues = None
    if issues is None:
        return
    mine = next((i for i in issues if i.get("title") == TITLE and "pull_request" not in i), None)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if problems:
        body = (f"**{stamp}** — the guard found a problem:\n\n" + "\n".join(f"- {p}" for p in problems)
                + "\n\n(Arabic) العساس لقى مشكل فالموقع. صيفط هاد الصفحة لـ Claude باش يشوفها.")
        if mine:
            gh(f"/issues/{mine['number']}/comments", "POST", {"body": body})
        else:
            gh("/issues", "POST", {"title": TITLE, "body": body})
    elif mine:
        gh(f"/issues/{mine['number']}/comments", "POST",
           {"body": f"**{stamp}** — ✅ everything is fine again. Closing.\n\nكولشي رجع مزيان ✅"})
        gh(f"/issues/{mine['number']}", "PATCH", {"state": "closed"})


def check_links(public: Path):
    """Every internal link and file reference must point to something that exists (broken links hurt Google ranking)."""
    broken = {}
    for f in public.rglob("*.html"):
        for u in re.findall(r'(?:href|src)="(/[^"#?]*)', f.read_text(encoding="utf-8", errors="replace")):
            t = public / u.lstrip("/")
            if u.endswith("/"):
                t = t / "index.html"
            if not t.exists():
                broken.setdefault(u, str(f.relative_to(public)))
    if broken:
        sample = ", ".join(f"{u} (on {p})" for u, p in list(broken.items())[:8])
        bad(f"{len(broken)} broken internal links: {sample}")
    else:
        ok("all internal links work")


def main():
    args = sys.argv[1:]
    if args[:1] == ["--local"]:
        check_pages_local(Path(args[1]) if len(args) > 1 else ROOT / "public")
    else:
        check_up()
        check_tls()
        check_dns()
        check_domain()
        public = build_locally()
        check_integrity(public)
        check_pages_live()
        check_pages_local(public)
        check_links(public)
        check_commits()
        report()
    print(f"\n{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
