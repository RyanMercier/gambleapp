import requests
import pandas as pd
import io
import time
import re
from requests.exceptions import RequestException

WIKIDATA_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "DataCollectorBot/2.2 (ryanmercier77@gmail.com)"}

def clean_text(text: str) -> str:
    """Remove XML tags, control characters, and trim whitespace."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text).strip()

def safe_request(query, retries=2, delay=10):
    """Send a request with up to 2 retries before skipping."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                WIKIDATA_URL,
                params={"query": query, "format": "csv"},
                headers=HEADERS,
                timeout=90
            )
            response.raise_for_status()
            return response.text
        except RequestException as e:
            print(f"Request failed (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Skipping this page due to repeated failures.")
                return ""
    return ""

def fetch_with_paging(query, per_page=2000, max_pages=100):
    """Fetch results with pagination, skipping failed pages."""
    all_names = []
    for page in range(max_pages):
        q = f"{query}\nLIMIT {per_page} OFFSET {page*per_page}"
        print(f"Fetching page {page+1}...")
        text = safe_request(q)
        if not text:
            continue  # skip this page, keep going

        if text.strip().startswith("<?xml") or "<literal" in text:
            names = re.findall(r"<literal[^>]*>(.*?)</literal>", text)
            names = [clean_text(n) for n in names]
        else:
            try:
                df = pd.read_csv(io.StringIO(text), quotechar='"', engine="python", on_bad_lines="skip")
                if "personLabel" in df.columns:
                    names = df["personLabel"].dropna().map(clean_text).tolist()
                else:
                    names = []
            except Exception as e:
                print(f"Parsing failed on page {page+1}: {e}")
                continue

        if not names:
            print("No more results, stopping.")
            break
        all_names.extend(names)
        time.sleep(2)
    return list(set(all_names))

# Politicians (including presidents)
politicians_query = """
SELECT DISTINCT ?personLabel WHERE {
  ?person wdt:P31 wd:Q5;
          wdt:P106 ?occupation.
  VALUES ?occupation { wd:Q82955 wd:Q30461 }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

# Influencers (expanded categories)
influencer_occupations = [
    "wd:Q17125263",  # YouTuber
    "wd:Q112895739", # TikToker
    "wd:Q967972",    # Instagram personality
    "wd:Q18814623",  # Social media influencer
    "wd:Q245068",    # Model
    "wd:Q33999",     # Actor
    "wd:Q177220",    # Musician
    "wd:Q488205",    # Pornographic actor
    "wd:Q214917",    # Pornographic actress
    "wd:Q1930187",   # Streamer
    "wd:Q3407706",   # Media personality
    "wd:Q25191"      # Billionaire
]

if __name__ == "__main__":
    print("Fetching politicians...")
    politicians = fetch_with_paging(politicians_query)
    pd.DataFrame(politicians, columns=["Name"]).to_csv("politicians.csv", index=False)
    print(f"Saved politicians.csv with {len(politicians)} names")

    print("Fetching influencers...")
    all_influencers = []
    for qid in influencer_occupations:
        query = f"""
        SELECT DISTINCT ?personLabel WHERE {{
          ?person wdt:P31 wd:Q5;
                  wdt:P106 {qid}.
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        names = fetch_with_paging(query)
        print(f" - {qid} → {len(names)} names")
        all_influencers.extend(names)

    all_influencers = list(set(all_influencers))
    pd.DataFrame(all_influencers, columns=["Name"]).to_csv("influencers.csv", index=False)
    print(f"Saved influencers.csv with {len(all_influencers)} names")
