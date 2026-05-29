"""
🧪 TEST VERSION of monitor.py — points to a LOCAL mock page
================================================================
This mirrors the exact logic of ../monitor.py (hash → compare →
unified diff → write/clear latest_changes.md) but:

  * It fetches http://localhost:8000/mock_vrp.html instead of the
    real Google pages, so you can validate the whole pipeline offline.
  * It keeps its own state files (test_hashes.json, test_snapshots/)
    so it never interferes with the real page_hashes.json/snapshots/.
  * It writes the SAME latest_changes.md file the production script
    would, so you can confirm the diff artifact is produced correctly.

It also performs a sanity check that PROVES Playwright actually waited
for JavaScript: it compares the raw HTML (no JS) against the rendered
text (JS executed) and confirms the injected content only appears in
the rendered version.

HOW TO RUN (see test/TEST_GUIDE.md for full walkthrough):
  1. Terminal A:  cd test && python -m http.server 8000
  2. Terminal B:  cd test && python test_monitor.py      # baseline
  3. Edit mock_vrp.html (change the "Last updated" line)
  4. Terminal B:  python test_monitor.py                 # detects change
================================================================
"""

import difflib
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────
PAGES = {
    "Mock VRP Page (TEST)": "http://localhost:8000/mock_vrp.html",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Separate test-only state so we never touch the production files.
HASHES_FILE = os.path.join(SCRIPT_DIR, "test_hashes.json")
SNAPSHOTS_DIR = os.path.join(SCRIPT_DIR, "test_snapshots")
# Write to the REAL changes file (in the repo root) so we can confirm
# the production artifact is generated exactly as it would be live.
CHANGES_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "latest_changes.md")

# Optional Chromium override (only needed where the Playwright CDN is blocked).
CHROME_PATH = os.environ.get("CHROME_PATH")

os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


# ─── SAME HELPERS AS PRODUCTION ───────────────────────────────────
def fetch_page_content(url, browser):
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)  # wait for the 2s JS setTimeout to fire
        return page.inner_text("body").strip()
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return None
    finally:
        page.close()


def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_filename(name):
    return "".join(c if c.isalnum() else "_" for c in name)


def load_hashes():
    if os.path.exists(HASHES_FILE):
        with open(HASHES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_hashes(hashes):
    with open(HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def load_snapshot(page_name):
    path = os.path.join(SNAPSHOTS_DIR, f"{safe_filename(page_name)}.txt")
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return ""


def save_snapshot(page_name, content):
    path = os.path.join(SNAPSHOTS_DIR, f"{safe_filename(page_name)}.txt")
    with open(path, "w") as f:
        f.write(content)


def generate_diff(old_text, new_text, page_name):
    diff = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile=f"{page_name} (before)",
        tofile=f"{page_name} (after)",
        n=2,
        lineterm="",
    )
    return "\n".join(diff)


def launch_browser(p):
    launch_args = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if CHROME_PATH:
        launch_args["executable_path"] = CHROME_PATH
    return p.chromium.launch(**launch_args)


# ─── PROOF THAT PLAYWRIGHT WAITS FOR JS ───────────────────────────
def prove_js_rendering(url, rendered_text):
    """
    Confirm the content we captured really came from executed JavaScript.

    The mock page shows a "Loading dynamic content..." placeholder, and only
    AFTER a 2-second setTimeout does JS replace it with the reward table.

    The definitive proof is that the placeholder DISAPPEARS:
      * Raw HTML (urllib, no JS) still shows the loader, and the reward table
        only exists as text inside a <script> string — not as visible content.
      * Playwright's rendered text has NO loader left and DOES show the reward.
    If JS had not run, the rendered text would still contain the loader.

    (Note: a naive `"$1,500,000" in raw_html` check would be misleading, because
    that string literally appears inside the page's inline <script> source.)
    """
    loader = "Loading dynamic content"
    reward = "$1,500,000"
    try:
        raw_html = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"   (could not fetch raw HTML for the JS check: {e})")
        return

    raw_has_loader = loader in raw_html             # expected True (no JS yet)
    rendered_has_loader = loader in rendered_text   # expected False (JS replaced it)
    rendered_has_reward = reward in rendered_text   # expected True (JS injected it)

    print("\n🔬 JS-rendering proof:")
    print(f"   raw HTML still shows the loader?        {raw_has_loader}  (expected: True)")
    print(f"   rendered text still shows the loader?   {rendered_has_loader}  (expected: False)")
    print(f"   rendered text shows injected reward?    {rendered_has_reward}  (expected: True)")
    if raw_has_loader and not rendered_has_loader and rendered_has_reward:
        print("   ✅ PASS — Playwright waited for and executed the page's JavaScript.")
    else:
        print("   ❌ FAIL — JS rendering did not behave as expected.")


# ─── MAIN ─────────────────────────────────────────────────────────
def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"🧪 TEST RUN — {now}")
    print("=" * 60)

    old_hashes = load_hashes()
    new_hashes = {}
    changes = []
    first_run = len(old_hashes) == 0

    with sync_playwright() as p:
        browser = launch_browser(p)

        for name, url in PAGES.items():
            print(f"\n📄 {name}...")
            content = fetch_page_content(url, browser)

            if content is None:
                print("   ⏭️ Skipped (fetch failed — is `python -m http.server 8000` running in test/?)")
                if name in old_hashes:
                    new_hashes[name] = old_hashes[name]
                continue

            # Show a short preview so it's obvious JS content was captured.
            print(f"   📝 Captured {len(content)} chars. Preview:")
            for line in content.split("\n")[:8]:
                print(f"   │ {line}")

            # Prove the JS actually ran (only meaningful for the mock page).
            prove_js_rendering(url, content)

            current_hash = hash_content(content)
            new_hashes[name] = current_hash
            print(f"\n   🔢 Hash: {current_hash[:16]}...")

            if first_run or name not in old_hashes:
                save_snapshot(name, content)
                print("   📝 Baseline saved")
            elif old_hashes[name] != current_hash:
                print("   🚨 CHANGE DETECTED")
                old_content = load_snapshot(name)
                diff = generate_diff(old_content, content, name)
                changes.append((name, url, diff))
                save_snapshot(name, content)
            else:
                print("   ✅ No change")

        browser.close()

    save_hashes(new_hashes)

    if changes:
        with open(CHANGES_FILE, "w") as f:
            f.write(f"# 🚨 Page Changes Detected — {now}\n\n")
            f.write(f"**{len(changes)} page(s) changed.**\n\n")
            for name, url, diff in changes:
                f.write(f"---\n\n## 📄 {name}\n\n")
                f.write(f"🔗 {url}\n\n")
                f.write(f"### Diff:\n\n```diff\n{diff}\n```\n\n")
        print(f"\n📋 Wrote {CHANGES_FILE} ({len(changes)} change(s))")
    else:
        if os.path.exists(CHANGES_FILE):
            os.remove(CHANGES_FILE)
        if first_run:
            print("\n📝 First run complete — baseline saved. Now edit mock_vrp.html and re-run.")
        else:
            print("\n✅ No changes. (Did you edit mock_vrp.html between runs?)")


if __name__ == "__main__":
    main()
