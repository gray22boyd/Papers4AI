"""
Test Professor Exclusion Functionality
Validates that professor filtering and score penalties work correctly
"""

def test_query_parser_exclusion():
    """Test that query parser detects professor exclusion"""
    from intelligent_agent import IntelligentRecruitingAgent

    # Create mock agent (will use fallback parser without Claude API)
    agent = IntelligentRecruitingAgent(None, None, None)

    # Test 1: "no professors"
    criteria = agent._parse_query_fallback("RL + CV, no professors")
    assert criteria["exclude_professors"] == True, "Should detect 'no professors'"
    print("[PASS] Detected 'no professors'")

    # Test 2: "exclude professors"
    criteria = agent._parse_query_fallback("computer vision, exclude professors")
    assert criteria["exclude_professors"] == True, "Should detect 'exclude professors'"
    print("[PASS] Detected 'exclude professors'")

    # Test 3: "early career only"
    criteria = agent._parse_query_fallback("robotics experts, early career only")
    assert criteria["exclude_professors"] == True, "Should detect 'early career only'"
    print("[PASS] Detected 'early career only'")

    # Test 4: "junior only"
    criteria = agent._parse_query_fallback("NLP researchers, junior only")
    assert criteria["exclude_senior"] == True, "Should detect 'junior only'"
    print("[PASS] Detected 'junior only'")

    # Test 5: No exclusion
    criteria = agent._parse_query_fallback("RL + CV experts")
    assert criteria.get("exclude_professors", False) == False, "Should not exclude by default"
    print("[PASS] No false positive exclusion")


def test_config_exclusion():
    """Test configuration-based exclusion"""
    from intelligent_config import (
        EXCLUDE_PROFESSORS_BY_DEFAULT,
        PROFESSOR_SCORE_PENALTY,
        SENIOR_RESEARCHER_SCORE_PENALTY,
        EARLY_CAREER_SCORE_BOOST
    )

    # Check default values
    assert EXCLUDE_PROFESSORS_BY_DEFAULT == False, "Should be False by default"
    print(f"[PASS] Default exclusion: {EXCLUDE_PROFESSORS_BY_DEFAULT}")

    # Check penalty values
    assert 0.0 <= PROFESSOR_SCORE_PENALTY <= 1.0, "Penalty should be between 0 and 1"
    assert 0.0 <= SENIOR_RESEARCHER_SCORE_PENALTY <= 1.0, "Penalty should be between 0 and 1"
    assert EARLY_CAREER_SCORE_BOOST >= 1.0, "Boost should be >= 1.0"

    print(f"[PASS] Professor penalty: {PROFESSOR_SCORE_PENALTY} (30% reduction)")
    print(f"[PASS] Senior penalty: {SENIOR_RESEARCHER_SCORE_PENALTY} (15% reduction)")
    print(f"[PASS] Early-career boost: {EARLY_CAREER_SCORE_BOOST} (10% increase)")


def test_score_penalties():
    """Test that score penalties are applied correctly"""
    from intelligent_config import (
        PROFESSOR_SCORE_PENALTY,
        SENIOR_RESEARCHER_SCORE_PENALTY,
        EARLY_CAREER_SCORE_BOOST
    )

    # Simulated base scores
    base_score = 80.0

    # Test professor penalty
    professor_score = base_score * PROFESSOR_SCORE_PENALTY
    expected_professor = 80.0 * 0.7  # 56.0
    assert abs(professor_score - expected_professor) < 0.1, f"Professor score should be {expected_professor}"
    print(f"[PASS] Professor: {base_score} -> {professor_score} ({PROFESSOR_SCORE_PENALTY}x)")

    # Test senior penalty
    senior_score = base_score * SENIOR_RESEARCHER_SCORE_PENALTY
    expected_senior = 80.0 * 0.85  # 68.0
    assert abs(senior_score - expected_senior) < 0.1, f"Senior score should be {expected_senior}"
    print(f"[PASS] Senior: {base_score} -> {senior_score} ({SENIOR_RESEARCHER_SCORE_PENALTY}x)")

    # Test early-career boost
    early_score = base_score * EARLY_CAREER_SCORE_BOOST
    expected_early = 80.0 * 1.1  # 88.0
    assert abs(early_score - expected_early) < 0.1, f"Early-career score should be {expected_early}"
    print(f"[PASS] Early-career: {base_score} -> {early_score} ({EARLY_CAREER_SCORE_BOOST}x)")


def test_seniority_classification():
    """Test that seniority classification makes sense"""
    from author_expertise import AuthorExpertiseAnalyzer
    from datetime import datetime

    analyzer = AuthorExpertiseAnalyzer()
    current_year = datetime.now().year

    # Test 1: PhD student (3 years, 5 papers)
    phd_papers = [
        {"year": current_year - 3},
        {"year": current_year - 2},
        {"year": current_year - 2},
        {"year": current_year - 1},
        {"year": current_year}
    ]
    seniority = analyzer.estimate_seniority(phd_papers)
    assert seniority["level"] in ["phd_student", "phd_student_advanced"], f"Should classify as PhD student, got {seniority['level']}"
    print(f"[PASS] PhD student classification: {seniority['level']}")

    # Test 2: Professor (20 years, 80 papers)
    professor_papers = [{"year": current_year - i} for i in range(20)] * 4  # 80 papers
    seniority = analyzer.estimate_seniority(professor_papers)
    assert seniority["level"] in ["professor", "senior_researcher"], f"Should classify as professor/senior, got {seniority['level']}"
    print(f"[PASS] Professor classification: {seniority['level']}")

    # Test 3: Mid-career (10 years, 30 papers)
    midcareer_papers = [{"year": current_year - i//3} for i in range(30)]
    seniority = analyzer.estimate_seniority(midcareer_papers)
    assert seniority["level"] in ["mid_career", "senior_researcher"], f"Should classify as mid-career, got {seniority['level']}"
    print(f"[PASS] Mid-career classification: {seniority['level']}")


def test_exclusion_patterns():
    """Test various exclusion patterns"""
    from intelligent_agent import IntelligentRecruitingAgent

    agent = IntelligentRecruitingAgent(None, None, None)

    test_cases = [
        ("RL experts, no profs", True, False),
        ("CV researchers, exclude professor", True, False),
        ("NLP experts, not professor", True, False),
        ("robotics, early career only", True, False),
        ("video generation, junior researchers", True, False),
        ("diffusion models, non-professor", True, False),
        ("RL + CV, no senior researchers", False, True),
        ("NLP, junior only", True, True),  # Should exclude both
        ("robotics experts, early stage", True, True),  # Should exclude both
    ]

    for query, expect_prof_exclude, expect_senior_exclude in test_cases:
        criteria = agent._parse_query_fallback(query)
        prof_exclude = criteria.get("exclude_professors", False)
        senior_exclude = criteria.get("exclude_senior", False)

        assert prof_exclude == expect_prof_exclude, f"Query '{query}' should have exclude_professors={expect_prof_exclude}, got {prof_exclude}"
        assert senior_exclude == expect_senior_exclude, f"Query '{query}' should have exclude_senior={expect_senior_exclude}, got {senior_exclude}"

        print(f"[PASS] '{query}' -> profs={prof_exclude}, senior={senior_exclude}")


def test_score_ordering():
    """Test that score penalties change ordering correctly"""
    from intelligent_config import (
        PROFESSOR_SCORE_PENALTY,
        EARLY_CAREER_SCORE_BOOST
    )

    # Simulated candidates
    candidates = [
        {"name": "Prof. Smith", "base_score": 95.0, "seniority": "professor"},
        {"name": "Dr. Chen", "base_score": 75.0, "seniority": "mid_career"},
        {"name": "Prof. Doe", "base_score": 92.0, "seniority": "professor"},
        {"name": "Dr. Wang", "base_score": 70.0, "seniority": "postdoc"},
    ]

    # Apply penalties/boosts
    for candidate in candidates:
        base = candidate["base_score"]
        level = candidate["seniority"]

        if level == "professor":
            final = base * PROFESSOR_SCORE_PENALTY
        elif level in ["mid_career", "postdoc"]:
            final = base * EARLY_CAREER_SCORE_BOOST
        else:
            final = base

        candidate["final_score"] = final

    # Before penalties (sorted by base_score)
    before = sorted(candidates, key=lambda x: x["base_score"], reverse=True)
    print("\nBefore penalties:")
    for i, c in enumerate(before, 1):
        print(f"  {i}. {c['name']} ({c['seniority']}) - {c['base_score']}")

    # After penalties (sorted by final_score)
    after = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    print("\nAfter penalties:")
    for i, c in enumerate(after, 1):
        print(f"  {i}. {c['name']} ({c['seniority']}) - {c['final_score']:.1f} (was {c['base_score']})")

    # Dr. Chen should now rank higher than professors
    chen_rank = next(i for i, c in enumerate(after) if c["name"] == "Dr. Chen")
    smith_rank = next(i for i, c in enumerate(after) if c["name"] == "Prof. Smith")

    assert chen_rank < smith_rank, "Mid-career should rank above professor after penalties"
    print(f"\n[PASS] Mid-career (rank {chen_rank+1}) now above professor (rank {smith_rank+1})")


def run_all_tests():
    """Run all professor exclusion tests"""
    print("\n" + "="*70)
    print("PROFESSOR EXCLUSION - TEST SUITE")
    print("="*70 + "\n")

    print("--- Query Parser Tests ---")
    test_query_parser_exclusion()

    print("\n--- Configuration Tests ---")
    test_config_exclusion()

    print("\n--- Score Penalty Tests ---")
    test_score_penalties()

    print("\n--- Seniority Classification Tests ---")
    test_seniority_classification()

    print("\n--- Exclusion Pattern Tests ---")
    test_exclusion_patterns()

    print("\n--- Score Ordering Tests ---")
    test_score_ordering()

    print("\n" + "="*70)
    print("ALL TESTS PASSED!")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
