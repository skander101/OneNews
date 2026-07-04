import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from .models import RedditPost

logger = logging.getLogger(__name__)

API_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsScraper:
    def __init__(self, config):
        self.config = config

    def fetch_posts(self) -> list[RedditPost]:
        resp = requests.get(f"{API_BASE}/topstories.json", timeout=15)
        resp.raise_for_status()
        all_ids = resp.json()

        limit = min(self.config.posts_per_subreddit * 3, 50)
        posts = []
        for story_id in all_ids[:limit]:
            try:
                detail = requests.get(f"{API_BASE}/item/{story_id}.json", timeout=10)
                detail.raise_for_status()
                data = detail.json()
                if not data or data.get("type") != "story":
                    continue
                url = data.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                posts.append(RedditPost(
                    id=f"hn_{story_id}",
                    title=data.get("title", ""),
                    url=url,
                    subreddit="hackernews",
                    score=data.get("score", 0),
                    num_comments=data.get("descendants", 0),
                    source_domain=urlparse(url).netloc,
                ))
            except Exception as exc:
                logger.debug("Failed to fetch HN item %s: %s", story_id, exc)

        posts.sort(key=lambda p: p.score, reverse=True)
        posts = posts[: self.config.posts_per_subreddit]
        logger.info("Fetched %d posts from Hacker News", len(posts))
        return posts
