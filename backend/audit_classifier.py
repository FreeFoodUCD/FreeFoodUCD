"""
Classifier audit: pull real posts from Apify and run through EventExtractor.
Run from backend/ directory: python audit_classifier.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from openai import OpenAI
import json
from collections import Counter

from apify_client import ApifyClient
from app.services.nlp.extractor import EventExtractor
from datetime import datetime

APIFY_TOKEN = os.environ["APIFY_API_TOKEN"]
ACTOR_ID = "apify/instagram-profile-scraper"

SOCIETIES = [
    ("Belfield FM", "belfield.fm"),
    ("UCD Actuarial Society", "ucdactuarial"),
    ("UCD Africa Society", "ucdafricasociety"),
    ("UCD Arabic Culture & Language Society", "ucd.aclsoc"),
    ("UCD Architecture Society", "ucdarcsoc"),
    ("UCD Arts Society", "artssocucd"),
    ("UCD Biological Society", "ucdbiosoc"),
    ("UCD Business Society", "ucdbusiness"),
    ("UCD Chem Eng Soc", "ucdchemengsoc"),
    ("UCD Chemical Society", "ucdchemsoc"),
    ("UCD Chess Society", "ucdchess"),
    ("UCD Chinese Society", "chinesesoc.ucd"),
    ("UCD Christian Union", "ucdcu"),
    ("UCD Civil & Structural Engineering Society", "ucd_civil_structural"),
    ("UCD Classical Society", "ucdclassicssoc"),
    ("UCD Commerce & Economics Society", "ucdcesoc"),
    ("UCD Dance Society", "ucddancesoc"),
    ("UCD Drama Society", "ucddramasoc"),
    ("UCD Drama Society", "ucddramsoc"),
    ("UCD Draw Society", "ucddrawsoc"),
    ("UCD Eastern European Society", "ucdees"),
    ("UCD ElecSoc", "ucd.elecsoc"),
    ("UCD Engineering Society", "ucdengineering"),
    ("UCD Engineering Society", "ucdengsoc"),
    ("UCD Erasmus Student Network", "esnucd"),
    ("UCD Film & Video Society", "ucdfilmsoc"),
    ("UCD Food Society", "ucdfoodsoc"),
    ("UCD French Society", "ucdfrenchsoc"),
    ("UCD GameSoc", "ucdgamesociety"),
    ("UCD Geography Society", "ucdgeogsoc"),
    ("UCD Geology Society", "ucdrocsoc"),
    ("UCD German Society", "ucdgermansoc"),
    ("UCD Gospel Choir", "ucdgospelchoir"),
    ("UCD Harry Potter Society", "ucdpottersoc"),
    ("UCD History Society", "ucdhistorysoc"),
    ("UCD Horse Racing Society", "ucdhrs"),
    ("UCD Horticulture Society", "ucd_hortsoc"),
    ("UCD IndSoc", "ucdindsoc"),
    ("UCD International Students Society", "issucd"),
    ("UCD Investors & Entrepreneurs", "ucdie"),
    ("UCD Islamic Society", "ucdisoc"),
    ("UCD Italian Society", "ucditaliansoc"),
    ("UCD Japanese Society", "ucdjsoc"),
    ("UCD Juggling Society", "ucdjuggling"),
    ("UCD Kevin Barry Cumann", "kevinbarrycumann"),
    ("UCD Law Society", "ucdlawsoc"),
    ("UCD LGBTQ+ Society", "ucd_lgbtqplus"),
    ("UCD Literary & Historical Society", "ucdlnh"),
    ("UCD Literary Society", "ucdlitsoc"),
    ("UCD Livingstone's Christian Society", "ucdlivingstones"),
    ("UCD Malaysian Society", "ucdmsoc"),
    ("UCD Mathematical Society", "ucdmathsoc"),
    ("UCD Mechsoc", "ucdmechsoc"),
    ("UCD Medical Society", "ucdmedsoc"),
    ("UCD Music Society", "ucdmusicsoc"),
    ("UCD Netsoc", "ucdnetsoc"),
    ("UCD Newman Catholic Society", "ucdnewmansoc"),
    ("UCD Nordic Society", "nordicsocietyucd"),
    ("UCD Nursing & Midwifery Society", "namsocucd"),
    ("UCD Pharmacy & Toxicology Society", "pharmtoxucd"),
    ("UCD PhD Society", "ucdphdsociety"),
    ("UCD Philosophy Society", "ucdphilsoc"),
    ("UCD Physics Society", "physics_society_ucd"),
    ("UCD Politics & International Relations Society", "ucdpolsoc"),
    ("UCD Psychological Society", "psychsocietyucd"),
    ("UCD Science Society", "ucdscisoc"),
    ("UCD Sci-Fi Society", "ucdscifi"),
    ("UCD Sinn Féin", "ucdsinnfein"),
    ("UCD Social Democrats", "ucdsocdems"),
    ("UCD Social Sciences Students", "ucdsocscistudents"),
    ("UCD Student Legal Service", "ucdstudentlegalservice"),
    ("UCD Sustainability Society", "ucdsussoc"),
    ("UCD TV Society", "ucdtvsoc"),
    ("UCD Veterinary Nursing Society", "ucdvnsoc"),
    ("UCD Veterinary Society", "ucdvetsoc"),
    ("UCD Women in STEM", "womeninstem_ucd"),
    ("UCD Young Fine Gael", "ucd_yfg"),
]

POSTS_PER_SOCIETY = 10

JUDGE_PROMPT = """\
You are judging Instagram posts from UCD (University College Dublin, Belfield campus) student societies.

Caption: "{caption}"

Answer in JSON only:
{{
  "is_free_food_event": true/false,
  "reasoning": "one sentence",
  "food_keyword": "word(s) that indicate food, or null",
  "time": "HH:MM in 24h format, or null",
  "location": "building or room name on UCD campus, or null",
  "members_only": true/false
}}

Rules:
- true only if food/drinks are clearly being offered for free (not sold, not BYOF)
- Members-only events → still return true (we pass these through with a tag)
- Off-campus venues → false. Off-campus means: pubs, bars, restaurants, city centre,
  Rathmines, Ranelagh, Dundrum, Grafton Street, O'Connell Street, or any named venue
  outside UCD Belfield campus
- On-campus means: any UCD Belfield building — Newman Building, O'Brien Centre for Science,
  James Joyce Library, Sutherland School of Law, Lochlann Quinn Business School,
  Engineering & Materials Science Centre, Student Centre (Blue Room, Red Room, FitzGerald
  Chamber, Harmony Studio, Brava Lounge, Astra Hall, UCD Cinema, Clubhouse Bar, Atrium),
  UCD Village (Auditorium), O'Reilly Hall, The Pavilion, Sports Centre, Conway Institute,
  Geary Institute, NovaUCD, Newstead, Agriculture & Food Science Centre, Health Sciences
  Centre, Veterinary Sciences Centre, Computer Science & Informatics Centre, or simply
  "UCD", "Belfield", or "campus" with no other venue mentioned
- Paid events (ticket price, entry fee, explicit € amount) → false
- If location is unknown/not mentioned, assume on-campus (UCD society default)\
"""


def fetch_posts():
    client = ApifyClient(APIFY_TOKEN)
    usernames = [handle for _, handle in SOCIETIES]
    print(f"Fetching {POSTS_PER_SOCIETY} posts each from {len(usernames)} accounts via Apify...")

    run = client.actor(ACTOR_ID).call(run_input={
        "usernames": usernames,
        "resultsLimit": POSTS_PER_SOCIETY,
        "resultsType": "posts",
        "searchType": "user",
        "addParentData": False,
    })

    raw = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Apify returned {len(raw)} dataset items\n")

    posts_by_handle = {}
    for item in raw:
        if "latestPosts" in item and isinstance(item["latestPosts"], list):
            uname = (item.get("username") or "").lower()
            posts = []
            for p in item["latestPosts"][:POSTS_PER_SOCIETY]:
                caption = p.get("caption", "") or ""
                ts_raw = p.get("timestamp")
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now()
                url = p.get("url") or (f"https://instagram.com/p/{p['shortCode']}/" if p.get("shortCode") else "")
                posts.append({"caption": caption, "timestamp": ts, "url": url})
            posts_by_handle[uname] = posts
        else:
            uname = (item.get("ownerUsername") or item.get("username") or
                     (item.get("owner") or {}).get("username") or "").lower()
            if uname:
                caption = item.get("caption", "") or ""
                ts_raw = item.get("timestamp")
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else datetime.now()
                url = item.get("url") or ""
                posts_by_handle.setdefault(uname, [])
                if len(posts_by_handle[uname]) < POSTS_PER_SOCIETY:
                    posts_by_handle[uname].append({"caption": caption, "timestamp": ts, "url": url})

    return posts_by_handle


def run_audit(posts_by_handle):
    extractor = EventExtractor()

    accepted = []
    rejected = []

    for society_name, handle in SOCIETIES:
        posts = posts_by_handle.get(handle, [])
        if not posts:
            print(f"  ⚠️  No posts returned for @{handle}")
            continue
        for post in posts:
            caption = post["caption"]
            ts = post["timestamp"]
            url = post["url"]
            passed = extractor.classify_event(caption)
            reason = extractor.get_rejection_reason(caption)
            entry = {
                "society": society_name,
                "handle": handle,
                "caption": caption,
                "url": url,
                "timestamp": ts,
                "passed": passed,
                "reason": reason,
            }
            if passed:
                result = extractor.extract_event(caption, post_timestamp=ts)
                entry["extracted"] = result
                accepted.append(entry)
            else:
                rejected.append(entry)

    return accepted, rejected


def judge_posts_with_llm(posts_flat):
    """Posts_flat: list of {handle, caption, timestamp, url}."""
    client = OpenAI()  # picks up OPENAI_API_KEY from env
    results = []
    total = len(posts_flat)
    print(f"Running LLM audit on {total} posts (this takes a few minutes)...")
    for i, post in enumerate(posts_flat, 1):
        if i == 1 or i % 100 == 0:
            print(f"  LLM judging post {i}/{total}...")
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(caption=post["caption"][:800])}],
        )
        try:
            data = json.loads(resp.choices[0].message.content)
        except Exception:
            data = {
                "is_free_food_event": None,
                "reasoning": "parse error",
                "food_keyword": None,
                "time": None,
                "location": None,
                "members_only": False,
            }
        results.append({**post, "llm": data})
    print(f"  Done — {total} posts judged.\n")
    return results


def compare_results(accepted, rejected, llm_results):
    """Merge classifier results with LLM verdicts; return categorised dicts."""
    llm_by_url = {r["url"]: r["llm"] for r in llm_results}

    true_positives = []   # classifier PASS + LLM YES → compare extraction
    false_negatives = []  # classifier FAIL + LLM YES → missing keyword
    false_positives = []  # classifier PASS + LLM NO  → flag for review

    for e in accepted:
        llm = llm_by_url.get(e["url"])
        if llm is None:
            continue
        if llm.get("is_free_food_event") is True:
            true_positives.append({**e, "llm": llm})
        elif llm.get("is_free_food_event") is False:
            false_positives.append({**e, "llm": llm})

    for e in rejected:
        llm = llm_by_url.get(e["url"])
        if llm is None:
            continue
        if llm.get("is_free_food_event") is True:
            false_negatives.append({**e, "llm": llm})

    # Find extraction misses within true positives
    time_misses = []
    location_misses = []
    for e in true_positives:
        ex = e.get("extracted") or {}
        llm = e["llm"]
        extractor_time_found = ex.get("extracted_data", {}).get("time_found", False)
        extractor_location = ex.get("location")
        llm_time = llm.get("time")
        llm_location = llm.get("location")

        if llm_time and not extractor_time_found:
            time_misses.append({**e, "llm_time": llm_time})
        if llm_location and not extractor_location:
            location_misses.append({**e, "llm_location": llm_location})

    return {
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "time_misses": time_misses,
        "location_misses": location_misses,
    }


def print_report(accepted, rejected, comparison=None):
    total = len(accepted) + len(rejected)
    print("=" * 70)
    print(f"CLASSIFIER AUDIT REPORT  —  {total} posts analysed")
    print("=" * 70)

    print(f"\n✅ ACCEPTED ({len(accepted)} posts)\n")
    for e in accepted:
        print(f"  @{e['handle']}  [{e['timestamp'].strftime('%d %b')}]")
        print(f"  Caption: {e['caption'][:120].strip()!r}")
        if e.get("extracted"):
            ex = e["extracted"]
            print(f"  → Title:    {ex['title']}")
            print(f"  → Location: {ex['location'] or 'Not found'}")
            print(f"  → Time:     {ex['start_time'].strftime('%I:%M %p') if ex['start_time'] else 'Not found'}")
            print(f"  → Date:     {ex['start_time'].strftime('%A %d %b') if ex['start_time'] else 'Not found'}")
            print(f"  → Members:  {ex['extracted_data'].get('members_only', False)}")
        print(f"  {e['url']}")
        print()

    print(f"\n❌ REJECTED ({len(rejected)} posts)\n")

    reason_counts = Counter(e["reason"] for e in rejected)
    print("  Rejection reasons:")
    for reason, count in reason_counts.most_common():
        print(f"    {count}x  {reason}")
    print()

    # Show rejections that mention food words but still failed — likely gaps
    food_hints = [
        'food', 'eat', 'drink', 'snack', 'lunch', 'dinner', 'breakfast',
        'pizza', 'cake', 'cookie', 'treat', 'refresh', 'catering', 'buffet',
        'popcorn', 'chips', 'chocolate', 'sandwich', 'burger', 'wrap',
        'sushi', 'curry', 'soup', 'pasta', 'taco', 'nachos', 'crisps',
        'biscuit', 'donut', 'sweet', 'cupcake', 'waffle',
    ]
    interesting = [
        e for e in rejected
        if any(w in e["caption"].lower() for w in food_hints)
        and e["reason"] == "No explicit food keyword found"
    ]
    if interesting:
        print(f"  ⚠️  POSSIBLE FALSE NEGATIVES ({len(interesting)} posts — food mentioned but rejected):\n")
        for e in interesting:
            print(f"    @{e['handle']}  [{e['timestamp'].strftime('%d %b')}]")
            print(f"    Caption: {e['caption'][:150].strip()!r}")
            print(f"    {e['url']}")
            print()
    else:
        print("  No obvious false negatives detected.\n")

    # Show accepted posts missing time or location
    tba = [e for e in accepted if not (e.get("extracted") or {}).get("location") or
           not (e.get("extracted") or {}).get("extracted_data", {}).get("time_found")]
    if tba:
        print(f"\n  ⚠️  ACCEPTED BUT INCOMPLETE EXTRACTION ({len(tba)} posts):\n")
        for e in tba:
            ex = e.get("extracted") or {}
            missing = []
            if not ex.get("location"):
                missing.append("location")
            if not ex.get("extracted_data", {}).get("time_found"):
                missing.append("time")
            print(f"    @{e['handle']}  missing: {', '.join(missing)}")
            print(f"    Caption: {e['caption'][:150].strip()!r}")
            print()

    if not comparison:
        return

    # ------------------------------------------------------------------ #
    #  LLM COMPARISON SECTION                                             #
    # ------------------------------------------------------------------ #
    fn = comparison["false_negatives"]
    fp = comparison["false_positives"]
    tp = comparison["true_positives"]
    tm = comparison["time_misses"]
    lm = comparison["location_misses"]

    print()
    print("=" * 70)
    print(f"LLM COMPARISON  —  {len(tp)} true-pos | {len(fn)} false-neg | {len(fp)} false-pos")
    print("=" * 70)

    # --- False negatives grouped by LLM food_keyword ---
    if fn:
        print(f"\n🔴 FALSE NEGATIVES ({len(fn)}) — classifier rejected, LLM says food event\n")
        kw_groups = {}
        for e in fn:
            kw = (e["llm"].get("food_keyword") or "unknown").lower().strip()
            kw_groups.setdefault(kw, []).append(e)
        for kw, entries in sorted(kw_groups.items(), key=lambda x: -len(x[1])):
            print(f"  Keyword: \"{kw}\"  ({len(entries)} posts) ← consider adding to extractor")
            for e in entries:
                print(f"    @{e['handle']}  [{e['timestamp'].strftime('%d %b')}]  reason: {e['reason']}")
                print(f"    LLM: {e['llm'].get('reasoning', '')}")
                print(f"    Caption: {e['caption'][:120].strip()!r}")
                print(f"    {e['url']}")
                print()
    else:
        print("\n🔴 FALSE NEGATIVES: none found\n")

    # --- False positives ---
    if fp:
        print(f"\n🟡 FALSE POSITIVES ({len(fp)}) — classifier accepted, LLM says NOT a food event\n")
        for e in fp:
            print(f"  @{e['handle']}  [{e['timestamp'].strftime('%d %b')}]")
            print(f"  LLM: {e['llm'].get('reasoning', '')}")
            print(f"  Caption: {e['caption'][:120].strip()!r}")
            print(f"  {e['url']}")
            print()
    else:
        print("\n🟡 FALSE POSITIVES: none found\n")

    # --- Time misses (both agree it's food, but extractor missed the time) ---
    if tm:
        print(f"\n🕐 TIME MISSES ({len(tm)}) — LLM found time, extractor did not\n")
        for e in tm:
            print(f"  @{e['handle']}  LLM time: {e['llm_time']}")
            print(f"  Caption: {e['caption'][:120].strip()!r}")
            print(f"  {e['url']}")
            print()
    else:
        print("\n🕐 TIME MISSES: none found\n")

    # --- Location misses ---
    if lm:
        print(f"\n📍 LOCATION MISSES ({len(lm)}) — LLM found location, extractor did not\n")
        for e in lm:
            print(f"  @{e['handle']}  LLM location: {e['llm_location']}")
            print(f"  Caption: {e['caption'][:120].strip()!r}")
            print(f"  {e['url']}")
            print()
    else:
        print("\n📍 LOCATION MISSES: none found\n")


class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, text):
        for f in self.files: f.write(text)
    def flush(self):
        for f in self.files: f.flush()


if __name__ == "__main__":
    _report_path = os.path.join(os.path.dirname(__file__), "audit_report.txt")
    _report_file = open(_report_path, "w")
    sys.stdout = Tee(sys.__stdout__, _report_file)

    try:
        posts_by_handle = fetch_posts()
        accepted, rejected = run_audit(posts_by_handle)

        posts_flat = [
            {"handle": e["handle"], "caption": e["caption"],
             "timestamp": e["timestamp"], "url": e["url"]}
            for e in accepted + rejected
        ]

        llm_results = judge_posts_with_llm(posts_flat)
        comparison = compare_results(accepted, rejected, llm_results)
        print_report(accepted, rejected, comparison)
    finally:
        sys.stdout = sys.__stdout__
        _report_file.close()
        print(f"Report saved to {_report_path}")
