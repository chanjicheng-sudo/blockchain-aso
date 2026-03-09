#!/usr/bin/env python3
"""
Step 3: ASO Thematic Keyword Analysis
Reads competitor_metadata.docx from ../step2/, outputs keyword_analysis.csv
"""

import csv
import os
import re
from collections import Counter, defaultdict

from docx import Document

# ── Paths ──────────────────────────────────────────────────────────────────
STEP1_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "step1")
STEP2_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "step2")
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keyword_analysis.csv")

# ── Stopwords ──────────────────────────────────────────────────────────────
STOPWORDS = set(
    "the a an and or of to in for with your you our all is are by on at "
    "from more that this be can as its it we have their my new get use one "
    "over into also so any up not via has was been will let do no i me us "
    "them they he she its which who what when where how if but just about "
    "into out up down re ve ll s t d m".split()
)

# ── Theme classification keywords ─────────────────────────────────────────
# These seed words help assign tokens to themes discovered from the data.
THEME_SEEDS = {
    "Trading Actions": [
        "buy", "sell", "trade", "trading", "swap", "exchange", "convert",
        "order", "spot", "futures", "margin", "leverage", "limit",
        "options", "otc", "p2p", "orders",
        "buy sell", "buy bitcoin", "buy crypto", "sell crypto", "buy btc",
        "spot trading", "futures trading", "margin trading", "copy trading",
        "trade crypto", "trade bitcoin", "buy sell trade", "instant buy",
        "buy ethereum", "buy eth",
    ],
    "Asset Coverage": [
        "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto",
        "cryptocurrency", "token", "tokens", "coin", "coins", "altcoin",
        "altcoins", "digital", "assets", "digital assets", "doge", "xrp",
        "bnb", "usdt", "usdc", "litecoin", "ltc", "matic", "polygon",
        "meme", "meme coins", "crypto assets", "digital currency",
        "cryptocurrencies", "bitcoin btc", "bitcoin ethereum",
        "crypto bitcoin", "bitcoin crypto",
        "dogecoin", "tether", "ada", "ripple", "tron", "trx", "avax",
        "cardano", "shib", "pepe", "ton", "sui", "apt", "near",
        "stablecoin", "stablecoins", "currencies", "currency",
        "supported", "1000", "100", "200", "300", "500",
        "avalanche", "polkadot", "dot", "bch", "shiba", "inu",
        "shiba inu", "asset",
    ],
    "Custody & Storage": [
        "wallet", "wallets", "custody", "custodial", "non-custodial",
        "self-custody", "storage", "store", "hold", "holding", "vault",
        "cold", "hardware", "seed", "phrase", "backup", "recovery",
        "keys", "private", "private keys", "seed phrase", "cold storage",
        "crypto wallet", "bitcoin wallet", "secure wallet",
        "hardware wallet", "self custody", "address",
    ],
    "Earning & Yield": [
        "earn", "earning", "yield", "apy", "interest", "staking", "stake",
        "rewards", "passive", "income", "cashback", "bonus",
        "earn crypto", "earn rewards", "staking rewards", "passive income",
        "earn interest", "crypto rewards", "rates",
    ],
    "DeFi & Web3": [
        "defi", "dex", "dapp", "dapps", "web3", "decentralized",
        "decentralised", "protocol", "liquidity", "pool", "amm",
        "smart", "contract", "bridge", "layer", "chain", "multichain",
        "multi-chain", "nft", "nfts", "collectible", "collectibles",
        "blockchain", "onchain", "on-chain", "network", "networks",
        "smart contract", "nft wallet", "defi wallet", "web3 wallet",
        "decentralized finance", "crypto nft",
    ],
    "Security & Trust": [
        "secure", "security", "safe", "safety", "protect", "protected",
        "protection", "encrypt", "encrypted", "encryption", "biometric",
        "2fa", "authentication", "pin", "password", "trusted", "trust",
        "verified", "audit", "audited", "insured", "insurance", "fdic",
        "regulated", "regulation", "compliance", "kyc", "aml",
        "secure crypto", "trusted crypto", "safe secure",
        "securely", "safely", "risk", "privacy", "email",
    ],
    "Usability & Experience": [
        "easy", "simple", "fast", "instant", "quick", "friendly",
        "beginner", "intuitive", "seamless", "smooth", "convenient",
        "powerful", "advanced", "pro", "professional",
        "easy use", "user friendly", "beginner friendly",
        "one app", "all one", "simple easy",
        "support", "easily", "instantly", "seamlessly", "experience",
        "features", "using", "enjoy", "customer", "service",
        "all-in-one", "designed", "effortlessly",
    ],
    "Payments & Banking": [
        "pay", "payment", "payments", "send", "receive", "transfer",
        "transfers", "deposit", "withdraw", "withdrawal", "bank", "banking",
        "card", "cards", "debit", "credit", "visa", "mastercard", "ach",
        "wire", "fiat", "usd", "dollar", "dollars", "money", "cash",
        "fees", "fee", "low fees", "zero fees", "no fees",
        "send receive", "bank transfer", "debit card", "credit card",
        "mobile banking", "send crypto", "transactions", "transaction",
    ],
    "Portfolio & Tracking": [
        "portfolio", "track", "tracker", "tracking", "monitor",
        "alert", "alerts", "notification", "notifications", "price",
        "prices", "chart", "charts", "market", "markets", "data",
        "watchlist", "news", "feed", "live", "tools",
        "price alert", "price alerts", "market data", "portfolio tracker",
        "crypto tracker", "live price", "real time", "real-time",
        "crypto market", "insights",
    ],
    "Identity & Brand Trust": [
        "million", "millions", "users", "trusted", "leading", "top",
        "best", "popular", "rated", "reviews", "global", "worldwide",
        "countries", "platform", "app", "official", "brand",
        "million users", "trusted platform", "leading crypto",
        "crypto app", "crypto platform", "world", "binance",
    ],
    "Account & Finance": [
        "account", "accounts", "invest", "investing", "investment",
        "investments", "savings", "save", "retire", "retirement",
        "ira", "brokerage", "wealth", "financial", "finance",
        "stock", "stocks", "fund", "funds", "etf", "management",
        "investment accounts", "checking account",
        "mobile check", "bill pay", "services", "products",
    ],
    "Multi-Platform & Access": [
        "mobile", "desktop", "browser", "extension", "download",
        "free", "available", "access", "connect", "login", "sign",
        "manage", "control", "explore", "discover", "device",
        "directly", "multiple", "place", "create", "set",
        "manage crypto", "explore crypto", "crypto exchange",
        "information", "view", "help",
        "anytime", "anywhere", "start", "join", "unlock",
    ],
}


def load_categories():
    """Load category labels from step1 CSV, keyed by app_name (lowercased)."""
    import glob
    pattern = os.path.join(STEP1_DIR, "*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        return {}
    cats = {}
    with open(files[0], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            name = row.get('app_name', '').strip()
            cat = row.get('category', '').strip()
            if name:
                cats[name.lower()] = cat
    return cats


def find_docx():
    """Find the competitor_metadata.docx in step2."""
    path = os.path.join(STEP2_DIR, "competitor_metadata.docx")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Not found: {path}")
    return path


def parse_docx(path):
    """Parse the docx into a list of app entries."""
    doc = Document(path)
    entries = []
    current = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text or text.startswith('─'):
            if text.startswith('─') and current:
                entries.append(current)
                current = None
            continue

        # Check for title (14pt bold dark blue)
        if para.runs:
            run = para.runs[0]
            if run.bold and run.font.size and run.font.size.pt >= 13:
                current = {'title': text, 'short_desc': '', 'long_desc': '', 'developer': '', 'tags': ''}
                continue

        if current is not None:
            if text.startswith('Developer:'):
                current['developer'] = text.replace('Developer:', '', 1).strip()
            elif text.startswith('Tags:'):
                current['tags'] = text.replace('Tags:', '', 1).strip()
            elif text.startswith('Short Description:'):
                current['short_desc'] = text.replace('Short Description:', '', 1).strip()
            else:
                if current['long_desc']:
                    current['long_desc'] += '\n' + text
                else:
                    current['long_desc'] = text

    # Catch last entry if no trailing separator
    if current and current.get('title'):
        entries.append(current)

    return entries


def match_category(app_title, category_map):
    """Match an app title to its category from step1 CSV."""
    title_lower = app_title.lower()
    # Try exact match first
    if title_lower in category_map:
        return category_map[title_lower]
    # Try substring match (Play Store titles may differ slightly from CSV)
    for csv_name, cat in category_map.items():
        # Match if one contains the other, or first word matches
        if csv_name in title_lower or title_lower in csv_name:
            return cat
        # Match on first significant word
        csv_first = csv_name.split(':')[0].split('-')[0].strip()
        title_first = title_lower.split(':')[0].split('-')[0].strip()
        if csv_first == title_first and len(csv_first) > 3:
            return cat
    return ""


def tokenise(text):
    """Extract unigrams and bigrams from text, filtering stopwords."""
    if not text:
        return [], []

    text = text.lower()
    text = re.sub(r'[^\w\s\-]', ' ', text)
    words = [w for w in text.split() if w and w not in STOPWORDS and len(w) > 1]

    unigrams = list(set(words))
    bigrams = list(set(f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)))

    return unigrams, bigrams


def classify_theme(token):
    """Assign a token to its best-fit theme."""
    token_lower = token.lower()
    best_theme = None
    best_score = 0

    for theme, seeds in THEME_SEEDS.items():
        # Exact match
        if token_lower in [s.lower() for s in seeds]:
            return theme
        # Partial match
        token_words = set(token_lower.split())
        for seed in seeds:
            seed_words = set(seed.lower().split())
            overlap = token_words & seed_words
            if overlap:
                s = len(overlap) / max(len(token_words), len(seed_words))
                if s > best_score:
                    best_score = s
                    best_theme = theme

    return best_theme if best_theme else None


def main():
    print("=" * 60)
    print("Step 3: ASO Keyword Analysis")
    print("=" * 60)

    # Load category labels from step1
    category_map = load_categories()
    print(f"\nLoaded {len(category_map)} category labels from step1")

    # Parse docx
    docx_path = find_docx()
    print(f"Reading: {docx_path}")
    entries = parse_docx(docx_path)
    print(f"Parsed {len(entries)} app entries")

    # Attach categories to all entries (including Blockchain.com)
    BC_CATEGORY = "Centralized Exchange (CEX)"
    competitors = []
    for e in entries:
        title_lower = e['title'].lower()
        if 'blockchain wallet' in title_lower or 'blockchain.com' in title_lower:
            e['category'] = BC_CATEGORY
            print(f"TARGET: {e['title']} → {BC_CATEGORY}")
        else:
            e['category'] = match_category(e['title'], category_map)
        competitors.append(e)

    print(f"Total apps (incl. Blockchain.com): {len(competitors)}")

    # ── Tokenise all competitors ───────────────────────────────────────────
    # Track which app indices contain each token, per field
    token_title = defaultdict(set)
    token_short = defaultdict(set)
    token_long = defaultdict(set)
    token_tags = defaultdict(set)
    token_any = defaultdict(set)
    token_type = {}

    for idx, comp in enumerate(competitors):
        for field, tracker in [
            ('title', token_title),
            ('short_desc', token_short),
            ('long_desc', token_long),
            ('tags', token_tags),
        ]:
            unigrams, bigrams = tokenise(comp.get(field, ''))
            for u in unigrams:
                tracker[u].add(idx)
                token_any[u].add(idx)
                token_type[u] = "unigram"
            for b in bigrams:
                tracker[b].add(idx)
                token_any[b].add(idx)
                token_type[b] = "bigram"

    # ── Apply frequency threshold ──────────────────────────────────────────
    num_competitors = len(competitors)
    min_freq = max(2, int(num_competitors * 0.03))
    print(f"Minimum frequency threshold: {min_freq} apps")

    qualified_tokens = {
        t for t, apps in token_any.items() if len(apps) >= min_freq
    }
    print(f"Tokens passing threshold: {len(qualified_tokens)}")

    # ── Classify themes ────────────────────────────────────────────────────
    themed_tokens = {}
    unthemed = 0
    for token in qualified_tokens:
        theme = classify_theme(token)
        if theme:
            themed_tokens[token] = theme
        else:
            unthemed += 1

    print(f"Themed tokens: {len(themed_tokens)}, Discarded (no theme): {unthemed}")

    # ── Compute per-keyword stats ────────────────────────────────────────
    table_stakes_threshold = num_competitors * 0.6

    keyword_stats = {}
    for token, theme in themed_tokens.items():
        title_indices = token_title.get(token, set())
        short_indices = token_short.get(token, set())
        long_indices = token_long.get(token, set())
        tags_indices = token_tags.get(token, set())
        any_indices = token_any.get(token, set())

        reach = len(any_indices)
        table_stakes = reach > table_stakes_threshold

        keyword_stats[token] = {
            'theme': theme,
            'table_stakes': table_stakes,
            'title_indices': title_indices,
            'short_indices': short_indices,
            'long_indices': long_indices,
            'tags_indices': tags_indices,
            'any_indices': any_indices,
        }

    # ── Build rows: one row per keyword × app ──────────────────────────────
    rows = []

    for token, stats in keyword_stats.items():
        for idx in sorted(stats['any_indices']):
            comp = competitors[idx]
            app_name = comp['title']
            category = comp.get('category', '')

            rows.append({
                'keyword': token,
                'type': token_type[token],
                'theme': stats['theme'],
                'app_name': app_name,
                'category': category,
                'in_title': 1 if idx in stats['title_indices'] else 0,
                'in_short': 1 if idx in stats['short_indices'] else 0,
                'in_long': 1 if idx in stats['long_indices'] else 0,
                'in_tags': 1 if idx in stats['tags_indices'] else 0,
                'reach': len(stats['any_indices']),
                'table_stakes': 'TRUE' if stats['table_stakes'] else 'FALSE',
            })

    # Sort by reach desc, then keyword, then app_name
    rows.sort(key=lambda r: (-r['reach'], r['keyword'], r['app_name']))

    # ── Write CSV ──────────────────────────────────────────────────────────
    fieldnames = [
        'keyword', 'type', 'theme',
        'app_name', 'category',
        'in_title', 'in_short', 'in_long', 'in_tags',
        'reach', 'table_stakes',
    ]

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # ── Summary ────────────────────────────────────────────────────────────
    unique_keywords = len(keyword_stats)
    theme_counts = Counter(s['theme'] for s in keyword_stats.values())
    ts_count = sum(1 for s in keyword_stats.values() if s['table_stakes'])

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Unique keywords: {unique_keywords}")
    print(f"Total rows (keyword × app): {len(rows)}")
    print(f"Table-stakes keywords: {ts_count}")
    print(f"\nThemes ({len(theme_counts)}):")
    for theme, count in theme_counts.most_common():
        print(f"  {theme}: {count} keywords")
    print(f"\nOutput: {OUTPUT}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
