"""
🧪 Discord webhook smoke test
================================================================
Sends ONE test message to the Discord webhook to confirm it works.
Run this once during setup:

    python test/send_discord_test.py

A success looks like HTTP 204 and a "🧪 Test from page-monitor setup"
message appearing in your Discord channel.

Note: this must run in an environment whose network policy ALLOWS
discord.com. (Some locked-down/CI environments block it.)
================================================================
"""

from datetime import datetime, timezone

import requests

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1405538181989793803/Rs0Yi4b8DV1uIXPLpWQxARSRpjSEc-alnuVvl3oxZIhy5i9KaXuCu5K_iNW9xfcuqvPz"


def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    payload = {"content": f"🧪 Test from page-monitor setup — {timestamp}"}

    print(f"Posting test message to Discord ({timestamp})...")
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=15)
        if r.status_code == 204:
            print("✅ Success (HTTP 204) — check your Discord channel.")
        else:
            print(f"⚠️ Unexpected response: HTTP {r.status_code} — {r.text}")
    except Exception as e:
        print(f"❌ Failed to reach Discord: {e}")


if __name__ == "__main__":
    main()
