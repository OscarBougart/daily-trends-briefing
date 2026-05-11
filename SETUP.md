# Daily Trends Briefing — Setup Guide

## Quick Start (5 minutes)

### 1. Install Python dependencies
```bash
cd daily_trends
pip install -r requirements.txt
```

### 2. Configure your email
```bash
cp config_example.py config.py
```
Edit `config.py` with your email details. For Gmail, you need an **App Password**:
- Go to https://myaccount.google.com/apppasswords
- You must have 2-Step Verification enabled
- Generate a password for "Mail"
- Paste the 16-character code into config.py

### 3. Test it
```bash
python daily_briefing.py
```
You should receive an email with a PDF within a minute.

---

## Schedule It to Run Daily

### macOS / Linux (cron)
Open your crontab:
```bash
crontab -e
```
Add this line to run every day at 8:00 AM:
```
0 8 * * * cd /path/to/daily_trends && /usr/bin/python3 daily_briefing.py >> /tmp/briefing.log 2>&1
```
Replace `/path/to/daily_trends` with the actual path.

**Important:** Your laptop needs to be open/awake at 8 AM. On macOS, you can
use `caffeinate` or `pmset` to schedule a wake, or use `launchd` instead:

### macOS (launchd — recommended, survives restarts)
Create `~/Library/LaunchAgents/com.dailybriefing.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailybriefing</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/daily_trends/daily_briefing.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/daily_trends</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/briefing.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/briefing_err.log</string>
</dict>
</plist>
```
Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.dailybriefing.plist
```

### Windows (Task Scheduler)
1. Open Task Scheduler (search in Start menu)
2. Click "Create Basic Task"
3. Name: "Daily Trends Briefing"
4. Trigger: Daily at 8:00 AM
5. Action: Start a program
   - Program: `python` (or full path like `C:\Python312\python.exe`)
   - Arguments: `daily_briefing.py`
   - Start in: `C:\path\to\daily_trends`
6. Finish

---

## Customization

### Add/remove sources
Edit `daily_briefing.py` — each `fetch_*` function is independent. 
Comment out any you don't want in the `main()` function.

### Change the PDF layout
The `build_pdf()` function controls everything. Adjust colors, 
font sizes, and sections as you like.

### Add new sources
Create a new `fetch_*` function that returns a list of dicts,
add it to `main()`, and add a section in `build_pdf()`.

---

## Troubleshooting

**"Gmail: less secure apps" error**
→ You MUST use an App Password, not your regular password.

**Reddit returns empty**
→ Reddit sometimes rate-limits. The script handles this gracefully.

**Script works but no email arrives**
→ Check your spam folder. Also check /tmp/briefing.log for errors.

**Laptop was asleep when scheduled**
→ On macOS, launchd will run the job the next time you open the laptop.
  On Windows, check "Run task as soon as possible after a scheduled start is missed" in Task Scheduler.
