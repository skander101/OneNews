---
title: News Digest
emoji: 📰
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# OneNews

**⚠️ Experimental / Educational project — built to learn how scrapers and AI work from scratch. Not production-ready. Not intended to be.**

**Your daily news, scraped, scored, sorted, and served in tabs. No AI slop, no crypto bros, no "you won't believe what happens next."**

OneNews pulls from ~40 RSS feeds across 9 categories — Geopolitical, World Health, Tech, Cybersecurity, Funny/Weird, Gaming, Movies, Arab World, and Tunisia — runs them through a trust/recency/coverage scoring engine, and displays everything in a clean tabbed web UI. All written from scratch to understand every moving part.

## What makes it special?

- **Built to learn.** Everything is hand-rolled — no black boxes, no copy-paste agency code.
- **Zero ads, zero trackers.** Just headlines, summaries, and a relevance score.
- **Keyword-based topic detection** with regex patterns (not an LLM hallucinating categories).
- **Source-domain fallback** — when keywords fail, the domain decides (onion.com → Funny/Weird, variety.com → Movies, etc.)
- **Trust scoring** based on source rep, article length, factual language, clickbait penalties, and opinion markers.
- **Date-grouped UI** with daily headers. News doesn't care about your feed order.
- **Scoring model you can tune** — every weight lives in one config file.

## Quick Start

```bash
python webapp.py
```

Opens at `http://localhost:5050`. First load takes ~5 min while 40 RSS feeds get fetched and scored. Go make tea.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Flask |
| Scraping | feedparser + requests + trafilatura |
| NLP | regex patterns (no transformers — runs on a toaster) |
| Scoring | weighted: pop 0.20 × trust 0.35 × coverage 0.30 × recency 0.15 |
| UI | vanilla HTML/CSS/JS, zero frameworks |

## Categories

Geopolitical | World Health | Tech | Cybersecurity | Funny/Weird | Gaming | Movies | Arab World | Tunisia

## What I learned building this

- How RSS feeds actually work under the hood (you'd be surprised how many are broken)
- Trafilatura for article extraction (beats rolling your own readability)
- The surprisingly hard problem of classifying news with just regex
- Why domain-level fallbacks matter when keyword matching comes up empty
- That Flask is perfectly fine for small stuff despite what Twitter says
- Scoring is 90% tuning weights and 10% math

## FAQ

**Q: Will it scale?**  
A: It scales to your sofa. It's a single Flask process running on whatever laptop you own.

**Q: Is this production-ready?**  
A: No. Read the first sentence of this README again.

**Q: Night mode?**  
A: The UI is already dark. You're welcome.

**Q: Why 4 AM Tunisian time for refresh?**  
A: That's when the coffee kicks in.

**Q: Can I contribute?**  
A: This is a learning project. Fork it and make your own.
