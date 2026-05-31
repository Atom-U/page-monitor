"""
Post the contents of latest_changes.md to a Discord webhook.

Reads the webhook URL from the DISCORD_WEBHOOK environment variable.
Splits the content into <1900-char chunks on line boundaries so each
message stays under Discord's 2000-char limit. Skips gracefully if the
webhook is missing or the changes file does not exist.
"""

import os
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANGES_FILE = os.path.join(SCRIPT_DIR, "latest_changes.md")
CHUNK_LIMIT = 1900


def chunk_lines(text, limit=CHUNK_LIMIT):
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        # A single line longer than the limit gets hard-split.
        if len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(line), limit):
                chunks.append(line[i:i + limit])
            continue
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks


def main():
    webhook = os.environ.get("DISCORD_WEBHOOK")
    if not webhook:
        print("DISCORD_WEBHOOK not set — skipping Discord notification.")
        return 0

    if not os.path.exists(CHANGES_FILE):
        print(f"{CHANGES_FILE} not found — nothing to post.")
        return 0

    with open(CHANGES_FILE, "r") as f:
        content = f.read().strip()

    if not content:
        print(f"{CHANGES_FILE} is empty — nothing to post.")
        return 0

    chunks = chunk_lines(content)
    print(f"Posting {len(chunks)} chunk(s) to Discord...")

    for i, chunk in enumerate(chunks, 1):
        resp = requests.post(webhook, json={"content": chunk}, timeout=15)
        if resp.status_code >= 300:
            print(f"  ❌ Chunk {i}/{len(chunks)} failed: "
                  f"{resp.status_code} {resp.text[:200]}")
            return 1
        print(f"  ✅ Chunk {i}/{len(chunks)} posted")

    return 0


if __name__ == "__main__":
    sys.exit(main())
