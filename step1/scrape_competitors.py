#!/usr/bin/env python3
"""
Blockchain.com Competitor Scraper
Scrapes Google Play Store for crypto competitor apps + US financial institutions.
Outputs: blockchain_competitors.csv
"""

import csv
import json
import os
import random
import re
import sys
import time
import traceback
from collections import OrderedDict
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

# ── Constants ──────────────────────────────────────────────────────────────
TARGET_CRYPTO = 50
TARGET_FI = 10
MAX_DEPTH = 3
SELF_PKG = "com.blockchain.android"
BASE = "https://play.google.com"
SEARCH_URL = f"{BASE}/store/search?q=blockchain.com&c=apps&gl=US"
APP_URL = lambda pkg: f"{BASE}/store/apps/details?id={pkg}&gl=US"
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blockchain_competitors.csv")

HEADERS = [
    "#", "app_name", "category", "developer", "play_store_package_id",
    "key_features", "positioning_vs_blockchain"
]

# Category keywords for auto-classification
CATEGORY_HINTS = {
    "Self-Custody Wallet": ["self-custody", "non-custodial", "seed phrase", "private key", "your keys", "decentralized wallet"],
    "Centralized Exchange (CEX)": ["exchange", "buy and sell", "trading platform", "cex", "order book"],
    "DeFi / DEX Wallet": ["defi", "dex", "decentralized exchange", "swap", "liquidity", "yield"],
    "Neo-bank with Crypto": ["bank", "debit card", "direct deposit", "neobank", "spending", "paycheck"],
    "Trading Terminal / Tracker": ["portfolio tracker", "price alert", "watchlist", "market data", "screener", "charting"],
}

# US Financial Institutions to append
US_FINANCIAL_INSTITUTIONS = [
    {"pkg": "com.chase.sig.android", "name": "Chase Mobile", "cat": "Traditional Bank"},
    {"pkg": "com.infonow.bofa", "name": "Bank of America", "cat": "Traditional Bank"},
    {"pkg": "com.wf.wellsfargomobile", "name": "Wells Fargo", "cat": "Traditional Bank"},
    {"pkg": "com.citi.citimobile", "name": "Citi Mobile", "cat": "Traditional Bank"},
    {"pkg": "com.schwab.mobile.charles", "name": "Schwab Mobile", "cat": "Brokerage / Wealth Management"},
    {"pkg": "com.fidelity.android", "name": "Fidelity Investments", "cat": "Brokerage / Wealth Management"},
    {"pkg": "com.vanguard", "name": "Vanguard", "cat": "Brokerage / Wealth Management"},
    {"pkg": "com.tdameritrade.mobi", "name": "TD Ameritrade", "cat": "Brokerage / Wealth Management"},
    {"pkg": "com.usaa.mobile.android.usaa", "name": "USAA", "cat": "Insurance / Financial Services"},
    {"pkg": "com.americanexpress.android.acctsvcs.us", "name": "Amex", "cat": "Insurance / Financial Services"},
]


# ── Helpers ────────────────────────────────────────────────────────────────
def delay():
    time.sleep(random.uniform(1.0, 3.0))


def classify_category(desc):
    desc_lower = (desc or "").lower()
    scores = {}
    for cat, keywords in CATEGORY_HINTS.items():
        scores[cat] = sum(1 for kw in keywords if kw in desc_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other / Hybrid"


def extract_features(desc, max_features=5):
    """Pull 3-5 standout features from description text."""
    if not desc:
        return ""
    feature_keywords = [
        "self-custody", "non-custodial", "custodial", "DeFi", "NFT", "staking",
        "earn", "swap", "dex", "lending", "borrowing", "credit card", "debit card",
        "bank transfer", "wire transfer", "ACH", "FDIC", "insured", "margin",
        "futures", "options", "leverage", "copy trading", "social trading",
        "portfolio tracker", "price alerts", "watchlist", "recurring buy",
        "100+ coins", "200+ coins", "300+ coins", "500+ coins", "1000+ tokens",
        "biometric", "2FA", "multi-sig", "hardware wallet", "cold storage",
        "seedless", "MPC", "passkey", "limit order", "stop loss",
        "instant buy", "P2P", "OTC", "web3", "dApp browser", "WalletConnect",
        "bitcoin", "ethereum", "solana", "multi-chain", "layer 2",
        "rewards", "cashback", "interest", "yield", "APY",
        "mobile check deposit", "direct deposit", "bill pay", "investment accounts",
    ]
    desc_lower = desc.lower()
    found = []
    for kw in feature_keywords:
        if kw.lower() in desc_lower and kw not in found:
            found.append(kw)
            if len(found) >= max_features:
                break
    if len(found) < 3:
        # Fallback: extract first few sentences as features
        sentences = re.split(r'[.!?\n]', desc)
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and len(s) < 80:
                found.append(s)
                if len(found) >= max_features:
                    break
    return ", ".join(found[:max_features])


def positioning_summary(app_name, desc, category):
    """Generate a 1-line positioning vs Blockchain.com."""
    desc_lower = (desc or "").lower()
    traits = []

    if "custod" in desc_lower and "non-custod" not in desc_lower and "self-custod" not in desc_lower:
        traits.append("custodial model")
    elif "self-custod" in desc_lower or "non-custod" in desc_lower:
        traits.append("self-custody focus")

    if any(w in desc_lower for w in ["beginner", "simple", "easy", "first crypto"]):
        traits.append("beginner-friendly")
    if any(w in desc_lower for w in ["advanced", "pro", "trader", "margin", "futures"]):
        traits.append("advanced trading features")
    if any(w in desc_lower for w in ["defi", "dapp", "web3", "decentralized"]):
        traits.append("DeFi/Web3 emphasis")
    if any(w in desc_lower for w in ["bank", "debit card", "direct deposit", "paycheck"]):
        traits.append("banking integration")
    if any(w in desc_lower for w in ["social", "copy trading", "community"]):
        traits.append("social/copy trading")
    if any(w in desc_lower for w in ["nft", "collectible"]):
        traits.append("NFT support")

    if not traits:
        traits.append("general crypto app")

    return f"{app_name}: {', '.join(traits)}"


# ── Scraping Functions ─────────────────────────────────────────────────────

def scrape_app_cards(page):
    """Extract app package IDs from a list/grid of app cards on the current page."""
    apps = []
    try:
        # Wait for any app links to appear
        page.wait_for_selector('a[href*="/store/apps/details?id="]', timeout=8000)
    except PwTimeout:
        return apps

    links = page.query_selector_all('a[href*="/store/apps/details?id="]')
    for link in links:
        href = link.get_attribute("href") or ""
        match = re.search(r'id=([a-zA-Z0-9._]+)', href)
        if match:
            pkg = match.group(1)
            # Try to get app name from the card
            name = ""
            try:
                # Try multiple selectors for the app name within the card
                name_el = link.query_selector('span, div[style*="line-clamp"]')
                if name_el:
                    name = name_el.inner_text().strip()
            except:
                pass
            if not name:
                name = pkg
            apps.append({"pkg": pkg, "name": name})
    return apps


def scrape_search_results(page):
    """Scrape apps from the Play Store search results page."""
    print("\n[SEARCH] Scraping search results for 'blockchain.com'...")
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
    delay()

    # Scroll to load more results
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

    apps = scrape_app_cards(page)
    print(f"  Found {len(apps)} apps in search results")
    return apps


def scrape_app_detail(page, pkg, retries=3):
    """Scrape a single app's detail page for description, developer, etc."""
    for attempt in range(retries):
        try:
            url = APP_URL(pkg)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            delay()

            info = {"pkg": pkg, "name": "", "developer": "", "description": ""}

            # App name
            try:
                name_el = page.query_selector('h1[itemprop="name"], h1')
                if name_el:
                    info["name"] = name_el.inner_text().strip()
            except:
                pass

            # Developer
            try:
                # Try multiple selectors for developer
                dev_el = page.query_selector('a[href*="/store/apps/dev"], div[class*="developer"] a')
                if dev_el:
                    info["developer"] = dev_el.inner_text().strip()
                else:
                    # Try the second link/text near the title
                    dev_links = page.query_selector_all('a[href*="/store/apps/dev"]')
                    if dev_links:
                        info["developer"] = dev_links[0].inner_text().strip()
            except:
                pass

            # Description - try expanding it first
            try:
                # Click "About this app" or expand button if present
                expand_btns = page.query_selector_all('button:has-text("About this"), [data-g-id="description"] button')
                for btn in expand_btns:
                    try:
                        btn.click()
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass

            try:
                desc_el = page.query_selector('[data-g-id="description"], [itemprop="description"], div[class*="description"]')
                if desc_el:
                    info["description"] = desc_el.inner_text().strip()[:3000]
            except:
                pass

            # If no description, try the meta tag
            if not info["description"]:
                try:
                    meta = page.query_selector('meta[name="description"]')
                    if meta:
                        info["description"] = meta.get_attribute("content") or ""
                except:
                    pass

            return info

        except Exception as e:
            print(f"    Retry {attempt+1}/{retries} for {pkg}: {e}")
            delay()

    return {"pkg": pkg, "name": pkg, "developer": "", "description": ""}


def scrape_similar_apps(page, pkg):
    """From an app's detail page, scrape 'Similar apps' and 'Users also installed'."""
    similar = []
    try:
        url = APP_URL(pkg)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        delay()

        # Scroll down to load similar sections
        for _ in range(4):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        # Find all sections that might contain similar/related apps
        similar = scrape_app_cards(page)

    except Exception as e:
        print(f"    Error scraping similar apps for {pkg}: {e}")

    return similar


def scrape_additional_search_terms(page, terms):
    """Search for additional terms to find more competitors."""
    all_apps = []
    for term in terms:
        print(f"\n[SEARCH] Scraping search results for '{term}'...")
        try:
            search_url = f"{BASE}/store/search?q={term.replace(' ', '+')}&c=apps&gl=US"
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            delay()

            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            apps = scrape_app_cards(page)
            print(f"  Found {len(apps)} apps for '{term}'")
            all_apps.extend(apps)
        except Exception as e:
            print(f"  Error searching '{term}': {e}")
    return all_apps


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Blockchain.com Competitor Scraper")
    print("=" * 60)

    # Collected apps: pkg -> {name, developer, description, ...}
    collected = OrderedDict()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        # ── Phase 1: Search results ──
        search_apps = scrape_search_results(page)
        for app in search_apps:
            pkg = app["pkg"]
            if pkg != SELF_PKG and pkg not in collected:
                collected[pkg] = {"name": app["name"]}
                print(f"  [{len(collected)}/{TARGET_CRYPTO}] Found: {app['name']} — {pkg}")

        # ── Phase 2: Similar apps from Blockchain.com's page ──
        print(f"\n[SIMILAR] Scraping similar/related apps from Blockchain.com's page...")
        similar = scrape_similar_apps(page, SELF_PKG)
        for app in similar:
            pkg = app["pkg"]
            if pkg != SELF_PKG and pkg not in collected:
                collected[pkg] = {"name": app["name"]}
                print(f"  [{len(collected)}/{TARGET_CRYPTO}] Found: {app['name']} — {pkg}")

        # ── Phase 3: Additional search terms to broaden results ──
        if len(collected) < TARGET_CRYPTO:
            extra_terms = [
                "crypto wallet",
                "bitcoin wallet",
                "crypto exchange",
                "defi wallet",
                "buy bitcoin",
                "cryptocurrency trading",
                "web3 wallet",
                "nft wallet",
            ]
            extra_apps = scrape_additional_search_terms(page, extra_terms)
            for app in extra_apps:
                pkg = app["pkg"]
                if pkg != SELF_PKG and pkg not in collected:
                    collected[pkg] = {"name": app["name"]}
                    print(f"  [{len(collected)}/{TARGET_CRYPTO}] Found: {app['name']} — {pkg}")
                    if len(collected) >= TARGET_CRYPTO:
                        break

        # ── Phase 4: BFS on collected apps' similar sections (up to depth 3) ──
        if len(collected) < TARGET_CRYPTO:
            print(f"\n[BFS] Need {TARGET_CRYPTO - len(collected)} more apps, starting BFS crawl...")
            bfs_queue = list(collected.keys())[:20]  # Start with first 20
            visited_for_similar = set()
            depth = 0

            while len(collected) < TARGET_CRYPTO and depth < MAX_DEPTH and bfs_queue:
                depth += 1
                print(f"\n  [BFS Depth {depth}] Visiting {len(bfs_queue)} app pages...")
                next_queue = []

                for pkg in bfs_queue:
                    if pkg in visited_for_similar:
                        continue
                    visited_for_similar.add(pkg)

                    sim_apps = scrape_similar_apps(page, pkg)
                    for app in sim_apps:
                        apkg = app["pkg"]
                        if apkg != SELF_PKG and apkg not in collected:
                            collected[apkg] = {"name": app["name"]}
                            next_queue.append(apkg)
                            print(f"  [{len(collected)}/{TARGET_CRYPTO}] Found: {app['name']} — {apkg}")
                            if len(collected) >= TARGET_CRYPTO:
                                break

                    if len(collected) >= TARGET_CRYPTO:
                        break

                bfs_queue = next_queue[:15]

        # Trim to exactly TARGET_CRYPTO
        crypto_pkgs = list(collected.keys())[:TARGET_CRYPTO]

        # ── Phase 5: Get detailed info for each crypto app ──
        print(f"\n[DETAIL] Fetching details for {len(crypto_pkgs)} crypto apps...")
        crypto_rows = []
        for i, pkg in enumerate(crypto_pkgs):
            print(f"  [{i+1}/{len(crypto_pkgs)}] Fetching: {pkg}")
            info = scrape_app_detail(page, pkg)

            name = info["name"] or collected[pkg].get("name", pkg)
            desc = info["description"]
            cat = classify_category(desc)
            features = extract_features(desc)
            positioning = positioning_summary(name, desc, cat)

            crypto_rows.append({
                "#": i + 1,
                "app_name": name,
                "category": cat,
                "developer": info["developer"],
                "play_store_package_id": pkg,
                "key_features": features,
                "positioning_vs_blockchain": positioning,
            })

        # ── Phase 6: US Financial Institutions ──
        print(f"\n[FI] Fetching details for {TARGET_FI} US financial institutions...")
        fi_rows = []
        for i, fi in enumerate(US_FINANCIAL_INSTITUTIONS[:TARGET_FI]):
            print(f"  [{i+1}/{TARGET_FI}] Fetching: {fi['pkg']}")
            info = scrape_app_detail(page, fi["pkg"])

            name = info["name"] or fi["name"]
            desc = info["description"]
            features = extract_features(desc)

            # Custom positioning for FI
            desc_lower = (desc or "").lower()
            fi_traits = []
            if any(w in desc_lower for w in ["fdic", "insured"]):
                fi_traits.append("FDIC insured")
            if any(w in desc_lower for w in ["crypto", "bitcoin", "digital asset"]):
                fi_traits.append("offers some crypto exposure")
            else:
                fi_traits.append("no crypto offering")
            fi_traits.append("legacy brand trust")
            fi_traits.append("same security-conscious demographic")
            pos = f"{name}: {', '.join(fi_traits)}"

            fi_rows.append({
                "#": TARGET_CRYPTO + i + 1,
                "app_name": name,
                "category": fi["cat"],
                "developer": info["developer"],
                "play_store_package_id": fi["pkg"],
                "key_features": features,
                "positioning_vs_blockchain": pos,
            })

        browser.close()

    # ── Write CSV ──────────────────────────────────────────────────────────
    all_rows = crypto_rows + fi_rows
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n" + "=" * 60)
    print(f"DONE! Total apps: {len(all_rows)}")
    print(f"  Crypto competitors: {len(crypto_rows)}")
    print(f"  Financial institutions: {len(fi_rows)}")
    print(f"  Output: {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
