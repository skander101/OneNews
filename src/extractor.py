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
        doc = self._trafilatura.bare_extraction(downloaded, with_metadata=True)
        title = (doc.title if doc else None) or self._extract_title_meta(downloaded) or ""
        image = ""
        published, published_iso = ("", "")
        if doc:
            image = doc.image or ""
            published, published_iso = self._parse_trafilatura_date(doc.date)
        if not image:
            soup = BeautifulSoup(downloaded, "html.parser")
            image = self._extract_og_image_soup(soup)
        return Article(
            url=url, title=title, text=text, source_domain=domain,
            image_url=image, published=published, published_iso=published_iso,
        )

    def _extract_fallback(self, url: str, domain: str) -> Optional[Article]:
        resp = requests.get(url, headers={"User-Agent": "newsapp/1.0"}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        image = self._extract_og_image_soup(soup)
        published, published_iso = self._extract_fallback_date(soup)

        paragraphs = soup.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        if not text:
            return None
        return Article(
            url=url, title=title, text=text, source_domain=domain,
            image_url=image, published=published, published_iso=published_iso,
        )

    @staticmethod
    def _parse_trafilatura_date(raw_date: str | None) -> tuple[str, str]:
        if not raw_date:
            return ("", "")
        from datetime import datetime
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw_date.strip(), fmt)
                return (dt.strftime("%d %b %Y"), dt.strftime("%Y-%m-%d"))
            except ValueError:
                continue
        try:
            dt = datetime.fromisoformat(raw_date.strip())
            return (dt.strftime("%d %b %Y"), dt.strftime("%Y-%m-%d"))
        except (ValueError, TypeError):
            pass
        if len(raw_date) >= 10:
            try:
                dt = datetime.strptime(raw_date[:10], "%Y-%m-%d")
                return (dt.strftime("%d %b %Y"), raw_date[:10])
            except ValueError:
                pass
        return ("", "")

    @staticmethod
    def _extract_title_meta(html: str) -> Optional[str]:
        import html as html_mod
        import re
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return html_mod.unescape(m.group(1).strip()) if m else None

    @staticmethod
    def _extract_fallback_date(soup) -> tuple[str, str]:
        from datetime import datetime
        time_tag = soup.find("time")
        if time_tag:
            raw = time_tag.get("datetime") or time_tag.get_text(strip=True)
            if raw:
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(raw.strip(), fmt)
                        return (dt.strftime("%d %b %Y"), dt.strftime("%Y-%m-%d"))
                    except ValueError:
                        continue
                try:
                    dt = datetime.fromisoformat(raw.strip())
                    return (dt.strftime("%d %b %Y"), dt.strftime("%Y-%m-%d"))
                except (ValueError, TypeError):
                    pass
        for prop in ("article:published_time", "date"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                raw = tag["content"].strip()
                for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(raw, fmt)
                        return (dt.strftime("%d %b %Y"), dt.strftime("%Y-%m-%d"))
                    except ValueError:
                        continue
                try:
                    dt = datetime.fromisoformat(raw)
                    return (dt.strftime("%d %b %Y"), dt.strftime("%Y-%m-%d"))
                except (ValueError, TypeError):
                    pass
                if len(raw) >= 10:
                    try:
                        dt = datetime.strptime(raw[:10], "%Y-%m-%d")
                        return (dt.strftime("%d %b %Y"), raw[:10])
                    except ValueError:
                        pass
        return ("", "")

    @staticmethod
    def _extract_og_image_soup(soup) -> str:
        for prop in ("og:image", "twitter:image", "article:image"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                return tag["content"]
        link = soup.find("link", rel="image_src")
        if link and link.get("href"):
            return link["href"]
        return ""


import requests
from bs4 import BeautifulSoup
