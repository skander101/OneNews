from collections import defaultdict

from .models import NewsCluster


class NewsPresenter:
    CATEGORIES = ["Geopolitical", "World Health", "Tech", "Cybersecurity", "Funny/Weird", "Gaming", "Movies", "Arab World", "Tunisia"]

    @staticmethod
    def display(clusters: list[NewsCluster], top_n: int = 10):
        if not clusters:
            print("\n  No news stories matched your interests this round.")
            return

        by_cat: dict[str, list[NewsCluster]] = defaultdict(list)
        for c in clusters:
            cat = "General"
            if c.articles and c.articles[0].analysis:
                ca = c.articles[0].analysis.category
                cat = ca if ca in NewsPresenter.CATEGORIES else "General"
            by_cat[cat].append(c)

        print("╔" + "═" * 78 + "╗")
        print("║  📰  NEWS DIGEST  —  Top Stories  ║".center(80))
        print("╚" + "═" * 78 + "╝")

        for cat in NewsPresenter.CATEGORIES:
            items = by_cat.get(cat, [])
            items.sort(key=lambda x: (x.articles[0].article.published_iso or x.articles[0].post.published_iso or "", x.final_score), reverse=True)
            items = items[:top_n]
            if not items:
                continue
            print(f"\n  ══ {cat} ({len(items)}) ══\n")
            for i, cluster in enumerate(items, 1):
                print(f"  #{i:<2} [{cluster.topic:<30}]  "
                      f"Score: {cluster.final_score:.2f}  "
                      f"Trust: {cluster.avg_trustworthiness:.0%}")
                item = cluster.articles[0]
                title = item.article.title[:72] + "…" if item.article.title and len(item.article.title) > 72 else (item.article.title or item.post.title)
                print(f"       {title}")
                published = item.article.published or item.post.published
                if published:
                    print(f"       📅 {published}")
                if item.analysis and item.analysis.summary:
                    short = item.analysis.summary[:72] + "…" if len(item.analysis.summary) > 72 else item.analysis.summary
                    print(f"       → {short}")
                print()

        print("▔" * 80)
