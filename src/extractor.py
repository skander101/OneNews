import logging
from typing import Optional
from urllib.parse import urlparse

from .models import Article

logger = logging.getLogger(__name__)


class ArticleExtractor:
    def __init__(self):
        self._trafilatura = None
        self._init_backend()

    def _init_backend(self):
        try:
            import trafilatura
            self._trafilatura = trafilatura
        except ImportError:
            logger.info("trafilatura not installed — using fallback extractor")

    def extract(self, url: str) -> Optional[Article]:
        domain = urlparse(url).netloc
        try:
            if self._trafilatura:
                return self._extract_trafilatura(url, domain)
            return self._extract_fallback(url, domain)
        except Exception as exc:
            logger.debug("Extraction failed for %s: %s", url, exc)
            return None

    def _extract_trafilatura(self, url: str, domain: str) -> Optional[Article]:
        downloaded = self._trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = self._trafilatura.extract(downloaded)
        if not text:
            return None
        title = self._extract_title_meta(downloaded) or ""
        image = self._extract_og_image(downloaded)
        return Article(url=url, title=title, text=text, source_domain=domain, image_url=image)

    def _extract_fallback(self, url: str, domain: str) -> Optional[Article]:
        resp = requests.get(url, headers={"User-Agent": "newsapp/1.0"}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        image = self._extract_og_image_soup(soup)

        paragraphs = soup.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        if not text:
            return None
        return Article(url=url, title=title, text=text, source_domain=domain, image_url=image)

    @staticmethod
    def _extract_title_meta(html: str) -> Optional[str]:
        import html as html_mod
        import re
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return html_mod.unescape(m.group(1).strip()) if m else None

    @staticmethod
    def _extract_og_image(html: str) -> str:
        import re
        m = re.search(
            r'<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE,
        )
        if m:
            return m.group(1)
        m = re.search(
            r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
            html, re.IGNORECASE,
        )
        return m.group(1) if m else ""

    @staticmethod
    def _extract_og_image_soup(soup) -> str:
        for prop in ("og:image", "twitter:image"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                return tag["content"]
        return ""


import requests
from bs4 import BeautifulSoup
