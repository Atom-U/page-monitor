"""
🔍 Android VRP Page Monitor
Checks 3 Google security pages for changes and notifies via Discord webhook.
Uses Playwright to handle JavaScript-rendered pages.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import requests
from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1405538181989793803/Rs0Yi4b8DV1uIXPLpWQxARSRpjSEc-alnuVvl3oxZIhy5i9KaXuCu5K_iNW9xfcuqvPz"

PAGES = {
    "Android VRP Rules": "https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules",
    "Severity Ratings": "https://source.android.com/docs/security/overview/updates-resources#severity",
    "About Rules": "https://bughunters.google.com/about/rules/about-this-section",
}

HASHES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_hashes.json")

# ─── FETCH PAGE WITH PLAYWRIGHT ───────────────────────────────────
def fetch_page_content(url, browser):
    """Opens a page in headless Chromium, waits for JS to load, returns text."""
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)  # extra wait for dynamic content
        content = page.inner_text("body")
        return content.strip()
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return None
    finally:
        page.close()

# ─── HASH CONTENT ─────────────────────────────────────────────────
def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ─── LOAD SAVED HASHES ───────────────────────────────────────────
def load_hashes():
    if os.path.exists(HASHES_FILE):
        with open(HASHES_FILE, "r") as f:
            return json.load(f)
    return {}

# ─── SAVE HASHES ─────────────────────────────────────────────────
def save_hashes(hashes):
    with open(HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)

# ─── SEND DISCORD NOTIFICATION ───────────────────────────────────
def send_discord_alert(page_name, url):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "content": (
            f"🚨 **Android VRP Page Changed!**\n"
            f"📄 **{page_name}**\n"
            f"🕐 Detected: {now}\n"
            f"👉 Review it: {url}"
        )
    }
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload)
        if r.status_code == 204:
            print(f"✅ Discord alert sent for: {page_name}")
        else:
            print(f"⚠️ Discord responded with {r.status_code}")
    except Exception as e:
        print(f"❌ Failed to send Discord alert: {e}")

# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    print(f"🔍 Page Monitor — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    old_hashes = load_hashes()
    new_hashes = {}
    changes_found = 0
    first_run = len(old_hashes) == 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for name, url in PAGES.items():
            print(f"\n📄 Fetching: {name}...")
            content = fetch_page_content(url, browser)

            if content is None:
                print(f"   ⏭️ Skipped (fetch failed)")
                # Keep old hash if fetch fails
                if name in old_hashes:
                    new_hashes[name] = old_hashes[name]
                continue

            current_hash = hash_content(content)
            new_hashes[name] = current_hash

            if first_run:
                print(f"   📝 First run — saved baseline hash")
            elif name not in old_hashes:
                print(f"   🆕 New page added — saved hash")
            elif old_hashes[name] != current_hash:
                print(f"   🚨 CHANGE DETECTED!")
                send_discord_alert(name, url)
                changes_found += 1
            else:
                print(f"   ✅ No change")

        browser.close()

    save_hashes(new_hashes)

    print(f"\n{'=' * 60}")
    if first_run:
        print("📝 First run complete — baselines saved. No alerts sent.")
    elif changes_found == 0:
        print("✅ All pages unchanged.")
    else:
        print(f"🚨 {changes_found} change(s) detected and reported!")

if __name__ == "__main__":
    main()
