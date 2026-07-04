"""
analyzer.py — NLP pipeline for news articles.

  1. Summarise article text (T5-small or sentence extraction)
  2. Classify topics (zero-shot DistilBERT or keyword matching with word boundaries)
  3. Assess trustworthiness (wide 0.1–1.0 spread with length/source/text-quality signals)
  4. Detect opinion vs. factual reporting
  5. Estimate political leaning
"""

import html
import logging
import re
from typing import Optional

from .models import Analysis, Article

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known domains with credibility bonuses (wider spread)
# ---------------------------------------------------------------------------
RELIABLE_DOMAINS = {
    "reuters.com": 0.20, "apnews.com": 0.20, "bbc.com": 0.15,
    "bbc.co.uk": 0.15, "npr.org": 0.12, "wsj.com": 0.12,
    "economist.com": 0.15, "nature.com": 0.20, "science.org": 0.18,
    "sciencedaily.com": 0.14, "theguardian.com": 0.08, "nytimes.com": 0.10,
    "washingtonpost.com": 0.10, "ft.com": 0.14, "bloomberg.com": 0.12,
}

UNRELIABLE_DOMAINS = {
    "infowars.com": -0.30, "breitbart.com": -0.20, "dailymail.co.uk": -0.12,
    "theonion.com": -0.25, "naturalnews.com": -0.30, "zerohedge.com": -0.15,
}

CLICKBAIT_PATTERNS = [
    r"you won'?t believe", r"shocked?", r"gobsmacked",
    r"this is what happens", r"number \d+ will",
    r"here'?s why", r"what happens next",
    r"blown away", r"mind.?blowing",
]

OPINION_MARKERS = [
    r"\bi think\b", r"\bin my opinion\b", r"\bpersonally\b",
    r"\bi believe\b", r"\bclearly\b", r"\bobviously\b",
    r"\bin my view\b", r"\bit seems\b", r"\bi feel\b",
]

LEFT_KEYWORDS = ["progressive", "equality", "social justice", "climate crisis",
                 "marginalized", "systemic", "privilege", "inequality"]
RIGHT_KEYWORDS = ["deregulation", "tax cuts", "free market", "traditional",
                  "sovereignty", "patriot", "heritage", "small government"]

# Topic keywords with word-boundary matching
# Note: use r"\bhack" (no trailing \b) to match "hackers", "hacked", "hacking" too
TOPIC_MAP: dict[str, list[str]] = {
    "artificial intelligence": [r"\bai\b", r"\bartificial intelligence\b",
                                r"\bmachine learning\b", r"\bgpt\b", r"\bllm\b",
                                r"\bneural network", r"\bdeep learning\b"],
    "climate change": [r"\bclimate\b", r"\bglobal warming\b", r"\bemissions\b",
                       r"\bcarbon\b", r"\brenewable\b", r"\bsolar\b", r"\bwind turbine",
                       r"\bheatwave\b", r"\bextreme weather\b", r"\bheat wave\b"],
    "health": [r"\bhealth\b", r"\bcovid\b", r"\bvaccine\b", r"\bdisease\b",
               r"\bhospital\b", r"\bmedical\b", r"\bcancer\b", r"\bdrug\b",
               r"\bod\b", r"\bpandemic\b", r"\bpatient\b", r"\bsurgery\b",
               r"\bdoctor\b", r"\bnurse\b", r"\btreatment\b", r"\btherapy\b",
               r"\bdementia\b", r"\bdiabetes\b", r"\bobesity\b", r"\bmental health\b",
               r"\babortion\b", r"\bpregnant\b", r"\bmedicine\b", r"\bclinical\b",
               r"\bsymptom\b", r"\bheat\b", r"\brabies\b", r"\bfever\b"],
    "economy": [r"\beconomy\b", r"\binflation\b", r"\bgdp\b", r"\binterest rate\b",
                r"\brecession\b", r"\bunemployment\b", r"\bmarket\b", r"\btariff\b",
                r"\btrade war\b", r"\bdebt\b", r"\bstock\b", r"\bprice\b", r"\bcost\b",
                r"\bfinancial\b"],
    "space": [r"\bspace\b", r"\bnasa\b", r"\bspacex\b", r"\bmars\b", r"\brocket\b",
              r"\bastronaut\b", r"\bgalaxy\b", r"\bplanet\b", r"\borgbit\b",
              r"\bstellar\b", r"\bcosmic\b"],
    "cybersecurity": [r"\bcyber\b", r"\bhack", r"\bsecurity breach\b",
                      r"\bdata breach\b", r"\bransomware\b", r"\bmalware\b",
                      r"\bphishing\b", r"\bzero.day\b", r"\bfirewall\b",
                      r"\bencryption\b", r"\bCVE\b", r"\bexploit\b",
                      r"\bbotnet\b", r"\bDDoS\b", r"\bvulnerability\b", r"\bfraud\b"],
    "politics": [r"\belection\b", r"\bvot(?:e|ing|er)\b", r"\bcongress\b",
                 r"\bparliament\b", r"\bsenate\b", r"\bpresident\b",
                 r"\bgovern(?:ment|or)\b", r"\bGOP\b", r"\bDemocrat\b",
                 r"\brepublican\b", r"\bpolitician\b", r"\bcandidate\b",
                 r"\bambassador\b", r"\bdiplomat\b", r"\bsanction\b",
                 r"\btreaty\b", r"\bembassy\b", r"\bminister\b", r"\bregime\b",
                 r"\blegislat\b", r"\bpolicy\b", r"\bfederal\b"],
    "science": [r"\bscien(?:ce|tist|tists|tific)\b", r"\bresearch\b", r"\bstudy\b",
                r"\bdiscovery\b", r"\bgenome\b", r"\bquantum\b", r"\bparticle\b",
                r"\bevolution\b", r"\bexperiment\b", r"\bjournal\b", r"\blab\b",
                r"\bDNA\b", r"\bgene\b", r"\bprotein\b", r"\bbiolog\b",
                r"\bchemical\b", r"\bphysics\b"],
    "technology": [r"\btech\b", r"\bsoftware\b", r"\bhardware\b", r"\bchip\b",
                   r"\bsemiconductor\b", r"\bapp\b", r"\balgorithm\b",
                   r"\bcomputer\b", r"\brobot\b", r"\bgaming\b", r"\bvideo game\b",
                   r"\bconsole\b", r"\bmobile\b", r"\bphone\b", r"\blaptop\b",
                   r"\bsmartphone\b", r"\bgadget\b", r"\bstartup\b",
                   r"\bplatform\b", r"\bdeveloper\b", r"\bcode\b", r"\bprogramming\b",
                   r"\bdigital\b", r"\bcloud\b", r"\bdevice\b", r"\bsmart\b", r"\bIoT\b",
                   r"\bOS\b", r"\bWindows\b", r"\bAndroid\b", r"\biOS\b",
                   r"\bPlayStation\b", r"\bapp\b", r"\bAI\b", r"\bA\.I",
                   r"\bEV\b", r"\belectric vehicle\b", r"\bgadget\b",
                   r"\btechlash\b"],
    "sports": [r"\bsport\b", r"\bfootball\b", r"\bsoccer\b", r"\bbasketball\b",
               r"\btennis\b", r"\bworld cup\b", r"\bolympic\b"],
    "education": [r"\beducation\b", r"\bschool\b", r"\buniversity\b",
                  r"\bstudent\b", r"\bteacher\b", r"\bcollege\b", r"\bcampus\b"],
    "immigration": [r"\bimmigra(?:nt|tion)\b", r"\bborder\b", r"\basylum\b",
                    r"\brefugee\b", r"\bdeport\b", r"\bvisa\b"],
    "energy": [r"\boil\b", r"\bgas\b", r"\bnuclear\b", r"\benergy\b",
               r"\bpower plant\b", r"\brenewable\b", r"\bfossil fuel\b"],
    "world": [r"\bwar\b", r"\bmilitary\b", r"\binvasion\b", r"\bsanction\b",
              r"\bforeign\b", r"\bdiplomat\b", r"\btreaty\b", r"\bconflict\b",
              r"\bearthquake\b", r"\bflood\b", r"\bdisaster\b", r"\bpresident\b",
              r"\bprime minister\b", r"\bgeopolitic\b", r"\balliance\b",
              r"\bmilitant\b", r"\bguerrilla\b", r"\bceasefire\b", r"\bterrorism\b",
              r"\bUkraine\b", r"\bRussia\b", r"\bChina\b", r"\bIran\b",
              r"\batomic\b", r"\bnuclear\b", r"\bmissile\b", r"\bdrone\b",
              r"\battack\b", r"\bstrike\b", r"\bbomb\b", r"\btroop\b",
              r"\bsoldier\b", r"\bmissile\b", r"\bdefence\b", r"\bdefense\b",
              r"\bNATO\b", r"\bUN\b", r"\bICC\b", r"\bintelligence\b",
              r"\bVatican\b", r"\bCatholic\b"],
    "funny": [r"\bfunny\b", r"\bjoke\b", r"\bhumor\b", r"\bcomedy\b",
              r"\bsatire\b", r"\bparody\b", r"\blol\b", r"\bwtf\b",
              r"\babsurd\b", r"\bridiculous\b", r"\bhilarious\b", r"\bcomic\b",
              r"\blaugh\b", r"\bclown\b"],
    "weird": [r"\bweird\b", r"\bstrange\b", r"\bbizarre\b", r"\boddb?all\b",
              r"\bpeculiar\b", r"\bunusual\b", r"\bodd\b", r"\bunbelievable\b",
              r"\bsurreal\b", r"\bunconventional\b", r"\bwtf\b"],
    "onion": [r"\bonion\b", r"\btheonion\b"],
    "gaming": [r"\bgam(?:e|ing|er|ers)\b", r"\besport\b", r"\bplaystation\b",
               r"\bxbox\b", r"\bnintendo\b", r"\bsteam\b", r"\bconsole\b",
               r"\bgta\b", r"\bgrand theft auto\b", r"\bfortnite\b",
               r"\bminecraft\b", r"\bvalorant\b", r"\bvideogame\b",
               r"\bvideo game\b"],
    "movies": [r"\bmovie\b", r"\bfilm\b", r"\bcinema\b", r"\bHollywood\b",
               r"\bbox office\b", r"\bblockbuster\b", r"\bOscar\b",
               r"\bactor\b", r"\bactress\b", r"\bscreenplay\b",
               r"\bdirector\b", r"\bNetflix\b", r"\bDisney\+\b",
               r"\bHBO\b", r"\breboot\b", r"\bsequel\b", r"\bprequel\b",
               r"\bIMAX\b", r"\banimation\b"],
    "tunisia": [r"\bTunisia\b", r"\bTunis\b", r"\bCarthage\b",
                r"\bSousse\b", r"\bSfax\b"],
    "arab_world": [r"\barab\b", r"\bgulf\b", r"\bmiddle east\b",
                   r"\bsaudi\b", r"\bQatar\b", r"\bUAE\b", r"\bDubai\b",
                   r"\bAbu Dhabi\b", r"\bDoha\b", r"\bRiyadh\b",
                   r"\bPalestin\b", r"\bGaza\b", r"\bWest Bank\b",
                   r"\bLeban\b", r"\bBeirut\b", r"\bBaghdad\b",
                   r"\bCairo\b", r"\bEgypt\b", r"\bSyria\b",
                   r"\bYemen\b", r"\bAmman\b", r"\bJordan\b",
                   r"\bOman\b", r"\bKuwait\b", r"\bBahrain\b",
                   r"\bUnrwa\b", r"\bHezbollah\b", r"\bHouthi\b",
                   r"\bOPEC\b", r"\bMENA\b"],
}

# Map detected topics -> target display categories
TOPIC_TO_CATEGORY: dict[str, str] = {
    "politics": "Geopolitical",
    "world": "Geopolitical",
    "immigration": "Geopolitical",
    "economy": "Geopolitical",
    "energy": "Geopolitical",
    "health": "World Health",
    "science": "World Health",
    "technology": "Tech",
    "artificial intelligence": "Tech",
    "space": "Tech",
    "cybersecurity": "Cybersecurity",
    "funny": "Funny/Weird",
    "weird": "Funny/Weird",
    "onion": "Funny/Weird",
    "sports": "Funny/Weird",
    "education": "Geopolitical",
    "climate change": "Geopolitical",
    "gaming": "Gaming",
    "movies": "Movies",
    "tunisia": "Tunisia",
    "arab_world": "Arab World",
}

FACTUAL_KEYWORDS = [
    r"\breport\b", r"\baccording to\b", r"\bsource said\b", r"\bstated\b",
    r"\bstudy found\b", r"\bdata show\b", r"\bofficial said\b",
    r"\bresearch suggests\b", r"\bthe study\b", r"\bsurvey\b",
]


class NewsAnalyzer:
    def __init__(self, config):
        self.config = config
        self._summariser = None
        self._classifier = None
        self._setup_models()

    # ------------------------------------------------------------------
    # Model loading (lazy)
    # ------------------------------------------------------------------
    def _setup_models(self):
        if not self.config.use_local_models:
            logger.info("Local models disabled — using rule-based analysis")
            return
        try:
            from transformers import pipeline
            logger.info("Loading summariser: %s ...", self.config.summarization_model)
            self._summariser = pipeline(
                "summarization",
                model=self.config.summarization_model,
                tokenizer=self.config.summarization_model,
            )
            logger.info("Loading zero-shot classifier ...")
            self._classifier = pipeline(
                "zero-shot-classification",
                model="typeform/distilbert-base-uncased-mnli",
            )
        except ImportError:
            logger.warning("transformers not available — using rule-based analysis")
        except Exception as exc:
            logger.warning("Model loading failed: %s — using rule-based", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze(self, article: Article) -> Analysis:
        summary = self._summarise(article)
        topics = self._classify_topics(article, summary)
        trust = self._assess_trustworthiness(article)
        is_opinion = self._detect_opinion(article.text or "")
        leaning = self._detect_political_leaning(article.text or "")

        category = self._map_category(topics)

        return Analysis(
            summary=summary,
            topics=topics,
            trustworthiness_score=trust,
            is_opinion=is_opinion,
            political_leaning=leaning,
            category=category,
        )

    # ------------------------------------------------------------------
    # 1. Summarisation
    # ------------------------------------------------------------------
    def _summarise(self, article: Article) -> str:
        title = article.title or ""
        text = article.text or ""

        if self._summariser:
            try:
                input_text = text[:1024]
                out = self._summariser(input_text, max_length=130, min_length=30,
                                       do_sample=False)
                return out[0]["summary_text"]
            except Exception as exc:
                logger.debug("Summariser failed: %s", exc)

        body = self._strip_metadata(text)
        body = self._strip_title_line(body, title)

        if not body or len(body) < len(title) * 1.5:
            return ""

        title_norm = self._norm(title)
        sentences = re.split(r"(?<=[.!?])\s+", body.strip())
        selected = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if self._is_title_like(s, title_norm):
                continue
            selected.append(s)
            if len(selected) >= 2:
                break
        return " ".join(selected) if selected else ""

    @staticmethod
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", html.unescape(s).lower().strip()).rstrip(".")

    @staticmethod
    def _is_title_like(sentence: str, title_norm: str) -> bool:
        s_norm = re.sub(r"\s+", " ", sentence.lower().strip()).rstrip(".")
        if s_norm == title_norm:
            return True
        words_s = set(s_norm.split())
        words_t = set(title_norm.split())
        if not words_s or not words_t:
            return False
        short, long = (words_s, words_t) if len(words_s) < len(words_t) else (words_t, words_s)
        overlap = len(short & long) / max(len(short), len(long))
        return overlap > 0.7

    @staticmethod
    def _strip_title_line(text: str, title: str) -> str:
        lines = text.split("\n")
        if not lines:
            return text
        first = lines[0].strip()
        if not first:
            return "\n".join(lines[1:]).strip()
        # Drop first line if it looks like a headline (short, no sentence-end punctuation)
        if len(first) < 150 and not re.search(r"[.!?]$", first):
            return "\n".join(lines[1:]).strip()
        return text

    @staticmethod
    def _strip_metadata(text: str) -> str:
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            clean = line.strip()
            if re.match(r"^\s*[—\-] (Published|Updated|BBC News|Image|Copyright)", clean, re.IGNORECASE):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    # ------------------------------------------------------------------
    # 2. Topic classification
    # ------------------------------------------------------------------
    def _classify_topics(self, article: Article, summary: str) -> list[str]:
        if self._classifier:
            try:
                text = f"{article.title} {summary}" if summary else article.title
                candidates = self.config.user_interests + ["other"]
                result = self._classifier(text[:512], candidates)
                return [
                    label for label, score in zip(result["labels"], result["scores"])
                    if score > 0.25
                ]
            except Exception as exc:
                logger.debug("Classifier failed: %s", exc)

        return self._keyword_topic_match(article, summary)

    DOMAIN_TOPICS: dict[str, str] = {
        "krebsonsecurity.com": "cybersecurity",
        "bleepingcomputer.com": "cybersecurity",
        "theonion.com": "onion",
        "ign.com": "gaming",
        "eurogamer.net": "gaming",
        "pcgamer.com": "gaming",
        "rockpapershotgun.com": "gaming",
        "kotaku.com": "gaming",
        "gamespot.com": "gaming",
        "arabnews.com": "arab_world",
        "middleeasteye.net": "arab_world",
        "thenationalnews.com": "arab_world",
        "newarab.com": "arab_world",
        "therecord.media": "cybersecurity",
        "threatpost.com": "cybersecurity",
        "thedailymash.co.uk": "funny",
        "babylonbee.com": "onion",
        "polygon.com": "gaming",
        "variety.com": "movies",
        "hollywoodreporter.com": "movies",
        "deadline.com": "movies",
        "screenrant.com": "movies",
        "tunisiaonlinenews.com": "tunisia",
    }

    def _keyword_topic_match(self, article: Article, summary: str) -> list[str]:
        text = f"{article.title} {summary}" if summary else article.title
        found = []
        for topic, patterns in TOPIC_MAP.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                found.append(topic)
        domain = re.sub(r"^www\.", "", (article.source_domain or ""))
        mapped = self.DOMAIN_TOPICS.get(domain)
        if mapped and mapped not in found:
            if not found:
                found.append(mapped)
        return found

    # ------------------------------------------------------------------
    # 3. Trustworthiness score  (0.0 – 1.0) — wider spread
    # ------------------------------------------------------------------
    def _assess_trustworthiness(self, article: Article) -> float:
        score = 0.40  # lower base for wider spread

        # --- Source reputation ---
        domain = article.source_domain or ""
        clean_domain = re.sub(r"^www\.", "", domain)
        score += RELIABLE_DOMAINS.get(clean_domain, 0.0)
        score += UNRELIABLE_DOMAINS.get(clean_domain, 0.0)

        # --- Extraction success ---
        text = article.text or ""
        title = article.title or ""
        if article.extraction_success is False:
            score -= 0.15
        elif len(text) > len(title) * 3:
            score += 0.05

        # --- Text length bonus (well-developed articles) ---
        word_count = len(text.split())
        if word_count > 200:
            score += 0.10
        elif word_count > 100:
            score += 0.05
        elif word_count > 50:
            score += 0.02

        # --- Factual language bonus ---
        factual_count = sum(1 for p in FACTUAL_KEYWORDS if re.search(p, text, re.IGNORECASE))
        score += min(factual_count * 0.02, 0.08)

        # --- Clickbait penalty ---
        if any(re.search(p, title, re.IGNORECASE) for p in CLICKBAIT_PATTERNS):
            score -= 0.20

        # --- Opinion marker penalty ---
        opinion_count = sum(
            1 for p in OPINION_MARKERS if re.search(p, text, re.IGNORECASE)
        )
        score -= opinion_count * 0.05

        # --- Cap & clamp ---
        return max(0.05, min(1.0, score))

    @staticmethod
    def _map_category(topics: list[str]) -> str:
        # Priority order: check high-signal topics first
        priority = ["onion", "funny", "weird", "cybersecurity", "gaming",
                     "technology", "artificial intelligence", "health", "science",
                     "tunisia", "arab_world", "world", "politics", "immigration", "economy",
                     "energy", "education", "climate change", "space", "sports", "movies"]
        topic_set = {t.lower() for t in topics}
        for p in priority:
            if p in topic_set:
                mapped = TOPIC_TO_CATEGORY.get(p)
                if mapped:
                    return mapped
        return "General"

    # ------------------------------------------------------------------
    # 4. Opinion detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_opinion(text: str) -> bool:
        count = sum(1 for p in OPINION_MARKERS if re.search(p, text.lower()))
        return count >= 3

    # ------------------------------------------------------------------
    # 5. Political leaning (simple keyword heuristics)
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_political_leaning(text: str) -> str:
        text_lower = text.lower()
        left = sum(1 for k in LEFT_KEYWORDS if k in text_lower)
        right = sum(1 for k in RIGHT_KEYWORDS if k in text_lower)
        if left > right + 1:
            return "left-leaning"
        if right > left + 1:
            return "right-leaning"
        return "centrist"
