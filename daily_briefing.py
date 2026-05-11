#!/usr/bin/env python3
"""
Daily Trends Briefing v2
========================
Pulls raw content from multiple sources, uses Claude AI to synthesize
real insights (not just titles), generates a PDF with clickable links,
and emails it to you.

Sources:
  Cocktails: Reddit r/cocktails, Punch, Imbibe, Difford's Guide,
             BAR TIMES Japan, DRiNK Magazine Asia, The Drink Magazine Mexico,
             Google search
  Apps/Tech: Product Hunt, TechCrunch, The Verge, Hacker News,
             Sensor Tower, 9to5Google, 9to5Mac, TechInAsia,
             Reddit, Google search

Usage:
  1. Copy config_example.py to config.py and fill in your details
  2. pip install -r requirements.txt
  3. python daily_briefing.py
"""

import datetime
import json
import re
import smtplib
import ssl
import traceback
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

# ── Load config ──────────────────────────────────────────────────────
try:
    from config import CONFIG
except ImportError:
    print("ERROR: config.py not found. Copy config_example.py to config.py and fill in your details.")
    raise SystemExit(1)

TODAY = datetime.date.today().strftime("%B %d, %Y")
DATE_SHORT = datetime.date.today().strftime("%Y-%m-%d")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 15


# ═══════════════════════════════════════════════════════════════════════
#  RAW DATA FETCHERS — gather content (not just titles)
# ═══════════════════════════════════════════════════════════════════════

def fetch_reddit_with_content(subreddit: str, limit: int = 8) -> list[dict]:
    """Fetch hot posts INCLUDING their text content from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit + 3}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        posts = r.json()["data"]["children"]
        results = []
        for p in posts:
            d = p["data"]
            if d.get("stickied"):
                continue
            results.append({
                "title": d["title"],
                "selftext": (d.get("selftext") or "")[:500],
                "score": d["score"],
                "url": f"https://reddit.com{d['permalink']}",
                "comments": d["num_comments"],
                "flair": d.get("link_flair_text", ""),
            })
        return results[:limit]
    except Exception as e:
        print(f"  [!] Reddit r/{subreddit} failed: {e}")
        return []


def fetch_punch() -> list[dict]:
    """Fetch Punch articles with excerpts."""
    url = "https://punchdrink.com/articles/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        # Try article blocks with excerpts
        for item in soup.select("article, .post, .entry")[:6]:
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            title_tag = item.find(["h2", "h3"])
            title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            link = a_tag["href"]
            if not link.startswith("http"):
                link = "https://punchdrink.com" + link
            desc_tag = item.find(["p", ".excerpt", ".summary"])
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            if title:
                articles.append({"title": title, "url": link, "excerpt": desc[:200]})
        # Fallback
        if not articles:
            for a_tag in soup.select("h2 a, h3 a")[:6]:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if title and link:
                    if not link.startswith("http"):
                        link = "https://punchdrink.com" + link
                    articles.append({"title": title, "url": link, "excerpt": ""})
        return articles[:5]
    except Exception as e:
        print(f"  [!] Punch failed: {e}")
        return []


def fetch_imbibe() -> list[dict]:
    """Fetch Imbibe magazine articles."""
    url = "https://imbibemagazine.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a_tag in soup.select("h2 a, h3 a, .entry-title a")[:5]:
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href", "")
            if title and link:
                articles.append({"title": title, "url": link, "excerpt": ""})
        return articles
    except Exception as e:
        print(f"  [!] Imbibe failed: {e}")
        return []


def fetch_diffords() -> list[dict]:
    """Fetch Difford's Guide content."""
    url = "https://www.diffordsguide.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a_tag in soup.select("h2 a, h3 a, .card a, a.card")[:5]:
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href", "")
            if title and link and len(title) > 3:
                if not link.startswith("http"):
                    link = "https://www.diffordsguide.com" + link
                articles.append({"title": title, "url": link, "excerpt": ""})
        return articles
    except Exception as e:
        print(f"  [!] Difford's failed: {e}")
        return []


def fetch_bar_times_japan() -> list[dict]:
    """Fetch BAR TIMES Japan — Japan's leading bartender web magazine (Japanese).
    Covers Suntory competitions, bar openings, bartender interviews, Japanese spirits."""
    url = "https://www.bar-times.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        # BAR TIMES uses various article containers
        for a_tag in soup.select("h2 a, h3 a, .post-title a, article a")[:10]:
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href", "")
            if title and link and len(title) > 3:
                if not link.startswith("http"):
                    link = "https://www.bar-times.com" + link
                # Skip navigation/menu links
                if any(skip in link for skip in ["/category", "/tag", "/page", "#"]):
                    continue
                articles.append({
                    "title": title,
                    "url": link,
                    "excerpt": "",
                    "source": "BAR TIMES Japan",
                })
        return articles[:6]
    except Exception as e:
        print(f"  [!] BAR TIMES Japan failed: {e}")
        return []


def fetch_drink_magazine_asia() -> list[dict]:
    """Fetch DRiNK Magazine Asia — the gold standard for Asian cocktail coverage.
    Covers bars across Singapore, Bangkok, Tokyo, Seoul, Taipei, Hong Kong."""
    url = "https://www.drinkmagazine.asia/latest-posts/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for item in soup.select("article, .post, .entry")[:8]:
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            title_tag = item.find(["h2", "h3"])
            title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            link = a_tag["href"]
            if not link.startswith("http"):
                link = "https://www.drinkmagazine.asia" + link
            desc_tag = item.find("p")
            desc = desc_tag.get_text(strip=True)[:200] if desc_tag else ""
            if title and len(title) > 3:
                articles.append({
                    "title": title,
                    "url": link,
                    "excerpt": desc,
                    "source": "DRiNK Magazine Asia",
                })
        # Fallback to headline links
        if not articles:
            for a_tag in soup.select("h2 a, h3 a")[:6]:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if title and link:
                    articles.append({
                        "title": title,
                        "url": link,
                        "excerpt": "",
                        "source": "DRiNK Magazine Asia",
                    })
        return articles[:6]
    except Exception as e:
        print(f"  [!] DRiNK Magazine Asia failed: {e}")
        return []


def fetch_the_drink_magazine_mexico() -> list[dict]:
    """Fetch The Drink Magazine — Mexico's main cocktail & spirits publication (Spanish).
    Covers CDMX bar scene, mezcal, tequila, Mexican coctelería."""
    url = "https://thedrinkmagazine.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for item in soup.select("article, .post, .jeg_post")[:8]:
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            title_tag = item.find(["h2", "h3"])
            title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            link = a_tag["href"]
            if not link.startswith("http"):
                link = "https://thedrinkmagazine.com" + link
            desc_tag = item.find("p")
            desc = desc_tag.get_text(strip=True)[:200] if desc_tag else ""
            if title and len(title) > 3:
                articles.append({
                    "title": title,
                    "url": link,
                    "excerpt": desc,
                    "source": "The Drink Magazine (Mexico)",
                })
        # Fallback
        if not articles:
            for a_tag in soup.select("h2 a, h3 a")[:6]:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if title and link:
                    articles.append({
                        "title": title,
                        "url": link,
                        "excerpt": "",
                        "source": "The Drink Magazine (Mexico)",
                    })
        return articles[:6]
    except Exception as e:
        print(f"  [!] The Drink Magazine (Mexico) failed: {e}")
        return []


def fetch_product_hunt_detailed() -> list[dict]:
    """Fetch Product Hunt with descriptions."""
    url = "https://www.producthunt.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        products = []
        for script in soup.find_all("script"):
            text = script.string or ""
            names = re.findall(r'"name"\s*:\s*"([^"]{3,60})"', text)
            taglines = re.findall(r'"tagline"\s*:\s*"([^"]{3,120})"', text)
            for i, name in enumerate(names[:8]):
                if any(c in name.lower() for c in ["script", "style", "function", "http", "prod"]):
                    continue
                tagline = taglines[i] if i < len(taglines) else ""
                products.append({"name": name, "tagline": tagline})
            if products:
                break
        return products[:5]
    except Exception as e:
        print(f"  [!] Product Hunt failed: {e}")
        return []


def fetch_techcrunch() -> list[dict]:
    """Fetch TechCrunch with article excerpts."""
    url = "https://techcrunch.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for item in soup.select("article, .post-block")[:8]:
            a_tag = item.find("a", href=True)
            title_tag = item.find(["h2", "h3"])
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = a_tag["href"] if a_tag else ""
            excerpt_tag = item.find(["p", ".post-block__content"])
            excerpt = excerpt_tag.get_text(strip=True)[:200] if excerpt_tag else ""
            if title:
                articles.append({"title": title, "url": link, "excerpt": excerpt})
        if not articles:
            for a_tag in soup.select("h2 a, h3 a")[:6]:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if title:
                    articles.append({"title": title, "url": link, "excerpt": ""})
        return articles[:6]
    except Exception as e:
        print(f"  [!] TechCrunch failed: {e}")
        return []


def fetch_theverge() -> list[dict]:
    """Fetch The Verge headlines."""
    url = "https://www.theverge.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a_tag in soup.select("h2 a, h3 a")[:6]:
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href", "")
            if title and link:
                if not link.startswith("http"):
                    link = "https://www.theverge.com" + link
                articles.append({"title": title, "url": link, "excerpt": ""})
        return articles
    except Exception as e:
        print(f"  [!] The Verge failed: {e}")
        return []


def fetch_hacker_news() -> list[dict]:
    """Fetch top stories from Hacker News via their public API.
    HN catches technically interesting apps and tools early."""
    try:
        # Get top story IDs
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers=HEADERS, timeout=TIMEOUT,
        )
        r.raise_for_status()
        story_ids = r.json()[:15]  # Top 15 stories

        stories = []
        for sid in story_ids:
            try:
                sr = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    headers=HEADERS, timeout=5,
                )
                sr.raise_for_status()
                item = sr.json()
                if item and item.get("title"):
                    stories.append({
                        "title": item["title"],
                        "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "score": item.get("score", 0),
                        "comments": item.get("descendants", 0),
                        "source": "Hacker News",
                    })
            except Exception:
                continue
        return stories[:8]
    except Exception as e:
        print(f"  [!] Hacker News failed: {e}")
        return []


def fetch_sensor_tower() -> list[dict]:
    """Fetch Sensor Tower blog — industry standard for app download analytics,
    top chart movers, and revenue trends by country."""
    url = "https://sensortower.com/blog"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for item in soup.select("article, .post, .blog-post, .entry")[:8]:
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            title_tag = item.find(["h2", "h3", "h4"])
            title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            link = a_tag["href"]
            if not link.startswith("http"):
                link = "https://sensortower.com" + link
            desc_tag = item.find("p")
            desc = desc_tag.get_text(strip=True)[:200] if desc_tag else ""
            if title and len(title) > 3:
                articles.append({"title": title, "url": link, "excerpt": desc})
        # Fallback
        if not articles:
            for a_tag in soup.select("h2 a, h3 a, h4 a")[:6]:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if title and link:
                    if not link.startswith("http"):
                        link = "https://sensortower.com" + link
                    articles.append({"title": title, "url": link, "excerpt": ""})
        return articles[:5]
    except Exception as e:
        print(f"  [!] Sensor Tower failed: {e}")
        return []


def fetch_9to5(site: str = "google") -> list[dict]:
    """Fetch 9to5Google or 9to5Mac — covers app updates, new features,
    and trending apps on Android/iOS platforms."""
    base = f"https://9to5{site}.com/"
    try:
        r = requests.get(base, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a_tag in soup.select("h2 a, h3 a, .post-title a")[:6]:
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href", "")
            if title and link and len(title) > 3:
                articles.append({
                    "title": title,
                    "url": link,
                    "excerpt": "",
                    "source": f"9to5{site.capitalize()}",
                })
        return articles
    except Exception as e:
        print(f"  [!] 9to5{site.capitalize()} failed: {e}")
        return []


def fetch_techinasia() -> list[dict]:
    """Fetch TechInAsia — covers Southeast Asian startups, apps,
    and tech trends across the region."""
    url = "https://www.techinasia.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for item in soup.select("article, .post-card, .content-card")[:8]:
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            title_tag = item.find(["h2", "h3"])
            title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
            link = a_tag["href"]
            if not link.startswith("http"):
                link = "https://www.techinasia.com" + link
            if title and len(title) > 3:
                articles.append({"title": title, "url": link, "excerpt": ""})
        # Fallback
        if not articles:
            for a_tag in soup.select("h2 a, h3 a")[:6]:
                title = a_tag.get_text(strip=True)
                link = a_tag.get("href", "")
                if title and link:
                    if not link.startswith("http"):
                        link = "https://www.techinasia.com" + link
                    articles.append({"title": title, "url": link, "excerpt": ""})
        return articles[:6]
    except Exception as e:
        print(f"  [!] TechInAsia failed: {e}")
        return []


def search_google_news(query: str, num: int = 5) -> list[dict]:
    """Search Google for recent news on a topic."""
    search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&tbm=nws&num={num}"
    try:
        r = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for item in soup.select("div.SoaBEf, div.dbsr, div.Gx5Zad"):
            a_tag = item.find("a", href=True)
            title_tag = item.find(["h3", "div.BNeawe", ".mCBkyc"])
            desc_tag = item.find(["div.GI74Re", "div.BNeawe.s3v9rd", ".GI74Re"])
            if a_tag and title_tag:
                title = title_tag.get_text(strip=True)
                link = a_tag["href"]
                if link.startswith("/url?q="):
                    link = link.split("/url?q=")[1].split("&")[0]
                desc = desc_tag.get_text(strip=True)[:200] if desc_tag else ""
                results.append({"title": title, "url": link, "excerpt": desc})
        return results[:num]
    except Exception as e:
        print(f"  [!] Google News search failed for '{query}': {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════
#  AI SYNTHESIS — Claude turns raw data into real insights
# ═══════════════════════════════════════════════════════════════════════

def ai_synthesize(raw_data: dict) -> dict:
    """
    Send all raw data to Claude API and get back a synthesized briefing
    with real insights, not just headlines.
    """
    api_key = CONFIG.get("anthropic_api_key", "")
    if not api_key:
        print("  [!] No Anthropic API key — skipping AI synthesis, using raw data")
        return fallback_format(raw_data)

    prompt = f"""You are a daily trends analyst. Today is {TODAY}.

I'm going to give you raw data scraped from multiple sources. Your job is to synthesize this into TWO briefing sections. Write with SUBSTANCE — tell me what's actually happening, what's interesting, what matters. Be specific: name bars, cities, ingredients, app names, countries.

SECTION 1: COCKTAIL & BAR TRENDS
Focus on:
- What top bars around the world are doing (new menus, techniques, concepts)
- Trending ingredients and spirits people are excited about
- Interesting new cocktail recipes or techniques worth trying
- Any notable bar openings or industry moves
- PAY SPECIAL ATTENTION to Japan (BAR TIMES data may be in Japanese — translate and summarize), Mexico (The Drink Magazine data may be in Spanish — translate and summarize), and broader Asia (DRiNK Magazine Asia covers Singapore, Bangkok, Seoul, Taipei, Hong Kong)
- When data from these regional sources is available, always include at least one bullet about Japan/Asia and one about Mexico/Latin America

SECTION 2: APP & TECH TRENDS
Focus on:
- Specific apps that are blowing up right now — name them, say what they do, where they're popular (e.g. "Ram is trending in Japan — it shows real-time road traffic for specific streets")
- Social media trending topics worth knowing
- Notable tech news that matters

RULES:
- Write 4-6 bullet points per section
- Each bullet: 2-3 sentences of REAL insight with specifics
- Include the most relevant source URL for each bullet
- If the scraped data is thin, use your knowledge to add context
- NO generic filler — every bullet should teach me something

Return ONLY valid JSON (no markdown, no backticks):
{{
  "cocktail_bullets": [
    {{"text": "Your detailed insight here...", "url": "https://source-url-if-available"}},
  ],
  "app_bullets": [
    {{"text": "Your detailed insight here...", "url": "https://source-url-if-available"}},
  ],
  "cocktail_headline": "One punchy line summarizing the cocktail mood",
  "app_headline": "One punchy line summarizing app/tech today"
}}

RAW DATA:

=== REDDIT r/cocktails ===
{json.dumps(raw_data.get('reddit_cocktails', []), indent=2)[:3000]}

=== PUNCH MAGAZINE ===
{json.dumps(raw_data.get('punch', []), indent=2)[:2000]}

=== IMBIBE MAGAZINE ===
{json.dumps(raw_data.get('imbibe', []), indent=2)[:1500]}

=== DIFFORD'S GUIDE ===
{json.dumps(raw_data.get('diffords', []), indent=2)[:1500]}

=== COCKTAIL NEWS (Google) ===
{json.dumps(raw_data.get('cocktail_news', []), indent=2)[:2000]}

=== BAR NEWS (Google) ===
{json.dumps(raw_data.get('bar_news', []), indent=2)[:2000]}

=== BAR TIMES JAPAN (Japanese bartender magazine — may contain Japanese text) ===
{json.dumps(raw_data.get('bar_times_japan', []), indent=2)[:2000]}

=== DRiNK MAGAZINE ASIA (Asia's leading bar publication — Singapore, Tokyo, Bangkok, Seoul, HK) ===
{json.dumps(raw_data.get('drink_magazine_asia', []), indent=2)[:2000]}

=== THE DRINK MAGAZINE MEXICO (Mexican cocktail scene — may contain Spanish text) ===
{json.dumps(raw_data.get('drink_magazine_mexico', []), indent=2)[:2000]}

=== PRODUCT HUNT ===
{json.dumps(raw_data.get('product_hunt', []), indent=2)[:2000]}

=== TECHCRUNCH ===
{json.dumps(raw_data.get('techcrunch', []), indent=2)[:2000]}

=== THE VERGE ===
{json.dumps(raw_data.get('theverge', []), indent=2)[:2000]}

=== REDDIT r/apps ===
{json.dumps(raw_data.get('reddit_apps', []), indent=2)[:2000]}

=== HACKER NEWS (developer community — technically interesting apps and tools) ===
{json.dumps(raw_data.get('hacker_news', []), indent=2)[:2000]}

=== SENSOR TOWER (app download analytics, chart movers, revenue trends) ===
{json.dumps(raw_data.get('sensor_tower', []), indent=2)[:1500]}

=== 9to5Google (Android app news and updates) ===
{json.dumps(raw_data.get('9to5google', []), indent=2)[:1500]}

=== 9to5Mac (iOS app news and updates) ===
{json.dumps(raw_data.get('9to5mac', []), indent=2)[:1500]}

=== TECHINASIA (Southeast Asian startups and apps) ===
{json.dumps(raw_data.get('techinasia', []), indent=2)[:1500]}

=== TRENDING APPS (Google) ===
{json.dumps(raw_data.get('app_news', []), indent=2)[:2000]}

=== SOCIAL MEDIA TRENDS (Google) ===
{json.dumps(raw_data.get('social_trends', []), indent=2)[:2000]}
"""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        response_data = r.json()
        text = response_data["content"][0]["text"].strip()
        if text.startswith("```"):
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        print(f"  [!] AI synthesis failed: {e}")
        traceback.print_exc()
        return fallback_format(raw_data)


def fallback_format(raw_data: dict) -> dict:
    """If AI synthesis fails, format raw data with whatever content we have."""
    cocktail_bullets = []
    for post in raw_data.get("reddit_cocktails", [])[:3]:
        text = post["title"]
        if post.get("selftext"):
            text += f" — {post['selftext'][:150]}"
        cocktail_bullets.append({"text": text, "url": post["url"]})
    for article in raw_data.get("punch", [])[:2]:
        text = article["title"]
        if article.get("excerpt"):
            text += f" — {article['excerpt'][:150]}"
        cocktail_bullets.append({"text": f"[Punch] {text}", "url": article["url"]})

    app_bullets = []
    for article in raw_data.get("techcrunch", [])[:3]:
        text = article["title"]
        if article.get("excerpt"):
            text += f" — {article['excerpt'][:150]}"
        app_bullets.append({"text": text, "url": article.get("url", "")})
    for p in raw_data.get("product_hunt", [])[:2]:
        text = p["name"]
        if p.get("tagline"):
            text += f" — {p['tagline']}"
        app_bullets.append({"text": text, "url": "https://producthunt.com"})

    return {
        "cocktail_bullets": cocktail_bullets,
        "app_bullets": app_bullets,
        "cocktail_headline": "Today's cocktail scene (AI synthesis unavailable — raw data below)",
        "app_headline": "Today's app & tech landscape (AI synthesis unavailable — raw data below)",
    }


# ═══════════════════════════════════════════════════════════════════════
#  PDF GENERATION — clickable links, real content
# ═══════════════════════════════════════════════════════════════════════

def build_pdf(briefing: dict, output_path: str):
    """Build a clean PDF with clickable links and real content."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.4 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BriefingTitle", parent=styles["Title"],
        fontSize=20, textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=2, alignment=1,
    )
    date_style = ParagraphStyle(
        "DateStyle", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#888888"),
        alignment=1, spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "SectionHead", parent=styles["Heading2"],
        fontSize=13, textColor=colors.HexColor("#e94560"),
        spaceBefore=10, spaceAfter=3,
    )
    headline_style = ParagraphStyle(
        "Headline", parent=styles["Italic"],
        fontSize=9, textColor=colors.HexColor("#555555"),
        spaceBefore=0, spaceAfter=8, leftIndent=4,
    )
    bullet_style = ParagraphStyle(
        "BulletItem", parent=styles["Normal"],
        fontSize=8.5, leading=12, textColor=colors.HexColor("#222222"),
        spaceBefore=2, spaceAfter=6, leftIndent=14, bulletIndent=4,
    )

    story = []

    # Header
    story.append(Paragraph("Daily Trends Briefing", title_style))
    story.append(Paragraph(TODAY, date_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#e94560")))

    # ════════ COCKTAIL SECTION ════════
    story.append(Paragraph("🍸 COCKTAIL &amp; BAR TRENDS", section_style))
    if briefing.get("cocktail_headline"):
        story.append(Paragraph(f"<i>{_esc(briefing['cocktail_headline'])}</i>", headline_style))

    for item in briefing.get("cocktail_bullets", []):
        text = _esc(item["text"])
        url = item.get("url", "")
        if url and url.startswith("http"):
            line = f'• {text}  <a href="{url}" color="#0066cc"><u>[Read more →]</u></a>'
        else:
            line = f"• {text}"
        story.append(Paragraph(line, bullet_style))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))

    # ════════ APP / TECH SECTION ════════
    story.append(Paragraph("📱 APP &amp; TECH TRENDS", section_style))
    if briefing.get("app_headline"):
        story.append(Paragraph(f"<i>{_esc(briefing['app_headline'])}</i>", headline_style))

    for item in briefing.get("app_bullets", []):
        text = _esc(item["text"])
        url = item.get("url", "")
        if url and url.startswith("http"):
            line = f'• {text}  <a href="{url}" color="#0066cc"><u>[Read more →]</u></a>'
        else:
            line = f"• {text}"
        story.append(Paragraph(line, bullet_style))

    # Footer
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=6.5, textColor=colors.HexColor("#999999"), alignment=1,
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Generated on {TODAY} · AI-synthesized from Reddit, Punch, Imbibe, "
        f"Difford's, BAR TIMES Japan, DRiNK Magazine Asia, The Drink Magazine Mexico, "
        f"Product Hunt, TechCrunch, The Verge, Hacker News, Sensor Tower, "
        f"9to5Google, 9to5Mac, TechInAsia, Google News",
        footer_style,
    ))

    doc.build(story)
    print(f"  [✓] PDF saved to {output_path}")


def _esc(text: str) -> str:
    """Escape XML special characters for ReportLab Paragraphs."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ═══════════════════════════════════════════════════════════════════════
#  EMAIL
# ═══════════════════════════════════════════════════════════════════════

def send_email(pdf_path: str):
    """Send the PDF as an email attachment."""
    cfg = CONFIG["email"]
    msg = MIMEMultipart()
    msg["From"] = cfg["sender"]
    msg["To"] = cfg["recipient"]
    msg["Subject"] = f"Daily Trends Briefing — {TODAY}"

    body = (
        f"Good morning!\n\n"
        f"Your daily trends briefing for {TODAY} is attached.\n"
        f"Open the PDF — all links are clickable.\n\n"
        f"— Your Briefing Bot"
    )
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={Path(pdf_path).name}")
    msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
        server.starttls(context=context)
        server.login(cfg["sender"], cfg["app_password"])
        server.send_message(msg)
    print(f"  [✓] Email sent to {cfg['recipient']}")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*55}")
    print(f"  Daily Trends Briefing v2 — {TODAY}")
    print(f"{'='*55}\n")

    raw_data = {}

    # ── Cocktail sources ──
    print("📡 Fetching cocktail data...")
    raw_data["reddit_cocktails"] = fetch_reddit_with_content("cocktails", limit=8)
    print(f"   Reddit r/cocktails: {len(raw_data['reddit_cocktails'])} posts")

    raw_data["punch"] = fetch_punch()
    print(f"   Punch: {len(raw_data['punch'])} articles")

    raw_data["imbibe"] = fetch_imbibe()
    print(f"   Imbibe: {len(raw_data['imbibe'])} articles")

    raw_data["diffords"] = fetch_diffords()
    print(f"   Difford's: {len(raw_data['diffords'])} articles")

    raw_data["bar_times_japan"] = fetch_bar_times_japan()
    print(f"   BAR TIMES Japan: {len(raw_data['bar_times_japan'])} articles")

    raw_data["drink_magazine_asia"] = fetch_drink_magazine_asia()
    print(f"   DRiNK Magazine Asia: {len(raw_data['drink_magazine_asia'])} articles")

    raw_data["drink_magazine_mexico"] = fetch_the_drink_magazine_mexico()
    print(f"   The Drink Magazine (Mexico): {len(raw_data['drink_magazine_mexico'])} articles")

    raw_data["cocktail_news"] = search_google_news("cocktail trends new ingredients 2026")
    raw_data["bar_news"] = search_google_news("best bars world new menu opening 2026")
    print(f"   Google News (cocktails): {len(raw_data['cocktail_news'])} results")
    print(f"   Google News (bars): {len(raw_data['bar_news'])} results")

    # ── App/Tech sources ──
    print("\n📡 Fetching app & tech data...")
    raw_data["product_hunt"] = fetch_product_hunt_detailed()
    print(f"   Product Hunt: {len(raw_data['product_hunt'])} products")

    raw_data["techcrunch"] = fetch_techcrunch()
    print(f"   TechCrunch: {len(raw_data['techcrunch'])} articles")

    raw_data["theverge"] = fetch_theverge()
    print(f"   The Verge: {len(raw_data['theverge'])} articles")

    raw_data["reddit_apps"] = fetch_reddit_with_content("apps", limit=5)
    print(f"   Reddit r/apps: {len(raw_data['reddit_apps'])} posts")

    raw_data["hacker_news"] = fetch_hacker_news()
    print(f"   Hacker News: {len(raw_data['hacker_news'])} stories")

    raw_data["sensor_tower"] = fetch_sensor_tower()
    print(f"   Sensor Tower: {len(raw_data['sensor_tower'])} articles")

    raw_data["9to5google"] = fetch_9to5("google")
    print(f"   9to5Google: {len(raw_data['9to5google'])} articles")

    raw_data["9to5mac"] = fetch_9to5("mac")
    print(f"   9to5Mac: {len(raw_data['9to5mac'])} articles")

    raw_data["techinasia"] = fetch_techinasia()
    print(f"   TechInAsia: {len(raw_data['techinasia'])} articles")

    raw_data["app_news"] = search_google_news("trending apps popular downloads 2026")
    raw_data["social_trends"] = search_google_news("social media trends viral today 2026")
    print(f"   Google News (apps): {len(raw_data['app_news'])} results")
    print(f"   Google News (social): {len(raw_data['social_trends'])} results")

    # ── AI Synthesis ──
    print("\n🧠 Synthesizing with Claude AI...")
    briefing = ai_synthesize(raw_data)
    print(f"   Cocktail insights: {len(briefing.get('cocktail_bullets', []))}")
    print(f"   App/Tech insights: {len(briefing.get('app_bullets', []))}")

    # ── Build PDF ──
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    pdf_path = str(output_dir / f"daily_briefing_{DATE_SHORT}.pdf")

    print("\n📄 Building PDF...")
    build_pdf(briefing, pdf_path)

    # ── Send email ──
    print("\n📧 Sending email...")
    try:
        send_email(pdf_path)
    except Exception as e:
        print(f"  [!] Email failed: {e}")
        traceback.print_exc()
        print(f"\n  PDF is still available at: {pdf_path}")

    print(f"\n{'='*55}")
    print("  Done! ✓")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()