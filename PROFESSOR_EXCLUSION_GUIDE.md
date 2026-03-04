# Professor Exclusion Guide

## Problem

The intelligent search system was returning too many professors because they naturally have:
- ✅ More papers (50-200+ publications)
- ✅ Higher citation counts
- ✅ Better venue quality
- ✅ Longer publication history

**Result:** Professors dominated search results, making it hard to find early-career researchers, postdocs, or industry candidates.

---

## Solution

Implemented **4-tier professor handling system**:

### 1. **Hard Exclusion** (Remove entirely)
Query-based or config-based filtering

### 2. **Score Penalties** (De-rank)
Professors get 30% score penalty even if not excluded

### 3. **Early-Career Boost** (Promote)
PhD students, postdocs, mid-career get 10% score boost

### 4. **Smart Query Parsing** (Auto-detect)
LLM recognizes "no professors", "early career only", etc.

---

## Usage Examples

### Exclude Professors via Query

```python
# Natural language exclusion
results = intelligent_agent.multi_stage_search("reinforcement learning, no professors")
results = intelligent_agent.multi_stage_search("CV + NLP, exclude professors")
results = intelligent_agent.multi_stage_search("diffusion models, early career only")
results = intelligent_agent.multi_stage_search("robotics, junior researchers only")

# All of these will be detected by the LLM and exclude professors
```

### Exclude Professors via Configuration

Edit `backend/intelligent_config.py`:

```python
# Exclude professors by default (for ALL queries)
EXCLUDE_PROFESSORS_BY_DEFAULT = True  # Was False

# Now ALL queries exclude professors automatically
```

### Adjust Score Penalties

Edit `backend/intelligent_config.py`:

```python
# Stronger professor penalty (50% instead of 30%)
PROFESSOR_SCORE_PENALTY = 0.5  # Was 0.7

# Stronger senior penalty (30% instead of 15%)
SENIOR_RESEARCHER_SCORE_PENALTY = 0.7  # Was 0.85

# Bigger early-career boost (20% instead of 10%)
EARLY_CAREER_SCORE_BOOST = 1.2  # Was 1.1
```

### Exclude Both Professors AND Senior Researchers

```python
# Via query
results = intelligent_agent.multi_stage_search("RL + CV, junior only")
results = intelligent_agent.multi_stage_search("video generation, no senior researchers")

# Via config
EXCLUDE_PROFESSORS_BY_DEFAULT = True
# Senior exclusion must be query-based (no config option yet)
```

---

## How It Works

### Stage 6: Seniority Estimation

```python
# ALWAYS runs for ALL candidates
for candidate in validated:
    seniority = estimate_seniority(candidate.papers)
    # Classifies as: phd_student, postdoc, mid_career, senior_researcher, professor
```

**Classification logic:**
- **PhD Student**: ≤5 years, ≤10 papers, high first-author ratio
- **Postdoc**: ≤7 years, ≤15 papers
- **Mid-Career**: 8+ years, 20+ papers
- **Senior Researcher**: 8+ years, 3+ papers/year productivity
- **Professor**: 15+ years, 50+ papers

### Stage 6b: Professor Exclusion (NEW)

```python
exclude_profs = criteria.get("exclude_professors", False) or EXCLUDE_PROFESSORS_BY_DEFAULT

if exclude_profs:
    for candidate in validated:
        if candidate.seniority.level == "professor":
            REJECT  # Hard filter - completely removed
```

### Stage 7: Score Penalties (NEW)

```python
for candidate in validated:
    base_score = calculate_intelligence_score(candidate)

    if candidate.seniority.level == "professor":
        final_score = base_score * 0.7  # 30% penalty

    elif candidate.seniority.level == "senior_researcher":
        final_score = base_score * 0.85  # 15% penalty

    elif candidate.seniority.level in ["phd_student", "postdoc", "mid_career"]:
        final_score = base_score * 1.1  # 10% boost
```

---

## Query Detection Patterns

The LLM parser recognizes these patterns:

### Professor Exclusion Triggers:
- "no professor"
- "no profs"
- "exclude professor"
- "not professor"
- "early career only"
- "junior researcher"
- "non-professor"

### Senior Exclusion Triggers:
- "no senior"
- "exclude senior"
- "junior only"
- "early stage"
- "early-career only"

**Examples:**
```
"Find RL experts, no professors" → exclude_professors=True
"CV researchers, early career only" → exclude_professors=True
"NLP experts, junior only" → exclude_senior=True, exclude_professors=True
"Robotics PhDs and postdocs" → exclude_professors=True (implied)
```

---

## Configuration Options

All settings in `backend/intelligent_config.py`:

```python
# ============================================================================
# SENIORITY PREFERENCES
# ============================================================================

# Exclude professors by default (even if not in query)
EXCLUDE_PROFESSORS_BY_DEFAULT = False  # Set to True to always exclude

# Professor score penalty (multiply final score)
PROFESSOR_SCORE_PENALTY = 0.7  # 1.0 = no penalty, 0.5 = 50% penalty, 0.0 = effectively excluded

# Senior researcher score penalty
SENIOR_RESEARCHER_SCORE_PENALTY = 0.85  # 15% penalty

# Early-career score boost
EARLY_CAREER_SCORE_BOOST = 1.1  # 10% boost for phd_student, postdoc, mid_career
```

---

## Before/After Comparison

### Query: "reinforcement learning computer vision"

**Before:**
```
1. Prof. John Smith (Professor, 150 papers) - Score: 95.2
2. Prof. Jane Doe (Professor, 120 papers) - Score: 92.1
3. Prof. Bob Lee (Professor, 200 papers) - Score: 91.8
4. Dr. Alice Chen (Mid-career, 25 papers) - Score: 78.3
5. Dr. Tom Wang (Postdoc, 12 papers) - Score: 65.7
...
```

**After (with penalties):**
```
1. Dr. Alice Chen (Mid-career, 25 papers) - Score: 86.1 (was 78.3, +10% boost)
2. Dr. Tom Wang (Postdoc, 12 papers) - Score: 72.3 (was 65.7, +10% boost)
3. Dr. Sarah Kim (Postdoc, 15 papers) - Score: 71.2 (was 64.7, +10% boost)
4. Prof. John Smith (Professor, 150 papers) - Score: 66.6 (was 95.2, -30% penalty)
5. Prof. Jane Doe (Professor, 120 papers) - Score: 64.5 (was 92.1, -30% penalty)
...
```

**After (with exclusion):**
```
Query: "reinforcement learning computer vision, no professors"

1. Dr. Alice Chen (Mid-career, 25 papers) - Score: 86.1
2. Dr. Tom Wang (Postdoc, 12 papers) - Score: 72.3
3. Dr. Sarah Kim (Postdoc, 15 papers) - Score: 71.2
4. Dr. Mark Liu (Mid-career, 30 papers) - Score: 68.9
5. Dr. Emma Brown (Postdoc, 18 papers) - Score: 67.4
...
# No professors in results!
```

---

## Logging & Debugging

### Check Exclusion Stats

```bash
# View professor exclusion logs
grep "professor_exclusion" logs/queries.jsonl | jq '.'

# Example output:
{
  "timestamp": "2026-03-04T10:30:15",
  "query": "RL + CV, no professors",
  "stage": "professor_exclusion",
  "status": "success",
  "details": {
    "passed": 12,
    "rejected": 8,
    "exclude_professors": true,
    "exclude_senior": false,
    "duration_ms": 5.2
  }
}
```

### Check Score Adjustments

```python
results = intelligent_agent.multi_stage_search("RL + CV")

for candidate in results[:10]:
    print(f"{candidate['name']}:")
    print(f"  Seniority: {candidate['seniority']['level']}")
    print(f"  Base score: {candidate['base_intelligence_score']}")
    print(f"  Adjustment: {candidate['score_adjustment']}")
    print(f"  Final score: {candidate['intelligence_score']}")
    print()
```

**Example output:**
```
Dr. Alice Chen:
  Seniority: mid_career
  Base score: 78.3
  Adjustment: Early-career boost (1.1x)
  Final score: 86.1

Prof. John Smith:
  Seniority: professor
  Base score: 95.2
  Adjustment: Professor penalty (0.7x)
  Final score: 66.6
```

---

## Tuning Recommendations

### Scenario 1: Still seeing too many professors

**Solution 1:** Enable default exclusion
```python
EXCLUDE_PROFESSORS_BY_DEFAULT = True
```

**Solution 2:** Increase penalty
```python
PROFESSOR_SCORE_PENALTY = 0.5  # 50% penalty instead of 30%
```

**Solution 3:** Boost early-career more
```python
EARLY_CAREER_SCORE_BOOST = 1.3  # 30% boost instead of 10%
```

### Scenario 2: Want to find industry researchers (not academics)

```python
# Query-based
results = intelligent_agent.multi_stage_search("RL + CV, industry only, no professors")

# This combines:
# 1. Affiliation filter (industry)
# 2. Professor exclusion
```

### Scenario 3: Want ONLY postdocs

```python
# Query-based (LLM will detect)
results = intelligent_agent.multi_stage_search("RL + CV, postdocs only")

# Or explicit criteria
criteria = {
    "topics": ["reinforcement_learning", "computer_vision"],
    "seniority": "postdoc",
    "exclude_professors": True
}
```

### Scenario 4: Want to find rising stars (early-career with high impact)

```python
# Boost early-career significantly
EARLY_CAREER_SCORE_BOOST = 1.5  # 50% boost

# Penalize professors heavily
PROFESSOR_SCORE_PENALTY = 0.4  # 60% penalty

# Query
results = intelligent_agent.multi_stage_search("RL + CV, early career, top venues")
```

---

## Testing

Test the exclusion logic:

```python
# Test exclusion detection
from intelligent_agent import IntelligentRecruitingAgent

agent = IntelligentRecruitingAgent(...)

# Test 1: Query-based exclusion
criteria = agent.parse_complex_query("RL experts, no professors")
assert criteria["exclude_professors"] == True

# Test 2: Fallback parser
criteria = agent._parse_query_fallback("CV researchers, exclude professors")
assert criteria["exclude_professors"] == True

# Test 3: Config-based exclusion
from intelligent_config import EXCLUDE_PROFESSORS_BY_DEFAULT
# Should be False by default, set to True to test
```

---

## API Response Changes

The API now includes seniority information in results:

```json
{
  "name": "Dr. Alice Chen",
  "intelligence_score": 86.1,
  "base_intelligence_score": 78.3,
  "seniority_multiplier": 1.1,
  "score_adjustment": "Early-career boost (1.1x)",
  "seniority": {
    "level": "mid_career",
    "confidence": 0.8,
    "years_active": 8,
    "total_papers": 25,
    "papers_per_year": 3.1,
    "is_active": true
  },
  "expertise_details": { ... },
  "impact": { ... }
}
```

---

## Summary

### What Changed

✅ **Added query detection** - "no professors" automatically recognized
✅ **Added hard exclusion** - Stage 6b removes professors entirely if requested
✅ **Added score penalties** - Professors get 30% penalty, seniors get 15%
✅ **Added early-career boost** - PhD/postdoc/mid-career get 10% boost
✅ **Added configuration** - Easy to tune or enable by default
✅ **Added logging** - Track exclusions and score adjustments

### Configuration Quick Reference

```python
# Exclude professors by default
EXCLUDE_PROFESSORS_BY_DEFAULT = True  # Set in intelligent_config.py

# Adjust penalties/boosts
PROFESSOR_SCORE_PENALTY = 0.7          # 1.0=none, 0.5=50% penalty
SENIOR_RESEARCHER_SCORE_PENALTY = 0.85 # 1.0=none, 0.7=30% penalty
EARLY_CAREER_SCORE_BOOST = 1.1         # 1.0=none, 1.3=30% boost
```

### Query Examples

```python
# Exclude professors
"RL + CV, no professors"
"video generation, exclude professors"
"robotics, early career only"

# Exclude senior researchers too
"NLP experts, junior only"
"diffusion models, early stage researchers"

# Specific seniority
"RL researchers, postdocs only"
"CV experts, mid-career"
```

---

**Last Updated:** March 4, 2026
