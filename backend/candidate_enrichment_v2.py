"""
Candidate Enrichment Module v2 - SOTA Approach

Uses WebSearch + LLM extraction instead of manual scraping.
Modern AI agents (Perplexity, Claude) use this approach:
1. WebSearch for candidate info
2. LLM reads search snippets
3. LLM extracts structured data

Much better than BeautifulSoup scraping (no rate limits, bot detection, broken HTML)
"""

import os
import json
import time
from typing import Dict, List, Optional
import logging

# Try to import web search library (free, no API key needed)
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False
    print("[ENRICH] ddgs not installed. Install with: pip install ddgs")

# Optional: Anthropic Claude API
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[ENRICH] anthropic package not installed. Enrichment features disabled.")

logger = logging.getLogger(__name__)


class CandidateEnricherV2:
    """
    SOTA candidate enrichment using WebSearch + LLM

    No web scraping - uses search APIs + Claude to extract info
    """

    def __init__(self):
        self.cache = {}  # Cache enriched data
        self.claude = None
        self.ddgs = None

        # Initialize Claude if available
        if HAS_ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.claude = Anthropic(api_key=api_key)
                logger.info("[ENRICH] Claude API initialized for enrichment")
            else:
                logger.warning("[ENRICH] ANTHROPIC_API_KEY not set - enrichment disabled")

        # Initialize DuckDuckGo search if available
        if HAS_DDGS:
            self.ddgs = DDGS()
            logger.info("[ENRICH] DuckDuckGo search initialized")

    def _web_search_default(self, query: str) -> List[Dict]:
        """
        Default web search implementation using DuckDuckGo

        Returns list of search results with 'title' and 'snippet' fields
        """
        if not self.ddgs:
            return []

        try:
            results = []
            # DuckDuckGo text search
            ddgs_results = self.ddgs.text(query, max_results=5)

            for result in ddgs_results:
                results.append({
                    'title': result.get('title', ''),
                    'snippet': result.get('body', ''),
                    'url': result.get('href', '')
                })

            return results

        except Exception as e:
            logger.error(f"[ENRICH] DuckDuckGo search failed: {e}")
            return []

    def enrich_candidate(self, candidate: Dict, web_search_fn: callable = None) -> Dict:
        """
        Enrich candidate using WebSearch + LLM extraction

        Args:
            candidate: Candidate dict with name, affiliation, papers
            web_search_fn: Optional custom web search function
                          If not provided, uses DuckDuckGo search
                          Signature: web_search_fn(query) -> List[{'title': str, 'snippet': str}]

        Returns:
            Enriched candidate with:
            - current_position: "Professor", "Research Scientist", etc.
            - current_affiliation: Latest affiliation
            - is_professor: Boolean
            - is_industry: Boolean
            - is_academic: Boolean
            - bio_snippet: Short bio from search results
        """
        name = candidate.get('name', '')

        # Check cache first
        if name in self.cache:
            logger.info(f"[ENRICH] Using cached data for {name}")
            return {**candidate, **self.cache[name]}

        # Fallback if no Claude API
        if not self.claude:
            logger.info(f"[ENRICH] Skipping enrichment for {name} (no Claude API)")
            return candidate

        try:
            # Search for current position
            affiliation = candidate.get('affiliation', '')
            search_query = f'"{name}" current position affiliation {affiliation}'

            logger.info(f"[ENRICH] Searching for: {name}")

            # Perform web search (use provided function or default to DuckDuckGo)
            if web_search_fn:
                search_results = web_search_fn(search_query)
            else:
                search_results = self._web_search_default(search_query)

            if not search_results:
                logger.warning(f"[ENRICH] No search results for {name}")
                return candidate

            # Use Claude to extract structured info from search results
            enriched_data = self._extract_with_llm(name, search_results, affiliation)

            # Cache the result
            if enriched_data:
                self.cache[name] = enriched_data
                logger.info(f"[ENRICH] ✓ {name}: {enriched_data.get('current_position')} at {enriched_data.get('current_affiliation')}")
                return {**candidate, **enriched_data}

        except Exception as e:
            logger.error(f"[ENRICH] Failed to enrich {name}: {e}")

        return candidate

    def _extract_with_llm(self, name: str, search_results: List[Dict], known_affiliation: str) -> Optional[Dict]:
        """
        Use Claude to extract position/affiliation from search results

        This is the SOTA approach - LLM reads clean search snippets and extracts structured data
        """
        if not self.claude or not search_results:
            return None

        try:
            # Format search results as context
            context_parts = []
            for i, result in enumerate(search_results[:5], 1):  # Top 5 results
                title = result.get('title', '')
                snippet = result.get('snippet', result.get('description', ''))
                context_parts.append(f"{i}. {title}\n   {snippet}")

            context = "\n\n".join(context_parts)

            prompt = f"""You are analyzing search results to determine a researcher's current position and affiliation.

Researcher: {name}
Known affiliation (from papers): {known_affiliation}

Search Results:
{context}

Extract the following information:
1. current_position: Their current job title (e.g., "Professor", "Assistant Professor", "Postdoc", "Research Scientist", "Staff Scientist", "PhD Student", etc.)
2. current_affiliation: Their current institution/company
3. is_professor: true if they are any type of professor (Professor, Associate Professor, Assistant Professor)
4. is_postdoc: true if they are a postdoctoral researcher
5. is_industry: true if they work at a company (not .edu, not university)
6. is_academic: true if they work at a university or research institute
7. bio_snippet: One sentence summary of their work (if available)

If information is not found in search results, use null.

Return JSON only:
{{
  "current_position": "string or null",
  "current_affiliation": "string or null",
  "is_professor": boolean,
  "is_postdoc": boolean,
  "is_industry": boolean,
  "is_academic": boolean,
  "bio_snippet": "string or null"
}}"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)

            # Add enrichment source
            result['enrichment_source'] = 'web_search_llm'

            return result

        except Exception as e:
            logger.error(f"[ENRICH] LLM extraction failed for {name}: {e}")
            return None

    def apply_enrichment_filters(self, candidates: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply enrichment-based filters to candidates

        Args:
            candidates: List of enriched candidates
            filters: Dict of filter conditions
                - exclude_professors: bool
                - exclude_postdocs: bool
                - exclude_academics: bool
                - industry_only: bool
                - academic_only: bool

        Returns:
            Filtered list of candidates
        """
        filtered = []

        for candidate in candidates:
            # Skip if not enriched
            if not candidate.get('current_position'):
                # If no enrichment data, include by default (can't filter)
                filtered.append(candidate)
                continue

            # Apply filters
            if filters.get('exclude_professors') and candidate.get('is_professor'):
                logger.info(f"[FILTER] ✗ Excluding professor: {candidate['name']}")
                continue

            if filters.get('exclude_postdocs') and candidate.get('is_postdoc'):
                logger.info(f"[FILTER] ✗ Excluding postdoc: {candidate['name']}")
                continue

            if filters.get('exclude_academics') and candidate.get('is_academic'):
                logger.info(f"[FILTER] ✗ Excluding academic: {candidate['name']}")
                continue

            if filters.get('industry_only') and not candidate.get('is_industry'):
                logger.info(f"[FILTER] ✗ Not industry: {candidate['name']}")
                continue

            if filters.get('academic_only') and not candidate.get('is_academic'):
                logger.info(f"[FILTER] ✗ Not academic: {candidate['name']}")
                continue

            # Passed all filters
            filtered.append(candidate)

        logger.info(f"[FILTER] ✓ {len(filtered)}/{len(candidates)} candidates passed enrichment filters")
        return filtered


# Global instance
candidate_enricher = None


def initialize():
    """Initialize the candidate enricher v2"""
    global candidate_enricher
    if candidate_enricher is None:
        candidate_enricher = CandidateEnricherV2()
        logger.info("[ENRICH] Candidate enricher v2 initialized (WebSearch + LLM)")


def enrich_candidates(candidates: List[Dict], use_enrichment: bool = True, web_search_fn: callable = None) -> List[Dict]:
    """
    Enrich a list of candidates with web-searched data

    Args:
        candidates: List of candidate dicts
        use_enrichment: Whether to actually enrich (can disable for speed)
        web_search_fn: Function to perform web search

    Returns:
        List of enriched candidates
    """
    if not use_enrichment or candidate_enricher is None:
        return candidates

    enriched = []
    for i, candidate in enumerate(candidates):
        try:
            logger.info(f"[ENRICH] Enriching {i+1}/{len(candidates)}: {candidate.get('name')}")
            enriched_candidate = candidate_enricher.enrich_candidate(candidate, web_search_fn)
            enriched.append(enriched_candidate)
            time.sleep(1)  # Rate limiting for API calls
        except Exception as e:
            logger.error(f"[ENRICH] Failed to enrich {candidate.get('name')}: {e}")
            enriched.append(candidate)  # Include un-enriched

    return enriched


def filter_by_enrichment(candidates: List[Dict], query: str) -> List[Dict]:
    """
    Parse query for enrichment-based filters and apply them

    Understands phrases like:
    - "exclude professors"
    - "industry only"
    - "no academics"
    - "postdocs only"

    Args:
        candidates: List of enriched candidates
        query: User query string

    Returns:
        Filtered candidates
    """
    query_lower = query.lower()

    filters = {}

    # Detect exclusions
    if 'exclude professor' in query_lower or 'no professor' in query_lower:
        filters['exclude_professors'] = True
        logger.info("[FILTER] Detected: exclude_professors")

    if 'exclude postdoc' in query_lower or 'no postdoc' in query_lower:
        filters['exclude_postdocs'] = True
        logger.info("[FILTER] Detected: exclude_postdocs")

    if 'exclude academic' in query_lower or 'no academic' in query_lower:
        filters['exclude_academics'] = True
        logger.info("[FILTER] Detected: exclude_academics")

    # Detect requirements
    if 'industry only' in query_lower or 'from industry' in query_lower:
        filters['industry_only'] = True
        logger.info("[FILTER] Detected: industry_only")

    if 'academic only' in query_lower or 'academia only' in query_lower:
        filters['academic_only'] = True
        logger.info("[FILTER] Detected: academic_only")

    # Apply filters if any detected
    if filters and candidate_enricher:
        return candidate_enricher.apply_enrichment_filters(candidates, filters)

    return candidates
