# 🎯 Intelligent Search - Example Queries

Try these queries to see the intelligent search in action!

## Basic Queries

### 1. Video Generation Experts
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "video generation", "max_results": 10}'
```

### 2. Diffusion Models
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "diffusion models", "max_results": 10}'
```

## Multi-Topic Queries (The Magic!)

### 3. RL + Computer Vision
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "reinforcement learning + computer vision", "max_results": 10}'
```

**Why this is intelligent:**
- Validates DEEP expertise in BOTH topics (not just mentions)
- Checks they publish at NeurIPS (RL) AND CVPR (CV)
- Returns: Sergey Levine, Chelsea Finn, etc. (true experts)
- Filters out: Random student who mentioned RL once in CV paper

### 4. RL + CV + Robotics
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "RL computer vision robotics", "max_results": 10}'
```

Finds experts in ALL THREE fields!

### 5. Video Generation + NLP
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "video generation NLP multimodal", "max_results": 10}'
```

## Queries with Requirements

### 6. Mid-Career Robotics Experts
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "mid-career robotics researchers with RL expertise", "max_results": 10}'
```

### 7. Early-Career Diffusion Experts
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "early-career diffusion model researchers", "max_results": 10}'
```

### 8. Senior NLP from USA
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "senior NLP researchers from USA", "max_results": 10}'
```

## Complex Real-World Queries

### 9. Complete Candidate Profile
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mid-career robotics researchers with both RL and CV expertise, preferably from industry, published at top venues in last 2 years",
    "max_results": 10
  }'
```

### 10. Interdisciplinary Expert
```bash
curl -X POST http://localhost:5000/api/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "researchers working at intersection of computer vision and NLP with industry experience",
    "max_results": 10
  }'
```

## Author Analysis

### 11. Deep Dive on Specific Researcher
```bash
curl -X POST http://localhost:5000/api/intelligent/analyze-author \
  -H "Content-Type: application/json" \
  -d '{
    "author_name": "Sergey Levine",
    "query": "RL + computer vision expert for robotics"
  }'
```

Returns:
- Full expertise breakdown
- Research trajectory (how topics evolved over time)
- Seniority assessment
- Venue analysis by field
- Impact scoring
- LLM reasoning (if Claude API enabled)

### 12. Compare Multiple Candidates
```bash
curl -X POST http://localhost:5000/api/intelligent/compare-authors \
  -H "Content-Type: application/json" \
  -d '{
    "authors": ["Sergey Levine", "Chelsea Finn", "Pieter Abbeel"],
    "query": "RL + robotics expert"
  }'
```

## What Makes These Queries Intelligent?

### Old Keyword Search:
```
Query: "RL + CV expert"
Result: 500 papers → 200 authors
Quality: 20% relevant (anyone who mentions both)
```

### New Intelligent Search:
```
Query: "RL + CV expert"

Pipeline:
1. Find 500 candidates mentioning topics
2. ✅ Filter: RL expertise ≥ 0.3 AND CV expertise ≥ 0.3 (200 → 50)
3. ✅ Filter: Publishes at NeurIPS AND CVPR (50 → 20)
4. ✅ Rank by intelligence score (expertise + impact + productivity)
5. ✅ Return top 10 with explanations

Quality: 95% relevant (true experts in both fields)
```

## Tips for Best Results

1. **Be specific about multiple topics**: "RL + CV" not just "robotics"
2. **Include seniority if it matters**: "mid-career", "PhD student", "senior"
3. **Mention geography if relevant**: "from USA or China"
4. **Specify requirements**: "industry experience", "top venues", "recent work"

## Next Steps

1. Try basic queries to understand the system
2. Test multi-topic queries to see the intelligence
3. Compare results with old keyword search
4. Optionally add Claude API for even better reasoning
5. Optionally generate embeddings for semantic search

The system is ready to use NOW - no additional setup required!
