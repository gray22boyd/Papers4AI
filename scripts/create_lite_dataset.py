"""
Create a lightweight dataset for deployment.
Filters to recent papers (2020+) to reduce memory usage.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "papers.json"
OUTPUT_FILE = DATA_DIR / "papers_lite.json"

MIN_YEAR = 2020  # Only include papers from 2020 onwards

def main():
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        papers = json.load(f)
    
    print(f"Total papers: {len(papers):,}")
    
    # Filter to recent years
    filtered = [p for p in papers if p.get("year", 0) >= MIN_YEAR]
    
    # Re-index IDs
    for i, paper in enumerate(filtered, 1):
        paper["id"] = i
    
    print(f"Papers from {MIN_YEAR}+: {len(filtered):,}")
    
    # Save lite version
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False)
    
    size_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"Saved to {OUTPUT_FILE} ({size_mb:.1f} MB)")

if __name__ == "__main__":
    main()
