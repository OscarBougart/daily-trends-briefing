# ── Configuration for Daily Trends Briefing ──────────────────────────
# Copy this file to config.py and fill in your real details.
#
# For Gmail:
#   1. Enable 2-Step Verification on your Google account
#   2. Go to https://myaccount.google.com/apppasswords
#   3. Generate an "App Password" for "Mail"
#   4. Use that 16-character password below (NOT your regular password)
#
# For Outlook/Hotmail:
#   smtp_server: "smtp-mail.outlook.com"
#   smtp_port: 587
#
# For Yahoo:
#   smtp_server: "smtp.mail.yahoo.com"
#   smtp_port: 587

CONFIG = {
    "email": {
        "sender": "oscar.bougart.dev@gmail.com",           # Your email address
        "recipient": "oscar.bougart.dev@gmail.com",         # Where to receive the briefing
        "app_password": "jzwr nqcz zjns tsdf",       # Gmail App Password (NOT your normal password)
        "smtp_server": "smtp.gmail.com",             # Change if not using Gmail
        "smtp_port": 587,
    },
}
