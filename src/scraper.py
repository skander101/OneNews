import logging
from urllib.parse import urlparse

from .models import RedditPost

logger = logging.getLogger(__name__)


class RedditScraper:
    def __init__(self, config):
        self.config = config
        self._praw = None
        self._init_praw()

    def _init_praw(self):
        cid = self.config.reddit_client_id
        secret = self.config.reddit_client_secret
        if not cid or not secret:
            raise ValueError(
                "Reddit API credentials not found.\n"
                "  Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env, or\n"
                "  use python main.py --demo to run with sample data."
            )
        try:
            import praw
            self._praw = praw.Reddit(
                client_id=cid,
                client_secret=secret,
                user_agent=self.config.reddit_user_agent,
            )
            logger.info("Reddit API initialised via PRAW")
        except ImportError:
            raise ImportError("praw is required. Install with: pip install praw")

    def fetch_posts(self) -> list[RedditPost]:
        seen = set()
        posts = []
        for sub in self.config.news_subreddits:
            logger.info("Fetching r/%s ...", sub)
            try:
                batch = self._fetch_subreddit(sub)
                for p in batch:
                    if p.id not in seen:
                        seen.add(p.id)
                        posts.append(p)
            except Exception as exc:
                logger.error("Failed to fetch r/%s: %s", sub, exc)
        return posts

    def _fetch_subreddit(self, subreddit: str) -> list[RedditPost]:
        results = []
        sub = self._praw.subreddit(subreddit)
        for submission in sub.hot(limit=self.config.posts_per_subreddit):
            if submission.is_self:
                continue
            results.append(RedditPost(
                id=submission.id,
                title=submission.title,
                url=submission.url,
                subreddit=subreddit.lower(),
                score=submission.score,
                num_comments=submission.num_comments,
                source_domain=urlparse(submission.url).netloc,
            ))
        return results
