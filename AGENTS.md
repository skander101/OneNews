# NewsApp — Agent Summary

## Project Structure

```
newsapp/
├── AGENTS.md               ← this file
├── config.py               ← dataclass with all settings (feeds, weights, interests)
├── main.py                 ← entrypoint (CLI or module)
├── requirements.txt
├── webapp.py               ← Flask web server (serves frontend)
├── templates/
│   └── index.html          ← tabbed UI, dynamically generated from categories
├── static/                 ← (empty, reserved for assets)
└── src/
    ├── __init__.py
    ├── rss_feed_scraper.py ← RSS feed fetcher + article extractor (trafilatura)
    ├── models.py           ← NewsItem, Article, Post, Cluster, Analysis dataclasses
    ├── analyzer.py         ← NLP: summarisation, topic classification, trust, opinion, leaning
    ├── clustering.py       ← similarity-based article clustering + scoring
    └── presenter.py        ← output formatting (terminal + web JSON)
```

## Current State

### RSS Feeds (42 sources across 9 categories)
- **Geopolitical**: BBC World, NYT World, NYT Politics, NPR, Al Jazeera, The Guardian
- **World Health**: BBC Health, NYT Science, Stat News, Science Daily
- **Tech**: BBC Tech, NYT Tech, TechCrunch, Wired, The Verge, Ars Technica
- **Cybersecurity**: The Hacker News, Krebs on Security, BleepingComputer, Threatpost, The Record
- **Funny/Weird**: The Onion, r/nottheonion, Daily Mash, Babylon Bee
- **Gaming**: IGN, Eurogamer, PC Gamer, Kotaku, Gamespot, Polygon
- **Movies**: Variety, Hollywood Reporter, Deadline, Screen Rant
- **Arab World**: Arab News, Middle East Eye, The New Arab, France24 ME
- **Tunisia**: Tunisia Online News, North Africa Post, Africa News
- `posts_per_subreddit = 3` → ~126 posts total per run

### Topic Detection (keyword-based, word-boundary regex)
- 21 topics tracked: gaming, movies, tunisia, arab_world, AI, climate, health, economy, space, cybersecurity, politics, science, technology, sports, education, immigration, energy, world, funny, weird, onion
- Source-domain fallback: applies only when keyword matching finds zero topics (avoids false positives for off-topic articles from movie/entertainment sites)
- Priority ordering determines which category wins: onion > funny > weird > cybersecurity > gaming > technology > AI > health > science > tunisia > arab_world > world > politics > immigration > economy > energy > education > climate > space > sports > movies

### Categories (9)
Geopolitical | World Health | Tech | Cybersecurity | Funny/Weird | Gaming | Movies | Arab World | Tunisia

### Scoring Model
- `final_score = 0.20*pop + 0.35*trust + 0.30*coverage + 0.15*recency`
- Trust spread 0.05–1.00 based on source reputation, extraction success, article length, factual language, clickbait/opinion penalties
- Clustering: similarity threshold 0.70; articles merge into clusters; cluster gets max(article scores)
- Recency: 1.0 for <1h, decays linearly to 0.0 at 72h

### Web UI
- Flask app at port 5050
- Tabbed interface (dynamically generated from CATEGORIES list)
- Cards with image, topic badge, summary, trust/coverage badges, relevance score bar, date badge
- Articles grouped by date (date headers in indigo, uppercase) and sorted by relevance within each day
- Article extraction via trafilatura with readability fallback
- NYT blocked (403) → falls back to title-only extraction

## What We Did

### Category Overhaul (prior to this session)
- Split everything into 5 categories: Geopolitical, World Health, Tech, Cybersecurity, Funny/Weird
- Removed crypto topic; merged funny/weird/onion/sports into Funny/Weird
- Fixed category "bleeding" (NYT World → Geopolitical, not Tech)
- Added subject-based keywords + regex for all topics
- Added source-domain fallback for krebs, bleepingcomputer, theonion
- Priority-based `_map_category` with word-boundary patterns
- Removed fluff tagging; expanded factual/clickbait/opinion signals
- Recency weight reduced from 0.25 to 0.15
- Off-topic detection: penalized AI/space articles in general news feeds
- Rebranded "Health" → "World Health"

### Stability & Config
- Moved all settings to `Config` dataclass
- Reduced feed count, added per-feed error tolerance (continues on failure)
- Removed pointless re-clustering in presenter; now uses clusters from pipeline directly

### Gaming + Arab World (previous session)
- Added 3 gaming feeds and 2 Arab world feeds
- Added `gaming` and `arab_world` topics with keyword patterns + domain fallback
- Moved `arab_world` above `world` in priority
- Added Gaming and Arab World to CATEGORIES
- Lowered `posts_per_subreddit` to 2

### Date Grouping (recent)
- Added `published_iso` field to Article model for reliable date sorting
- Clusters sorted by date (newest first), then by relevance score within each day
- Date headers rendered as indigo uppercase badges above article groups
- Failed date parsing falls back to ISO format parsing for display

### Movies + Tunisia (current session)
- Added 4 movie feeds (Variety, Hollywood Reporter, Deadline, Screen Rant)
- Added 3 Tunisia feeds (Tunisia Online News, North Africa Post, Africa News)
- Added `movies` and `tunisia` topics to TOPIC_MAP with keyword patterns
- Added movie/entertainment and Tunisia domains to DOMAIN_TOPICS
- Changed domain fallback to only trigger when keyword matching finds zero topics (reduces off-topic leakage)
- Movies placed last in priority (acts as catch-all for entertainment sites)
- Tunisia placed above arab_world/world for correct categorization of Tunisia articles
- Added Movies and Tunisia to CATEGORIES (now 9 total)
- Raised `posts_per_subreddit` to 3 for adequate article counts per category
 
 
 ### HOW TO RUN:
 - python webapp.py 