import json
import logging
import os
import sys
import threading
from collections import defaultdict
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from config import Config
from main import run_pipeline
from src.models import NewsItem
from src.rss_feed_scraper import RSSFeedScraper

logging.basicConfig(level=logging.INFO, format="%(levelname).1s %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

cfg = Config()

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
CORS(app, origins=cfg.cors_origins.split(",") if cfg.cors_origins != "*" else "*")

cache_lock = threading.Lock()

CACHE_FILE = os.getenv("CACHE_FILE", "/tmp/cache_data.json")

CATEGORIES = ["Geopolitical", "World Health", "Tech", "Cybersecurity", "Funny/Weird", "Gaming", "Movies", "Arab World", "Tunisia"]

cached_by_cat: dict[str, list[dict]] = defaultdict(list)
cached_results: list[dict] = []
cached_status = "starting"
cached_last_refresh = None


def _cluster_to_html_dict(c):
    category = "General"
    if c.articles and c.articles[0].analysis:
        cat = c.articles[0].analysis.category
        category = cat if cat in CATEGORIES else "General"
    return {
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
                "sponsor": a.analysis.sponsor.get("display", "") if a.analysis else "",
                "sponsor_info": a.analysis.sponsor if a.analysis else {},
                "source_bias": a.analysis.source_bias if a.analysis else "",
                "source_factuality": a.analysis.source_factuality if a.analysis else "",
                "article_leaning": a.analysis.article_leaning if a.analysis else "",
                "sourcing_penalty": a.analysis.sourcing_penalty if a.analysis else 0,
                "score": a.post.score,
                "comments": a.post.num_comments,
                "url": a.post.url,
                "image": a.article.image_url if a.article else a.post.image_url,
                "published": a.post.published,
                "published_iso": a.post.published_iso,
            }
            for a in c.articles[:5]
        ],
    }


def _cluster_to_api_dict(c):
    cat = "General"
    if c.articles and c.articles[0].analysis:
        ca = c.articles[0].analysis.category
        cat = ca if ca in CATEGORIES else "General"
    return {
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
                "title": a.post.title,
                "url": a.post.url,
                "domain": a.article.source_domain if a.article else "",
                "summary": a.analysis.summary if a.analysis else "",
                "topics": a.analysis.topics if a.analysis else [],
                "trust": round(a.analysis.trustworthiness_score, 2) if a.analysis else 0,
                "sponsor": a.analysis.sponsor.get("display", "") if a.analysis else "",
                "sponsor_info": a.analysis.sponsor if a.analysis else {},
                "source_bias": a.analysis.source_bias if a.analysis else "",
                "source_factuality": a.analysis.source_factuality if a.analysis else "",
                "article_leaning": a.analysis.article_leaning if a.analysis else "",
                "sourcing_penalty": a.analysis.sourcing_penalty if a.analysis else 0,
                "score": a.post.score,
                "comments": a.post.num_comments,
                "image": a.article.image_url if a.article else a.post.image_url,
                "published": a.post.published,
                "published_iso": a.post.published_iso,
            }
            for a in c.articles[:5]
        ],
    }


def refresh_data():
    global cached_by_cat, cached_results, cached_status, cached_last_refresh
    with cache_lock:
        cached_status = "running"
    try:
        scraper = RSSFeedScraper(cfg)
        posts = scraper.fetch_posts()
        items = [NewsItem(post=p) for p in posts]
        new_clusters = run_pipeline(items, cfg)
        html_dicts = [_cluster_to_html_dict(c) for c in new_clusters]
        api_dicts = [_cluster_to_api_dict(c) for c in new_clusters]
        by_cat: dict[str, list[dict]] = defaultdict(list)
        for d in html_dicts:
            by_cat[d["category"]].append(d)
        with cache_lock:
            cached_by_cat = by_cat
            cached_results = api_dicts
            cached_last_refresh = datetime.now(timezone.utc)
            cached_status = f"ok — {len(new_clusters)} clusters from {len(items)} articles"
        _save_cache(by_cat, api_dicts, cached_status, cached_last_refresh)
        logger.info("Refresh complete: %s", cached_status)
    except Exception as exc:
        with cache_lock:
            cached_status = f"error: {exc}"
        logger.error("Pipeline failed: %s", exc)


def _save_cache(by_cat, results, status, last_refresh):
    try:
        data = {
            "by_cat": {k: v for k, v in by_cat.items()},
            "results": results,
            "status": status,
            "last_refresh": last_refresh.isoformat() if last_refresh else None,
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as exc:
        logger.warning("Failed to write cache file: %s", exc)


def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ---- Web UI ----

@app.route("/")
def index():
    with cache_lock:
        bc = cached_by_cat
        status = cached_status
    grouped_by_date = {}
    for cat in CATEGORIES:
        items = bc.get(cat, [])
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
    return render_template("index.html", grouped_by_date=grouped_by_date, categories=CATEGORIES, status=status, total=total, tab_counts=tab_counts)


# ---- REST API ----

@app.route("/api/v1/status")
def api_status():
    with cache_lock:
        status = cached_status
        lr = cached_last_refresh
        n_clusters = len(cached_results)
        n_articles = sum(c["total_coverage"] for c in cached_results)
    return jsonify({
        "status": "ok",
        "clusters": n_clusters,
        "total_articles": n_articles,
        "last_refresh": lr.isoformat() if lr else None,
        "pipeline_status": status,
    })


@app.route("/api/v1/posts")
def api_posts():
    category = request.args.get("category")
    topic = request.args.get("topic")
    limit = request.args.get("limit", type=int)
    min_score = request.args.get("min_score", type=float)

    with cache_lock:
        all_results = list(cached_results)

    filtered = all_results
    if category:
        filtered = [r for r in filtered if r["category"].lower() == category.lower()]
    if topic:
        filtered = [r for r in filtered if topic.lower() in [t.lower() for t in r.get("articles", [])[:1]]]
    if min_score is not None:
        filtered = [r for r in filtered if r["final_score"] >= min_score]
    if limit:
        filtered = filtered[:limit]

    return jsonify({"clusters": filtered, "meta": {"total": len(filtered)}})


@app.route("/api/v1/categories")
def api_categories():
    return jsonify({"categories": CATEGORIES})


def _build_sponsors():
    with cache_lock:
        results = list(cached_results)
    groups: dict[str, dict] = {}
    for cluster in results:
        for article in cluster.get("articles", []):
            info = article.get("sponsor_info", {})
            display = info.get("display", "") or article.get("sponsor", "")
            if not display:
                continue
            if display not in groups:
                groups[display] = {
                    "display": display,
                    "parent": info.get("parent", ""),
                    "category": info.get("category", ""),
                    "bias": info.get("bias", ""),
                    "factuality": info.get("factuality", ""),
                    "wikipedia": info.get("wikipedia", ""),
                    "owners": info.get("owners", []),
                    "owner_wikis": info.get("owner_wikis", {}),
                    "sources": set(),
                }
            groups[display]["sources"].add(article.get("domain", ""))
    return sorted(
        [
            {
                "display": g["display"],
                "parent": g["parent"],
                "category": g["category"],
                "bias": g["bias"],
                "factuality": g["factuality"],
                "wikipedia": g["wikipedia"],
                "owners": g["owners"],
                "owner_wikis": g["owner_wikis"],
                "sources": sorted(g["sources"]),
                "source_count": len(g["sources"]),
            }
            for g in groups.values()
        ],
        key=lambda x: x["display"].lower(),
    )


@app.route("/api/v1/sponsors")
def api_sponsors():
    return jsonify({"sponsors": _build_sponsors()})




@app.route("/api/v1/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=refresh_data, daemon=True).start()
    return jsonify({"status": "accepted", "message": "refresh started"}), 202


@app.route("/health")
def health():
    with cache_lock:
        ok = "error" not in cached_status
    if ok:
        return jsonify({"status": "healthy"}), 200
    return jsonify({"status": "unhealthy", "message": cached_status}), 503


# ---- Startup (runs in both WSGI and dev modes) ----

_cache_data = _load_cache()
if _cache_data:
    cached_by_cat = defaultdict(list, _cache_data.get("by_cat", {}))
    cached_results = _cache_data.get("results", [])
    cached_status = _cache_data.get("status", "idle")
    lr = _cache_data.get("last_refresh")
    if lr:
        try:
            cached_last_refresh = datetime.fromisoformat(lr)
        except Exception:
            pass
    logger.info("Loaded cached data: %s", cached_status)

if not cached_results:
    threading.Thread(target=refresh_data, daemon=True).start()

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        refresh_data,
        trigger="cron",
        hour=cfg.refresh_hour,
        minute=cfg.refresh_minute,
        timezone=cfg.refresh_timezone,
        id="daily_refresh",
        name="Daily news refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — daily refresh at %02d:%02d %s", cfg.refresh_hour, cfg.refresh_minute, cfg.refresh_timezone)
except ImportError:
    logger.warning("APScheduler not available — scheduled refresh disabled")


# ---- Dev server (not used in WSGI/gunicorn) ----

if __name__ == "__main__":
    app.run(host=cfg.host, port=cfg.port, debug=(cfg.flask_env != "production"))
