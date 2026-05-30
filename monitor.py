"""
Android VRP Page Monitor
Fetches JS-rendered pages, compares with saved snapshots, writes latest_changes.md if anything changed.
Discord posting is handled externally (by Claude).
"""

import difflib
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PAGES = {
    "Android VRP Rules": "https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules",
    "Severity Ratings": "https://source.android.com/docs/security/overview/updates-resources#severity",
    "About Rules": "https://bughunters.google.com/about/rules/about-this-section",
}

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
HASHES_FILE   = os.path.join(BASE_DIR, "page_hashes.json")
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")
CHANGES_FILE  = os.path.join(BASE_DIR, "latest_changes.md")

# Older Playwright Chromium that is already present in the container
CHROMIUM_EXEC = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def snapshot_path(name: str) -> str:
    safe = name.replace(" ", "_").replace("/", "-")
    return os.path.join(SNAPSHOTS_DIR, f"{safe}.txt")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_hashes() -> dict:
    if os.path.exists(HASHES_FILE):
        with open(HASHES_FILE) as f:
            return json.load(f)
    return {}


def save_hashes(hashes: dict) -> None:
    with open(HASHES_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def load_snapshot(name: str) -> str | None:
    p = snapshot_path(name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return f.read()
    return None


def save_snapshot(name: str, content: str) -> None:
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    with open(snapshot_path(name), "w", encoding="utf-8") as f:
        f.write(content)


def build_diff(old: str | None, new: str) -> str:
    if old is None:
        return "(no previous snapshot available — baseline created this run)\n"
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="before", tofile="after", lineterm=""))
    if diff:
        return "\n".join(diff[:200])  # cap at 200 lines to stay readable
    return "(content changed but diff is empty — possible whitespace-only difference)\n"


# ─── FETCH ────────────────────────────────────────────────────────────────────
def fetch_page(url: str, browser) -> str | None:
    page = browser.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)
        content = page.inner_text("body")
        return content.strip()
    except Exception as e:
        print(f"  ⚠️  Fetch error: {e}")
        return None
    finally:
        page.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main() -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"🔍 Page Monitor — {now_str}")
    print("=" * 60)

    # Remove stale changes file from a previous run
    if os.path.exists(CHANGES_FILE):
        os.remove(CHANGES_FILE)

    old_hashes = load_hashes()
    new_hashes  = {}
    change_blocks: list[str] = []
    first_run = len(old_hashes) == 0

    launch_args = {"headless": True, "args": ["--ignore-certificate-errors", "--no-sandbox"]}
    if os.path.exists(CHROMIUM_EXEC):
        launch_args["executable_path"] = CHROMIUM_EXEC

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_args)

        for name, url in PAGES.items():
            print(f"\n📄 {name}")
            print(f"   {url}")
            content = fetch_page(url, browser)

            if content is None:
                print("   ⏭️  Skipped (fetch failed)")
                if name in old_hashes:
                    new_hashes[name] = old_hashes[name]
                continue

            current_hash = hash_text(content)
            new_hashes[name] = current_hash

            if first_run or name not in old_hashes:
                save_snapshot(name, content)
                print("   📝 Baseline saved")
            elif old_hashes[name] != current_hash:
                print("   🚨 CHANGE DETECTED")
                old_content = load_snapshot(name)
                diff_text   = build_diff(old_content, content)
                save_snapshot(name, content)
                block = (
                    f"## {name}\n"
                    f"**URL:** {url}\n\n"
                    f"```diff\n{diff_text}\n```\n"
                )
                change_blocks.append(block)
            else:
                print("   ✅ No change")

        browser.close()

    save_hashes(new_hashes)

    print("\n" + "=" * 60)
    if first_run:
        print("📝 First run — baselines saved. No changes file written.")
        sys.exit(0)

    if change_blocks:
        with open(CHANGES_FILE, "w", encoding="utf-8") as f:
            f.write(f"# Android VRP — Detected changes ({now_str})\n\n")
            f.write("\n---\n\n".join(change_blocks))
        print(f"🚨 {len(change_blocks)} change(s) detected → latest_changes.md written")
    else:
        print("✅ All pages unchanged.")


if __name__ == "__main__":
    main()
