# 🍸📱 Daily Trends Briefing

An automated Python pipeline that scrapes 20+ sources every morning, uses AI to synthesize the raw data into real insights, generates a clean one-page PDF, and emails it to you.

Built to stay on top of **cocktail & bar industry trends** and **app & tech trends** without doomscrolling.

## What You Get

A PDF in your inbox every morning that looks like this:

> **🍸 COCKTAIL & BAR TRENDS**
> 
> *Clarified cocktails and savory ingredients are dominating bar menus worldwide*
> 
> • Sips in Barcelona just launched their summer menu focused on fermented fruit cordials. Their clarified Passion Fruit Negroni uses lacto-fermented passion fruit — a technique gaining traction across Mediterranean bars. [Read more →]
> 
> • BAR TIMES Japan reports that Kyoto's newest speakeasy is experimenting with hojicha-infused whisky highballs using custom carbonation rigs... [Read more →]

Every bullet has substance and a clickable link to the source.

## Architecture

```
Scrape → Synthesize → Generate → Deliver
```

1. **Scrape** — Python pulls raw data from 20+ websites and APIs
2. **Synthesize** — Claude AI reads everything and writes real insights (not just headlines)
3. **Generate** — ReportLab builds a formatted PDF with clickable links
4. **Deliver** — SMTP sends it to your inbox with the PDF attached

## Sources

### Cocktails & Bar Industry
| Source | Region | What It Covers |
|--------|--------|----------------|
| Reddit r/cocktails | Global | Community buzz, recipes, techniques |
| Punch Magazine | USA | Deep cocktail journalism |
| Imbibe Magazine | USA | Drinks culture and recipes |
| Difford's Guide | UK | Cocktail encyclopedia and news |
| BAR TIMES | Japan 🇯🇵 | Japan's bartender web magazine |
| DRiNK Magazine Asia | Asia 🌏 | Bars across Singapore, Tokyo, Bangkok, Seoul, HK |
| The Drink Magazine | Mexico 🇲🇽 | CDMX bar scene, mezcal, Mexican spirits |
| Google News | Global | Cocktail trends, bar openings |

### Apps & Tech
| Source | Focus | What It Covers |
|--------|-------|----------------|
| Product Hunt | Global | Daily new app launches |
| TechCrunch | USA/Global | Tech industry news |
| The Verge | USA/Global | Tech and app coverage |
| Hacker News | Developer community | Technically interesting tools and apps |
| Sensor Tower | Global | App download analytics and chart movers |
| 9to5Google | Android | App updates and trending Android apps |
| 9to5Mac | iOS | App updates and trending iOS apps |
| TechInAsia | Southeast Asia | Asian startups and apps |
| Reddit r/apps | Global | Community app recommendations |
| Google News | Global | Viral apps, social media trends |

## Setup

### 1. Clone and install
```bash
git clone https://github.com/YOUR-USERNAME/daily-trends-briefing.git
cd daily-trends-briefing
pip install -r requirements.txt
```

### 2. Configure
```bash
cp config_example.py config.py
```
Edit `config.py` with:
- Your **Anthropic API key** from [console.anthropic.com](https://console.anthropic.com/settings/keys) (~$0.01/day)
- Your **email** and **Gmail App Password** from [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### 3. Test
```bash
python daily_briefing.py
```

### 4. Schedule (runs daily)

**Windows** — Task Scheduler → Create Basic Task → Daily → `python daily_briefing.py`

**macOS/Linux** — Add to crontab:
```bash
0 8 * * * cd /path/to/daily-trends-briefing && python3 daily_briefing.py
```

See [SETUP.md](SETUP.md) for detailed instructions.

## How It Works

The script follows an **ETL (Extract, Transform, Load)** pattern:

- **Extract** — Each `fetch_*` function scrapes one source using `requests` + `BeautifulSoup` (or hits a JSON API for Reddit/Hacker News). Every fetcher is wrapped in `try/except` so one failure doesn't crash the pipeline.

- **Transform** — All raw data is sent to Claude's API with a detailed prompt. The AI reads headlines, excerpts, and post content from all sources — including Japanese and Spanish — and synthesizes them into 8-12 bullets of real insight with specific names, cities, and techniques.

- **Load** — ReportLab generates a PDF with clickable hyperlinks, and `smtplib` emails it as an attachment.

## Customization

**Add a new source:** Write a `fetch_*` function, call it in `main()`, and the AI prompt automatically picks it up. See the code comments for examples.

**Change regions:** Edit the AI prompt in `ai_synthesize()` to focus on different countries or topics.

**Switch delivery method:** Swap `send_email()` for a Telegram bot, Slack webhook, or any other notification system.

## Tech Stack

- **Python 3.10+**
- **requests** + **BeautifulSoup4** — Web scraping
- **Anthropic API (Claude Sonnet)** — AI synthesis
- **ReportLab** — PDF generation
- **smtplib** — Email delivery

## Cost

- **Anthropic API:** ~$0.01–0.03 per briefing (~$1/month)
- **Everything else:** Free

## License

MIT