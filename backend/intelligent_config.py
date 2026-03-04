"""
Centralized Configuration for Intelligent Search System
All thresholds and parameters in one place for easy tuning
"""

# ============================================================================
# EXPERTISE THRESHOLDS - Adaptive based on query complexity
# ============================================================================

# Adaptive thresholds based on number of topics in query
SINGLE_TOPIC_MIN_EXPERTISE = 0.30    # Strict for single topic queries
MULTI_TOPIC_MIN_EXPERTISE = 0.15     # Relaxed for 2 topics (was 0.25 - too strict)
THREE_TOPIC_MIN_EXPERTISE = 0.10     # Very relaxed for 3+ topics

# ============================================================================
# VENUE REQUIREMENTS
# ============================================================================

# Minimum papers required at venues in each field
VENUE_MIN_PAPERS_SINGLE_FIELD = 3    # Papers in one field
VENUE_MIN_PAPERS_MULTI_FIELD = 2     # Lower for interdisciplinary (was 3 - too strict)

# Use OR logic for multi-field requirements
# True: Allow missing 1 field (e.g., 2 out of 3 fields OK)
# False: Require ALL fields (strict AND logic)
USE_VENUE_OR_LOGIC = True

# ============================================================================
# ALGORITHMIC IMPROVEMENTS
# ============================================================================

# Use harmonic mean instead of geometric mean for combining topic scores
# Harmonic mean is less punishing for imbalanced expertise
# Example: geometric(0.4, 0.2) = 0.28, harmonic(0.4, 0.2) = 0.27
USE_HARMONIC_MEAN = True

# Allow dominant topic strategy
# Accept candidates with strong expertise in one topic and moderate in others
# Example: Accept 0.40 + 0.20 instead of requiring 0.30 + 0.30
ALLOW_DOMINANT_TOPIC = True

# Dominant topic thresholds
DOMINANT_TOPIC_MIN_SCORE = 0.30      # Strongest topic must be >= this
DOMINANT_TOPIC_OTHER_MIN = 0.15      # Other topics must be >= this

# ============================================================================
# SCORING WEIGHTS
# ============================================================================

# Final intelligence score calculation
EXPERTISE_WEIGHT = 0.5        # Weight for topic expertise
IMPACT_WEIGHT = 0.3          # Weight for venue quality/recency
PRODUCTIVITY_WEIGHT = 0.2    # Weight for paper count

# Impact score calculation (in author_expertise.py)
RECENCY_WEIGHT = 0.4         # Weight for recent papers
VENUE_QUALITY_WEIGHT = 0.6   # Weight for top-tier venues

# ============================================================================
# SENIORITY THRESHOLDS
# ============================================================================

# PhD Student classification
PHD_STUDENT_MAX_YEARS = 5
PHD_STUDENT_MAX_PAPERS = 10

# Postdoc classification
POSTDOC_MAX_YEARS = 7
POSTDOC_MAX_PAPERS = 15

# Mid-career classification
MID_CAREER_MIN_YEARS = 8
MID_CAREER_MIN_PAPERS = 20

# Senior researcher classification
SENIOR_MIN_YEARS = 8
SENIOR_MIN_PRODUCTIVITY = 3.0  # Papers per year

# Professor classification
PROFESSOR_MIN_YEARS = 15
PROFESSOR_MIN_PAPERS = 50

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================

# Query caching
QUERY_CACHE_TTL_MINUTES = 15  # Cache lifetime
QUERY_CACHE_MAX_SIZE = 100    # Maximum cached queries

# ============================================================================
# SENIORITY PREFERENCES
# ============================================================================

# Default seniority filtering (None = no default filter)
# Options: "phd_student", "postdoc", "mid_career", "senior_researcher", "professor", None
DEFAULT_SENIORITY_PREFERENCE = None  # Set to "mid_career" to exclude professors by default

# Exclude professors by default (even if not specified in query)
EXCLUDE_PROFESSORS_BY_DEFAULT = False  # Set to True to always exclude professors

# Professor score penalty (multiply final score by this if professor)
# 1.0 = no penalty, 0.5 = 50% penalty, 0.0 = effectively excluded
PROFESSOR_SCORE_PENALTY = 0.7  # 30% penalty for professors

# Senior researcher score penalty
SENIOR_RESEARCHER_SCORE_PENALTY = 0.85  # 15% penalty for senior researchers

# Prefer early-career researchers (boost scores)
EARLY_CAREER_SCORE_BOOST = 1.1  # 10% boost for phd_student, postdoc, mid_career

# ============================================================================
# LOGGING SETTINGS
# ============================================================================

LOG_LEVEL = "INFO"
LOG_REJECTED_CANDIDATES = False  # Set to True for debugging
ENABLE_PERFORMANCE_LOGGING = True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_adaptive_threshold(num_topics: int) -> float:
    """
    Get expertise threshold based on number of topics in query

    Args:
        num_topics: Number of topics in the query

    Returns:
        Minimum expertise threshold for each topic
    """
    if num_topics == 1:
        return SINGLE_TOPIC_MIN_EXPERTISE
    elif num_topics == 2:
        return MULTI_TOPIC_MIN_EXPERTISE
    else:
        return THREE_TOPIC_MIN_EXPERTISE


def should_use_or_logic(num_fields: int) -> bool:
    """
    Determine if OR logic should be used for venue intersection

    Args:
        num_fields: Number of required fields

    Returns:
        True if OR logic should be used
    """
    return USE_VENUE_OR_LOGIC and num_fields >= 2


def get_required_fields_count(total_fields: int) -> int:
    """
    Calculate minimum number of fields required when using OR logic

    Args:
        total_fields: Total number of required fields

    Returns:
        Minimum number of fields that must be satisfied
    """
    if USE_VENUE_OR_LOGIC:
        # Require N-1 fields (allow missing 1)
        return max(1, total_fields - 1)
    else:
        # Require ALL fields
        return total_fields
