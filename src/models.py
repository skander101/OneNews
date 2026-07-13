from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RedditPost:
    id: str
    title: str
    url: str
    subreddit: str
    score: int
    num_comments: int
    source_domain: str = ""
    image_url: str = ""
    published: str = ""
    published_iso: str = ""


@dataclass
class Article:
    url: str
    title: str
    text: str
    source_domain: str
    extraction_success: bool = True
    image_url: str = ""
    published: str = ""
    published_iso: str = ""


@dataclass
class Analysis:
    summary: str
    topics: list[str]
    trustworthiness_score: float
    is_opinion: bool
    political_leaning: str = "centrist"
    category: str = "General"
    sponsor: dict = field(default_factory=dict)
    source_bias: str = ""
    source_factuality: str = ""
    article_leaning: str = "centrist"
    sourcing_penalty: float = 0.0


@dataclass
class NewsItem:
    post: RedditPost
    article: Optional[Article] = None
    analysis: Optional[Analysis] = None
    final_score: float = 0.0


@dataclass
class NewsCluster:
    topic: str
    articles: list[NewsItem]
    total_coverage: int
    avg_trustworthiness: float
    avg_popularity: float
    top_post_url: str
    final_score: float = 0.0
    image_url: str = ""
