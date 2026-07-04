#!/usr/bin/env python3

import argparse
import logging
import sys
import time

from config import Config
from src.models import Article, NewsItem
from src.extractor import ArticleExtractor
from src.analyzer import NewsAnalyzer
from src.aggregator import NewsAggregator
from src.presenter import NewsPresenter

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname).1s %(message)s",
    stream=sys.stderr,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OneNews — RSS news aggregator")
    parser.add_argument("--demo", action="store_true", help="Use sample data (no internet)")
    parser.add_argument("--source", choices=["feeds", "hn", "reddit"], default=None,
                        help="Data source (default: RSS feeds)")
    parser.add_argument("--models", action="store_true", help="Enable local ML models (slower)")
    parser.add_argument("--subreddits", nargs="+", default=None, help="Override subreddits")
    parser.add_argument("--limit", type=int, default=None, help="Posts per subreddit")
    return parser.parse_args()


def run_pipeline(items: list[NewsItem], cfg: Config, skip_extraction: bool = False):
    if not skip_extraction:
        print("═══  Extracting article content  ═══")
        extractor = ArticleExtractor()
        for i, item in enumerate(items, 1):
            print(f"  [{i:>2}/{len(items)}] {item.post.title[:60]:<60}  ", end="", flush=True)
            article = extractor.extract(item.post.url)
            if article:
                print(f"✓  ({article.source_domain})")
            else:
                article = Article(
                    url=item.post.url,
                    title=item.post.title,
                    text=item.post.title,
                    source_domain=item.post.source_domain or "reddit.com",
                    extraction_success=False,
                    image_url=item.post.image_url,
                )
                print(f"✗  (title only)")
            item.article = article
    else:
        print("═══  Extraction skipped (articles already loaded)  ═══")

    print("\n═══  Analysing articles  ═══")
    analyzer = NewsAnalyzer(cfg)
    for i, item in enumerate(items, 1):
        print(f"  [{i:>2}/{len(items)}] analysing ...  ", end="", flush=True)
        item.analysis = analyzer.analyze(item.article)
        cat = item.analysis.category
        topics = ", ".join(item.analysis.topics) if item.analysis.topics else "(none)"
        print(f"{cat:<14} topic: {topics:<30} trust: {item.analysis.trustworthiness_score:.0%}")

    print("\n═══  Clustering & ranking  ═══")
    aggregator = NewsAggregator(cfg)
    clusters = aggregator.cluster_news(items)
    print(f"  → {len(clusters)} story clusters found\n")

    print("═══  Results  ═══")
    presenter = NewsPresenter()
    presenter.display(clusters)

    return clusters


def main():
    args = parse_args()
    cfg = Config()

    if args.models:
        cfg.use_local_models = True
        logging.getLogger().setLevel(logging.DEBUG)
    if args.subreddits:
        cfg.news_subreddits = args.subreddits
    if args.limit:
        cfg.posts_per_subreddit = args.limit

    total_start = time.perf_counter()

    source = args.source or "feeds"

    if args.demo:
        from src.mockdata import generate_demo_items
        print("═══  Loading demo data  ═══")
        items = generate_demo_items()
        print(f"  → {len(items)} sample articles loaded\n")
        clusters = run_pipeline(items, cfg, skip_extraction=True)
        n_posts = len(items)

    elif source == "hn":
        from src.hn_scraper import HackerNewsScraper
        print("═══  Scraping Hacker News  ═══")
        scraper = HackerNewsScraper(cfg)
        posts = scraper.fetch_posts()
        n_posts = len(posts)
        print(f"  → {n_posts} posts collected\n")
        if not posts:
            sys.exit(1)
        items = [NewsItem(post=p) for p in posts]
        clusters = run_pipeline(items, cfg)

    elif source == "reddit":
        from src.scraper import RedditScraper
        print("═══  Scraping Reddit  ═══")
        scraper = RedditScraper(cfg)
        posts = scraper.fetch_posts()
        n_posts = len(posts)
        print(f"  → {n_posts} posts collected\n")
        if not posts:
            sys.exit(1)
        items = [NewsItem(post=p) for p in posts]
        clusters = run_pipeline(items, cfg)

    else:
        from src.rss_feed_scraper import RSSFeedScraper
        print("═══  Fetching RSS news feeds  ═══")
        scraper = RSSFeedScraper(cfg)
        posts = scraper.fetch_posts()
        n_posts = len(posts)
        print(f"  → {n_posts} posts collected\n")
        if not posts:
            sys.exit(1)
        items = [NewsItem(post=p) for p in posts]
        clusters = run_pipeline(items, cfg)

    elapsed = time.perf_counter() - total_start
    print(f"\n  Done in {elapsed:.1f}s — {n_posts} posts, {len(clusters)} clusters\n")


if __name__ == "__main__":
    main()
