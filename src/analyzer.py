import html
import logging
import re
from typing import Optional

from .models import Analysis, Article

logger = logging.getLogger(__name__)

RELIABLE_DOMAINS = {
    "reuters.com": 0.20, "apnews.com": 0.20, "bbc.com": 0.15,
    "bbc.co.uk": 0.15, "npr.org": 0.12, "wsj.com": 0.12,
    "economist.com": 0.15, "nature.com": 0.20, "science.org": 0.18,
    "sciencedaily.com": 0.14, "theguardian.com": 0.08, "nytimes.com": 0.10,
    "washingtonpost.com": 0.10, "ft.com": 0.14, "bloomberg.com": 0.12,
    "sciencenews.org": 0.14, "medscape.com": 0.12, "nih.gov": 0.16,
    "news.harvard.edu": 0.14, "nawaat.org": 0.12, "tunisienumerique.com": 0.10,
}

UNRELIABLE_DOMAINS = {
    "infowars.com": -0.30, "breitbart.com": -0.20, "dailymail.co.uk": -0.12,
    "theonion.com": -0.25, "naturalnews.com": -0.30, "zerohedge.com": -0.15,
}

SPONSOR_INFO: dict[str, dict] = {
    # ── Government-funded ──
    "bbc.com": {
        "display": "BBC", "parent": "BBC", "category": "government", "bias": "left-center", "factuality": "high",
        "owners": ["UK Government (licence fee payers)"],
        "wikipedia": "https://en.wikipedia.org/wiki/BBC",
        "owner_wikis": {"UK Government (licence fee payers)": "https://en.wikipedia.org/wiki/Government_of_the_United_Kingdom"},
    },
    "bbc.co.uk": {
        "display": "BBC", "parent": "BBC", "category": "government", "bias": "left-center", "factuality": "high",
        "owners": ["UK Government (licence fee payers)"],
        "wikipedia": "https://en.wikipedia.org/wiki/BBC",
        "owner_wikis": {"UK Government (licence fee payers)": "https://en.wikipedia.org/wiki/Government_of_the_United_Kingdom"},
    },
    "npr.org": {
        "display": "NPR", "parent": "National Public Radio", "category": "government", "bias": "left-center", "factuality": "high",
        "owners": ["Corporation for Public Broadcasting", "Member stations"],
        "wikipedia": "https://en.wikipedia.org/wiki/NPR",
        "owner_wikis": {"Corporation for Public Broadcasting": "https://en.wikipedia.org/wiki/Corporation_for_Public_Broadcasting"},
    },
    "aljazeera.com": {
        "display": "Al Jazeera", "parent": "Al Jazeera Media Network", "category": "government", "bias": "left-center", "factuality": "high",
        "owners": ["Government of Qatar"],
        "wikipedia": "https://en.wikipedia.org/wiki/Al_Jazeera_Media_Network",
        "owner_wikis": {"Government of Qatar": "https://en.wikipedia.org/wiki/Government_of_Qatar"},
    },
    "france24.com": {
        "display": "France 24", "parent": "France Médias Monde", "category": "government", "bias": "center", "factuality": "high",
        "owners": ["French Government"],
        "wikipedia": "https://en.wikipedia.org/wiki/France_24",
        "owner_wikis": {"French Government": "https://en.wikipedia.org/wiki/Government_of_France"},
    },
    "arabnews.com": {
        "display": "Arab News", "parent": "Saudi Research & Publishing", "category": "government", "bias": "center", "factuality": "high",
        "owners": ["Saudi Government"],
        "wikipedia": "https://en.wikipedia.org/wiki/Arab_News",
        "owner_wikis": {"Saudi Government": "https://en.wikipedia.org/wiki/Government_of_Saudi_Arabia"},
    },

    # ── Media Conglomerate ──
    "wired.com": {
        "display": "Wired (Condé Nast)", "parent": "Condé Nast", "category": "conglomerate", "bias": "left-center", "factuality": "high",
        "owners": ["Advance Publications", "Newhouse family"],
        "wikipedia": "https://en.wikipedia.org/wiki/Cond%C3%A9_Nast",
        "owner_wikis": {"Advance Publications": "https://en.wikipedia.org/wiki/Advance_Publications", "Newhouse family": "https://en.wikipedia.org/wiki/Newhouse_family"},
    },
    "arstechnica.com": {
        "display": "Ars Technica (Condé Nast)", "parent": "Condé Nast", "category": "conglomerate", "bias": "left-center", "factuality": "high",
        "owners": ["Advance Publications", "Newhouse family"],
        "wikipedia": "https://en.wikipedia.org/wiki/Cond%C3%A9_Nast",
        "owner_wikis": {"Advance Publications": "https://en.wikipedia.org/wiki/Advance_Publications", "Newhouse family": "https://en.wikipedia.org/wiki/Newhouse_family"},
    },
    "wsj.com": {
        "display": "Wall Street Journal", "parent": "News Corp (Dow Jones)", "category": "conglomerate", "bias": "center", "factuality": "high",
        "owners": ["Murdoch family", "Public shareholders (NASDAQ: NWSA)"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Wall_Street_Journal",
        "owner_wikis": {"Murdoch family": "https://en.wikipedia.org/wiki/Murdoch_family"},
    },
    "pcgamer.com": {
        "display": "PC Gamer (Future)", "parent": "Future plc", "category": "conglomerate", "bias": "center", "factuality": "high",
        "owners": ["Public shareholders (LSE: FUTR)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Future_plc",
        "owner_wikis": {},
    },
    "ign.com": {
        "display": "IGN (Ziff Davis)", "parent": "Ziff Davis", "category": "conglomerate", "bias": "center", "factuality": "high",
        "owners": ["Public shareholders (NASDAQ: ZD)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Ziff_Davis",
        "owner_wikis": {},
    },

    # ── Private Equity ──
    "techcrunch.com": {
        "display": "TechCrunch", "parent": "Yahoo Inc.", "category": "private_equity", "bias": "center", "factuality": "high",
        "owners": ["Apollo Global Management"],
        "wikipedia": "https://en.wikipedia.org/wiki/TechCrunch",
        "owner_wikis": {"Apollo Global Management": "https://en.wikipedia.org/wiki/Apollo_Global_Management"},
    },
    "theverge.com": {
        "display": "The Verge (Vox Media)", "parent": "Vox Media", "category": "private_equity", "bias": "left-center", "factuality": "high",
        "owners": ["NBCUniversal (Comcast)", "Accel Partners", "General Atlantic"],
        "wikipedia": "https://en.wikipedia.org/wiki/Vox_Media",
        "owner_wikis": {
            "NBCUniversal (Comcast)": "https://en.wikipedia.org/wiki/NBCUniversal",
            "Accel Partners": "https://en.wikipedia.org/wiki/Accel",
            "General Atlantic": "https://en.wikipedia.org/wiki/General_Atlantic",
        },
    },
    "polygon.com": {
        "display": "Polygon (Vox Media)", "parent": "Vox Media", "category": "private_equity", "bias": "left-center", "factuality": "high",
        "owners": ["NBCUniversal (Comcast)", "Accel Partners", "General Atlantic"],
        "wikipedia": "https://en.wikipedia.org/wiki/Vox_Media",
        "owner_wikis": {
            "NBCUniversal (Comcast)": "https://en.wikipedia.org/wiki/NBCUniversal",
            "Accel Partners": "https://en.wikipedia.org/wiki/Accel",
            "General Atlantic": "https://en.wikipedia.org/wiki/General_Atlantic",
        },
    },
    "kotaku.com": {
        "display": "Kotaku (G/O Media)", "parent": "G/O Media", "category": "private_equity", "bias": "left-center", "factuality": "high",
        "owners": ["Great Hill Partners"],
        "wikipedia": "https://en.wikipedia.org/wiki/G/O_Media",
        "owner_wikis": {"Great Hill Partners": "https://en.wikipedia.org/wiki/Great_Hill_Partners"},
    },
    "gamespot.com": {
        "display": "GameSpot (Fandom)", "parent": "Fandom Inc.", "category": "private_equity", "bias": "center", "factuality": "high",
        "owners": ["TPG Capital", "Integrated Media Co."],
        "wikipedia": "https://en.wikipedia.org/wiki/Fandom_(website)",
        "owner_wikis": {"TPG Capital": "https://en.wikipedia.org/wiki/TPG_Inc."},
    },
    "screenrant.com": {
        "display": "Screen Rant (Valnet)", "parent": "Valnet Inc.", "category": "private_equity", "bias": "center", "factuality": "mixed",
        "owners": ["Valnet Inc."],
        "wikipedia": "https://en.wikipedia.org/wiki/Valnet",
        "owner_wikis": {},
    },
    "nature.com": {
        "display": "Nature (Springer Nature)", "parent": "Springer Nature", "category": "private_equity", "bias": "center", "factuality": "high",
        "owners": ["Holtzbrinck Publishing Group", "BC Partners"],
        "wikipedia": "https://en.wikipedia.org/wiki/Springer_Nature",
        "owner_wikis": {
            "Holtzbrinck Publishing Group": "https://en.wikipedia.org/wiki/Holtzbrinck_Publishing_Group",
            "BC Partners": "https://en.wikipedia.org/wiki/BC_Partners",
        },
    },
    "eurogamer.net": {
        "display": "Eurogamer (ReedPop)", "parent": "ReedPop (Gamer Network)", "category": "private_equity", "bias": "center", "factuality": "high",
        "owners": ["RELX Group"],
        "wikipedia": "https://en.wikipedia.org/wiki/ReedPop",
        "owner_wikis": {"RELX Group": "https://en.wikipedia.org/wiki/RELX"},
    },

    # ── Wealthy Private Owner ──
    "washingtonpost.com": {
        "display": "The Washington Post", "parent": "Nash Holdings", "category": "wealthy_private", "bias": "left-center", "factuality": "high",
        "owners": ["Jeff Bezos"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Washington_Post",
        "owner_wikis": {"Jeff Bezos": "https://en.wikipedia.org/wiki/Jeff_Bezos"},
    },
    "bloomberg.com": {
        "display": "Bloomberg", "parent": "Bloomberg L.P.", "category": "wealthy_private", "bias": "center", "factuality": "high",
        "owners": ["Michael Bloomberg (88%)", "Merck family (12%)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Bloomberg_L.P.",
        "owner_wikis": {
            "Michael Bloomberg (88%)": "https://en.wikipedia.org/wiki/Michael_Bloomberg",
            "Merck family (12%)": "https://en.wikipedia.org/wiki/Merck_family",
        },
    },
    "variety.com": {
        "display": "Variety", "parent": "Penske Media Corporation", "category": "wealthy_private", "bias": "center", "factuality": "high",
        "owners": ["Jay Penske"],
        "wikipedia": "https://en.wikipedia.org/wiki/Variety_(magazine)",
        "owner_wikis": {"Jay Penske": "https://en.wikipedia.org/wiki/Jay_Penske"},
    },
    "hollywoodreporter.com": {
        "display": "Hollywood Reporter", "parent": "Penske Media Corporation", "category": "wealthy_private", "bias": "center", "factuality": "high",
        "owners": ["Jay Penske"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Hollywood_Reporter",
        "owner_wikis": {"Jay Penske": "https://en.wikipedia.org/wiki/Jay_Penske"},
    },
    "deadline.com": {
        "display": "Deadline", "parent": "Penske Media Corporation", "category": "wealthy_private", "bias": "center", "factuality": "high",
        "owners": ["Jay Penske"],
        "wikipedia": "https://en.wikipedia.org/wiki/Deadline_Hollywood",
        "owner_wikis": {"Jay Penske": "https://en.wikipedia.org/wiki/Jay_Penske"},
    },
    "statnews.com": {
        "display": "STAT News", "parent": "Boston Globe Media", "category": "wealthy_private", "bias": "center", "factuality": "high",
        "owners": ["John W. Henry"],
        "wikipedia": "https://en.wikipedia.org/wiki/STAT_News",
        "owner_wikis": {"John W. Henry": "https://en.wikipedia.org/wiki/John_W._Henry"},
    },
    "theonion.com": {
        "display": "The Onion", "parent": "Global Tetrahedron", "category": "wealthy_private", "bias": "satire", "factuality": "satire",
        "owners": ["Global Tetrahedron LLC"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Onion",
        "owner_wikis": {},
    },

    # ── Corporate ──
    "nytimes.com": {
        "display": "The New York Times", "parent": "The New York Times Company", "category": "corporate", "bias": "left-center", "factuality": "high",
        "owners": ["Ochs-Sulzberger family (controlling)", "Public shareholders (NYSE: NYT)"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_New_York_Times",
        "owner_wikis": {"Ochs-Sulzberger family (controlling)": "https://en.wikipedia.org/wiki/Ochs-Sulzberger_family"},
    },
    "reuters.com": {
        "display": "Reuters", "parent": "Thomson Reuters", "category": "corporate", "bias": "center", "factuality": "high",
        "owners": ["The Woodbridge Company (Thomson family)", "Public shareholders"],
        "wikipedia": "https://en.wikipedia.org/wiki/Thomson_Reuters",
        "owner_wikis": {"The Woodbridge Company (Thomson family)": "https://en.wikipedia.org/wiki/Woodbridge_Company"},
    },
    "ft.com": {
        "display": "Financial Times", "parent": "Financial Times", "category": "corporate", "bias": "center", "factuality": "high",
        "owners": ["Nikkei Inc."],
        "wikipedia": "https://en.wikipedia.org/wiki/Financial_Times",
        "owner_wikis": {"Nikkei Inc.": "https://en.wikipedia.org/wiki/Nikkei,_Inc."},
    },
    "economist.com": {
        "display": "The Economist", "parent": "The Economist Group", "category": "corporate", "bias": "center", "factuality": "high",
        "owners": ["Pearson plc (50%)", "The Rothschild family"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Economist",
        "owner_wikis": {
            "Pearson plc (50%)": "https://en.wikipedia.org/wiki/Pearson_plc",
            "The Rothschild family": "https://en.wikipedia.org/wiki/Rothschild_family",
        },
    },
    "therecord.media": {
        "display": "The Record", "parent": "Recorded Future", "category": "corporate", "bias": "center", "factuality": "high",
        "owners": ["Mastercard"],
        "wikipedia": "https://en.wikipedia.org/wiki/Recorded_Future",
        "owner_wikis": {"Mastercard": "https://en.wikipedia.org/wiki/Mastercard"},
    },

    # ── Independent ──
    "theguardian.com": {
        "display": "The Guardian", "parent": "Guardian Media Group", "category": "independent", "bias": "left-center", "factuality": "high",
        "owners": ["Scott Trust Limited (no shareholders, protects editorial independence)"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Guardian",
        "owner_wikis": {"Scott Trust Limited (no shareholders, protects editorial independence)": "https://en.wikipedia.org/wiki/Scott_Trust_Limited"},
    },
    "apnews.com": {
        "display": "Associated Press", "parent": "Associated Press", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Member newspapers (cooperative, non-profit)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Associated_Press",
        "owner_wikis": {},
    },
    "science.org": {
        "display": "Science (AAAS)", "parent": "American Association for the Advancement of Science", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["AAAS membership (non-profit scientific society)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Science_(journal)",
        "owner_wikis": {},
    },
    "krebsonsecurity.com": {
        "display": "Krebs on Security", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Brian Krebs (independent journalist)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Krebs_on_Security",
        "owner_wikis": {"Brian Krebs (independent journalist)": "https://en.wikipedia.org/wiki/Brian_Krebs"},
    },
    "bleepingcomputer.com": {
        "display": "BleepingComputer", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Lawrence Abrams (founder)"],
        "wikipedia": "https://en.wikipedia.org/wiki/BleepingComputer",
        "owner_wikis": {},
    },
    "threatpost.com": {
        "display": "Threatpost", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Independent editorial team"],
        "wikipedia": "",
        "owner_wikis": {},
    },
    "thehackernews.com": {
        "display": "The Hacker News", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Independent editorial team"],
        "wikipedia": "",
        "owner_wikis": {},
    },
    "thedailymash.co.uk": {
        "display": "Daily Mash", "parent": "Independent", "category": "independent", "bias": "satire", "factuality": "satire",
        "owners": ["Neil Rafferty (founder)"],
        "wikipedia": "https://en.wikipedia.org/wiki/The_Daily_Mash",
        "owner_wikis": {},
    },
    "babylonbee.com": {
        "display": "Babylon Bee", "parent": "Independent", "category": "independent", "bias": "satire", "factuality": "satire",
        "owners": ["Seth Dillon (CEO)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Babylon_Bee",
        "owner_wikis": {},
    },
    "sciencedaily.com": {
        "display": "ScienceDaily", "parent": "ScienceDaily LLC", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Dan Hogan (founder)"],
        "wikipedia": "https://en.wikipedia.org/wiki/ScienceDaily",
        "owner_wikis": {},
    },
    "sciencenews.org": {
        "display": "Science News", "parent": "Society for Science", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Society for Science (non-profit)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Science_News",
        "owner_wikis": {"Society for Science (non-profit)": "https://en.wikipedia.org/wiki/Society_for_Science"},
    },
    "medscape.com": {
        "display": "Medscape", "parent": "WebMD Health Corp", "category": "corporate", "bias": "center", "factuality": "high",
        "owners": ["Internet Brands (KKR & Co.)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Medscape",
        "owner_wikis": {"Internet Brands (KKR & Co.)": "https://en.wikipedia.org/wiki/Internet_Brands"},
    },
    "nih.gov": {
        "display": "National Institutes of Health", "parent": "U.S. Department of Health and Human Services", "category": "government", "bias": "center", "factuality": "high",
        "owners": ["U.S. Federal Government"],
        "wikipedia": "https://en.wikipedia.org/wiki/National_Institutes_of_Health",
        "owner_wikis": {"U.S. Federal Government": "https://en.wikipedia.org/wiki/Federal_Government_of_the_United_States"},
    },
    "news.harvard.edu": {
        "display": "Harvard Gazette", "parent": "Harvard University", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Harvard University (non-profit educational institution)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Harvard_Gazette",
        "owner_wikis": {"Harvard University (non-profit educational institution)": "https://en.wikipedia.org/wiki/Harvard_University"},
    },
    "middleeasteye.net": {
        "display": "Middle East Eye", "parent": "Independent", "category": "independent", "bias": "left-center", "factuality": "mixed",
        "owners": ["Independent (London-based, reader-supported)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Middle_East_Eye",
        "owner_wikis": {},
    },
    "newarab.com": {
        "display": "The New Arab", "parent": "Fikra Publishing", "category": "independent", "bias": "left-center", "factuality": "mixed",
        "owners": ["Fikra Publishing Ltd."],
        "wikipedia": "https://en.wikipedia.org/wiki/The_New_Arab",
        "owner_wikis": {},
    },
    "tunisiaonlinenews.com": {
        "display": "Tunisia Online News", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "mixed",
        "owners": ["Independent editorial team"],
        "wikipedia": "",
        "owner_wikis": {},
    },
    "northafricapost.com": {
        "display": "North Africa Post", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "mixed",
        "owners": ["Independent editorial team"],
        "wikipedia": "",
        "owner_wikis": {},
    },
    "africanews.com": {
        "display": "Africa News", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "high",
        "owners": ["Independent (NGO-funded)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Africa_News",
        "owner_wikis": {},
    },
    "nawaat.org": {
        "display": "Nawaat", "parent": "Independent", "category": "independent", "bias": "left-center", "factuality": "high",
        "owners": ["Independent editorial team (Tunisia-based, reader-supported)"],
        "wikipedia": "https://en.wikipedia.org/wiki/Nawaat",
        "owner_wikis": {},
    },
    "tunisienumerique.com": {
        "display": "Tunisie Numérique", "parent": "Independent", "category": "independent", "bias": "center", "factuality": "mixed",
        "owners": ["A. Ben Hassan (founder)"],
        "wikipedia": "",
        "owner_wikis": {},
    },
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

# Build outlet names from SPONSOR_INFO for sourcing detection
_OUTLET_NAMES = sorted(
    set(
        v["display"].split(" (")[0]  # "Wired (Condé Nast)" → "Wired"
        for v in SPONSOR_INFO.values()
    ),
    key=len, reverse=True,  # longest first to match "The New York Times" before "The"
)
SOURCING_PATTERNS = [
    rf"\baccording to (?:a[n]?\s+)?{re.escape(name)}\b" for name in _OUTLET_NAMES
] + [
    rf"\b{re.escape(name)}\s+(?:reported|reports|writes|notes|noted|broke the story)\b" for name in _OUTLET_NAMES
] + [
    rf"\bin a\s+(?:recent\s+)?{re.escape(name)}\s+(?:article|story|report|investigation)\b" for name in _OUTLET_NAMES
]

LEFT_KEYWORDS = ["progressive", "equality", "social justice", "climate crisis",
                 "marginalized", "systemic", "privilege", "inequality",
                 "lgbt", "lgbtq", "gay", "lesbian", "transgender", "queer",
                 "civil rights", "voting rights", "reproductive rights",
                 "abortion", "workers' rights", "unionize", "unionizing",
                 "woke", "diversity", "inclusion", "equity",
                 "feminism", "feminist", "misogyny", "patriarchy",
                 "racism", "racial justice", "police brutality",
                 "wealth tax", "universal healthcare", "green new deal",
                 "income inequality", "living wage", "minimum wage",
                 "decolonize", "antisemitism", "islamophobia",
                 "environmental justice", "disability rights"]
RIGHT_KEYWORDS = ["deregulation", "tax cuts", "free market", "traditional",
                  "sovereignty", "patriot", "heritage", "small government",
                  "law and order", "border security", "illegal immigration",
                  "religious freedom", "family values", "pro-life",
                  "second amendment", "gun rights", "school choice",
                  "fiscal conservative", "limited government",
                  "meritocracy", "personal responsibility",
                  "drain the swamp", "deep state", "woke agenda",
                  "critical race theory", "cancel culture",
                  "mass deportation", "america first",
                  "nationalism", "populism", "constitutional conservative"]

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
                   r"\bdigital\b", r"\bcloud\b", r"\bdevice\b", r"\bsmart\b",
                   r"\bIoT\b", r"\bOS\b", r"\bWindows\b", r"\bAndroid\b", r"\biOS\b",
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

    @staticmethod
    def _detect_sponsor(article: Article) -> dict:
        domain = re.sub(r"^www\.", "", (article.source_domain or ""))
        info = SPONSOR_INFO.get(domain)
        if info:
            return dict(info)
        return {"display": "", "parent": "", "category": "", "bias": "", "factuality": "", "owners": [], "owner_wikis": {}}

    def _detect_article_leaning(self, text: str) -> str:
        text_lower = text.lower()
        left = sum(1 for k in LEFT_KEYWORDS if k in text_lower)
        right = sum(1 for k in RIGHT_KEYWORDS if k in text_lower)
        diff = left - right
        if diff >= 2:
            return "left"
        if diff >= 1:
            return "left-center"
        if right - left >= 2:
            return "right"
        if right - left >= 1:
            return "right-center"
        return "center"

    @staticmethod
    def _detect_sourced_content(text: str) -> float:
        if not text:
            return 0.0
        count = sum(1 for p in SOURCING_PATTERNS if re.search(p, text, re.IGNORECASE))
        if count >= 3:
            return 0.40
        if count >= 2:
            return 0.25
        if count >= 1:
            return 0.15
        return 0.0

    def analyze(self, article: Article) -> Analysis:
        summary = self._summarise(article)
        topics = self._classify_topics(article, summary)
        trust = self._assess_trustworthiness(article)
        is_opinion = self._detect_opinion(article.text or "")
        sourcing_penalty = self._detect_sourced_content(article.text or "")

        sponsor = self._detect_sponsor(article)
        source_bias = sponsor.get("bias", "")
        source_factuality = sponsor.get("factuality", "")
        article_leaning = self._detect_article_leaning(article.text or "")

        category = self._map_category(topics)

        return Analysis(
            summary=summary,
            topics=topics,
            trustworthiness_score=trust,
            is_opinion=is_opinion,
            political_leaning=article_leaning,
            category=category,
            sponsor=sponsor,
            source_bias=source_bias,
            source_factuality=source_factuality,
            article_leaning=article_leaning,
            sourcing_penalty=sourcing_penalty,
        )

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
        "nawaat.org": "tunisia",
        "tunisienumerique.com": "tunisia",
        "sciencenews.org": "health",
        "medscape.com": "health",
        "nih.gov": "health",
        "news.harvard.edu": "health",
    }

    def _keyword_topic_match(self, article: Article, summary: str) -> list[str]:
        text = f"{article.title} {summary}" if summary else article.title
        found = []
        for topic, patterns in TOPIC_MAP.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                found.append(topic)
        domain = re.sub(r"^www\.", "", (article.source_domain or ""))
        mapped = self.DOMAIN_TOPICS.get(domain)
        # Only use domain fallback if keyword matching found nothing
        if mapped and mapped not in found:
            if not found:
                found.append(mapped)
        return found

    def _assess_trustworthiness(self, article: Article) -> float:
        score = 0.40

        domain = article.source_domain or ""
        clean_domain = re.sub(r"^www\.", "", domain)
        score += RELIABLE_DOMAINS.get(clean_domain, 0.0)
        score += UNRELIABLE_DOMAINS.get(clean_domain, 0.0)

        text = article.text or ""
        title = article.title or ""
        if article.extraction_success is False:
            score -= 0.15
        elif len(text) > len(title) * 3:
            score += 0.05

        word_count = len(text.split())
        if word_count > 200:
            score += 0.10
        elif word_count > 100:
            score += 0.05
        elif word_count > 50:
            score += 0.02

        factual_count = sum(1 for p in FACTUAL_KEYWORDS if re.search(p, text, re.IGNORECASE))
        score += min(factual_count * 0.02, 0.08)

        if any(re.search(p, title, re.IGNORECASE) for p in CLICKBAIT_PATTERNS):
            score -= 0.20

        opinion_count = sum(1 for p in OPINION_MARKERS if re.search(p, text, re.IGNORECASE))
        score -= opinion_count * 0.05

        return max(0.05, min(1.0, score))

    @staticmethod
    def _map_category(topics: list[str]) -> str:
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

    @staticmethod
    def _detect_opinion(text: str) -> bool:
        count = sum(1 for p in OPINION_MARKERS if re.search(p, text.lower()))
        return count >= 3
