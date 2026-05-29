"""
🧪 TEST VERSION — points to localhost mock page
Use this to validate the monitor logic works before pointing at real URLs.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

import requests
from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1405538181989793803/Rs0Yi4b8DV1uIXPLpWQxARSRpjSEc-alnuVvl3oxZIhy5i9KaXuCu5K_iNW9xfcuqvPz"

# 🧪 TEST URLS — pointing to localhost mock
PAGES = {
    "Mock VRP Page (TEST)": "http://localhost:8000/mock_vrp.html",
}

HASHES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_hashes.json")

# ─── FETCH PAGE WITH PLAYWRIGHT ───────────────────────────────────
def fetch_page_content(url, browser):
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)  # wait for JS to inject content
        content = page.inner_text("body")
        return content.strip()
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return None
    finally:
        page.close()

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

def send_discord_alert(page_name, url, preview):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "content": (
            f"🧪 **[TEST] Page Changed!**\n"
            f"📄 **{page_name}**\n"
            f"🕐 Detected: {now}\n"
            f"👉 URL: {url}\n"
            f"📝 Preview: ```{preview[:200]}```"
        )
    }
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload)
        if r.status_code == 204:
            print(f"✅ Discord alert sent for: {page_name}")
        else:
            print(f"⚠️ Discord responded with {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ Failed to send Discord alert: {e}")

def main():
    print(f"🧪 TEST RUN — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
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
                continue

            print(f"   📝 Extracted content ({len(content)} chars):")
            print(f"   ┌─────────────────────────────────────────")
            for line in content.split("\n")[:10]:
                print(f"   │ {line}")
            print(f"   └─────────────────────────────────────────")

            current_hash = hash_content(content)
            new_hashes[name] = current_hash
            print(f"   🔢 Hash: {current_hash[:16]}...")

            if first_run:
                print(f"   📝 First run — saved baseline")
            elif name not in old_hashes:
                print(f"   🆕 New page — saved hash")
            elif old_hashes[name] != current_hash:
                print(f"   🚨 CHANGE DETECTED!")
                send_discord_alert(name, url, content)
                changes_found += 1
            else:
                print(f"   ✅ No change")

        browser.close()

    save_hashes(new_hashes)

    print(f"\n{'=' * 60}")
    if first_run:
        print("📝 First run complete — baseline saved. Now modify mock_vrp.html and re-run!")
    elif changes_found == 0:
        print("✅ No changes. (Did you modify mock_vrp.html?)")
    else:
        print(f"🚨 {changes_found} change(s) detected and Discord notified!")

if __name__ == "__main__":
    main()
