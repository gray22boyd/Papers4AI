# 🧪 Test Queries - Showcase Intelligent Search

Run these queries to see what the agent can do WITHOUT Claude API!

---

## Test 1: Single Topic (Baseline)

**What it tests:** Basic expertise validation

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "video generation",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test1_results.json
```

**Look for:**
- `expertise_details.expertise.video_generation` should be > 0.3
- `intelligence_score` shows overall quality
- `impact.venue_score` shows publication quality

---

## Test 2: Two Topics (The Killer Feature!)

**What it tests:** Multi-topic expertise validation

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "reinforcement learning computer vision",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test2_results.json
```

**What happens:**
- Finds people who mention BOTH topics
- Validates they have RL ≥ 0.25 AND CV ≥ 0.25
- Checks they publish at NeurIPS (RL) AND CVPR (CV)
- **May return 0 results** if no one meets the strict bar!

**Look for:**
- `expertise_details.expertise.reinforcement_learning` ≥ 0.25
- `expertise_details.expertise.computer_vision` ≥ 0.25
- `venue_details` showing publications in both fields

**Expected:** Probably 0 results (proves it's strict!)

---

## Test 3: Broader Multi-Topic (Should Work)

**What it tests:** More common topic combination

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "computer vision nlp",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test3_results.json
```

**What happens:**
- Finds multimodal researchers (vision + language)
- Common combination, should find results

**Look for:**
- Both `computer_vision` and `nlp` expertise scores
- Conferences should include CVPR/ICCV (CV) and ACL/EMNLP (NLP)

---

## Test 4: Three Topics (Ultra Strict)

**What it tests:** Finding true interdisciplinary experts

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "robotics reinforcement learning computer vision",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test4_results.json
```

**What happens:**
- Must have expertise in ALL THREE topics
- Extremely strict filtering
- **Likely 0 results** (few people are experts in 3 fields!)

**Look for:**
- All three expertise scores ≥ 0.25
- Publishes at ICRA/IROS (robotics) + NeurIPS (RL) + CVPR (CV)

**Expected:** 0-2 results (if any exist, they're unicorns!)

---

## Test 5: Video + NLP (Multimodal)

**What it tests:** Finding video-language researchers

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "video generation nlp",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test5_results.json
```

**What happens:**
- Hot research area (text-to-video models)
- Should find some results

**Look for:**
- `video_generation` and `nlp` expertise
- Recent papers (2023-2024)

---

## Test 6: Diffusion Models

**What it tests:** Trending topic

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "diffusion models",
    "use_llm": false,
    "max_results": 10
  }' | python -m json.tool > test6_results.json
```

**What happens:**
- Hot topic, should have many results
- Test intelligence scoring across many candidates

**Look for:**
- `expertise_details.expertise.diffusion_models`
- `intelligence_score` ranking
- Top results should have higher scores

---

## Test 7: Robotics (Single Topic, Many Results)

**What it tests:** Ranking quality with many candidates

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "robotics",
    "use_llm": false,
    "max_results": 10
  }' | python -m json.tool > test7_results.json
```

**What happens:**
- Broad topic, many results
- Tests intelligence scoring and ranking

**Look for:**
- Results sorted by `intelligence_score` (highest first)
- Top results should have:
  - Higher `expertise.robotics` scores
  - Better `impact.venue_score`
  - More recent work

---

## Test 8: With Seniority Filter

**What it tests:** Career stage detection

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "video generation, mid-career",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test8_results.json
```

**What happens:**
- Finds video generation experts
- Filters to mid-career (8-15 years)

**Look for:**
- `seniority.level` should be "mid_career" or close
- `seniority.years_active` should be 8-15
- `seniority.confidence` shows detection confidence

---

## Test 9: Early Career Researchers

**What it tests:** Finding junior researchers

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "diffusion models, early-career",
    "use_llm": false,
    "max_results": 5
  }' | python -m json.tool > test9_results.json
```

**What happens:**
- Finds diffusion experts
- Filters to PhD students / postdocs

**Look for:**
- `seniority.level` = "phd_student" or "postdoc"
- `seniority.years_active` < 8
- Fewer total papers (5-15 typical)

---

## Test 10: The Full Power Query

**What it tests:** Everything combined

```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "computer vision nlp, mid-career",
    "use_llm": false,
    "max_results": 10
  }' | python -m json.tool > test10_results.json
```

**What happens:**
- Multi-topic validation (CV + NLP)
- Seniority filtering (mid-career)
- Intelligence ranking

**Look for:**
- Both topic expertise scores ≥ 0.25
- Mid-career seniority
- High intelligence scores
- Publications at both CV and NLP venues

---

## 🎯 Expected Results Summary

| Test | Topics | Expected Results | Why |
|------|--------|------------------|-----|
| Test 1 | Video gen | 5-10 | Single topic, common |
| Test 2 | RL + CV | 0-2 | Very strict, rare combo |
| Test 3 | CV + NLP | 3-8 | Common multimodal area |
| Test 4 | 3 topics | 0-1 | Extremely strict |
| Test 5 | Video + NLP | 2-5 | Emerging area |
| Test 6 | Diffusion | 10+ | Hot topic |
| Test 7 | Robotics | 10+ | Broad topic |
| Test 8 | Video + seniority | 3-7 | Combined filters |
| Test 9 | Diffusion + early | 5-10 | Many new researchers |
| Test 10 | CV+NLP + mid | 2-5 | Full power combo |

---

## 📊 How to Analyze Results

### 1. Check Expertise Scores
```json
"expertise_details": {
  "expertise": {
    "video_generation": 0.025,  // Too low (2.5%)
    "nlp": 0.1,                  // Low (10%)
    "computer_vision": 0.5       // Good! (50%)
  }
}
```

**Scale:**
- 0.0 - 0.1: Mentioned it once or twice
- 0.1 - 0.25: Some familiarity
- **0.25 - 0.5: Significant expertise** ← Minimum threshold
- 0.5 - 0.8: Deep expertise
- 0.8+: World-class expert

### 2. Check Intelligence Score
```json
"intelligence_score": 9.5
```

**Formula:**
```
intelligence = expertise_depth * 0.5 +
               impact_score * 0.3 +
               productivity * 0.2
```

Higher = better overall quality

### 3. Check Seniority
```json
"seniority": {
  "level": "mid_career",
  "confidence": 0.7,
  "years_active": 9,
  "papers_per_year": 2.3
}
```

**Levels:** phd_student → postdoc → mid_career → senior_researcher → professor

### 4. Check Impact
```json
"impact": {
  "impact_score": 18.3,    // Overall impact
  "recency_score": 1.8,    // Recent publications?
  "venue_score": 1.85      // Top-tier venues?
}
```

Higher = better publication quality + recency

---

## 🔍 What to Look For

### ✅ Good Signs
- Multiple expertise scores ≥ 0.3
- Intelligence score ≥ 8.0
- Publications at top venues (NeurIPS, CVPR, ICLR, ACL)
- Recent papers (2023-2024)
- High confidence seniority estimation

### ⚠️ Red Flags
- Expertise scores < 0.1 (just mentioned the topic)
- Intelligence score < 5.0 (low quality)
- Only old papers (< 2020)
- Low venue scores (no top-tier publications)

---

## 💡 Pro Tips

### Test the Difference

**Run a keyword search first:**
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "RL computer vision", "limit": 10}'
```

**Then run intelligent search:**
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "reinforcement learning computer vision", "max_results": 10}'
```

**Compare:**
- Keyword: Returns anyone who mentions both words
- Intelligent: Only returns true experts in BOTH fields

### Understand "0 Results"

If you get 0 results, **that's a feature, not a bug!**

It means: "No one in your database meets the strict expertise bar for ALL required topics"

This is GOOD - it prevents false positives!

### Adjust Your Query

If too strict:
- Try related topics: "vision language" instead of "computer vision nlp"
- Lower complexity: 2 topics instead of 3
- Use broader terms: "robotics" instead of "RL + CV + robotics"

---

## 🎉 Run All Tests

Quick script to run all 10 tests:

```bash
# Create test directory
mkdir -p intelligent_search_tests
cd intelligent_search_tests

# Run all tests
curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "video generation", "use_llm": false, "max_results": 5}' | python -m json.tool > test1_video.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "reinforcement learning computer vision", "use_llm": false, "max_results": 5}' | python -m json.tool > test2_rl_cv.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "computer vision nlp", "use_llm": false, "max_results": 5}' | python -m json.tool > test3_cv_nlp.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "robotics reinforcement learning computer vision", "use_llm": false, "max_results": 5}' | python -m json.tool > test4_three_topics.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "video generation nlp", "use_llm": false, "max_results": 5}' | python -m json.tool > test5_video_nlp.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "diffusion models", "use_llm": false, "max_results": 10}' | python -m json.tool > test6_diffusion.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "robotics", "use_llm": false, "max_results": 10}' | python -m json.tool > test7_robotics.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "video generation, mid-career", "use_llm": false, "max_results": 5}' | python -m json.tool > test8_seniority.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "diffusion models, early-career", "use_llm": false, "max_results": 5}' | python -m json.tool > test9_early_career.json

curl -X POST http://localhost:5000/api/intelligent/search -H "Content-Type: application/json" -d '{"query": "computer vision nlp, mid-career", "use_llm": false, "max_results": 10}' | python -m json.tool > test10_full_power.json

echo "All tests complete! Check the JSON files."
```

---

**Ready to test?** Pick one or run them all!
