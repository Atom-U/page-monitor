# 🔍 Android VRP Page Monitor

Monitors Google Android security pages for changes. When a page changes, it
writes a unified diff to `latest_changes.md`; a [Claude Routine](ROUTINE_INSTRUCTIONS.md)
then reads that diff, summarizes the bug-bounty impact, and posts it to Discord.

## Pages Monitored
- [Android VRP Rules](https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules)
- [Severity Ratings](https://source.android.com/docs/security/overview/updates-resources#severity)
- [About Rules](https://bughunters.google.com/about/rules/about-this-section)

## How It Works
1. **Fetch** — Playwright (headless Chromium) loads each page and waits for
   JavaScript to render, then captures the visible text.
2. **Hash & compare** — the text is SHA256-hashed and compared with the value
   stored in `page_hashes.json` from the previous run.
3. **Diff** — if a page changed, a unified diff (old vs new) is written to
   `latest_changes.md`. The current text is stored in `snapshots/`.
4. **No change** — `latest_changes.md` is deleted if it exists, so the Routine
   knows there is nothing to report.

> The script itself does **not** post to Discord. That keeps it deterministic
> and free. The Claude Routine handles summarizing + notifying.

## Files
| File | Purpose |
|---|---|
| `monitor.py` | Production monitor (the 3 real pages). |
| `page_hashes.json` | Saved hashes — the memory across runs. **Committed.** |
| `snapshots/` | Last captured text of each page (used for diffing). **Committed.** |
| `latest_changes.md` | Diff output, regenerated each run. **Gitignored.** |
| `ROUTINE_INSTRUCTIONS.md` | The prompt to paste into the Claude Routine. |
| `test/` | Local end-to-end validation (see below). |

## Run It Manually
```bash
pip install -r requirements.txt
playwright install chromium
python monitor.py
```

## Local Test (validate before deploying)
The `test/` folder proves the pipeline works on a JS-rendered page **without**
touching the real URLs or Discord. See [`test/TEST_GUIDE.md`](test/TEST_GUIDE.md).

```bash
# Terminal A
cd test && python -m http.server 8000

# Terminal B
cd test && python test_monitor.py        # 1st run → baseline, no diff
#   ...edit mock_vrp.html...
python test_monitor.py                    # 2nd run → detects change, writes latest_changes.md
```

The test also prints a **JS-rendering proof**: it confirms the injected content
appears only in Playwright's rendered text, not in the raw HTML.

## Discord Webhook Test
```bash
python test/send_discord_test.py          # posts "🧪 Test from page-monitor setup — <time>"
```
(Requires an environment whose network policy allows `discord.com`.)

## Triggered By
A Claude Routine — runs daily at 9:00 GMT+7.
