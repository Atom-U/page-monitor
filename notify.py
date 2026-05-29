"""
Reads latest_changes.md, summarizes in French via Claude API,
and posts the result to Discord.
"""

import os
import sys
from datetime import datetime, timezone

import anthropic
import requests

DISCORD_WEBHOOK = (
    "https://discord.com/api/webhooks/1405538181989793803/"
    "Rs0Yi4b8DV1uIXPLpWQxARSRpjSEc-alnuVvl3oxZIhy5i9KaXuCu5K_iNW9xfcuqvPz"
)

PAGES = {
    "Android VRP Rules": "https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules",
    "Severity Ratings": "https://source.android.com/docs/security/overview/updates-resources#severity",
    "About Rules": "https://bughunters.google.com/about/rules/about-this-section",
}

CHANGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "latest_changes.md")

SYSTEM_PROMPT = """\
Tu es un expert en sécurité Android et en programmes de bug bounty.
On te donne un diff de pages web liées au Android Vulnerability Rewards Program (VRP) de Google.
Ta tâche est d'analyser ce diff et de produire un résumé clair et concis en français.

Pour chaque page modifiée :
- Identifie ce qui a été ajouté, supprimé ou modifié.
- Ignore les changements triviaux (horodatages, compteurs dynamiques, CSS).
- Évalue l'impact sur un chasseur de bugs : montants de récompenses, critères d'éligibilité, périmètre, nouvelles règles.
- Attribue un niveau d'impact : faible / moyen / élevé — et justifie brièvement.

Réponds uniquement avec le corps du message Discord, formaté exactement ainsi pour chaque page :

📄 **[Nom de la page]**
🔗 [URL]

🧠 **Résumé des changements :**
[analyse concise]

⚠️ **Impact :** [faible / moyen / élevé — raison]
"""


def summarize(diff_content: str) -> str:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": diff_content}],
        system=SYSTEM_PROMPT,
    )
    return message.content[0].text.strip()


def post_discord(text: str):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    full_message = f"🚨 **Android VRP Pages Changed — {today}**\n\n{text}"

    # Discord has a 2000-char limit per message; split if needed
    chunks = [full_message[i:i+1900] for i in range(0, len(full_message), 1900)]
    for chunk in chunks:
        r = requests.post(DISCORD_WEBHOOK, json={"content": chunk})
        if r.status_code not in (200, 204):
            print(f"⚠️  Discord responded with {r.status_code}: {r.text}")
            sys.exit(1)
    print("✅ Discord notified.")


def main():
    if not os.path.exists(CHANGES_FILE):
        print("No latest_changes.md found — nothing to notify.")
        return

    with open(CHANGES_FILE) as f:
        diff_content = f.read()

    print("🤖 Summarizing changes with Claude...")
    summary = summarize(diff_content)

    print("📨 Posting to Discord...")
    post_discord(summary)


if __name__ == "__main__":
    main()
