"""
🔍 Android VRP Page Monitor
Checks Google security pages for changes, saves snapshots, and writes
latest_changes.md with diffs when changes are detected.
"""

import difflib
import hashlib
import json
import os
from datetime import datetime, timezone

import requests
from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────
PAGES = {
    "Android VRP Rules": "https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules",
    "Severity Ratings": "https://source.android.com/docs/security/overview/updates-resources#severity",
    "About Rules": "https://bughunters.google.com/about/rules/about-this-section",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HASHES_FILE = os.path.join(BASE_DIR, "page_hashes.json")
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")
CHANGES_FILE = os.path.join(BASE_DIR, "latest_changes.md")

# ─── FETCH PAGE WITH PLAYWRIGHT ───────────────────────────────────
def fetch_page_content(url, browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        response = page.goto(url, wait_until="networkidle", timeout=60000)
        if response and response.status >= 400:
            print(f"⚠️ HTTP {response.status} for {url}")
            return None
        page.wait_for_timeout(3000)
        content = page.inner_text("body")
        text = content.strip()
        # Treat proxy/network error pages as fetch failures
        if len(text) < 100 or "not in allowlist" in text.lower() or "access denied" in text.lower():
            print(f"⚠️ Blocked or empty response for {url}")
            return None
        return text
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return None
    finally:
        page.close()
        context.close()

# ─── HELPERS ──────────────────────────────────────────────────────
def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_hashes():
    if os.path.exists(HASHES_FILE):
        with open(HASHES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_hashes(hashes):
    with open(HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)

def snapshot_path(name):
    safe = name.replace(" ", "_").replace("/", "-")
    return os.path.join(SNAPSHOTS_DIR, f"{safe}.txt")

def load_snapshot(name):
    path = snapshot_path(name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_snapshot(name, content):
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    with open(snapshot_path(name), "w", encoding="utf-8") as f:
        f.write(content)

def build_diff(old_text, new_text):
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    return "".join(diff[:200])  # cap at 200 diff lines to avoid huge files

# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"🔍 Page Monitor — {now_str}")
    print("=" * 60)

    # Remove stale changes file from previous run
    if os.path.exists(CHANGES_FILE):
        os.remove(CHANGES_FILE)

    old_hashes = load_hashes()
    new_hashes = {}
    first_run = len(old_hashes) == 0
    change_blocks = []

    with sync_playwright() as p:
        # Use system-installed Chromium if the default build is unavailable
        chromium_fallback = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        launch_kwargs = {"headless": True}
        if not os.path.exists("/opt/pw-browsers/chromium_headless_shell-1223") and os.path.exists(chromium_fallback):
            launch_kwargs["executable_path"] = chromium_fallback
        browser = p.chromium.launch(**launch_kwargs)

        for name, url in PAGES.items():
            print(f"\n📄 Fetching: {name}...")
            content = fetch_page_content(url, browser)

            if content is None:
                print("   ⏭️ Skipped (fetch failed)")
                if name in old_hashes:
                    new_hashes[name] = old_hashes[name]
                continue

            current_hash = hash_content(content)
            new_hashes[name] = current_hash

            if first_run:
                print("   📝 First run — saved baseline")
                save_snapshot(name, content)
            elif name not in old_hashes:
                print("   🆕 New page — saved snapshot")
                save_snapshot(name, content)
            elif old_hashes[name] != current_hash:
                print("   🚨 CHANGE DETECTED!")
                old_content = load_snapshot(name)
                diff = build_diff(old_content, content)
                change_blocks.append({
                    "name": name,
                    "url": url,
                    "diff": diff,
                })
                save_snapshot(name, content)
            else:
                print("   ✅ No change")

        browser.close()

    save_hashes(new_hashes)

    print(f"\n{'=' * 60}")
    if first_run:
        print("📝 First run complete — baselines saved.")
    elif not change_blocks:
        print("✅ All pages unchanged.")
    else:
        print(f"🚨 {len(change_blocks)} change(s) detected — writing latest_changes.md")
        with open(CHANGES_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Android VRP Changes — {now_str}\n\n")
            for block in change_blocks:
                f.write(f"## {block['name']}\n")
                f.write(f"URL: {block['url']}\n\n")
                f.write("```diff\n")
                f.write(block["diff"] or "(no diff available)")
                f.write("\n```\n\n")
        print(f"✅ latest_changes.md written.")


if __name__ == "__main__":
    main()
