"""
Quick test of candidate enrichment v2
"""
import sys
sys.path.insert(0, 'backend')

import os
os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', 'test-key')

from candidate_enrichment_v2 import CandidateEnricherV2

# Create enricher
enricher = CandidateEnricherV2()

print("=" * 60)
print("CANDIDATE ENRICHMENT V2 TEST")
print("=" * 60)

# Check if modules loaded
print(f"\n[OK] DuckDuckGo available: {enricher.ddgs is not None}")
print(f"[OK] Claude API available: {enricher.claude is not None}")

if enricher.ddgs is None:
    print("\n[ERROR] DuckDuckGo search not available!")
    print("   Install with: pip install ddgs")
    sys.exit(1)

if enricher.claude is None:
    print("\n[ERROR] Claude API not available!")
    print("   Set ANTHROPIC_API_KEY in .env file")
    sys.exit(1)

# Test with a well-known researcher
test_candidate = {
    "name": "Sergey Levine",
    "affiliation": "UC Berkeley",
    "papers": []
}

print(f"\n{'='*60}")
print(f"Testing enrichment for: {test_candidate['name']}")
print(f"{'='*60}\n")

# Enrich the candidate
enriched = enricher.enrich_candidate(test_candidate)

# Display results
print("\nENRICHMENT RESULTS:")
print(f"  Name: {enriched.get('name')}")
print(f"  Current Position: {enriched.get('current_position', 'NOT FOUND')}")
print(f"  Current Affiliation: {enriched.get('current_affiliation', 'NOT FOUND')}")
print(f"  Is Professor: {enriched.get('is_professor', False)}")
print(f"  Is Industry: {enriched.get('is_industry', False)}")
print(f"  Is Academic: {enriched.get('is_academic', False)}")
bio = enriched.get('bio_snippet', 'N/A')
print(f"  Bio: {bio[:100] if bio else 'N/A'}...")

# Test filtering
print(f"\n{'='*60}")
print("TESTING FILTER: 'exclude professors'")
print(f"{'='*60}\n")

candidates = [enriched]
from candidate_enrichment_v2 import filter_by_enrichment

filtered = filter_by_enrichment(candidates, "exclude professors")

print(f"  Before filter: {len(candidates)} candidates")
print(f"  After filter: {len(filtered)} candidates")
print(f"  [OK] Professor was {'EXCLUDED' if len(filtered) == 0 else 'INCLUDED'}")

print(f"\n{'='*60}")
print("[SUCCESS] ENRICHMENT TEST COMPLETE!")
print(f"{'='*60}\n")
