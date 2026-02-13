"""
Search Engine for Academic Papers
=================================
Simple but effective keyword search with relevance scoring.
"""

import json
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

from config import PAPERS_JSON, TITLE_WEIGHT, ABSTRACT_WEIGHT, PHRASE_MULTIPLIER


class PaperSearchEngine:
    """In-memory search engine for academic papers."""

    def __init__(self):
        self.papers = []
        self.papers_by_id = {}
        self.conferences = set()
        self.years = set()
        self._loaded = False

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

    def _parse_query(self, query: str) -> tuple:
        """Parse query into phrases and keywords."""
        phrases = []
        keywords = []

        # Extract quoted phrases
        phrase_pattern = r'"([^"]+)"'
        for match in re.finditer(phrase_pattern, query):
            phrases.append(match.group(1).lower())

        # Remove phrases and get remaining keywords
        remaining = re.sub(phrase_pattern, "", query)
        keywords = [w.lower() for w in remaining.split() if len(w) >= 2]

        return phrases, keywords

    def _score_paper(self, paper: dict, phrases: list, keywords: list) -> float:
        """Calculate relevance score for a paper."""
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        score = 0.0

        # Score phrase matches (higher priority)
        for phrase in phrases:
            if phrase in title:
                score += TITLE_WEIGHT * PHRASE_MULTIPLIER * 2
            if phrase in abstract:
                score += ABSTRACT_WEIGHT * PHRASE_MULTIPLIER

        # Score keyword matches
        for keyword in keywords:
            # Title matches
            title_count = title.count(keyword)
            if title_count > 0:
                score += TITLE_WEIGHT * min(title_count, 3)  # Cap at 3 matches

            # Abstract matches
            abstract_count = abstract.count(keyword)
            if abstract_count > 0:
                score += ABSTRACT_WEIGHT * min(abstract_count, 5)  # Cap at 5 matches

        return score

    def search(
        self,
        query: str,
        conferences: Optional[list] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """
        Search papers by query with optional filters.

        Args:
            query: Search query (supports phrases in quotes)
            conferences: List of conference names to filter by
            year_min: Minimum year filter
            year_max: Maximum year filter
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            Dict with results, total count, and query info
        """
        if not query or not query.strip():
            return {
                "results": [],
                "total": 0,
                "query": query,
                "offset": offset,
                "limit": limit,
            }

        phrases, keywords = self._parse_query(query)

        if not phrases and not keywords:
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
            # Apply filters
            if conferences_set and paper.get("conference") not in conferences_set:
                continue

            paper_year = paper.get("year", 0)
            if year_min and paper_year < year_min:
                continue
            if year_max and paper_year > year_max:
                continue

            # Calculate score
            score = self._score_paper(paper, phrases, keywords)

            if score > 0:
                scored_papers.append((score, paper))

        # Sort by score (descending), then by year (descending)
        scored_papers.sort(key=lambda x: (-x[0], -x[1].get("year", 0)))

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
                "authors_data": paper.get("authors_data", []),  # Structured author data with links
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
            "phrases": phrases,
            "keywords": keywords,
        }


# Global instance
search_engine = PaperSearchEngine()
