import logging
import sys
import threading
from collections import defaultdict

from flask import Flask, render_template

from config import Config
from main import run_pipeline
from src.models import NewsItem
from src.rss_feed_scraper import RSSFeedScraper

logging.basicConfig(level=logging.INFO, format="%(levelname).1s %(message)s", stream=sys.stderr)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

clusters = []
pipeline_status = "idle"

CATEGORIES = ["Geopolitical", "World Health", "Tech", "Cybersecurity", "Funny/Weird", "Gaming", "Movies", "Arab World", "Tunisia"]


def refresh_data():
    global clusters, pipeline_status
    pipeline_status = "running"
    cfg = Config()
    try:
        scraper = RSSFeedScraper(cfg)
        posts = scraper.fetch_posts()
        items = [NewsItem(post=p) for p in posts]
        clusters = run_pipeline(items, cfg)
        pipeline_status = f"ok — {len(clusters)} clusters from {len(items)} articles"
    except Exception as exc:
        pipeline_status = f"error: {exc}"
        logging.error("Pipeline failed: %s", exc)


@app.route("/")
def index():
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for c in clusters:
        category = "General"
        if c.articles and c.articles[0].analysis:
            cat = c.articles[0].analysis.category
            category = cat if cat in CATEGORIES else "General"

        by_cat[category].append({
            "category": category,
            "topic": c.topic,
            "score": round(c.final_score, 2),
            "trust": f"{c.avg_trustworthiness:.0%}",
            "coverage": c.total_coverage,
            "image_url": c.image_url,
            "top_post_url": c.top_post_url,
            "articles": [
                {
                    "title": a.post.title,
                    "domain": a.article.source_domain if a.article else "",
                    "summary": a.analysis.summary if a.analysis else "",
                    "topics": a.analysis.topics if a.analysis else [],
                    "trust": f"{a.analysis.trustworthiness_score:.0%}" if a.analysis else "",
                    "score": a.post.score,
                    "comments": a.post.num_comments,
                    "url": a.post.url,
                    "image": a.article.image_url if a.article else a.post.image_url,
                    "published": a.post.published,
                    "published_iso": a.post.published_iso,
                }
                for a in c.articles[:5]
            ],
        })

    grouped_by_date = {}
    for cat in CATEGORIES:
        items = by_cat.get(cat, [])
        items.sort(key=lambda x: (x["articles"][0]["published_iso"] or "", x["score"]), reverse=True)
        date_groups = []
        seen_date = None
        for item in items:
            d = item["articles"][0]["published"] or "Unknown"
            if d != seen_date:
                date_groups.append({"date": d, "items": []})
                seen_date = d
            date_groups[-1]["items"].append(item)
        grouped_by_date[cat] = date_groups

    total = sum(len(g["items"]) for groups in grouped_by_date.values() for g in groups)
    tab_counts = {cat: sum(len(g["items"]) for g in grouped_by_date[cat]) for cat in CATEGORIES}
    return render_template("index.html", grouped_by_date=grouped_by_date, categories=CATEGORIES, status=pipeline_status, total=total, tab_counts=tab_counts)


@app.route("/refresh")
def refresh():
    threading.Thread(target=refresh_data, daemon=True).start()
    return "ok", 202


if __name__ == "__main__":
    refresh_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
