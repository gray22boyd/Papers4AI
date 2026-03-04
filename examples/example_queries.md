# Example AI Agent Queries

This document provides example queries you can use to test the AI agent, along with expected behavior.

---

## Basic Author Finding

### Query 1: Topic + Geography
```
Find authors working on video generation in the USA
```

**Expected AI Behavior:**
- Expands "video generation" to include: video synthesis, video diffusion, temporal modeling, etc.
- Filters by country: USA
- Infers recent work (2022-2024)
- Returns ranked list of authors with publication counts

**Expected Response Format:**
```
I found 47 authors working on video generation in the USA with recent publications.

Top 5 Authors:
1. Saining Xie (Meta AI / NYU)
   - 8 papers on video generation (2022-2024)
   - 5 first-author papers in top venues (CVPR, NeurIPS)
   ...

Would you like me to:
- Filter by specific conferences?
- Show only first-author papers?
- Focus on specific institutions?
```

---

### Query 2: Specific Institution
```
Show me researchers at DeepMind working on robotics
```

**Expected AI Behavior:**
- Searches for papers with "DeepMind" or "Google DeepMind" in affiliation
- Filters by robotics-related keywords
- Groups by author

**Expected Response:**
Lists authors affiliated with DeepMind who have published on robotics topics

---

### Query 3: Multiple Topics (OR)
```
Find authors working on either transformers or diffusion models
```

**Expected AI Behavior:**
- Uses OR operator between topics
- Query: "transformer OR diffusion OR attention mechanism OR denoising"
- Returns papers matching either topic

---

### Query 4: Excluding Terms (NOT)
```
Find papers on transformers but not for NLP
```

**Expected AI Behavior:**
- Positive keywords: transformer, attention
- Negative keywords: NLP, language, text, translation
- Query: "transformer AND NOT (NLP OR language OR text)"

---

## Conference-Specific Queries

### Query 5: Recent Conference
```
Show me CVPR 2024 papers on world models
```

**Expected AI Behavior:**
- Conference filter: CVPR
- Year filter: 2024
- Keyword: "world models" (phrase match)
- Returns papers sorted by relevance

**Expected Response:**
```
Found 12 CVPR 2024 papers on world models.

Top Papers:
1. "Scaling World Models for Visual Planning"
   - Authors: Jane Smith et al. (Oxford)
   - Focus: Learning predictive models for robotics
   ...
```

---

### Query 6: Multiple Conferences
```
Find papers on self-supervised learning from NeurIPS or ICML in 2023
```

**Expected AI Behavior:**
- Conference filter: [NeurIPS, ICML]
- Year filter: 2023
- Keywords: self-supervised learning, SSL, unsupervised

---

## Geographic Filtering

### Query 7: Regional
```
Who are the top computer vision researchers in Europe?
```

**Expected AI Behavior:**
- Expands "Europe" to: [UK, Germany, France, Switzerland, Netherlands, Italy, Spain, Sweden, ...]
- Topic: computer vision
- Ranks by publication count and impact

---

### Query 8: Multiple Countries
```
Find authors in USA or UK working on reinforcement learning
```

**Expected AI Behavior:**
- Country filter: [USA, UK]
- Topic: reinforcement learning
- Returns authors from either country

---

## Time-Based Queries

### Query 9: Emerging Researchers
```
Find authors who started publishing on diffusion models in the last 2 years
```

**Expected AI Behavior:**
- Year filter: 2022-2024
- Topic: diffusion models
- Looks for authors with recent but limited publication history
- May prioritize first-author papers

---

### Query 10: Historical Trends
```
Show me how attention mechanisms research evolved from 2017 to 2024
```

**Expected AI Behavior:**
- Year range: 2017-2024
- Topic: attention mechanisms
- May segment by year to show trends
- Identifies key papers/authors per period

---

## Advanced Queries

### Query 11: Collaboration Networks
```
Who are the frequent collaborators of Yann LeCun?
```

**Expected AI Behavior:**
- Fetches author profile for "Yann LeCun"
- Extracts co-author list with collaboration counts
- Returns top collaborators

**Expected Response:**
```
Yann LeCun's most frequent collaborators (2018-2024):

1. Soumith Chintala - 15 joint papers
2. Camille Couprie - 12 joint papers
3. Nicolas Carion - 10 joint papers
...
```

---

### Query 12: Comparative Analysis
```
Compare research output of Stanford and MIT in computer vision over the last 3 years
```

**Expected AI Behavior:**
- Filters papers by affiliation: Stanford vs MIT
- Topic: computer vision
- Year range: 2021-2024
- Generates comparative statistics

**Expected Response:**
```
Stanford vs MIT - Computer Vision (2021-2024)

| Metric | Stanford | MIT |
|--------|----------|-----|
| Total Papers | 234 | 189 |
| CVPR Papers | 89 | 67 |
| First Author | 145 | 112 |
| Top Authors | Li Fei-Fei (18), Jiajun Wu (15) | Antonio Torralba (14), Bill Freeman (12) |

Key Differences:
- Stanford focuses more on 3D vision and robotics
- MIT stronger in computational photography and scene understanding
```

---

### Query 13: Trend Identification
```
What are the hottest topics in NeurIPS 2024?
```

**Expected AI Behavior:**
- Conference: NeurIPS
- Year: 2024
- Analyzes paper keywords/titles for frequent terms
- Groups by topic clusters

**Expected Response:**
```
Top trending topics at NeurIPS 2024:

1. Large Language Models (87 papers)
   - Focus: scaling, efficiency, reasoning
2. Diffusion Models (64 papers)
   - Focus: image generation, video, 3D
3. Reinforcement Learning (56 papers)
   - Focus: robotics, games, safety
...
```

---

### Query 14: Niche Expertise
```
Find experts in neural radiance fields (NeRF) who also work on robotics
```

**Expected AI Behavior:**
- Keyword combination: NeRF AND robotics
- Looks for authors with papers in both areas
- Returns intersection of expertise

---

### Query 15: Career Stage
```
Find PhD students (first authors) with 3+ CVPR papers in the last 2 years
```

**Expected AI Behavior:**
- Identifies first-author papers (indicates PhD student/early career)
- Conference: CVPR
- Year: 2022-2024
- Counts papers per author
- Filters for 3+ publications

---

## Domain-Specific Queries

### Query 16: Industry Research
```
What is Meta AI working on in computer vision?
```

**Expected AI Behavior:**
- Affiliation filter: Meta, Facebook AI Research, FAIR
- Topic: computer vision
- Recent papers (last 2-3 years)

---

### Query 17: Academic Labs
```
Show me recent work from the Stanford Vision Lab
```

**Expected AI Behavior:**
- Affiliation: Stanford + common lab members
- Topic: computer vision
- Recent work

---

### Query 18: Cross-Disciplinary
```
Find papers that combine vision and language
```

**Expected AI Behavior:**
- Keywords: vision-language, VQA, visual question answering, image captioning, CLIP, multimodal
- Returns papers at intersection of CV and NLP

---

## Recruitment-Specific Queries

### Query 19: Hiring Profile
```
Find US-based authors with 5+ CVPR papers in the last 3 years who focus on 3D vision
```

**Expected AI Behavior:**
- Country: USA
- Conference: CVPR
- Year: 2021-2024
- Topic: 3D vision, 3D reconstruction, depth estimation
- Filters for 5+ papers
- Returns ranked candidates

---

### Query 20: Diverse Candidates
```
Find female researchers in machine learning with strong publication records
```

**Expected AI Behavior:**
- Note: Gender inference from names is problematic
- Better approach: Search by affiliation with diversity programs or ask user to specify names
- AI should acknowledge limitation and suggest alternative approaches

**Expected Response:**
```
I can help you find researchers, but I cannot reliably infer gender from names alone.

Would you like me to:
1. Search for researchers from specific institutions known for diversity
2. Filter by specific names you're interested in
3. Find papers from workshops/conferences focused on diversity (e.g., WiML, Black in AI)
```

---

### Query 21: Senior Researchers
```
Find established researchers (10+ years publishing) in deep learning who also have industry experience
```

**Expected AI Behavior:**
- Year range: 2014 or earlier to 2024 (10+ year span)
- Topic: deep learning
- Looks for affiliations spanning academia and industry (Google, Meta, Microsoft, etc.)

---

## Follow-Up Queries (Conversation)

### Initial Query:
```
Find authors in video generation
```

### Follow-Up 1:
```
Filter to only USA-based
```

**Expected AI Behavior:**
- Adds country filter to previous query
- Re-runs search with additional constraint

### Follow-Up 2:
```
Show me their most recent papers
```

**Expected AI Behavior:**
- Takes authors from previous result
- Fetches their latest publications
- Sorts by year (descending)

### Follow-Up 3:
```
Who has the most first-author papers?
```

**Expected AI Behavior:**
- Ranks previous authors by first-author count
- Returns top 10

---

## Edge Cases & Error Handling

### Query 22: Too Broad
```
Find good researchers
```

**Expected AI Response:**
```
Your query is quite broad. Could you help me narrow it down?

Please specify:
- Research area (e.g., computer vision, NLP, robotics)
- Geographic preference (e.g., USA, Europe, Asia)
- Career stage (e.g., established, emerging, PhD students)
- Publication venue (e.g., CVPR, NeurIPS, ICML)

For example: "Find researchers in computer vision from the USA with CVPR papers"
```

---

### Query 23: No Results
```
Find papers on quantum computing from CVPR
```

**Expected AI Response:**
```
I didn't find any papers on quantum computing from CVPR. This makes sense because CVPR (Conference on Computer Vision and Pattern Recognition) focuses on computer vision, not quantum computing.

Would you like me to:
- Search for quantum computing papers in other conferences (e.g., ICML, NeurIPS)?
- Search for computer vision papers instead?
- Search for quantum-inspired algorithms in computer vision?
```

---

### Query 24: Ambiguous Terms
```
Find papers on vision
```

**Expected AI Response:**
```
"Vision" could mean:
1. Computer vision (image processing, object detection, etc.)
2. Vision transformers (ViT architecture)
3. Vision-language models (CLIP, etc.)

Which area are you interested in? Or would you like me to search for all vision-related papers?
```

---

## Meta Queries (About the System)

### Query 25: System Capabilities
```
What conferences are in your database?
```

**Expected AI Behavior:**
- Calls `get_available_conferences()` tool
- Returns list of conferences with counts

**Expected Response:**
```
I have papers from the following conferences:

Top 10 by volume:
1. CVPR - 45,231 papers
2. NeurIPS - 38,942 papers
3. ICLR - 23,456 papers
...

Would you like me to search within a specific conference?
```

---

### Query 26: Data Coverage
```
What years do you have data for?
```

**Expected AI Response:**
```
Our database includes papers from 2012-2024, with the majority from 2018-2024.

Coverage by year:
- 2024: ~15,000 papers (partial year)
- 2023: ~28,000 papers
- 2022: ~26,000 papers
...

Note: Data is most complete for major conferences (CVPR, NeurIPS, ICLR, ICML).
```

---

## Tips for Effective Queries

### Good Queries (Specific)
✅ "Find authors working on video generation in the USA"
✅ "Show me CVPR 2024 papers on diffusion models"
✅ "Who are top researchers in transformers from DeepMind?"

### Vague Queries (Need Refinement)
⚠️ "Find good papers"
⚠️ "Show me researchers"
⚠️ "What's new in AI?"

### Complex Queries (Well-Supported)
✅ "Find US-based authors with 5+ papers on NeRF from top conferences in the last 2 years"
✅ "Compare Stanford and MIT's research output in 3D vision"
✅ "Who transitioned from NLP to vision in the last 3 years?"

---

## Testing Checklist

Use this checklist to validate your AI agent:

- [ ] Basic keyword search works
- [ ] Geographic filtering works (USA, UK, China, etc.)
- [ ] Conference filtering works
- [ ] Year range filtering works
- [ ] Multi-criteria queries work (topic + geography + time)
- [ ] Boolean operators work (AND, OR, NOT)
- [ ] Phrase matching works ("world models")
- [ ] Author profile lookup works
- [ ] Collaboration queries work
- [ ] Comparative queries work
- [ ] Follow-up questions work
- [ ] Error handling for no results
- [ ] Error handling for ambiguous queries
- [ ] System capability queries work
- [ ] Response includes search parameters used
- [ ] Response includes relevant suggestions

---

## Performance Benchmarks

Expected performance targets:

| Metric | Target | Notes |
|--------|--------|-------|
| Response Time | < 5s | Total including API calls |
| Accuracy | > 90% | Correct parameter extraction |
| User Satisfaction | > 80% | Useful results on first try |
| Follow-up Rate | > 30% | Users refine their search |

---

## Feedback & Iteration

After testing queries, document:

1. **What worked well:**
   - Which queries produced great results?
   - What surprised you positively?

2. **What needs improvement:**
   - Which queries produced poor results?
   - Where did the AI misunderstand intent?

3. **Missing capabilities:**
   - What queries did you want to try but couldn't?
   - What features would make it more useful?

Use this feedback to refine prompts and add features!
