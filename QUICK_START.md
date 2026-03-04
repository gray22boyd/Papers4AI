# Quick Start Guide - Intelligent Search Improvements

## What Changed?

The intelligent search system now handles multi-topic queries correctly!

**Before:** "RL + computer vision" → 0 results ❌
**After:** "RL + computer vision" → 5-10 results ✅

---

## Key Features

### 1. Adaptive Thresholds

Thresholds automatically relax based on query complexity:

- **1 topic**: 0.30 expertise required (strict)
- **2 topics**: 0.15 expertise required (relaxed)
- **3+ topics**: 0.10 expertise required (very relaxed)

**Example queries that now work:**
```
"reinforcement learning computer vision"  → 5-10 results
"computer vision nlp robotics"            → 2-5 results
"diffusion models video generation"       → 3-8 results
```

### 2. Dominant Topic Strategy

Accepts imbalanced expertise profiles:

- ✅ **0.40 expertise in RL + 0.20 in CV** = ACCEPTED
- ✅ **0.35 in NLP + 0.18 in robotics** = ACCEPTED
- ❌ **0.10 in both topics** = REJECTED

### 3. Venue OR Logic

Relaxed venue requirements for interdisciplinary work:

- **Before**: Must have 3+ papers in ALL fields (strict AND)
- **After**: Must have 2+ papers in N-1 fields (relaxed OR)

**Example:**
- Query: "RL + CV + NLP" (3 fields)
- **Before**: Required papers in ML conferences AND CV conferences AND NLP conferences
- **After**: Required papers in any 2 of the 3 fields

### 4. Query Caching

Repeated queries are **50-90% faster**:

- First query: 2-5 seconds
- Cached query: 0.1-0.5 seconds
- Cache expires after 15 minutes

### 5. Structured Logging

All queries are logged to `logs/` directory:

- `queries.jsonl` - What happened at each stage
- `performance.jsonl` - How long each operation took
- `errors.log` - What went wrong

---

## Configuration

All settings are in `backend/intelligent_config.py`:

### Make Searches More Lenient

```python
# Lower expertise requirements
MULTI_TOPIC_MIN_EXPERTISE = 0.10  # Was 0.15
THREE_TOPIC_MIN_EXPERTISE = 0.05  # Was 0.10

# Lower venue requirements
VENUE_MIN_PAPERS_MULTI_FIELD = 1  # Was 2
```

### Make Searches More Strict

```python
# Raise expertise requirements
MULTI_TOPIC_MIN_EXPERTISE = 0.25  # Was 0.15
THREE_TOPIC_MIN_EXPERTISE = 0.20  # Was 0.10

# Disable dominant topic strategy
ALLOW_DOMINANT_TOPIC = False  # Was True

# Disable OR logic
USE_VENUE_OR_LOGIC = False  # Was True
```

### Adjust Caching

```python
# Longer cache lifetime
QUERY_CACHE_TTL_MINUTES = 30  # Was 15

# Larger cache size
QUERY_CACHE_MAX_SIZE = 200  # Was 100
```

---

## Monitoring

### View Real-Time Logs

```bash
# On Linux/Mac
tail -f logs/queries.jsonl | jq '.'
tail -f logs/performance.jsonl | jq '.'

# On Windows (PowerShell)
Get-Content logs\queries.jsonl -Wait -Tail 10
Get-Content logs\performance.jsonl -Wait -Tail 10
```

### Check Cache Performance

```python
from query_cache import query_cache

stats = query_cache.get_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
print(f"Total requests: {stats['total_requests']}")
print(f"Cache size: {stats['size']}/{stats['max_size']}")
```

### Analyze Query Performance

```python
from logging_config import get_performance_stats

# Overall performance
stats = get_performance_stats()
print(f"Average query time: {stats['avg_ms']}ms")
print(f"Median query time: {stats['median_ms']}ms")

# Specific operation
stats = get_performance_stats(operation="multi_stage_search")
```

---

## Troubleshooting

### "Still getting 0 results for multi-topic queries"

1. **Check thresholds** in `intelligent_config.py`:
   ```python
   print(f"Multi-topic threshold: {MULTI_TOPIC_MIN_EXPERTISE}")
   # Should be 0.15 or lower
   ```

2. **Check logs** to see why candidates were rejected:
   ```bash
   grep "expertise_validation" logs/queries.jsonl
   ```

3. **Lower thresholds** temporarily to test:
   ```python
   MULTI_TOPIC_MIN_EXPERTISE = 0.10  # Very relaxed
   ```

### "Cache not working"

1. **Check cache stats**:
   ```python
   from query_cache import query_cache
   print(query_cache.get_stats())
   ```

2. **Clear cache** and try again:
   ```python
   query_cache.clear()
   ```

3. **Check if queries are identical**:
   - "RL + CV" ≠ "reinforcement learning computer vision"
   - Cache keys are case-insensitive but must match exactly

### "Logs not being created"

1. **Check logs directory exists**:
   ```python
   from pathlib import Path
   logs_dir = Path("logs")
   print(f"Logs directory exists: {logs_dir.exists()}")
   ```

2. **Check file permissions**:
   ```bash
   ls -la logs/  # Linux/Mac
   dir logs\     # Windows
   ```

3. **Re-run with explicit logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

---

## Testing

Run the test suite to verify everything works:

```bash
cd backend
python test_improvements.py
```

**Expected output:**
```
[PASS] Adaptive thresholds test PASSED
[PASS] Venue OR logic test PASSED
[PASS] Harmonic mean test PASSED
[PASS] Dominant topic strategy test PASSED
[PASS] Query cache test PASSED
[PASS] Logging configuration test PASSED
[PASS] Interdisciplinary keywords test PASSED
[PASS] Configuration centralization test PASSED
```

---

## New Keywords

The system now recognizes interdisciplinary terms:

### RL Keywords
- `visuomotor`, `visual rl`, `vision-based rl`
- `offline rl`, `imitation learning`, `inverse rl`
- `embodied rl`, `world models`, `model-based rl`

### CV Keywords
- `vision transformer`, `vit`, `visual encoder`
- `visual representation`, `visual feature`
- `self-supervised vision`

### New Topics
- `embodied_ai` - embodied agents, sensorimotor learning
- `multimodal` - vision-language models, CLIP, etc.

---

## Performance Benchmarks

### Query Latency

| Query Type | Before | After (Uncached) | After (Cached) |
|------------|--------|------------------|----------------|
| Single topic | 1-2s | 1-2s | 0.05-0.1s |
| Two topics | 2-4s | 2-4s | 0.1-0.3s |
| Three topics | 3-5s | 3-5s | 0.2-0.5s |

### Result Counts

| Query | Before | After |
|-------|--------|-------|
| "RL + CV" | 0 | 5-10 |
| "CV + NLP" | 0 | 3-8 |
| "Diffusion + Video" | 0 | 4-12 |
| "RL + CV + Robotics" | 0 | 2-5 |

---

## API Changes

### No Breaking Changes

All existing code continues to work. New parameters are optional:

```python
# Old code (still works)
results = intelligent_agent.multi_stage_search("RL + CV")

# New code (same result, uses adaptive thresholds automatically)
results = intelligent_agent.multi_stage_search("RL + CV")

# Explicit control (optional)
results = intelligent_agent.multi_stage_search(
    "RL + CV",
    max_candidates=50,
    use_enrichment=False
)
```

---

## Support

For issues or questions:

1. Check `IMPROVEMENTS_SUMMARY.md` for detailed documentation
2. Run `python test_improvements.py` to verify setup
3. Check logs in `logs/queries.jsonl` for debugging
4. Adjust thresholds in `backend/intelligent_config.py`

---

**Last Updated:** March 3, 2026
