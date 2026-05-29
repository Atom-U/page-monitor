"""
🔍 Android VRP Page Monitor
Checks Google security pages for changes, saves snapshots, and writes
latest_changes.md with diffs when changes are detected.
"""

import difflib
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────
PAGES = {
    "Android VRP Rules": "https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules",
    "Severity Ratings": "https://source.android.com/docs/security/overview/updates-resources#severity",
    "About Rules": "https://bughunters.google.com/about/rules/about-this-section",
}

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
HASHES_FILE   = os.path.join(BASE_DIR, "page_hashes.json")
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")
CHANGES_FILE  = os.path.join(BASE_DIR, "latest_changes.md")

# Existing Playwright-compatible Chromium available in the environment
CHROMIUM_EXEC = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# ─── HELPERS ──────────────────────────────────────────────────────
def snapshot_path(name):
    safe = name.replace(" ", "_").replace("/", "-")
    return os.path.join(SNAPSHOTS_DIR, f"{safe}.txt")


BLOCKED_MARKERS = ["host not in allowlist", "access denied", "403 forbidden"]


def fetch_page(url, browser):
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        content = page.inner_text("body").strip()
        if any(m in content.lower() for m in BLOCKED_MARKERS):
            print(f"  ⚠️  Network policy blocked {url}")
            return None
        return content
    except Exception as e:
        print(f"  ⚠️  Error fetching {url}: {e}")
        return None
    finally:
        page.close()


def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_hashes():
    if os.path.exists(HASHES_FILE):
        with open(HASHES_FILE) as f:
            return json.load(f)
    return {}


def save_hashes(hashes):
    with open(HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def load_snapshot(name):
    p = snapshot_path(name)
    if os.path.exists(p):
        with open(p) as f:
            return f.read()
    return ""


def save_snapshot(name, content):
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    with open(snapshot_path(name), "w") as f:
        f.write(content)


def build_diff(old_text, new_text):
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=3))
    return "".join(diff)


# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"🔍 Page Monitor — {now_str}")
    print("=" * 60)

    # Remove stale changes file from a previous run
    if os.path.exists(CHANGES_FILE):
        os.remove(CHANGES_FILE)

    old_hashes = load_hashes()
    new_hashes  = {}
    first_run   = len(old_hashes) == 0
    change_blocks = []   # (name, url, diff_text)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=CHROMIUM_EXEC,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--ignore-certificate-errors"],
        )

        for name, url in PAGES.items():
            print(f"\n📄 Fetching: {name} ...")
            content = fetch_page(url, browser)

            if content is None:
                print("   ⏭️  Skipped (fetch failed)")
                if name in old_hashes:
                    new_hashes[name] = old_hashes[name]
                continue

            current_hash = hash_text(content)
            new_hashes[name] = current_hash

            if first_run:
                print("   📝 First run — baseline saved")
                save_snapshot(name, content)
            elif name not in old_hashes:
                print("   🆕 New page — hash saved")
                save_snapshot(name, content)
            elif old_hashes[name] != current_hash:
                print("   🚨 CHANGE DETECTED!")
                old_content = load_snapshot(name)
                diff = build_diff(old_content, content)
                change_blocks.append((name, url, diff))
                save_snapshot(name, content)
            else:
                print("   ✅ No change")

        browser.close()

    save_hashes(new_hashes)

    print(f"\n{'=' * 60}")
    if first_run:
        print("📝 First run complete — baselines saved. No alerts sent.")
    elif not change_blocks:
        print("✅ All pages unchanged.")
    else:
        print(f"🚨 {len(change_blocks)} change(s) detected — writing latest_changes.md")
        with open(CHANGES_FILE, "w") as f:
            f.write(f"# Android VRP Page Changes — {now_str}\n\n")
            for name, url, diff in change_blocks:
                f.write(f"## {name}\n")
                f.write(f"**URL:** {url}\n\n")
                f.write("```diff\n")
                f.write(diff if diff else "(content changed but diff unavailable)\n")
                f.write("\n```\n\n")


if __name__ == "__main__":
    main()
