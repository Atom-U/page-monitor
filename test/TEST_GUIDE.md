# 🧪 Test Guide — Local Validation

## 🎯 Goal
Validate the monitor works on a JavaScript-rendered page **before** running it
on the real Android VRP URLs — and prove Playwright actually waits for JS
(rather than reading raw HTML).

`test_monitor.py` mirrors `../monitor.py` exactly (hash → compare → unified
diff → write/clear `latest_changes.md`), but points at a local mock page and
keeps its own state (`test_hashes.json`, `test_snapshots/`).

## 📋 Steps

### 1️⃣ Open 2 terminals

### 2️⃣ Terminal A — start the local server
```bash
cd test
python -m http.server 8000
```
Leave it running. You should see: `Serving HTTP on 0.0.0.0 port 8000 ...`

### 3️⃣ Terminal B — first run (saves baseline)
```bash
cd test
python test_monitor.py
```
Expected:
- Prints the captured content (the reward amounts like `$1,500,000`).
- Prints the **JS-rendering proof** → `✅ PASS — Playwright executed the page's JavaScript.`
- `📝 Baseline saved`. **No** `latest_changes.md` is created.

### 4️⃣ Modify the mock page
Open `test/mock_vrp.html` and change this line:
```html
<p><em>Last updated: CHANGE_THIS_TEXT_TO_TEST</em></p>
```
to something like:
```html
<p><em>Last updated: 2026-05-29</em></p>
```

### 5️⃣ Re-run the monitor
```bash
python test_monitor.py
```
✅ You should see:
- `🚨 CHANGE DETECTED`
- `📋 Wrote .../latest_changes.md (1 change(s))`

Open `../latest_changes.md` — it contains a unified diff showing the old vs new
"Last updated" line. This is the exact artifact the Claude Routine reads in
production.

### 6️⃣ Run once more (no edit) to confirm the "no change" path
```bash
python test_monitor.py
```
Expected: `✅ No changes` and `latest_changes.md` is **deleted**.

## ✅ What this proves
- Playwright correctly renders JS content (not just raw HTML).
- Hash comparison detects real changes and ignores unchanged content.
- The diff file is written on change and removed when there's nothing to report.

## 🔔 Discord webhook (separate one-time check)
```bash
python send_discord_test.py
```
Posts `🧪 Test from page-monitor setup — <timestamp>` to the webhook.
Requires an environment whose network policy allows `discord.com`.
