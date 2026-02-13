"""
Paper Aggregation Script
========================
Scans the Paper Copilot paperlists repository and aggregates all papers
into a unified JSON and CSV format for the search engine.

Usage:
    python scripts/aggregate_papers.py

Output:
    - data/papers.json - All papers in JSON format
    - data/papers.csv  - All papers in CSV format
"""

import json
import os
import re
import csv
from pathlib import Path
from collections import defaultdict

# Configuration
PAPERLISTS_DIR = Path(__file__).parent.parent.parent / "paperlists"
OUTPUT_DIR = Path(__file__).parent.parent / "data"

# Folders to skip (not conference data)
SKIP_FOLDERS = {"tools", ".git", "__pycache__"}
SKIP_FILES = {"croissant.json", "README.md"}


def extract_year_from_filename(filename: str) -> int:
    """Extract year from filename like 'cvpr2024.json' -> 2024"""
    match = re.search(r'(\d{4})', filename)
    if match:
        return int(match.group(1))
    return 0


def split_semicolon_field(value: str, expected_count: int = 0) -> list:
    """Split a semicolon-separated field into a list."""
    if not value:
        return []
    parts = [p.strip() for p in str(value).split(";")]
    return parts


def parse_authors_with_metadata(paper: dict) -> list:
    """
    Parse authors and their metadata (homepage, scholar, etc.) into structured data.
    
    Returns a list of author objects:
    [
        {
            "name": "Author Name",
            "homepage": "https://...",
            "google_scholar": "https://scholar.google.com/citations?user=ID",
            "dblp": "https://dblp.org/pid/...",
            "orcid": "https://orcid.org/...",
            "linkedin": "https://linkedin.com/in/...",
            "affiliation": "University Name"
        },
        ...
    ]
    """
    # Get author names
    author_str = paper.get("author", "") or paper.get("author_site", "")
    if not author_str:
        return []
    
    # Split authors (semicolon is most common, but some use comma)
    if ";" in author_str:
        names = [a.strip() for a in author_str.split(";")]
    else:
        names = [a.strip() for a in author_str.split(",")]
    
    num_authors = len(names)
    
    # Extract metadata fields (all semicolon-separated)
    homepages = split_semicolon_field(paper.get("homepage", ""))
    google_scholars = split_semicolon_field(paper.get("google_scholar", ""))
    dblps = split_semicolon_field(paper.get("dblp", ""))
    orcids = split_semicolon_field(paper.get("orcid", ""))
    linkedins = split_semicolon_field(paper.get("linkedin", ""))
    affiliations = split_semicolon_field(paper.get("aff", ""))
    
    # Build author objects
    authors = []
    for i, name in enumerate(names):
        if not name:
            continue
            
        author = {"name": name}
        
        # Homepage
        if i < len(homepages) and homepages[i]:
            hp = homepages[i]
            if hp and not hp.startswith("http"):
                hp = "https://" + hp
            if hp:
                author["homepage"] = hp
        
        # Google Scholar
        if i < len(google_scholars) and google_scholars[i]:
            gs_id = google_scholars[i]
            if gs_id:
                author["google_scholar"] = f"https://scholar.google.com/citations?user={gs_id}"
        
        # DBLP
        if i < len(dblps) and dblps[i]:
            dblp_id = dblps[i]
            if dblp_id:
                author["dblp"] = f"https://dblp.org/pid/{dblp_id}"
        
        # ORCID
        if i < len(orcids) and orcids[i]:
            orcid_id = orcids[i]
            if orcid_id:
                author["orcid"] = f"https://orcid.org/{orcid_id}"
        
        # LinkedIn
        if i < len(linkedins) and linkedins[i]:
            li_id = linkedins[i]
            if li_id:
                author["linkedin"] = f"https://www.linkedin.com/in/{li_id}"
        
        # Affiliation
        if i < len(affiliations) and affiliations[i]:
            author["affiliation"] = affiliations[i]
        
        authors.append(author)
    
    return authors


def get_paper_url(paper: dict) -> str:
    """Extract the best URL for the paper."""
    # Priority: pdf > site > openreview > arxiv
    url_fields = ["pdf", "site", "openreview", "arxiv", "oa"]
    for field in url_fields:
        url = paper.get(field, "")
        if url and isinstance(url, str) and url.startswith("http"):
            return url
    return ""


def process_paper(paper: dict, conference: str, year: int, global_id: int) -> dict:
    """Process a single paper and return normalized data."""
    # Parse authors with metadata
    authors_data = parse_authors_with_metadata(paper)
    
    # Create simple author string for display/search
    authors_str = ", ".join(a["name"] for a in authors_data) if authors_data else ""
    
    return {
        "id": global_id,
        "paper_id": str(paper.get("id", "")),
        "title": paper.get("title", "").strip(),
        "abstract": paper.get("abstract", "").strip(),
        "authors": authors_str,
        "authors_data": authors_data,  # Structured author data with links
        "year": year,
        "conference": conference.upper(),
        "url": get_paper_url(paper),
        "status": paper.get("status", ""),
        "track": paper.get("track", ""),
        "keywords": paper.get("keywords", ""),
        "github": paper.get("github", ""),
        "project": paper.get("project", ""),
    }


def scan_paperlists(paperlists_dir: Path) -> list:
    """Scan all conference folders and aggregate papers."""
    all_papers = []
    stats = defaultdict(lambda: {"count": 0, "years": set()})
    global_id = 1
    errors = []

    print(f"\nScanning: {paperlists_dir}")
    print("-" * 60)

    if not paperlists_dir.exists():
        print(f"ERROR: Directory not found: {paperlists_dir}")
        print(f"   Please clone the paperlists repo first:")
        print(f"   git clone https://github.com/papercopilot/paperlists.git ../paperlists")
        return []

    # Iterate through conference folders
    for folder in sorted(paperlists_dir.iterdir()):
        if not folder.is_dir() or folder.name in SKIP_FOLDERS:
            continue

        conference = folder.name
        json_files = list(folder.glob("*.json"))

        if not json_files:
            continue

        conference_count = 0

        for json_file in sorted(json_files):
            if json_file.name in SKIP_FILES:
                continue

            year = extract_year_from_filename(json_file.name)

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    papers = json.load(f)

                if not isinstance(papers, list):
                    errors.append(f"Unexpected format in {json_file}")
                    continue

                for paper in papers:
                    if not isinstance(paper, dict):
                        continue

                    # Skip papers without title
                    if not paper.get("title"):
                        continue

                    processed = process_paper(paper, conference, year, global_id)
                    all_papers.append(processed)
                    global_id += 1
                    conference_count += 1
                    stats[conference]["years"].add(year)

            except json.JSONDecodeError as e:
                errors.append(f"JSON error in {json_file}: {e}")
            except Exception as e:
                errors.append(f"Error processing {json_file}: {e}")

        if conference_count > 0:
            stats[conference]["count"] = conference_count
            years_range = f"{min(stats[conference]['years'])}-{max(stats[conference]['years'])}"
            print(f"  [+] {conference.upper():12} | {conference_count:6,} papers | Years: {years_range}")

    return all_papers, stats, errors


def save_json(papers: list, output_path: Path):
    """Save papers to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON: {output_path} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")


def save_csv(papers: list, output_path: Path):
    """Save papers to CSV file (without authors_data for simplicity)."""
    if not papers:
        return

    fieldnames = ["id", "paper_id", "title", "abstract", "authors", "year", "conference", "url", "status", "track", "keywords", "github", "project"]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(papers)

    print(f"Saved CSV:  {output_path} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")


def print_summary(papers: list, stats: dict, errors: list):
    """Print aggregation summary."""
    print("\n" + "=" * 60)
    print("AGGREGATION SUMMARY")
    print("=" * 60)

    if not papers:
        print("ERROR: No papers found!")
        return

    years = [p["year"] for p in papers if p["year"] > 0]
    conferences = set(p["conference"] for p in papers)
    
    # Count authors with links
    authors_with_links = 0
    total_authors = 0
    for p in papers:
        for author in p.get("authors_data", []):
            total_authors += 1
            if any(k in author for k in ["homepage", "google_scholar", "dblp", "linkedin", "orcid"]):
                authors_with_links += 1

    print(f"\n  Total Papers:     {len(papers):,}")
    print(f"  Conferences:      {len(conferences)}")
    print(f"  Year Range:       {min(years)} - {max(years)}")
    print(f"  Total Authors:    {total_authors:,}")
    print(f"  Authors w/ Links: {authors_with_links:,} ({100*authors_with_links/total_authors:.1f}%)" if total_authors > 0 else "")

    # Papers by year
    print(f"\n  Papers by Year (recent):")
    year_counts = defaultdict(int)
    for p in papers:
        if p["year"] > 0:
            year_counts[p["year"]] += 1

    for year in sorted(year_counts.keys(), reverse=True)[:10]:
        print(f"      {year}: {year_counts[year]:,}")

    # Top conferences
    print(f"\n  Top Conferences:")
    conf_counts = [(conf, data["count"]) for conf, data in stats.items()]
    conf_counts.sort(key=lambda x: x[1], reverse=True)
    for conf, count in conf_counts[:10]:
        print(f"      {conf.upper():12}: {count:,}")

    if errors:
        print(f"\n  Errors: {len(errors)}")
        for err in errors[:5]:
            print(f"      - {err}")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("PAPER COPILOT DATA AGGREGATOR")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Scan and aggregate papers
    papers, stats, errors = scan_paperlists(PAPERLISTS_DIR)

    if not papers:
        return

    # Save outputs
    save_json(papers, OUTPUT_DIR / "papers.json")
    save_csv(papers, OUTPUT_DIR / "papers.csv")

    # Print summary
    print_summary(papers, stats, errors)

    print("\n[OK] Aggregation complete!")
    print(f"     Data files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
