import logging
import time
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlencode, parse_qs

import feedparser
import requests

from .models import RedditPost

logger = logging.getLogger(__name__)

TRACKING_PARAMS = {"at_medium", "at_campaign", "ref", "utm_source", "utm_medium", "utm_campaign"}

DEFAULT_FEEDS = [
    # Geopolitical
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.theguardian.com/world/rss",
    # World Health
    "https://www.statnews.com/feed/",
    "https://www.sciencedaily.com/rss/all.xml",
    "https://www.sciencenews.org/feed",
    "https://www.medscape.com/cx/rssfeeds/2700.xml",
    "https://www.nih.gov/news-events/news-releases/rss.xml",
    "https://news.harvard.edu/gazette/feed/",
    "https://news.harvard.edu/gazette/section/health-medicine/feed/",
    # Tech
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://www.theverge.com/rss/index.xml",
    "https://arstechnica.com/feed/",
    # Cybersecurity
    "https://feeds.feedburner.com/TheHackerNews",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://threatpost.com/feed/",
    "https://therecord.media/feed/",
    # Funny / Weird
    "https://www.theonion.com/rss",
    "https://www.reddit.com/r/nottheonion/.rss",
    "https://www.thedailymash.co.uk/feed",
    "https://babylonbee.com/feed",
    # Gaming
    "https://feeds.ign.com/ign/all",
    "https://www.eurogamer.net/feed",
    "https://www.pcgamer.com/rss/",
    "https://www.kotaku.com/rss",
    "https://www.gamespot.com/feeds/news/",
    "https://www.polygon.com/rss/index.xml",
    # Movies
    "https://variety.com/feed/",
    "https://www.hollywoodreporter.com/feed/",
    "https://deadline.com/feed/",
    "https://screenrant.com/feed/",
    # Arab World
    "https://www.arabnews.com/rss.xml",
    "https://www.middleeasteye.net/rss",
    "https://www.newarab.com/rss.xml",
    "https://www.france24.com/en/middle-east/rss",
    # Tunisia
    "https://www.tunisiaonlinenews.com/feed/",
    "https://northafricapost.com/feed/",
    "https://www.africanews.com/feed/",
]


class RSSFeedScraper:
    def __init__(self, config):
        self.config = config
        self.feeds = getattr(config, "rss_feeds", DEFAULT_FEEDS)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; newsapp/1.0)",
        })

    def fetch_posts(self) -> list[RedditPost]:
        seen_titles = set()
        posts = []
        for url in self.feeds:
            logger.info("Fetching RSS: %s", url)
            try:
                if "reddit.com" in url:
                    time.sleep(2.5)
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[: self.config.posts_per_subreddit]:
                    post = self._entry_to_post(entry, url)
                    if post and post.title not in seen_titles:
                        seen_titles.add(post.title)
                        posts.append(post)
            except Exception as exc:
                logger.warning("Failed RSS %s: %s", url, exc)
            time.sleep(1.0)
        return posts

    @staticmethod
    def _clean_url(url: str) -> str:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qs(parsed.query)
        clean = {k: v[0] for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
        if not clean:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(clean)}"

    @staticmethod
    def _extract_image(entry) -> str:
        for key in ("media_content", "media_thumbnail"):
            items = entry.get(key) or []
            for item in items:
                url = item.get("url", "")
                if url:
                    return url
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and "image" in link.get("type", ""):
                return link.get("href", "")
        return ""

    def _entry_to_post(self, entry, feed_url: str) -> RedditPost | None:
        title = entry.get("title", "")
        if not title:
            return None
        link = self._clean_url(entry.get("link", ""))
        domain = urlparse(link).netloc or urlparse(feed_url).netloc
        image_url = self._extract_image(entry)
        published, published_iso = self._format_date(entry)
        return RedditPost(
            id=entry.get("id", entry.get("guid", link)),
            title=title,
            url=link,
            subreddit=domain,
            score=0, num_comments=0,
            source_domain=domain,
            image_url=image_url,
            published=published,
            published_iso=published_iso,
        )

    @staticmethod
    def _format_date(entry) -> tuple[str, str]:
        raw = entry.get("published") or entry.get("updated") or ""
        if not raw:
            return ("", "")
        try:
            dt = parsedate_to_datetime(raw)
            display = dt.strftime("%d %b %Y")
            iso = dt.strftime("%Y-%m-%d")
            return (display, iso)
        except Exception:
            if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
                iso = raw[:10]
                from datetime import datetime
                try:
                    dt = datetime.strptime(iso, "%Y-%m-%d")
                    display = dt.strftime("%d %b %Y")
                except Exception:
                    display = iso
                return (display, iso)
            return (raw[:16], "")
