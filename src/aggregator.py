import logging
from collections import Counter
from typing import Optional

from .models import NewsCluster, NewsItem

logger = logging.getLogger(__name__)


class NewsAggregator:
    def __init__(self, config):
        self.config = config
        self._encoder = None
        self._setup_encoder()

    def _setup_encoder(self):
        if not self.config.use_local_models:
            logger.info("Local models disabled — using keyword similarity")
            return
        try:
            from sentence_transformers import SentenceTransformer
            model_name = f"sentence-transformers/{self.config.embedding_model}"
            logger.info("Loading embedding model: %s ...", model_name)
            self._encoder = SentenceTransformer(model_name)
        except ImportError:
            logger.warning("sentence-transformers not available — using keyword fallback")
        except Exception as exc:
            logger.warning("Embedding model failed: %s", exc)

    def compute_similarity(self, a: str, b: str) -> float:
        if self._encoder:
            emb_a = self._encoder.encode(a, normalize_embeddings=True)
            emb_b = self._encoder.encode(b, normalize_embeddings=True)
            return float(emb_a @ emb_b)
        return self._keyword_overlap(a, b)

    @staticmethod
    def _keyword_overlap(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        common = words_a & words_b
        return len(common) / max(len(words_a), len(words_b))

    def cluster_news(self, items: list[NewsItem]) -> list[NewsCluster]:
        clusters: list[list[NewsItem]] = []

        for item in items:
            if not item.analysis or not item.article:
                continue

            text = f"{item.article.title or item.post.title} {item.analysis.summary}"
            placed = False

            for cluster in clusters:
                rep = cluster[0]
                if not rep.analysis:
                    continue
                rep_text = f"{rep.article.title or rep.post.title} {rep.analysis.summary}"
                if self.compute_similarity(text, rep_text) >= self.config.similarity_threshold:
                    cluster.append(item)
                    placed = True
                    break

            if not placed:
                clusters.append([item])

        return self._rank_clusters(clusters)

    def _rank_clusters(self, raw: list[list[NewsItem]]) -> list[NewsCluster]:
        scored = []
        for group in raw:
            if not group:
                continue

            topic = self._main_topic(group)

            # Highest scoring post represents the cluster
            best = max(group, key=lambda x: x.post.score)

            avg_trust = sum(
                it.analysis.trustworthiness_score for it in group if it.analysis
            ) / max(len(group), 1)

            avg_pop = sum(it.post.score for it in group) / max(len(group), 1)

            # Pick the first non-empty image
            image_url = ""
            for it in group:
                src = it.article.image_url if it.article else ""
                if src:
                    image_url = src
                    break
                if it.post.image_url:
                    image_url = it.post.image_url
                    break

            cluster_score = self._cluster_score(group, avg_trust)

            cluster = NewsCluster(
                topic=topic,
                articles=group,
                total_coverage=len(group),
                avg_trustworthiness=avg_trust,
                avg_popularity=avg_pop,
                top_post_url=best.post.url,
                final_score=cluster_score,
                image_url=image_url,
            )
            scored.append(cluster)

        return sorted(scored, key=lambda c: c.final_score, reverse=True)

    def _cluster_score(self, group: list[NewsItem], avg_trust: float) -> float:
        scores = []
        for item in group:
            s = avg_trust * 0.50

            # Content quality: longer articles score higher
            if item.article and item.article.text:
                title_len = len(item.article.title or "")
                text_len = len(item.article.text)
                if text_len > title_len * 3:
                    s += 0.15
                elif text_len > title_len * 1.5:
                    s += 0.08

            # Successfully extracted vs title-only
            if item.article and item.article.extraction_success:
                s += 0.10
            else:
                s -= 0.10

            # More topics = richer article
            if item.analysis and item.analysis.topics:
                s += min(len(item.analysis.topics) * 0.06, 0.18)

            # Having a category means we actually understood it
            if item.analysis and item.analysis.category != "General":
                s += 0.05

            # Penalty for sourcing from another outlet's reporting
            if item.analysis:
                s -= item.analysis.sourcing_penalty * 0.40

            scores.append(max(0.05, min(1.0, s)))

        return sum(scores) / max(len(scores), 1)

    @staticmethod
    def _main_topic(cluster: list[NewsItem]) -> str:
        counter: Counter[str] = Counter()
        for item in cluster:
            if item.analysis:
                for t in item.analysis.topics:
                    counter[t] += 1
        if counter:
            return counter.most_common(1)[0][0]
        return (cluster[0].article.title or cluster[0].post.title or "")[:60]
