"""
Candidate Enrichment Module

Enriches candidate profiles by scraping their online presence:
- Google Scholar (current affiliation, position, bio)
- Homepage (detailed bio, research interests, current role)
- LinkedIn (industry vs academia, current position)
- Web search fallback (if no links available)

Enables intelligent filtering like "exclude professors" or "industry only"
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CandidateEnricher:
    """Enriches candidate profiles with web-scraped data"""

    def __init__(self):
        self.cache = {}  # Cache enriched data to avoid repeated scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def enrich_candidate(self, candidate: Dict) -> Dict:
        """
        Enrich a single candidate with web-scraped data

        Args:
            candidate: Candidate dict with name, links, affiliation

        Returns:
            Enriched candidate with additional fields:
            - current_position: "Professor", "Postdoc", "Research Scientist", etc.
            - current_affiliation: Latest affiliation
            - is_professor: Boolean
            - is_industry: Boolean
            - bio: Short bio text
            - interests: List of research interests
        """
        name = candidate.get('name', '')

        # Check cache first
        if name in self.cache:
            logger.info(f"[ENRICH] Using cached data for {name}")
            return {**candidate, **self.cache[name]}

        enriched_data = {
            'current_position': None,
            'current_affiliation': candidate.get('affiliation', None),
            'is_professor': False,
            'is_industry': False,
            'is_academic': False,
            'is_postdoc': False,
            'bio': None,
            'interests': [],
            'enrichment_sources': []
        }

        links = candidate.get('links', {})

        # Try Google Scholar first (most reliable for academics)
        if 'google_scholar' in links and links['google_scholar']:
            scholar_data = self._scrape_google_scholar(links['google_scholar'])
            if scholar_data:
                enriched_data.update(scholar_data)
                enriched_data['enrichment_sources'].append('google_scholar')

        # Try homepage for detailed bio
        if 'homepage' in links and links['homepage']:
            homepage_data = self._scrape_homepage(links['homepage'])
            if homepage_data:
                # Merge with existing data (Scholar takes precedence for affiliation)
                if not enriched_data['current_position']:
                    enriched_data['current_position'] = homepage_data.get('current_position')
                if not enriched_data['bio']:
                    enriched_data['bio'] = homepage_data.get('bio')
                if homepage_data.get('interests'):
                    enriched_data['interests'].extend(homepage_data['interests'])
                enriched_data['enrichment_sources'].append('homepage')

        # Fallback: Web search if no links or no position found
        if not enriched_data['current_position'] or not enriched_data['current_affiliation']:
            search_data = self._web_search_fallback(name, candidate.get('affiliation'))
            if search_data:
                if not enriched_data['current_position']:
                    enriched_data['current_position'] = search_data.get('current_position')
                if not enriched_data['current_affiliation']:
                    enriched_data['current_affiliation'] = search_data.get('current_affiliation')
                if not enriched_data['bio']:
                    enriched_data['bio'] = search_data.get('bio')
                enriched_data['enrichment_sources'].append('web_search')

        # Classify based on position
        position = enriched_data.get('current_position', '').lower()
        affiliation = enriched_data.get('current_affiliation', '').lower()

        # Check if professor
        professor_keywords = ['professor', 'prof.', 'chair', 'faculty']
        enriched_data['is_professor'] = any(kw in position for kw in professor_keywords)

        # Check if postdoc
        postdoc_keywords = ['postdoc', 'post-doc', 'postdoctoral']
        enriched_data['is_postdoc'] = any(kw in position for kw in postdoc_keywords)

        # Check if industry (not .edu, or has industry keywords)
        industry_keywords = ['research scientist', 'engineer', 'researcher at', 'scientist at', 'staff', 'principal']
        academic_indicators = ['.edu', 'university', 'college', 'institute', 'academia']

        has_industry_keyword = any(kw in position for kw in industry_keywords)
        has_academic_indicator = any(ind in affiliation for ind in academic_indicators)

        enriched_data['is_industry'] = has_industry_keyword and not has_academic_indicator
        enriched_data['is_academic'] = has_academic_indicator or enriched_data['is_professor']

        # Cache the result
        self.cache[name] = enriched_data

        logger.info(f"[ENRICH] {name}: {enriched_data['current_position']} at {enriched_data['current_affiliation']}")

        return {**candidate, **enriched_data}

    def _scrape_google_scholar(self, url: str) -> Optional[Dict]:
        """Scrape Google Scholar profile"""
        try:
            logger.info(f"[ENRICH] Scraping Google Scholar: {url}")

            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract current affiliation
            affiliation_elem = soup.find('div', class_='gsc_prf_il')
            affiliation = affiliation_elem.get_text(strip=True) if affiliation_elem else None

            # Extract position/bio
            bio_elem = soup.find('div', class_='gsc_prf_i')
            bio = bio_elem.get_text(strip=True) if bio_elem else None

            # Extract research interests
            interests = []
            interest_elems = soup.find_all('a', class_='gsc_prf_inta')
            for elem in interest_elems:
                interests.append(elem.get_text(strip=True))

            # Try to extract position from affiliation text
            position = None
            if affiliation:
                # Common patterns: "Professor at MIT", "Postdoc at Stanford", etc.
                position_match = re.search(r'(Professor|Associate Professor|Assistant Professor|Postdoc|PhD Student|Research Scientist|Staff Scientist|Principal Scientist|Senior Scientist)', affiliation, re.IGNORECASE)
                if position_match:
                    position = position_match.group(1)

            return {
                'current_affiliation': affiliation,
                'current_position': position,
                'bio': bio,
                'interests': interests
            }

        except Exception as e:
            logger.warning(f"[ENRICH] Failed to scrape Google Scholar: {e}")
            return None

    def _scrape_homepage(self, url: str) -> Optional[Dict]:
        """Scrape personal homepage"""
        try:
            logger.info(f"[ENRICH] Scraping homepage: {url}")

            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract text content
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()

            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = ' '.join(lines)

            # Look for position keywords
            position = None
            position_patterns = [
                r'I am (?:a |an )?(Professor|Associate Professor|Assistant Professor|Postdoc|Postdoctoral|PhD Student|Research Scientist|Staff Scientist)',
                r'(Professor|Associate Professor|Assistant Professor|Postdoc|Postdoctoral|PhD Student|Research Scientist|Staff Scientist) at',
                r'currently (?:a |an )?(Professor|Associate Professor|Assistant Professor|Postdoc|Postdoctoral|PhD Student|Research Scientist|Staff Scientist)',
            ]

            for pattern in position_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    position = match.group(1)
                    break

            # Extract bio (first 500 chars)
            bio = text[:500] if text else None

            # Try to find research interests section
            interests = []
            interests_match = re.search(r'(?:research interests?|interests?)[:\s]+([^\.]+)', text, re.IGNORECASE)
            if interests_match:
                interests_text = interests_match.group(1)
                # Split by common delimiters
                interests = [i.strip() for i in re.split(r'[,;]', interests_text) if i.strip()][:5]

            return {
                'current_position': position,
                'bio': bio,
                'interests': interests
            }

        except Exception as e:
            logger.warning(f"[ENRICH] Failed to scrape homepage: {e}")
            return None

    def _web_search_fallback(self, name: str, affiliation: str) -> Optional[Dict]:
        """
        Fallback: Web search for candidate info

        Searches for "[name] [affiliation] position" or "[name] researcher"
        and extracts position/affiliation from search results
        """
        try:
            logger.info(f"[ENRICH] Web searching for: {name}")

            # Try with affiliation first
            query = f'"{name}" {affiliation} position' if affiliation else f'"{name}" researcher position'

            # Use simple requests to search (in production, use proper web search API)
            # For now, return None - this would need WebSearch API integration
            # The architecture is in place, but actual implementation needs API keys

            return None

        except Exception as e:
            logger.warning(f"[ENRICH] Web search failed: {e}")
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
                - position_contains: List[str] (must contain at least one)
                - position_excludes: List[str] (must not contain any)

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
                logger.info(f"[FILTER] Excluding professor: {candidate['name']}")
                continue

            if filters.get('exclude_postdocs') and candidate.get('is_postdoc'):
                logger.info(f"[FILTER] Excluding postdoc: {candidate['name']}")
                continue

            if filters.get('exclude_academics') and candidate.get('is_academic'):
                logger.info(f"[FILTER] Excluding academic: {candidate['name']}")
                continue

            if filters.get('industry_only') and not candidate.get('is_industry'):
                logger.info(f"[FILTER] Not industry: {candidate['name']}")
                continue

            if filters.get('academic_only') and not candidate.get('is_academic'):
                logger.info(f"[FILTER] Not academic: {candidate['name']}")
                continue

            # Position contains filters
            if filters.get('position_contains'):
                position = candidate.get('current_position', '').lower()
                if not any(kw.lower() in position for kw in filters['position_contains']):
                    logger.info(f"[FILTER] Position doesn't match: {candidate['name']}")
                    continue

            # Position excludes filters
            if filters.get('position_excludes'):
                position = candidate.get('current_position', '').lower()
                if any(kw.lower() in position for kw in filters['position_excludes']):
                    logger.info(f"[FILTER] Position excluded: {candidate['name']}")
                    continue

            filtered.append(candidate)

        logger.info(f"[FILTER] {len(filtered)}/{len(candidates)} candidates passed enrichment filters")
        return filtered


# Global instance
candidate_enricher = None


def initialize():
    """Initialize the candidate enricher"""
    global candidate_enricher
    if candidate_enricher is None:
        candidate_enricher = CandidateEnricher()
        logger.info("[ENRICH] Candidate enricher initialized")


def enrich_candidates(candidates: List[Dict], use_enrichment: bool = True) -> List[Dict]:
    """
    Enrich a list of candidates with web-scraped data

    Args:
        candidates: List of candidate dicts
        use_enrichment: Whether to actually scrape (can disable for speed)

    Returns:
        List of enriched candidates
    """
    if not use_enrichment or candidate_enricher is None:
        return candidates

    enriched = []
    for candidate in candidates:
        try:
            enriched_candidate = candidate_enricher.enrich_candidate(candidate)
            enriched.append(enriched_candidate)
            time.sleep(0.5)  # Rate limiting
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

    if 'exclude postdoc' in query_lower or 'no postdoc' in query_lower:
        filters['exclude_postdocs'] = True

    if 'exclude academic' in query_lower or 'no academic' in query_lower:
        filters['exclude_academics'] = True

    # Detect requirements
    if 'industry only' in query_lower or 'from industry' in query_lower:
        filters['industry_only'] = True

    if 'academic only' in query_lower or 'academia only' in query_lower:
        filters['academic_only'] = True

    if 'postdoc' in query_lower and 'exclude' not in query_lower:
        filters['position_contains'] = ['postdoc']

    # Apply filters if any detected
    if filters and candidate_enricher:
        return candidate_enricher.apply_enrichment_filters(candidates, filters)

    return candidates
