"""
Author Expertise Modeling and Analysis
Understands author capabilities beyond paper count
"""
from typing import List, Dict, Set, Tuple
from collections import Counter
from datetime import datetime

# Import centralized configuration
from intelligent_config import (
    VENUE_MIN_PAPERS_MULTI_FIELD,
    get_required_fields_count
)


class AuthorExpertiseAnalyzer:
    """
    Analyzes author expertise, seniority, and research focus
    """

    # Top-tier venues by field
    TOP_VENUES = {
        "ml": ["NeurIPS", "ICML", "ICLR"],
        "cv": ["CVPR", "ICCV", "ECCV"],
        "nlp": ["ACL", "EMNLP", "NAACL"],
        "robotics": ["RSS", "CoRL", "ICRA"],
        "ai": ["AAAI", "IJCAI"],
        "general": ["Nature", "Science"]
    }

    def __init__(self):
        pass

    def estimate_seniority(self, papers: List[Dict]) -> Dict:
        """
        Estimate author's career stage based on publication record
        """
        if not papers:
            return {
                "level": "unknown",
                "confidence": 0.0,
                "signals": []
            }

        # Sort by year
        sorted_papers = sorted(papers, key=lambda p: p.get("year", 0))

        first_year = sorted_papers[0].get("year")
        last_year = sorted_papers[-1].get("year")
        current_year = datetime.now().year

        years_active = current_year - first_year if first_year else 0
        total_papers = len(papers)
        papers_per_year = total_papers / max(years_active, 1)

        # Recent activity
        recent_papers = [p for p in papers if p.get("year", 0) >= current_year - 2]
        is_active = len(recent_papers) >= 2

        # First author analysis
        first_author_count = sum(1 for p in papers if p.get("is_first_author", False))
        first_author_ratio = first_author_count / total_papers if total_papers > 0 else 0

        # Venue quality
        top_venue_count = sum(
            1 for p in papers
            if any(p.get("conference") in venues for venues in self.TOP_VENUES.values())
        )
        top_venue_ratio = top_venue_count / total_papers if total_papers > 0 else 0

        # Seniority rules
        signals = []
        level = "unknown"
        confidence = 0.0

        if years_active <= 3 and total_papers <= 5:
            level = "phd_student"
            confidence = 0.8
            signals.append("Few years active, low paper count")
        elif years_active <= 5 and total_papers <= 10 and first_author_ratio > 0.6:
            level = "phd_student_advanced"
            confidence = 0.7
            signals.append("5 years, mostly first author")
        elif years_active <= 7 and total_papers <= 15:
            level = "postdoc"
            confidence = 0.6
            signals.append("5-7 years, moderate papers")
        elif years_active >= 8 and total_papers >= 20:
            if papers_per_year >= 3:
                level = "senior_researcher"
                confidence = 0.8
                signals.append("High productivity, 8+ years")
            else:
                level = "mid_career"
                confidence = 0.7
                signals.append("8+ years, steady output")
        elif years_active >= 15 and total_papers >= 50:
            level = "professor"
            confidence = 0.9
            signals.append("15+ years, 50+ papers")
        else:
            level = "mid_career"
            confidence = 0.5
            signals.append("Default classification")

        # Adjust for top venues
        if top_venue_ratio > 0.6:
            confidence += 0.1
            signals.append(f"{int(top_venue_ratio*100)}% top venues")

        # Adjust for activity
        if not is_active:
            signals.append("Not recently active")
            if level not in ["professor", "senior_researcher"]:
                confidence *= 0.7

        # Detect founders from affiliation
        affiliation_text = " ".join(p.get("affiliation", "") for p in papers).lower()
        is_founder = any(keyword in affiliation_text for keyword in [
            "founder", "co-founder", "ceo", "cto", "chief", "startup"
        ])
        is_cofounder = "co-founder" in affiliation_text or "cofounder" in affiliation_text

        return {
            "level": level,
            "confidence": min(confidence, 1.0),
            "signals": signals,
            "years_active": years_active,
            "total_papers": total_papers,
            "papers_per_year": round(papers_per_year, 2),
            "first_author_ratio": round(first_author_ratio, 2),
            "top_venue_ratio": round(top_venue_ratio, 2),
            "is_active": is_active,
            "is_founder": is_founder and not is_cofounder,
            "is_cofounder": is_cofounder
        }

    def analyze_venues(self, papers: List[Dict]) -> Dict:
        """
        Analyze publication venues to understand research focus
        """
        venues = [p.get("conference") for p in papers if p.get("conference")]
        venue_counts = Counter(venues)

        # Categorize venues
        venue_categories = {
            "ml": [],
            "cv": [],
            "nlp": [],
            "robotics": [],
            "ai": [],
            "other": []
        }

        for venue, count in venue_counts.items():
            categorized = False
            for category, category_venues in self.TOP_VENUES.items():
                if venue in category_venues:
                    venue_categories[category].append({
                        "venue": venue,
                        "count": count
                    })
                    categorized = True
                    break
            if not categorized:
                venue_categories["other"].append({
                    "venue": venue,
                    "count": count
                })

        # Determine primary field
        field_scores = {
            field: sum(v["count"] for v in venues_list)
            for field, venues_list in venue_categories.items()
            if venues_list
        }

        primary_field = max(field_scores.items(), key=lambda x: x[1])[0] if field_scores else "unknown"

        # Interdisciplinary score
        active_fields = sum(1 for score in field_scores.values() if score >= 3)
        is_interdisciplinary = active_fields >= 2

        return {
            "venue_distribution": venue_categories,
            "venue_counts": dict(venue_counts.most_common()),
            "primary_field": primary_field,
            "field_scores": field_scores,
            "is_interdisciplinary": is_interdisciplinary,
            "active_fields": active_fields
        }

    def analyze_collaboration_network(self, papers: List[Dict]) -> Dict:
        """
        Analyze coauthors and collaboration patterns
        """
        all_coauthors = []

        for paper in papers:
            authors_data = paper.get("authors_data", [])
            for author_data in authors_data:
                coauthor = author_data.get("name")
                if coauthor:
                    all_coauthors.append(coauthor)

        # Count collaborations
        coauthor_counts = Counter(all_coauthors)

        # Remove self (will be most common)
        if coauthor_counts:
            top_author = coauthor_counts.most_common(1)[0][0]
            del coauthor_counts[top_author]

        # Frequent collaborators (3+ papers together)
        frequent_collaborators = {
            author: count
            for author, count in coauthor_counts.items()
            if count >= 3
        }

        # Unique collaborators
        unique_collaborators = len(coauthor_counts)

        # Collaboration diversity (higher = more diverse network)
        if unique_collaborators > 0:
            diversity = unique_collaborators / len(papers)
        else:
            diversity = 0

        return {
            "unique_collaborators": unique_collaborators,
            "frequent_collaborators": frequent_collaborators,
            "top_collaborators": dict(coauthor_counts.most_common(10)),
            "collaboration_diversity": round(diversity, 2)
        }

    def check_venue_intersection(
        self,
        papers: List[Dict],
        required_fields: List[str],
        use_or_logic: bool = True
    ) -> Tuple[bool, Dict]:
        """
        Check if author publishes at venues for required fields

        Args:
            papers: Author's papers
            required_fields: e.g., ["ml", "cv"] for RL + CV expert
            use_or_logic: If True, allow missing 1 field (N-1 logic)
                         If False, require ALL fields (strict AND logic)

        Returns:
            (has_sufficient_venues, details)
        """
        venue_analysis = self.analyze_venues(papers)
        field_scores = venue_analysis["field_scores"]

        # Check each required field
        field_presence = {}
        for field in required_fields:
            score = field_scores.get(field, 0)
            field_presence[field] = {
                "has_papers": score > 0,
                "paper_count": score,
                # Use configurable threshold (default 2 for multi-field)
                "is_significant": score >= VENUE_MIN_PAPERS_MULTI_FIELD
            }

        # Strategy 1: Original strict logic - ALL fields must be significant
        has_all = all(f["has_papers"] for f in field_presence.values())
        has_significant_all = all(f["is_significant"] for f in field_presence.values())

        # Strategy 2: OR logic - At least N-1 fields significant (NEW)
        if use_or_logic:
            significant_count = sum(1 for f in field_presence.values() if f["is_significant"])
            required_count = get_required_fields_count(len(required_fields))
            has_sufficient = significant_count >= required_count
        else:
            # Strict AND logic
            has_sufficient = has_significant_all

        return has_sufficient, {
            "field_presence": field_presence,
            "has_all_fields": has_all,
            "has_significant_all": has_significant_all,
            "has_sufficient": has_sufficient,
            "significant_count": sum(1 for f in field_presence.values() if f["is_significant"]),
            "required_count": get_required_fields_count(len(required_fields)) if use_or_logic else len(required_fields),
            "venue_distribution": venue_analysis["venue_distribution"],
            "strategy": "or_logic" if use_or_logic else "strict_and"
        }

    def compute_impact_score(self, papers: List[Dict]) -> Dict:
        """
        Compute author impact beyond paper count
        """
        # Recency scoring
        current_year = datetime.now().year
        recency_score = 0
        for paper in papers:
            year = paper.get("year", 0)
            years_ago = current_year - year
            if years_ago <= 1:
                recency_score += 2.0
            elif years_ago <= 3:
                recency_score += 1.5
            elif years_ago <= 5:
                recency_score += 1.0
            else:
                recency_score += 0.5

        # Venue quality scoring
        venue_score = 0
        for paper in papers:
            venue = paper.get("conference")
            is_top = any(
                venue in venues
                for venues in self.TOP_VENUES.values()
            )
            if is_top:
                venue_score += 2.0
            else:
                venue_score += 0.5

        # Normalize scores
        total_papers = len(papers) if papers else 1
        normalized_recency = recency_score / total_papers
        normalized_venue = venue_score / total_papers

        # Combined impact
        impact = (normalized_recency * 0.4 + normalized_venue * 0.6) * 10

        return {
            "impact_score": round(impact, 2),
            "recency_score": round(normalized_recency, 2),
            "venue_score": round(normalized_venue, 2),
            "total_papers": total_papers
        }

    def generate_author_profile(
        self,
        author_name: str,
        papers: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive author profile for intelligent matching
        """
        if not papers:
            return {
                "author_name": author_name,
                "has_data": False
            }

        seniority = self.estimate_seniority(papers)
        venues = self.analyze_venues(papers)
        network = self.analyze_collaboration_network(papers)
        impact = self.compute_impact_score(papers)

        return {
            "author_name": author_name,
            "has_data": True,
            "seniority": seniority,
            "venues": venues,
            "collaboration": network,
            "impact": impact,
            "summary": {
                "level": seniority["level"],
                "primary_field": venues["primary_field"],
                "is_interdisciplinary": venues["is_interdisciplinary"],
                "is_active": seniority["is_active"],
                "impact_score": impact["impact_score"]
            }
        }


# Global instance
expertise_analyzer = AuthorExpertiseAnalyzer()
