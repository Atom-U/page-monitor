# 🤖 Claude Routine Instructions

Copy-paste the block below into the **Instructions** field of your Claude Routine.

---

## 📋 Instructions to paste

```
You are a daily monitor for Android security pages.

STEP 1 — Run the monitoring script:
- Install dependencies: pip install -r requirements.txt
- Install Playwright browser: playwright install chromium
- Run: python monitor.py

STEP 2 — Check for changes:
- If a file named `latest_changes.md` exists in the repo root, it means changes were detected.
- If it does NOT exist, no changes were found. End the run silently. Do NOT post anything to Discord.

STEP 3 — Summarize and notify (only if latest_changes.md exists):
- Read the full content of `latest_changes.md`.
- Analyze the diff(s) carefully. For each changed page, identify:
  * What was added (new rules, new severity levels, new payouts, new requirements?)
  * What was removed
  * What was modified (payout amounts changed? eligibility criteria changed?)
- Ignore trivial changes like timestamps, dynamic counters, or CSS-injected text.
- Write a clear, concise summary in plain English (or French, whichever fits the user better).
- Highlight anything that could affect bug bounty earnings, eligibility, or scope.

STEP 4 — Post the summary to Discord:
- Send a POST request to this webhook:
  https://discord.com/api/webhooks/1405538181989793803/Rs0Yi4b8DV1uIXPLpWQxARSRpjSEc-alnuVvl3oxZIhy5i9KaXuCu5K_iNW9xfcuqvPz
- The webhook expects a JSON body with a "content" field, e.g. {"content": "..."}.
  Keep each message under Discord's 2000-character limit (split into multiple
  POSTs if a diff summary is long).
- Format the message like this:

🚨 **Android VRP Pages Changed — [date]**

📄 **[Page Name]**
🔗 [URL]

🧠 **Summary of changes:**
[your concise analysis here — what changed, why it matters for a bug bounty hunter]

⚠️ **Impact:** [low / medium / high — and why]

---

(repeat for each changed page)

STEP 5 — Commit updated state:
- Commit and push the updated `page_hashes.json` and `snapshots/` folder with message: "Update state [auto]"
- Do NOT commit `latest_changes.md` (it's regenerated each run and is gitignored).
```

---

## 🔧 Routine settings recap

| Field | Value |
|---|---|
| **Name** | Android VRP Page Monitor |
| **Repository** | Atom-U/page-monitor |
| **Trigger** | Daily at 9:00 GMT+7 ✅ |
| **Connectors** | None needed (the Routine posts to Discord directly) |
| **Network policy** | Must allow `discord.com`, `bughunters.google.com`, `source.android.com`, and the Playwright browser CDN |

> ⚠️ **Network note:** the Routine's environment must permit outbound access to
> `discord.com` (to post) and the Google pages (to fetch). If those hosts are
> blocked by the environment's network policy, fetches/posts will fail.

---

## 🧠 Why this design

| Choice | Reason |
|---|---|
| Script generates raw diff | Deterministic, no API cost, reliable |
| Claude Routine summarizes | Uses your existing Pro/Max plan, no extra key needed |
| Discord posted from Routine | One single notification with smart context |
| Snapshots stored in repo | Persistent memory across runs (the repo IS the state) |
