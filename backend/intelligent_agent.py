"""
Intelligent Recruiting Agent with Multi-Stage Reasoning
Combines semantic search, expertise modeling, and LLM reasoning
"""
import os
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Import centralized configuration
from intelligent_config import USE_VENUE_OR_LOGIC

# Import structured logging
from logging_config import log_query, log_performance, log_rejection

# Import query cache
from query_cache import query_cache

# Get logger for this module
logger = logging.getLogger(__name__)

# Import candidate enrichment v2 (WebSearch + LLM approach)
try:
    import candidate_enrichment_v2 as candidate_enrichment
    HAS_ENRICHMENT = True
except ImportError:
    HAS_ENRICHMENT = False
    print("[AGENT] candidate_enrichment_v2 module not found. Enrichment features disabled.")

# Optional: Anthropic Claude API
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[AGENT] anthropic package not installed. LLM features will be disabled.")
    print("  Install with: pip install anthropic")


class IntelligentRecruitingAgent:
    """
    Multi-stage intelligent agent that understands complex requirements
    Goes beyond keyword matching to find truly relevant candidates
    """

    def __init__(self, search_engine, semantic_engine, expertise_analyzer):
        self.search_engine = search_engine
        self.semantic_engine = semantic_engine
        self.expertise_analyzer = expertise_analyzer

        # Initialize Claude if available
        self.claude = None
        if HAS_ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.claude = Anthropic(api_key=api_key)
                print("[AGENT] Claude API initialized")
            else:
                print("[AGENT] ANTHROPIC_API_KEY not set in .env")

    def parse_complex_query(self, query: str) -> Dict:
        """
        Use LLM to understand complex query and extract criteria

        Example:
            "Find RL + CV experts for robotics, mid-career, industry experience"
            →
            {
                "topics": ["reinforcement_learning", "computer_vision"],
                "domain": "robotics",
                "seniority": "mid_career",
                "affiliation_type": "industry",
                "min_expertise": 0.3
            }
        """
        if not self.claude:
            # Fallback: Simple keyword extraction
            return self._parse_query_fallback(query)

        try:
            prompt = f"""Analyze this recruiting query and extract structured criteria:

Query: "{query}"

Extract:
1. Primary topics/fields (use standard names: reinforcement_learning, computer_vision, nlp, robotics, video_generation, diffusion_models, gans, meta_learning, etc.)
2. Domain/application area (if mentioned)
3. Seniority level (phd_student, postdoc, mid_career, senior_researcher, professor, or null)
4. Affiliation type (academic, industry, or null)
5. Geographic preference (countries, or null)
6. Minimum years of experience (number or null)
7. Special requirements (novel_methods, top_venues, recent_work, etc.)
8. Exclude professors? (true if query says "no professors", "exclude professors", "early career only", etc.)
9. Exclude senior researchers? (true if query says "no senior", "junior only", etc.)

Return JSON only, no explanation:
{{
  "topics": ["topic1", "topic2"],
  "domain": "string or null",
  "seniority": "string or null",
  "affiliation_type": "string or null",
  "countries": ["country1"] or null,
  "min_years": number or null,
  "special_requirements": ["req1"] or [],
  "exclude_professors": false,
  "exclude_senior": false
}}"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            parsed = json.loads(content)
            return parsed

        except Exception as e:
            print(f"[AGENT] LLM parsing failed: {e}")
            return self._parse_query_fallback(query)

    def _parse_query_fallback(self, query: str) -> Dict:
        """Fallback query parser using keywords"""
        query_lower = query.lower()

        # Detect topics
        topic_map = {
            "reinforcement learning": "reinforcement_learning",
            "rl": "reinforcement_learning",
            "computer vision": "computer_vision",
            "cv": "computer_vision",
            "video generation": "video_generation",
            "nlp": "nlp",
            "natural language": "nlp",
            "robotics": "robotics",
            "robot": "robotics",
            "diffusion": "diffusion_models",
            "gan": "gans"
        }

        topics = []
        for keyword, topic in topic_map.items():
            if keyword in query_lower:
                if topic not in topics:
                    topics.append(topic)

        # Detect seniority
        seniority = None
        if "student" in query_lower or "phd" in query_lower:
            seniority = "phd_student"
        elif "postdoc" in query_lower:
            seniority = "postdoc"
        elif "senior" in query_lower or "professor" in query_lower:
            seniority = "senior_researcher"
        elif "mid-career" in query_lower or "mid career" in query_lower:
            seniority = "mid_career"

        # Detect affiliation
        affiliation = None
        if "industry" in query_lower or "company" in query_lower:
            affiliation = "industry"
        elif "academic" in query_lower or "university" in query_lower:
            affiliation = "academic"

        # Detect professor exclusion
        exclude_professors = any(phrase in query_lower for phrase in [
            "no professor", "exclude professor", "not professor",
            "no profs", "exclude profs", "early career only",
            "junior researcher", "non-professor", "junior only",
            "early stage", "early-career only"
        ])

        # Detect senior exclusion
        exclude_senior = any(phrase in query_lower for phrase in [
            "no senior", "exclude senior", "junior only",
            "early stage", "early-career only"
        ])

        return {
            "topics": topics,
            "domain": None,
            "seniority": seniority,
            "affiliation_type": affiliation,
            "countries": None,
            "min_years": None,
            "special_requirements": [],
            "exclude_professors": exclude_professors,
            "exclude_senior": exclude_senior
        }

    def multi_stage_search(
        self,
        query: str,
        max_candidates: int = 50,
        use_enrichment: bool = False
    ) -> List[Dict]:
        """
        Multi-stage intelligent candidate search

        Stages:
        1. Parse query with LLM
        2. Multi-modal retrieval (semantic + keyword + venue)
        3. Expertise validation
        4. Venue intersection check
        5. Seniority filtering
        6. [OPTIONAL] Web enrichment (scrape homepages/Scholar for position)
        7. [OPTIONAL] Enrichment-based filtering (exclude professors, industry only, etc.)
        8. Ranking by intelligence score
        """
        start_time = time.time()
        logger.info(f"Starting intelligent search: {query}")
        log_query(query, "start", "initiated", {"max_candidates": max_candidates})

        try:
            # Stage 0: Check cache
            # Parse query first to get criteria for cache key
            stage_start = time.time()
            criteria = self.parse_complex_query(query)
            stage_duration = (time.time() - stage_start) * 1000

            logger.info(f"Parsed criteria: {json.dumps(criteria)}")
            log_query(query, "parse", "success", {
                "criteria": criteria,
                "duration_ms": stage_duration
            })

            # Check cache with parsed criteria
            cached_results = query_cache.get(query, criteria)
            if cached_results is not None:
                cache_duration = (time.time() - start_time) * 1000
                logger.info(f"Cache hit! Returning {len(cached_results)} cached results in {cache_duration:.1f}ms")
                log_query(query, "cache_hit", "success", {
                    "result_count": len(cached_results),
                    "duration_ms": cache_duration
                })
                log_performance("multi_stage_search_cached", cache_duration, {
                    "query": query,
                    "result_count": len(cached_results)
                })
                return cached_results

            # Stage 2: Multi-modal retrieval
            stage_start = time.time()
            candidates_pool = set()

            # 2a. Keyword search for each topic
            for topic in criteria.get("topics", []):
                # Map topic to search keywords
                topic_keywords = {
                    "reinforcement_learning": "reinforcement learning OR RL OR policy gradient",
                    "computer_vision": "computer vision OR CV OR image OR visual",
                    "video_generation": "video generation OR video synthesis",
                    "robotics": "robot OR manipulation OR navigation",
                    "nlp": "natural language OR NLP OR language model",
                    "diffusion_models": "diffusion OR DDPM OR stable diffusion",
                    "gans": "GAN OR generative adversarial",
                }

                search_query = topic_keywords.get(topic, topic.replace("_", " "))
                results = self.search_engine.search(
                    query=search_query,
                    limit=100,
                    countries=criteria.get("countries", []) or []
                )

                for paper in results.get("results", []):
                    for author_data in paper.get("authors_data", []):
                        candidates_pool.add(author_data.get("name"))

            stage_duration = (time.time() - stage_start) * 1000
            logger.info(f"Stage 2 - Retrieval: Found {len(candidates_pool)} candidate authors")
            log_query(query, "retrieval", "success", {
                "candidates_count": len(candidates_pool),
                "duration_ms": stage_duration
            })

            # Stage 3: Get full author data
            stage_start = time.time()
            candidates_with_data = []
            for author_name in candidates_pool:
                profile = self.search_engine.get_author_profile(author_name)
                if profile:
                    candidates_with_data.append(profile)

            stage_duration = (time.time() - stage_start) * 1000
            logger.info(f"Stage 3 - Load Data: Loaded {len(candidates_with_data)} author profiles")
            log_query(query, "load_data", "success", {
                "profiles_loaded": len(candidates_with_data),
                "duration_ms": stage_duration
            })

            # Stage 4: Expertise validation
            stage_start = time.time()
            validated = []
            required_topics = criteria.get("topics", [])
            rejected_count = 0

            for candidate in candidates_with_data:
                papers = candidate.get("papers", [])
                if not papers:
                    rejected_count += 1
                    log_rejection(candidate.get("name"), "expertise_validation", "No papers")
                    continue

                # Check interdisciplinary fit with ADAPTIVE thresholds
                if len(required_topics) >= 2:
                    is_match, details = self.semantic_engine.analyze_interdisciplinary_fit(
                        papers, required_topics,
                        adaptive_threshold=True  # NEW: Enable adaptive thresholds
                    )

                    if not is_match:
                        rejected_count += 1
                        log_rejection(
                            candidate.get("name"),
                            "expertise_validation",
                            "Failed expertise threshold",
                            details
                        )
                        continue  # Doesn't meet threshold in all topics

                    candidate["expertise_details"] = details
                else:
                    # Single topic - just compute expertise
                    expertise = self.semantic_engine.compute_author_expertise(papers)
                    candidate["expertise_details"] = {
                        "expertise": expertise,
                        "meets_threshold": True
                    }

                validated.append(candidate)

            stage_duration = (time.time() - stage_start) * 1000
            logger.info(f"Stage 4 - Expertise: {len(validated)} passed, {rejected_count} rejected")
            log_query(query, "expertise_validation", "success", {
                "passed": len(validated),
                "rejected": rejected_count,
                "duration_ms": stage_duration
            })

            # Stage 5: Venue intersection (if multi-topic)
            if len(required_topics) >= 2:
                stage_start = time.time()
                venue_filtered = []
                venue_rejected = 0

                # Map topics to venue fields
                topic_to_field = {
                    "reinforcement_learning": "ml",
                    "computer_vision": "cv",
                    "nlp": "nlp",
                    "robotics": "robotics",
                    "video_generation": "cv",
                    "diffusion_models": "ml",
                    "gans": "ml"
                }

                required_fields = list(set(
                    topic_to_field.get(t, "ai")
                    for t in required_topics
                ))

                for candidate in validated:
                    papers = candidate.get("papers", [])
                    has_venues, venue_details = self.expertise_analyzer.check_venue_intersection(
                        papers, required_fields,
                        use_or_logic=USE_VENUE_OR_LOGIC  # NEW: Use OR logic from config
                    )

                    if has_venues:
                        candidate["venue_details"] = venue_details
                        venue_filtered.append(candidate)
                    else:
                        venue_rejected += 1
                        log_rejection(
                            candidate.get("name"),
                            "venue_intersection",
                            "Insufficient venue coverage",
                            venue_details
                        )

                validated = venue_filtered
                stage_duration = (time.time() - stage_start) * 1000
                logger.info(f"Stage 5 - Venues: {len(validated)} passed, {venue_rejected} rejected")
                log_query(query, "venue_intersection", "success", {
                    "passed": len(validated),
                    "rejected": venue_rejected,
                    "duration_ms": stage_duration
                })

            # Stage 6: Estimate seniority for all candidates (always run)
            stage_start = time.time()
            for candidate in validated:
                papers = candidate.get("papers", [])
                seniority = self.expertise_analyzer.estimate_seniority(papers)
                candidate["seniority"] = seniority

            stage_duration = (time.time() - stage_start) * 1000
            logger.debug(f"Stage 6 - Seniority Estimation: {len(validated)} candidates analyzed")

            # Stage 6a: Seniority filtering (if requested)
            if criteria.get("seniority"):
                stage_start = time.time()
                seniority_filtered = []
                seniority_rejected = 0

                for candidate in validated:
                    # Match seniority level (with some flexibility)
                    target_level = criteria["seniority"]
                    actual_level = candidate["seniority"]["level"]

                    # Allow adjacent levels
                    level_hierarchy = [
                        "phd_student",
                        "phd_student_advanced",
                        "postdoc",
                        "mid_career",
                        "senior_researcher",
                        "professor"
                    ]

                    if target_level in level_hierarchy and actual_level in level_hierarchy:
                        target_idx = level_hierarchy.index(target_level)
                        actual_idx = level_hierarchy.index(actual_level)

                        # Accept +/- 1 level
                        if abs(target_idx - actual_idx) <= 1:
                            seniority_filtered.append(candidate)
                        else:
                            seniority_rejected += 1
                            log_rejection(
                                candidate.get("name"),
                                "seniority_filter",
                                f"Level mismatch: want {target_level}, has {actual_level}"
                            )
                    else:
                        # Unknown levels - include by default
                        seniority_filtered.append(candidate)

                validated = seniority_filtered
                stage_duration = (time.time() - stage_start) * 1000
                logger.info(f"Stage 6a - Seniority Match: {len(validated)} passed, {seniority_rejected} rejected")
                log_query(query, "seniority_filter", "success", {
                    "passed": len(validated),
                    "rejected": seniority_rejected,
                    "duration_ms": stage_duration
                })

            # Stage 6b: Professor/Senior exclusion (NEW)
            from intelligent_config import EXCLUDE_PROFESSORS_BY_DEFAULT

            exclude_profs = criteria.get("exclude_professors", False) or EXCLUDE_PROFESSORS_BY_DEFAULT
            exclude_senior = criteria.get("exclude_senior", False)

            if exclude_profs or exclude_senior:
                stage_start = time.time()
                exclusion_filtered = []
                exclusion_rejected = 0

                for candidate in validated:
                    actual_level = candidate.get("seniority", {}).get("level", "unknown")

                    # Check exclusions
                    should_exclude = False
                    exclusion_reason = None

                    if exclude_profs and actual_level == "professor":
                        should_exclude = True
                        exclusion_reason = "Professor excluded per query/config"
                    elif exclude_senior and actual_level in ["senior_researcher", "professor"]:
                        should_exclude = True
                        exclusion_reason = "Senior researcher excluded per query/config"

                    if should_exclude:
                        exclusion_rejected += 1
                        log_rejection(
                            candidate.get("name"),
                            "professor_exclusion",
                            exclusion_reason,
                            {"level": actual_level}
                        )
                    else:
                        exclusion_filtered.append(candidate)

                validated = exclusion_filtered
                stage_duration = (time.time() - stage_start) * 1000
                logger.info(f"Stage 6b - Exclusions: {len(validated)} passed, {exclusion_rejected} rejected (profs={exclude_profs}, senior={exclude_senior})")
                log_query(query, "professor_exclusion", "success", {
                    "passed": len(validated),
                    "rejected": exclusion_rejected,
                    "exclude_professors": exclude_profs,
                    "exclude_senior": exclude_senior,
                    "duration_ms": stage_duration
                })

            # Stage 6.5: Web Enrichment (Optional)
            if use_enrichment and HAS_ENRICHMENT:
                stage_start = time.time()
                logger.info(f"Stage 6.5 - Enrichment: Enriching {len(validated)} candidates with web data...")
                validated = candidate_enrichment.enrich_candidates(validated, use_enrichment=True)

                # Stage 6.6: Apply enrichment-based filters
                logger.info("Stage 6.6 - Enrichment Filters: Applying filters from query...")
                validated = candidate_enrichment.filter_by_enrichment(validated, query)

                stage_duration = (time.time() - stage_start) * 1000
                log_query(query, "enrichment", "success", {
                    "candidates_after": len(validated),
                    "duration_ms": stage_duration
                })

            # Stage 7: Rank by intelligence score
            from intelligent_config import (
                PROFESSOR_SCORE_PENALTY,
                SENIOR_RESEARCHER_SCORE_PENALTY,
                EARLY_CAREER_SCORE_BOOST
            )

            stage_start = time.time()
            for candidate in validated:
                papers = candidate.get("papers", [])

                # Compute impact score
                impact = self.expertise_analyzer.compute_impact_score(papers)
                candidate["impact"] = impact

                # Compute base intelligence score
                expertise_score = candidate.get("expertise_details", {}).get("combined_score", 0) * 100
                impact_score = impact["impact_score"]
                paper_count = len(papers)

                # Weighted combination
                base_intelligence_score = (
                    expertise_score * 0.5 +
                    impact_score * 0.3 +
                    min(paper_count / 20.0, 1.0) * 20 * 0.2
                )

                # Apply seniority-based score adjustments (NEW)
                seniority_level = candidate.get("seniority", {}).get("level", "unknown")
                score_multiplier = 1.0

                if seniority_level == "professor":
                    score_multiplier = PROFESSOR_SCORE_PENALTY  # Default 0.7 (30% penalty)
                    candidate["score_adjustment"] = f"Professor penalty ({PROFESSOR_SCORE_PENALTY}x)"
                elif seniority_level == "senior_researcher":
                    score_multiplier = SENIOR_RESEARCHER_SCORE_PENALTY  # Default 0.85 (15% penalty)
                    candidate["score_adjustment"] = f"Senior penalty ({SENIOR_RESEARCHER_SCORE_PENALTY}x)"
                elif seniority_level in ["phd_student", "phd_student_advanced", "postdoc", "mid_career"]:
                    score_multiplier = EARLY_CAREER_SCORE_BOOST  # Default 1.1 (10% boost)
                    candidate["score_adjustment"] = f"Early-career boost ({EARLY_CAREER_SCORE_BOOST}x)"
                else:
                    candidate["score_adjustment"] = "No adjustment"

                # Apply multiplier
                intelligence_score = base_intelligence_score * score_multiplier

                candidate["base_intelligence_score"] = round(base_intelligence_score, 1)
                candidate["intelligence_score"] = round(intelligence_score, 1)
                candidate["seniority_multiplier"] = score_multiplier

            # Sort by intelligence score (after adjustments)
            validated.sort(key=lambda x: x["intelligence_score"], reverse=True)

            stage_duration = (time.time() - stage_start) * 1000
            log_query(query, "ranking", "success", {
                "final_count": len(validated[:max_candidates]),
                "duration_ms": stage_duration
            })

            # Log total performance
            total_duration = (time.time() - start_time) * 1000
            logger.info(f"Search complete: {len(validated[:max_candidates])} results in {total_duration:.1f}ms")
            log_query(query, "complete", "success", {
                "result_count": len(validated[:max_candidates]),
                "total_duration_ms": total_duration
            })
            log_performance("multi_stage_search", total_duration, {
                "query": query,
                "result_count": len(validated[:max_candidates])
            })

            # Cache results before returning
            results = validated[:max_candidates]
            query_cache.set(query, criteria, results)

            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}", exc_info=True)
            log_query(query, "error", "failed", {"error": str(e)})
            raise

    def evaluate_candidate_with_llm(
        self,
        author_name: str,
        papers: List[Dict],
        query: str
    ) -> Dict:
        """
        Deep LLM-based evaluation of a candidate

        Returns match score, reasoning, strengths, and red flags
        """
        if not self.claude:
            return {
                "score": 50,
                "reasoning": "LLM evaluation unavailable (Claude API not configured)",
                "strengths": [],
                "red_flags": []
            }

        try:
            # Build paper summary
            top_papers = sorted(papers, key=lambda p: p.get("year", 0), reverse=True)[:10]
            paper_summary = ""
            for i, paper in enumerate(top_papers, 1):
                year = paper.get("year", "N/A")
                title = paper.get("title", "Untitled")
                conf = paper.get("conference", "Unknown")
                paper_summary += f"{i}. [{year}] {title} ({conf})\n"

            # Build venue list
            venues = list(set(p.get("conference") for p in papers if p.get("conference")))

            prompt = f"""Evaluate this candidate for the recruiting query.

Candidate: {author_name}
Publications: {len(papers)} total

Query: "{query}"

Recent Publications:
{paper_summary}

Venues: {', '.join(venues[:15])}

Analyze:
1. Does this candidate have DEEP expertise in the required areas (not just superficial mentions)?
2. Have they made novel contributions or just applied existing methods?
3. Do they publish at top venues for the required fields?
4. Is this a core research focus or tangential work?
5. What is their career stage/seniority level?
6. Are they a good fit for the query?

Provide:
- Match score: 0-100 (integer)
- Reasoning: 2-3 concise sentences explaining the score
- Strengths: 2-3 key selling points (list)
- Red flags: Any concerns (list, or empty if none)

Return JSON only:
{{
  "score": 85,
  "reasoning": "...",
  "strengths": ["point1", "point2"],
  "red_flags": ["flag1"]
}}"""

            response = self.claude.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)
            return result

        except Exception as e:
            print(f"[AGENT] LLM evaluation failed: {e}")
            return {
                "score": 50,
                "reasoning": f"Evaluation error: {str(e)}",
                "strengths": [],
                "red_flags": []
            }

    def intelligent_search(
        self,
        query: str,
        use_llm_ranking: bool = True,
        max_results: int = 20,
        use_enrichment: bool = False
    ) -> List[Dict]:
        """
        Full intelligent search pipeline

        Returns top candidates with detailed intelligence analysis

        Args:
            query: Search query
            use_llm_ranking: Use Claude for candidate evaluation
            max_results: Maximum number of results to return
            use_enrichment: Scrape web for current position/affiliation (enables "exclude professors" etc.)
        """
        # Stage 1-7: Multi-stage search
        candidates = self.multi_stage_search(query, max_candidates=50, use_enrichment=use_enrichment)

        # Stage 8: LLM re-ranking (optional, for top 20)
        if use_llm_ranking and self.claude and len(candidates) > 0:
            stage_start = time.time()
            logger.info(f"Stage 8 - LLM Eval: Evaluating top candidates")

            for candidate in candidates[:max_results]:
                author_name = candidate.get("name")
                papers = candidate.get("papers", [])

                llm_eval = self.evaluate_candidate_with_llm(
                    author_name, papers, query
                )

                candidate["llm_evaluation"] = llm_eval

                # Combine intelligence score with LLM score
                combined_score = (
                    candidate.get("intelligence_score", 0) * 0.6 +
                    llm_eval.get("score", 50) * 0.4
                )
                candidate["final_score"] = round(combined_score, 1)

            # Re-sort by final score
            candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)

            stage_duration = (time.time() - stage_start) * 1000
            log_performance("llm_evaluation", stage_duration, {
                "query": query,
                "candidates_evaluated": min(len(candidates), max_results)
            })

        return candidates[:max_results]


# Global instance (initialized in app.py)
intelligent_agent = None

def initialize(search_engine, semantic_engine, expertise_analyzer):
    """Initialize the intelligent agent"""
    global intelligent_agent
    intelligent_agent = IntelligentRecruitingAgent(
        search_engine, semantic_engine, expertise_analyzer
    )
    return intelligent_agent
