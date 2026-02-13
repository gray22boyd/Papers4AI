"""
Search Engine for Academic Papers
=================================
Keyword search with Boolean operators and relevance scoring.

Supports:
- Phrase search: "world models"
- AND operator: world AND models (both required)
- OR operator: video OR image (either matches)
- NOT operator: transformer NOT vision (exclude term)
- Combinations: "world models" AND video NOT image
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Tuple
from collections import defaultdict

from config import PAPERS_JSON, TITLE_WEIGHT, ABSTRACT_WEIGHT, PHRASE_MULTIPLIER


class BooleanQuery:
    """Parsed Boolean query with AND, OR, NOT terms."""
    
    def __init__(self):
        self.and_terms: List[str] = []      # All must match
        self.or_terms: List[str] = []       # At least one must match
        self.not_terms: List[str] = []      # None must match
        self.phrases: List[str] = []        # Exact phrase matches
    
    @classmethod
    def parse(cls, query: str) -> 'BooleanQuery':
        """
        Parse a query string with Boolean operators.
        
        Examples:
            "world models" AND video -> phrase "world models" AND term "video"
            transformer OR attention -> either term matches
            neural NOT network -> must have "neural", must NOT have "network"
            world models -> implicit AND between terms
        """
        bq = cls()
        
        # Extract quoted phrases first
        phrase_pattern = r'"([^"]+)"'
        for match in re.finditer(phrase_pattern, query):
            bq.phrases.append(match.group(1).lower())
        
        # Remove phrases from query for further processing
        remaining = re.sub(phrase_pattern, " PHRASE ", query)
        
        # Normalize operators (make case-insensitive)
        remaining = re.sub(r'\bAND\b', ' AND ', remaining, flags=re.IGNORECASE)
        remaining = re.sub(r'\bOR\b', ' OR ', remaining, flags=re.IGNORECASE)
        remaining = re.sub(r'\bNOT\b', ' NOT ', remaining, flags=re.IGNORECASE)
        
        # Split by OR first (lowest precedence)
        or_groups = re.split(r'\s+OR\s+', remaining, flags=re.IGNORECASE)
        
        if len(or_groups) > 1:
            # We have OR clauses
            for group in or_groups:
                group = group.strip()
                if group and group != "PHRASE":
                    # Check for NOT within OR group
                    if ' NOT ' in group.upper():
                        parts = re.split(r'\s+NOT\s+', group, flags=re.IGNORECASE)
                        if parts[0].strip() and parts[0].strip() != "PHRASE":
                            bq.or_terms.append(parts[0].strip().lower())
                        for not_part in parts[1:]:
                            if not_part.strip() and not_part.strip() != "PHRASE":
                                bq.not_terms.append(not_part.strip().lower())
                    else:
                        # Clean up AND within OR group
                        terms = re.split(r'\s+AND\s+', group, flags=re.IGNORECASE)
                        for term in terms:
                            term = term.strip()
                            if term and term != "PHRASE":
                                bq.or_terms.append(term.lower())
        else:
            # No OR, process AND and NOT
            remaining = or_groups[0]
            
            # Split by NOT
            not_split = re.split(r'\s+NOT\s+', remaining, flags=re.IGNORECASE)
            
            # First part (before any NOT) contains AND terms
            and_part = not_split[0]
            and_terms = re.split(r'\s+AND\s+', and_part, flags=re.IGNORECASE)
            
            for term in and_terms:
                # Split remaining spaces into individual words
                words = term.strip().split()
                for word in words:
                    word = word.strip()
                    if word and word != "PHRASE" and len(word) >= 2:
                        bq.and_terms.append(word.lower())
            
            # Everything after NOT goes to not_terms
            for not_part in not_split[1:]:
                words = not_part.strip().split()
                for word in words:
                    word = word.strip()
                    if word and word != "PHRASE" and len(word) >= 2:
                        bq.not_terms.append(word.lower())
        
        return bq
    
    def matches(self, text: str) -> bool:
        """Check if text matches the Boolean query."""
        text_lower = text.lower()
        
        # Check NOT terms first (exclusions)
        for term in self.not_terms:
            if term in text_lower:
                return False
        
        # Check phrases (all must match)
        for phrase in self.phrases:
            if phrase not in text_lower:
                return False
        
        # Check AND terms (all must match)
        for term in self.and_terms:
            if term not in text_lower:
                return False
        
        # Check OR terms (at least one must match, if any exist)
        if self.or_terms:
            if not any(term in text_lower for term in self.or_terms):
                return False
        
        return True
    
    def has_terms(self) -> bool:
        """Check if query has any search terms."""
        return bool(self.and_terms or self.or_terms or self.phrases)


class PaperSearchEngine:
    """In-memory search engine for academic papers."""

    def __init__(self):
        self.papers = []
        self.papers_by_id = {}
        self.conferences = set()
        self.years = set()
        self.authors_index = {}  # Normalized name -> author data
        self._loaded = False

    def _normalize_author_name(self, name: str) -> str:
        """Normalize author name for consistent indexing."""
        return name.strip().lower()

    def _build_author_index(self):
        """Build index mapping authors to their papers and metadata."""
        print("Building author index...")
        
        for paper in self.papers:
            authors_data = paper.get("authors_data", [])
            paper_year = paper.get("year", 0)
            paper_conf = paper.get("conference", "")
            
            # Check if this author is first author
            for idx, author in enumerate(authors_data):
                author_name = author.get("name", "").strip()
                if not author_name:
                    continue
                
                normalized = self._normalize_author_name(author_name)
                
                if normalized not in self.authors_index:
                    self.authors_index[normalized] = {
                        "name": author_name,  # Keep original casing
                        "papers": [],
                        "conferences": defaultdict(int),
                        "years": set(),
                        "first_author_count": 0,
                        "coauthors": defaultdict(int),
                        "affiliations": set(),
                        "links": {}
                    }
                
                author_entry = self.authors_index[normalized]
                author_entry["papers"].append(paper["id"])
                author_entry["conferences"][paper_conf] += 1
                author_entry["years"].add(paper_year)
                
                if idx == 0:  # First author
                    author_entry["first_author_count"] += 1
                
                # Collect affiliations
                if author.get("affiliation"):
                    author_entry["affiliations"].add(author["affiliation"])
                
                # Collect links (keep the most recent)
                for link_type in ["homepage", "google_scholar", "dblp", "linkedin", "orcid"]:
                    if author.get(link_type):
                        author_entry["links"][link_type] = author[link_type]
                
                # Track co-authors
                for other_author in authors_data:
                    other_name = other_author.get("name", "").strip()
                    if other_name and other_name != author_name:
                        author_entry["coauthors"][other_name] += 1
        
        # Convert sets to sorted lists for JSON serialization
        for author_data in self.authors_index.values():
            author_data["years"] = sorted(author_data["years"])
            author_data["affiliations"] = list(author_data["affiliations"])
        
        print(f"Indexed {len(self.authors_index):,} unique authors")

    def load_data(self, filepath: Path = PAPERS_JSON):
        """Load papers from JSON file into memory."""
        if self._loaded:
            return

        print(f"Loading papers from {filepath}...")
        with open(filepath, "r", encoding="utf-8") as f:
            self.papers = json.load(f)

        # Build indexes
        for paper in self.papers:
            self.papers_by_id[paper["id"]] = paper
            if paper.get("conference"):
                self.conferences.add(paper["conference"])
            if paper.get("year"):
                self.years.add(paper["year"])

        # Build author index
        self._build_author_index()

        self._loaded = True
        print(f"Loaded {len(self.papers):,} papers from {len(self.conferences)} conferences")

    def get_stats(self) -> dict:
        """Get database statistics."""
        return {
            "total_papers": len(self.papers),
            "conferences": len(self.conferences),
            "year_min": min(self.years) if self.years else 0,
            "year_max": max(self.years) if self.years else 0,
        }

    def get_conferences(self) -> list:
        """Get list of all conferences with paper counts."""
        counts = defaultdict(int)
        for paper in self.papers:
            if paper.get("conference"):
                counts[paper["conference"]] += 1

        return [
            {"name": conf, "count": count}
            for conf, count in sorted(counts.items(), key=lambda x: -x[1])
        ]

    def get_paper(self, paper_id: int) -> Optional[dict]:
        """Get a single paper by ID."""
        return self.papers_by_id.get(paper_id)

    def search_authors(self, query: str, limit: int = 20, offset: int = 0) -> dict:
        """
        Search for authors by name.
        
        Args:
            query: Author name to search for (partial match)
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            Dict with matching authors and their stats
        """
        query_lower = query.strip().lower()
        if not query_lower:
            return {"results": [], "total": 0}
        
        # Find matching authors
        matches = []
        for normalized_name, author_data in self.authors_index.items():
            if query_lower in normalized_name:
                paper_count = len(author_data["papers"])
                matches.append({
                    "name": author_data["name"],
                    "paper_count": paper_count,
                    "first_author_count": author_data["first_author_count"],
                    "conferences": dict(author_data["conferences"]),
                    "year_range": [min(author_data["years"]), max(author_data["years"])] if author_data["years"] else [],
                    "affiliations": author_data["affiliations"][:3],  # Top 3
                    "has_links": bool(author_data["links"]),
                })
        
        # Sort by paper count (most prolific first)
        matches.sort(key=lambda x: -x["paper_count"])
        
        total = len(matches)
        paginated = matches[offset:offset + limit]
        
        return {
            "results": paginated,
            "total": total,
            "query": query,
            "offset": offset,
            "limit": limit,
        }

    def get_author_profile(self, author_name: str) -> Optional[dict]:
        """
        Get full profile for an author.
        
        Args:
            author_name: Author name (case-insensitive)
            
        Returns:
            Full author profile with papers, co-authors, stats
        """
        normalized = self._normalize_author_name(author_name)
        
        if normalized not in self.authors_index:
            # Try partial match
            for name in self.authors_index:
                if normalized in name or name in normalized:
                    normalized = name
                    break
            else:
                return None
        
        author_data = self.authors_index[normalized]
        
        # Get full paper objects
        papers = []
        for paper_id in author_data["papers"]:
            paper = self.papers_by_id.get(paper_id)
            if paper:
                # Check if first author
                authors_data = paper.get("authors_data", [])
                is_first_author = (
                    len(authors_data) > 0 and 
                    self._normalize_author_name(authors_data[0].get("name", "")) == normalized
                )
                
                papers.append({
                    "id": paper["id"],
                    "title": paper.get("title", ""),
                    "year": paper.get("year", 0),
                    "conference": paper.get("conference", ""),
                    "url": paper.get("url", ""),
                    "is_first_author": is_first_author,
                    "authors": paper.get("authors", ""),
                })
        
        # Sort papers by year (newest first)
        papers.sort(key=lambda x: -x["year"])
        
        # Get top co-authors
        coauthors = sorted(
            author_data["coauthors"].items(),
            key=lambda x: -x[1]
        )[:10]
        
        # Conference breakdown
        conferences = sorted(
            author_data["conferences"].items(),
            key=lambda x: -x[1]
        )
        
        return {
            "name": author_data["name"],
            "paper_count": len(papers),
            "first_author_count": author_data["first_author_count"],
            "year_range": [min(author_data["years"]), max(author_data["years"])] if author_data["years"] else [],
            "affiliations": author_data["affiliations"],
            "links": author_data["links"],
            "conferences": [{"name": c, "count": n} for c, n in conferences],
            "coauthors": [{"name": c, "count": n} for c, n in coauthors],
            "papers": papers,
        }

    def _score_paper(self, paper: dict, bq: BooleanQuery) -> float:
        """Calculate relevance score for a paper."""
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        text = title + " " + abstract
        score = 0.0

        # Score phrase matches (highest priority)
        for phrase in bq.phrases:
            if phrase in title:
                score += TITLE_WEIGHT * PHRASE_MULTIPLIER * 2
            if phrase in abstract:
                score += ABSTRACT_WEIGHT * PHRASE_MULTIPLIER

        # Score AND terms
        for term in bq.and_terms:
            title_count = title.count(term)
            if title_count > 0:
                score += TITLE_WEIGHT * min(title_count, 3)
            
            abstract_count = abstract.count(term)
            if abstract_count > 0:
                score += ABSTRACT_WEIGHT * min(abstract_count, 5)

        # Score OR terms (bonus for each match)
        for term in bq.or_terms:
            title_count = title.count(term)
            if title_count > 0:
                score += TITLE_WEIGHT * min(title_count, 3)
            
            abstract_count = abstract.count(term)
            if abstract_count > 0:
                score += ABSTRACT_WEIGHT * min(abstract_count, 5)

        return score

    def search(
        self,
        query: str,
        conferences: Optional[list] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        author: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """
        Search papers by query with Boolean operators, or browse by filters.

        Supported syntax:
            - Phrases: "world models"
            - AND: world AND models (implicit between words)
            - OR: video OR image
            - NOT: transformer NOT vision
            - Empty query with filters: browse by conference/year/author

        Args:
            query: Search query with optional Boolean operators (can be empty if filters set)
            conferences: List of conference names to filter by
            year_min: Minimum year filter
            year_max: Maximum year filter
            author: Author name to filter by (partial match)
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            Dict with results, total count, and query info
        """
        query = query.strip() if query else ""
        author_filter = author.strip().lower() if author else None
        has_filters = conferences or year_min or year_max or author_filter
        
        # Parse Boolean query (if any)
        bq = BooleanQuery.parse(query) if query else None
        
        # If no query and no filters, return empty
        if not query and not has_filters:
            return {
                "results": [],
                "total": 0,
                "query": query,
                "offset": offset,
                "limit": limit,
            }

        # Filter and score papers
        scored_papers = []
        conferences_set = set(conferences) if conferences else None

        for paper in self.papers:
            # Apply conference/year filters
            if conferences_set and paper.get("conference") not in conferences_set:
                continue

            paper_year = paper.get("year", 0)
            if year_min and paper_year < year_min:
                continue
            if year_max and paper_year > year_max:
                continue
            
            # Apply author filter
            if author_filter:
                paper_authors = (paper.get("authors") or "").lower()
                if author_filter not in paper_authors:
                    continue

            # If we have a query, check Boolean match
            if bq and bq.has_terms():
                text = (paper.get("title") or "") + " " + (paper.get("abstract") or "")
                if not bq.matches(text):
                    continue
                score = self._score_paper(paper, bq)
            else:
                # No query, just browsing by filters - sort by year
                score = paper.get("year", 0)

            scored_papers.append((score, paper))

        # Sort by score (descending), then by year (descending)
        scored_papers.sort(key=lambda x: (-x[0], -x[1].get("year", 0)))
        
        # For browse mode (no query), we already sorted by year via score

        total = len(scored_papers)

        # Apply pagination
        paginated = scored_papers[offset : offset + limit]

        # Format results
        results = []
        for score, paper in paginated:
            results.append({
                "id": paper["id"],
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "authors": paper.get("authors", ""),
                "authors_data": paper.get("authors_data", []),
                "year": paper.get("year", 0),
                "conference": paper.get("conference", ""),
                "url": paper.get("url", ""),
                "github": paper.get("github", ""),
                "project": paper.get("project", ""),
                "score": round(score, 2),
            })

        return {
            "results": results,
            "total": total,
            "query": query,
            "offset": offset,
            "limit": limit,
            "parsed": {
                "phrases": bq.phrases if bq else [],
                "and_terms": bq.and_terms if bq else [],
                "or_terms": bq.or_terms if bq else [],
                "not_terms": bq.not_terms if bq else [],
            }
        }


# Global instance
search_engine = PaperSearchEngine()
