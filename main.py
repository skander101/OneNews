#!/usr/bin/env python3
"""
main.py — Entry point for the GenAI News App.

Pipeline:
  1. Scrape Reddit for news posts
  2. Extract article content from linked URLs
  3. Analyse each article (summarise, classify, score trustworthiness)
  4. Cluster related stories and rank them
  5. Display the top clusters to the user

Usage:
  python main.py                          # RSS news feeds (default, free)
  python main.py --source hn              # Hacker News (tech-heavy)
  python main.py --source reddit          # Reddit via PRAW (needs API key)
  python main.py --demo                   # sample data (no internet)
  python main.py --models                 # + GenAI models
"""

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
    parser = argparse.ArgumentParser(description="GenAI-powered news aggregator")
    parser.add_argument(
        "--demo", action="store_true",
        help="Run with sample data (no internet needed)",
    )
    parser.add_argument(
        "--source", choices=["feeds", "hn", "reddit"], default=None,
        help="Data source: feeds (RSS news feeds, default), hn (Hacker News), reddit (PRAW, needs API key)",
    )
    parser.add_argument(
        "--models", action="store_true",
        help="Enable local HuggingFace models (slower but smarter)",
    )
    parser.add_argument(
        "--subreddits", nargs="+", default=None,
        help="Override subreddit list (space-separated)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Posts per subreddit (default: config value)",
    )
    return parser.parse_args()


def run_pipeline(items: list[NewsItem], cfg: Config, skip_extraction: bool = False):
    """Shared pipeline: extract → analyse → cluster → present."""
    # ---- Stage 2: Extract articles -----------------------------------------
    if not skip_extraction:
        print("═══  Stage 2: Extracting article content  ═══")
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
                print(f"✗  (using title only)")
            item.article = article
    else:
        print("═══  Stage 2: Skipped (articles already loaded)  ═══")

    # ---- Stage 3: NLP Analysis ---------------------------------------------
    print("\n═══  Stage 3: Analysing articles (GenAI / NLP)  ═══")
    if cfg.use_local_models:
        print("  (local models enabled — first load may download files)")
    else:
        print("  (rule-based analysis — use --models for NN models)")

    analyzer = NewsAnalyzer(cfg)
    for i, item in enumerate(items, 1):
        print(f"  [{i:>2}/{len(items)}] analysing ...  ", end="", flush=True)
        item.analysis = analyzer.analyze(item.article)
        cat = item.analysis.category
        topics = ", ".join(item.analysis.topics) if item.analysis.topics else "(none detected)"
        print(f"{cat:<14} topic: {topics:<30} trust: {item.analysis.trustworthiness_score:.0%}")

    # ---- Stage 4: Cluster & Rank -------------------------------------------
    print("\n═══  Stage 4: Clustering & ranking  ═══")
    aggregator = NewsAggregator(cfg)
    clusters = aggregator.cluster_news(items)
    print(f"  → {len(clusters)} story clusters found\n")

    # ---- Stage 5: Present --------------------------------------------------
    print("═══  Stage 5: Results  ═══")
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

    # ---- Stage 1: Collect data ------------------------------------------------
    source = args.source or "feeds"

    if args.demo:
        from src.mockdata import generate_demo_items
        print("═══  Stage 1: Loading demo data  ═══")
        items = generate_demo_items()
        print(f"  → {len(items)} sample articles loaded\n")
        clusters = run_pipeline(items, cfg, skip_extraction=True)
        n_posts = len(items)

    elif source == "hn":
        from src.hn_scraper import HackerNewsScraper
        print("═══  Stage 1: Scraping Hacker News  ═══")
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
        print("═══  Stage 1: Scraping Reddit (PRAW)  ═══")
        scraper = RedditScraper(cfg)
        posts = scraper.fetch_posts()
        n_posts = len(posts)
        print(f"  → {n_posts} posts collected\n")
        if not posts:
            sys.exit(1)
        items = [NewsItem(post=p) for p in posts]
        clusters = run_pipeline(items, cfg)

    else:  # feeds (default)
        from src.rss_feed_scraper import RSSFeedScraper
        print("═══  Stage 1: Fetching RSS news feeds  ═══")
        scraper = RSSFeedScraper(cfg)
        posts = scraper.fetch_posts()
        n_posts = len(posts)
        print(f"  → {n_posts} posts collected\n")
        if not posts:
            sys.exit(1)
        items = [NewsItem(post=p) for p in posts]
        clusters = run_pipeline(items, cfg)

    elapsed = time.perf_counter() - total_start
    print(f"\n  Done in {elapsed:.1f}s — {n_posts} posts, {len(clusters)} clusters")
    print()


if __name__ == "__main__":
    main()
