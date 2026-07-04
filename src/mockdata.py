import random
import time

from .models import Analysis, Article, NewsItem, RedditPost

_MOCK_ARTICLES = [
    {
        "title": "New AI model achieves breakthrough in protein folding prediction",
        "text": (
            "Researchers at DeepMind and several universities have announced a major breakthrough "
            "in protein folding prediction using a new deep learning architecture. The model, called "
            "AlphaFold-Next, is able to predict protein structures with accuracy approaching "
            "experimental methods. This advancement could accelerate drug discovery and our "
            "understanding of diseases. The team trained the model on a dataset of over 100,000 "
            "known protein structures and used a novel attention mechanism to capture long-range "
            "interactions between amino acids. Early tests show the model generalises well to "
            "previously unseen protein families."
        ),
        "domain": "nature.com",
        "subreddit": "science",
        "score": 5420,
        "comments": 342,
    },
    {
        "title": "WHO declares new global health emergency as novel virus spreads across continents",
        "text": (
            "The World Health Organization has declared a Public Health Emergency of International "
            "Concern as a novel respiratory virus continues to spread rapidly across multiple "
            "continents. The virus, which emerged in Southeast Asia, has been detected in 15 "
            "countries so far. Health officials are implementing containment measures including "
            "travel restrictions and increased surveillance. The WHO is coordinating with national "
            "health agencies to ensure a rapid response. Vaccines are expected to begin clinical "
            "trials within six months, according to the Director-General."
        ),
        "domain": "reuters.com",
        "subreddit": "worldnews",
        "score": 8210,
        "comments": 2801,
    },
    {
        "title": "New study links ultra-processed foods to increased cancer risk",
        "text": (
            "A comprehensive study published in The Lancet has found a significant correlation "
            "between consumption of ultra-processed foods and increased risk of developing certain "
            "types of cancer. The study followed over 200,000 participants for 15 years and "
            "controlled for lifestyle factors such as smoking and exercise. Researchers found that "
            "participants who consumed the highest levels of ultra-processed foods had a 23% higher "
            "risk of developing colorectal cancer. The findings add to growing evidence that dietary "
            "patterns play a crucial role in cancer prevention."
        ),
        "domain": "bbc.com",
        "subreddit": "health",
        "score": 3890,
        "comments": 567,
    },
    {
        "title": "SpaceX successfully launches satellite constellation for global internet coverage",
        "text": (
            "SpaceX has successfully launched another batch of 60 Starlink satellites, bringing the "
            "total constellation size to over 5,000. The Falcon 9 rocket lifted off from Cape "
            "Canaveral and successfully deployed the satellites in low Earth orbit. This expansion "
            "will bring high-speed internet access to previously unserved rural areas across the "
            "globe. The company plans to increase the constellation to 12,000 satellites within "
            "the next three years, with initial tests showing latency as low as 20 milliseconds."
        ),
        "domain": "reuters.com",
        "subreddit": "technology",
        "score": 4560,
        "comments": 890,
    },
    {
        "title": "Federal Reserve signals interest rate cut as inflation continues to cool",
        "text": (
            "The Federal Reserve has signalled it may cut interest rates at its next meeting as "
            "inflation continues to trend downward toward the 2% target. Recent economic data "
            "shows consumer prices rose only 2.3% year-over-year, down from a peak of 9.1% two "
            "years ago. Fed Chair Jerome Powell stated that while progress has been made, the "
            "committee would remain data-dependent. Markets responded positively, with the S&P "
            "500 rising 1.2% on the news. Economists expect a quarter-point cut in September."
        ),
        "domain": "wsj.com",
        "subreddit": "economy",
        "score": 3200,
        "comments": 1200,
    },
    {
        "title": "Global climate summit reaches historic agreement on fossil fuel phase-out",
        "text": (
            "Nearly 200 nations have reached a landmark agreement to phase out fossil fuels at the "
            "UN Climate Summit in Dubai. The agreement sets a timeline for reducing coal, oil, and "
            "gas production, with developed nations committing to faster reductions. Developing "
            "countries will receive financial support through a new climate fund worth $100 billion "
            "annually. Environmental groups have cautiously welcomed the deal while noting that "
            "the timeline may need to accelerate to meet Paris Agreement targets. The agreement "
            "marks the first time all nations have explicitly committed to transitioning away from "
            "fossil fuels."
        ),
        "domain": "theguardian.com",
        "subreddit": "worldnews",
        "score": 9500,
        "comments": 3400,
    },
    {
        "title": "Cybersecurity researchers discover zero-day exploit affecting billions of devices",
        "text": (
            "Security researchers have discovered a critical vulnerability in a widely-used "
            "networking library that affects an estimated 3 billion devices worldwide. The "
            "zero-day exploit, dubbed 'PacketStorm', allows remote code execution without user "
            "interaction. Major technology companies including Google, Apple, and Microsoft have "
            "released emergency patches. Users are strongly advised to update their devices "
            "immediately. The vulnerability has been present in the codebase for over a decade "
            "and was discovered during a routine security audit."
        ),
        "domain": "reuters.com",
        "subreddit": "technology",
        "score": 6700,
        "comments": 1500,
    },
    {
        "title": "Unprecedented heatwave breaks temperature records across Europe",
        "text": (
            "An unprecedented heatwave is sweeping across Europe, with temperatures exceeding "
            "45°C in several countries. Multiple heat records have been broken, including the "
            "all-time high for the United Kingdom at 42.3°C. Authorities have issued red alerts "
            "and are urging residents to stay indoors. The extreme weather has been linked to "
            "climate change by leading meteorological agencies. Hospitals are reporting increased "
            "admissions for heat-related illnesses, and transport networks have been disrupted "
            "due to heat-damaged infrastructure."
        ),
        "domain": "bbc.com",
        "subreddit": "worldnews",
        "score": 7800,
        "comments": 2100,
    },
    {
        "title": "New CRISPR therapy shows promising results in clinical trial for sickle cell disease",
        "text": (
            "A groundbreaking CRISPR-based gene therapy has shown remarkable results in a Phase 3 "
            "clinical trial for sickle cell disease. Out of 45 patients, 42 showed complete "
            "remission of symptoms 12 months after treatment. The therapy, developed by Vertex "
            "Pharmaceuticals, uses CRISPR-Cas9 to edit the patient's own stem cells, correcting "
            "the genetic mutation responsible for the disease. The FDA has granted breakthrough "
            "therapy designation, potentially accelerating approval. This marks one of the first "
            "successful CRISPR-based treatments for a genetic blood disorder."
        ),
        "domain": "nature.com",
        "subreddit": "science",
        "score": 5100,
        "comments": 450,
    },
    {
        "title": "AI regulation bill passes Senate with bipartisan support",
        "text": (
            "The US Senate has passed a landmark artificial intelligence regulation bill with "
            "significant bipartisan support. The legislation requires AI companies to conduct "
            "safety testing before releasing powerful models, establish transparency requirements, "
            "and create a new federal agency to oversee AI development. The bill was co-sponsored "
            "by senators from both parties and represents one of the most comprehensive AI "
            "governance frameworks in the world. Tech companies have expressed mixed reactions, "
            "with some supporting the clarity while others worry about innovation impact."
        ),
        "domain": "nytimes.com",
        "subreddit": "politics",
        "score": 4300,
        "comments": 1800,
    },
]


def generate_demo_items() -> list[NewsItem]:
    items = []
    for art in _MOCK_ARTICLES:
        post = RedditPost(
            id=f"mock_{random.randint(100000, 999999)}",
            title=art["title"],
            url=f"https://{art['domain']}/article/{random.randint(1000, 9999)}",
            subreddit=art["subreddit"],
            score=art["score"],
            num_comments=art["comments"],
            source_domain=art["domain"],
        )
        article = Article(
            url=post.url,
            title=art["title"],
            text=art["text"],
            source_domain=art["domain"],
        )
        items.append(NewsItem(post=post, article=article))
    return items
