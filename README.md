# 🔍 Android VRP Page Monitor

Monitors Google Android security pages for changes and sends Discord alerts.

## Pages Monitored
- [Android VRP Rules](https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules)
- [Severity Ratings](https://source.android.com/docs/security/overview/updates-resources#severity)
- [About Rules](https://bughunters.google.com/about/rules/about-this-section)

## How It Works
1. Uses Playwright (headless browser) to fetch JS-rendered pages
2. Hashes the content and compares with previous run
3. If changed → sends a Discord webhook notification
4. Saves new hashes to `page_hashes.json`

## Triggered By
Claude Code Routine — runs daily at 9:00 GMT+7
