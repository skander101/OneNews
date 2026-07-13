import logging
import time
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
                    post = RedditPost(
                        id=full_url,
                        title=title,
                        url=full_url,
                        subreddit=domain,
                        score=0,
                        num_comments=0,
                        source_domain=domain,
                        image_url="",
                        published="",
                        published_iso="",
                    )
                    posts.append(post)
            except Exception as exc:
                logger.warning("Failed HTML scrape %s: %s", site["name"], exc)
            time.sleep(1.0)
        return posts

    @staticmethod
    def _find_article_links(soup: BeautifulSoup, site: dict) -> list:
        for selector in site["selectors"]:
            found = soup.select(selector)
            if found:
                return found
        return []
