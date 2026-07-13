#!/usr/bin/env python3
"""
Standalone script for PythonAnywhere scheduled tasks.
Run daily at 3:00 UTC (4:00 AM Tunisian time).

Usage:
    python3 /home/YOUR_USER/newsapp/refresh_task.py
"""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname).1s %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from main import run_pipeline
from src.models import NewsItem
from src.rss_feed_scraper import RSSFeedScraper

cfg = Config()

CACHE_FILE = os.getenv("CACHE_FILE", "/tmp/cache_data.json")

CATEGORIES = ["Geopolitical", "World Health", "Tech", "Cybersecurity", "Funny/Weird", "Gaming", "Movies", "Arab World", "Tunisia"]


def serialize_clusters(clusters):
    by_cat = defaultdict(list)
    results = []
    for c in clusters:
        cat = "General"
        if c.articles and c.articles[0].analysis:
            ca = c.articles[0].analysis.category
            cat = ca if ca in CATEGORIES else "General"

        html = {
            "category": cat,
            "topic": c.topic,
            "score": round(c.final_score, 2),
            "trust": f"{c.avg_trustworthiness:.0%}",
            "coverage": c.total_coverage,
            "image_url": c.image_url,
            "top_post_url": c.top_post_url,
            "articles": [
                {
                    "title": a.article.title or a.post.title,
                    "summary": a.analysis.summary if a.analysis else "",
                    "topics": a.analysis.topics if a.analysis else [],
                    "trust": f"{a.analysis.trustworthiness_score:.0%}" if a.analysis else "",
                    "sponsor": a.analysis.sponsor.get("display", "") if a.analysis else "",
                    "sponsor_info": a.analysis.sponsor if a.analysis else {},
                    "sourcing_penalty": a.analysis.sourcing_penalty if a.analysis else 0,
                    "score": a.post.score,
                    "comments": a.post.num_comments,
                    "url": a.post.url,
                    "image": a.article.image_url if a.article else a.post.image_url,
                    "published": a.article.published or a.post.published,
                    "published_iso": a.article.published_iso or a.post.published_iso,
                }
                for a in c.articles[:5]
            ],
        }
        by_cat[cat].append(html)

        api = {
            "id": f"cluster-{id(c)}",
            "topic": c.topic,
            "category": cat,
            "final_score": round(c.final_score, 2),
            "avg_trustworthiness": round(c.avg_trustworthiness, 2),
            "total_coverage": c.total_coverage,
            "image_url": c.image_url,
            "top_post_url": c.top_post_url,
            "articles": [
                {
                    "title": a.article.title or a.post.title,
                    "url": a.post.url,
                    "domain": a.article.source_domain if a.article else "",
                    "summary": a.analysis.summary if a.analysis else "",
                    "topics": a.analysis.topics if a.analysis else [],
                    "trust": round(a.analysis.trustworthiness_score, 2) if a.analysis else 0,
                    "sponsor": a.analysis.sponsor.get("display", "") if a.analysis else "",
                    "sponsor_info": a.analysis.sponsor if a.analysis else {},
                    "sourcing_penalty": a.analysis.sourcing_penalty if a.analysis else 0,
                    "score": a.post.score,
                    "comments": a.post.num_comments,
                    "image": a.article.image_url if a.article else a.post.image_url,
                    "published": a.article.published or a.post.published,
                    "published_iso": a.article.published_iso or a.post.published_iso,
                }
                for a in c.articles[:5]
            ],
        }
        results.append(api)

    data = {
        "by_cat": dict(by_cat),
        "results": results,
        "status": f"ok — {len(clusters)} clusters",
        "last_refresh": datetime.now(timezone.utc).isoformat(),
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)
    logger.info("Cache written to %s (%d clusters)", CACHE_FILE, len(clusters))


def main():
    logger.info("Starting refresh task...")
    scraper = RSSFeedScraper(cfg)
    posts = scraper.fetch_posts()
    items = [NewsItem(post=p) for p in posts]
    clusters = run_pipeline(items, cfg)
    serialize_clusters(clusters)
    logger.info("Refresh task done — %d clusters", len(clusters))


if __name__ == "__main__":
    main()
