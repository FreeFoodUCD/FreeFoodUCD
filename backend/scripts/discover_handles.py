"""
Discovery utility: scrape ucdsocieties.ie to find Instagram handles for all UCD societies.

Usage:
    cd backend && python scripts/discover_handles.py

Output:
    One line per discovered handle: <handle>  <society-slug>
    A summary of handles already in admin.py's seed list is printed at the end.
"""

import asyncio
import re
import sys

import httpx

SOCIETIES_URL = "https://ucdsocieties.ie/societies/"
BASE_DOMAIN = "https://ucdsocieties.ie"

# Current handles already seeded (from admin.py) — used to flag new ones
EXISTING_HANDLES = {
    "ucdmechsoc",
    "ucdindsoc",
    "ucd.aclsoc",
    "ucdpolsoc",
    "ucdengsoc",
    "ucdjsoc",
    "ucdmsoc",
    "ucdisoc",
    "ucdfrenchsoc",
    "ucdmathsoc",
    "ucdmedsoc",
    "ucdvnsoc",
    "ucdlawsoc",
    "ucdsocscistudents",
    "ucdfilmsoc",
    "ucdgamesociety",
    "ucdscisoc",
    "ucdchemengsoc",
    "ucd.elecsoc",
    "ucdafricasociety",
    "ucdfoodsoc",
    "ucddancesoc",
}

# Slugs to skip — not actual society pages
SKIP_SLUGS = {
    SOCIETIES_URL,
    BASE_DOMAIN + "/",
    BASE_DOMAIN + "/societies/",
    BASE_DOMAIN + "/contact/",
    BASE_DOMAIN + "/about/",
    BASE_DOMAIN + "/news/",
    BASE_DOMAIN + "/events/",
    BASE_DOMAIN + "/resources/",
    BASE_DOMAIN + "/login/",
    BASE_DOMAIN + "/register/",
    BASE_DOMAIN + "/privacy-policy/",
    BASE_DOMAIN + "/terms-and-conditions/",
}


async def fetch_society_slugs(client: httpx.AsyncClient) -> list[str]:
    """Fetch the societies listing page and extract individual society page URLs."""
    print(f"Fetching societies listing: {SOCIETIES_URL}", file=sys.stderr)
    res = await client.get(SOCIETIES_URL)
    res.raise_for_status()

    # Match absolute hrefs pointing to society pages under ucdsocieties.ie
    all_hrefs = re.findall(r'href="(https://ucdsocieties\.ie/[^/"]+/)"', res.text)
    slugs = list(set(all_hrefs) - SKIP_SLUGS)
    print(f"Found {len(slugs)} candidate society pages", file=sys.stderr)
    return sorted(slugs)


async def extract_instagram_handle(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch a society page and return its Instagram handle, or None."""
    try:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"  [WARN] {url}: {e}", file=sys.stderr)
        return None

    # Match instagram.com/<handle> anywhere in the page source
    match = re.search(r'instagram\.com/([^/"?\s\\]+)', r.text)
    if not match:
        return None

    handle = match.group(1).strip("/").rstrip("\\")
    # Skip generic/invalid values
    if handle in {"", "p", "reel", "reels", "explore", "accounts", "direct"}:
        return None
    return handle


async def run():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        slugs = await fetch_society_slugs(client)

        # Fetch all society pages concurrently (in batches to be polite)
        handles: dict[str, str] = {}  # handle -> slug
        batch_size = 10
        for i in range(0, len(slugs), batch_size):
            batch = slugs[i : i + batch_size]
            tasks = [extract_instagram_handle(client, url) for url in batch]
            results = await asyncio.gather(*tasks)
            for url, handle in zip(batch, results):
                if handle:
                    slug_name = url.rstrip("/").split("/")[-1]
                    handles[handle] = slug_name
                    print(f"  [OK] {slug_name} → @{handle}", file=sys.stderr)
                else:
                    slug_name = url.rstrip("/").split("/")[-1]
                    print(f"  [--] {slug_name} → no Instagram found", file=sys.stderr)

    # --- Print final results ---
    new_handles = {h: n for h, n in handles.items() if h not in EXISTING_HANDLES}
    already_known = {h: n for h, n in handles.items() if h in EXISTING_HANDLES}

    print("\n" + "=" * 70)
    print(f"DISCOVERED: {len(handles)} total handles")
    print(f"  Already seeded : {len(already_known)}")
    print(f"  NEW to add     : {len(new_handles)}")
    print("=" * 70)

    print("\n--- ALL HANDLES (for seed list) ---")
    for handle, name in sorted(handles.items()):
        marker = "  " if handle in EXISTING_HANDLES else "* "
        print(f'{marker}    {{"name": "UCD {name.replace("-", " ").title()}", "instagram_handle": "{handle}"}},')

    print("\n--- NEW HANDLES ONLY ---")
    for handle, name in sorted(new_handles.items()):
        print(f'    {{"name": "UCD {name.replace("-", " ").title()}", "instagram_handle": "{handle}"}},')


if __name__ == "__main__":
    asyncio.run(run())
