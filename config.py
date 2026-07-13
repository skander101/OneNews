import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "newsapp/1.0")

    rss_feeds: list[str] = field(default_factory=lambda: [
        # ---- Geopolitical ----
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.npr.org/1001/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.theguardian.com/world/rss",
        # ---- World Health ----
        "https://www.statnews.com/feed/",
        "https://www.sciencedaily.com/rss/all.xml",
        "https://www.sciencenews.org/feed",
        "https://www.medscape.com/cx/rssfeeds/2700.xml",
        "https://www.nih.gov/news-events/news-releases/rss.xml",
        "https://news.harvard.edu/gazette/feed/",
        "https://news.harvard.edu/gazette/section/health-medicine/feed/",
        # ---- Tech ----
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://www.theverge.com/rss/index.xml",
        "https://arstechnica.com/feed/",
        # ---- Cybersecurity ----
        "https://feeds.feedburner.com/TheHackerNews",
        "https://krebsonsecurity.com/feed/",
        "https://www.bleepingcomputer.com/feed/",
        "https://threatpost.com/feed/",
        "https://therecord.media/feed/",
        # ---- Funny / Weird ----
        "https://www.theonion.com/rss",
        "https://www.reddit.com/r/nottheonion/.rss",
        "https://www.thedailymash.co.uk/feed",
        "https://babylonbee.com/feed",
        # ---- Gaming ----
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://www.pcgamer.com/rss/",
        "https://www.kotaku.com/rss",
        "https://www.gamespot.com/feeds/news/",
        "https://www.polygon.com/rss/index.xml",
        # ---- Movies ----
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://deadline.com/feed/",
        "https://screenrant.com/feed/",
        # ---- Arab World ----
        "https://www.arabnews.com/rss.xml",
        "https://www.middleeasteye.net/rss",
        "https://www.newarab.com/rss.xml",
        "https://www.france24.com/en/middle-east/rss",
        # ---- Tunisia ----
        "https://www.tunisiaonlinenews.com/feed/",
        "https://northafricapost.com/feed/",
        "https://www.africanews.com/feed/",
        "https://nawaat.org/feed/",
        "https://www.tunisienumerique.com/feed-actualites-tunisie.xml",
        "https://lapresse.tn/feed/",
        "https://allafrica.com/tools/headlines/rdf/tunisia/headlines.rdf",
    ])

    # Fallback subreddits (used for --source reddit or --source rss)
    news_subreddits: list[str] = field(default_factory=lambda: [
        "worldnews", "news", "politics", "science", "technology",
        "UpliftingNews", "economy", "geopolitics",
    ])

    posts_per_subreddit: int = 3

    weight_popularity: float = 0.20
    weight_trustworthiness: float = 0.35
    weight_coverage: float = 0.30
    weight_recency: float = 0.15

    user_interests: list[str] = field(default_factory=lambda: [
        "artificial intelligence", "climate change", "health",
        "economy", "space exploration", "cybersecurity",
        "democracy", "science",
    ])

    use_local_models: bool = False
    summarization_model: str = "t5-small"
    embedding_model: str = "all-MiniLM-L6-v2"

    similarity_threshold: float = 0.70

    port: int = int(os.getenv("PORT", "5050"))
    host: str = os.getenv("HOST", "0.0.0.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    flask_env: str = os.getenv("FLASK_ENV", "production")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    refresh_hour: int = int(os.getenv("REFRESH_HOUR", "4"))
    refresh_minute: int = int(os.getenv("REFRESH_MINUTE", "0"))
    refresh_timezone: str = os.getenv("REFRESH_TIMEZONE", "Africa/Tunis")
