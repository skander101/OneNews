import logging
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .models import RedditPost

logger = logging.getLogger(__name__)

HTML_SITES = [
    {
        "name": "Webmanagercenter",
        "url": "https://www.webmanagercenter.com/",
        "selectors": [".entry-title a", "h3 a", "h2 a"],
        "domain": "webmanagercenter.com",
    },
    {
        "name": "Directinfo",
        "url": "https://directinfo.webmanagercenter.com/",
        "selectors": [".entry-title a", "h3 a", "h2 a"],
        "domain": "directinfo.webmanagercenter.com",
    },
    {
        "name": "Tuniscope",
        "url": "https://www.tuniscope.com/",
        "selectors": [".entry-title a", "h3 a", "h2 a", ".article-title a"],
        "domain": "tuniscope.com",
    },
]


class HTMLSiteScraper:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; newsapp/1.0)",
        })

    def fetch_posts(self) -> list[RedditPost]:
        seen_urls = set()
        posts = []
        for site in HTML_SITES:
            logger.info("Scraping HTML: %s (%s)", site["name"], site["url"])
            try:
                resp = self.session.get(site["url"], timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                links = self._find_article_links(soup, site)
                logger.info("  %s → %d links found", site["name"], len(links))
                for a_tag in links[: self.config.posts_per_subreddit]:
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get("href", "")
                    if not title or not href:
                        continue
                    full_url = urljoin(site["url"], href)
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    domain = site.get("domain") or urlparse(full_url).netloc
                    published, published_iso = self._extract_date(a_tag)
                    image_url = self._extract_image(a_tag, site["url"])
                    post = RedditPost(
                        id=full_url,
                        title=title,
                        url=full_url,
                        subreddit=domain,
                        score=0,
                        num_comments=0,
                        source_domain=domain,
                        image_url=image_url,
                        published=published,
                        published_iso=published_iso,
                    )
                    posts.append(post)
            except Exception as exc:
                logger.warning("Failed HTML scrape %s: %s", site["name"], exc)
            time.sleep(1.0)
        return posts

    @staticmethod
    def _extract_date(a_tag) -> tuple[str, str]:
        for parent_tag in ("div", "article", "li", "section"):
            parent = a_tag.find_parent(parent_tag)
            if not parent:
                continue
            time_tag = parent.find("time")
            if time_tag:
                raw = time_tag.get("datetime") or time_tag.get_text(strip=True)
                if raw:
                    parsed = _parse_date_str(raw)
                    if parsed:
                        return parsed
            date_el = parent.find(["span", "div"], class_=re.compile(r"date|time", re.I))
            if date_el:
                raw = date_el.get("datetime") or date_el.get_text(strip=True)
                if raw:
                    parsed = _parse_date_str(raw)
                    if parsed:
                        return parsed
        return ("", "")

    @staticmethod
    def _extract_image(a_tag, base_url: str) -> str:
        for ancestor in a_tag.parents:
            if ancestor.name not in ("div", "article", "li", "section"):
                continue
            img = ancestor.find("img")
            if not img:
                continue
            for attr in ("data-src", "data-lazy-src", "src", "data-srcset", "srcset"):
                val = img.get(attr, "")
                if val:
                    if attr in ("data-srcset", "srcset"):
                        val = val.split(",")[0].strip().split(" ")[0]
                    return urljoin(base_url, val)
        return ""

    @staticmethod
    def _find_article_links(soup: BeautifulSoup, site: dict) -> list:
        for selector in site["selectors"]:
            found = soup.select(selector)
            if found:
                return found
        return []


_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
]


def _parse_date_str(raw: str) -> tuple[str, str] | None:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo:
                display = dt.strftime("%d %b %Y")
                iso = dt.strftime("%Y-%m-%d")
            else:
                display = dt.strftime("%d %b %Y")
                iso = dt.strftime("%Y-%m-%d")
            return (display, iso)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(raw)
        display = dt.strftime("%d %b %Y")
        iso = dt.strftime("%Y-%m-%d")
        return (display, iso)
    except (ValueError, TypeError):
        pass
    return None
