#!/usr/bin/env python3
"""Saves the agent's new content without ever losing it to a merge conflict.

Someone may have pushed while the agent was working (site changes, UI texts). Instead of a rebase that can fail,
this copies the agent's files on top of the newest main: new files are added, and ui.json files are merged
key by key (texts already on main win, the agent only adds the keys that are missing).
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*a, check=True):
    return subprocess.run(["git", *a], cwd=ROOT, check=check, capture_output=True, text=True).stdout


def main():
    git("add", "content")
    changed = [l for l in git("diff", "--cached", "--name-only").splitlines() if l]
    if not changed:
        print("No new content.")
        return
    keep = Path(tempfile.mkdtemp())
    for rel in changed:
        src = ROOT / rel
        if src.exists():
            (keep / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, keep / rel)
    git("reset", "-q", "--hard")
    git("fetch", "-q", "origin", "main")
    git("reset", "-q", "--hard", "origin/main")
    for rel in changed:
        mine, dest = keep / rel, ROOT / rel
        if not mine.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and rel.endswith("/ui.json"):
            theirs = json.loads(dest.read_text(encoding="utf-8"))
            ours = json.loads(mine.read_text(encoding="utf-8"))
            for k, v in ours.items():
                theirs.setdefault(k, v)
            dest.write_text(json.dumps(theirs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif dest.exists() and rel.endswith(("_sent.json", "indexnow_sent.json")):
            try:
                a, b = json.loads(dest.read_text()), json.loads(mine.read_text())
                if isinstance(a, list) and isinstance(b, list):
                    dest.write_text(json.dumps(sorted(set(a) | set(b))))
                    continue
            except Exception:
                pass
            shutil.copy2(mine, dest)
        else:
            shutil.copy2(mine, dest)
    git("add", "content")
    if not git("diff", "--cached", "--name-only").strip():
        print("Nothing left to save.")
        return
    import datetime as dt
    git("commit", "-q", "-m", f"Daily content {dt.datetime.now(dt.timezone.utc).date()}")
    for attempt in range(3):
        if subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=ROOT).returncode == 0:
            print(f"Saved {len(changed)} files.")
            return
        git("pull", "-q", "--rebase", "-X", "theirs", "origin", "main", check=False)
    sys.exit("could not push the new content")


if __name__ == "__main__":
    main()
