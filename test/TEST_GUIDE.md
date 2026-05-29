# 🧪 Test Guide — Local Validation

## 🎯 Goal
Validate the monitor works on a JS-rendered page BEFORE running on the real Android VRP URLs.

## 📋 Steps

### 1️⃣ Open 2 terminals

### 2️⃣ Terminal 1 — Start the local server
```bash
cd test
python -m http.server 8000
```
Leave it running. You should see:
`Serving HTTP on 0.0.0.0 port 8000 ...`

### 3️⃣ Terminal 2 — First run (saves baseline)
```bash
cd test
python test_monitor.py
```

Expected: prints the extracted content (should show the reward amounts), saves baseline. NO Discord alert.

### 4️⃣ Modify the mock page
Open `test/mock_vrp.html` and change this line:
```html
<p><em>Last updated: CHANGE_THIS_TEXT_TO_TEST</em></p>
```
To something like:
```html
<p><em>Last updated: 2026-05-20</em></p>
```

### 5️⃣ Re-run the monitor
```bash
python test_monitor.py
```

✅ You should see:
- `🚨 CHANGE DETECTED!` in terminal
- A message on your Discord channel

### 6️⃣ If Discord works → 🎉 the logic is valid!
Now we know:
- ✅ Playwright correctly renders JS content
- ✅ Hash comparison works
- ✅ Discord webhook works

Then we can deploy on Claude Routines with confidence.
