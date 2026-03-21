# Ranking Tuning Guide

This guide provides best practices for adjusting ranking weights and optimizing search quality.

## Quick Reference

| Parameter | Default | Range | Impact |
|-----------|---------|-------|--------|
| alpha | 0.7 | 0.0-1.0 | Vector vs keyword balance |
| boost_exact_match | 1.5 | 1.0-3.0 | Exact keyword match priority |
| boost_metadata_match | 1.3 | 1.0-2.0 | Filter match priority |
| boost_quality_signals | 1.2 | 1.0-2.0 | Data quality priority |
| diversity_penalty | 0.9 | 0.0-1.0 | Result variety |
| personalization_weight | 0.2 | 0.0-0.5 | User preference impact |

## When to Adjust Alpha

The `alpha` parameter controls the balance between semantic and keyword search.

### Increase Alpha (> 0.7) When:

- Users search with natural language queries
- Semantic understanding is more important than exact keywords
- Queries contain synonyms or related concepts
- Example: "spacious family home near good schools"

```python
# Semantic-heavy configuration
alpha = 0.85  # 85% semantic, 15% keyword
```

### Decrease Alpha (< 0.7) When:

- Exact keyword matching is critical
- Users search with specific terms (addresses, IDs)
- Domain-specific terminology is important
- Example: "ul. Marszałkowska 100"

```python
# Keyword-heavy configuration
alpha = 0.5  # 50% semantic, 50% keyword
```

### Recommended Values by Use Case

| Use Case | Alpha | Rationale |
|----------|-------|-----------|
| General property search | 0.7 | Balanced approach |
| Address/location search | 0.4 | Keywords matter more |
| Lifestyle/feature search | 0.8 | Semantic understanding key |
| Investment property search | 0.6 | Mix of specific and general |

## Boost Factor Guidelines

### Exact Match Boost (1.0-3.0)

**Purpose:** Prioritize properties containing exact query terms.

**When to increase:**
- Users frequently search for specific features
- Exact term matching improves relevance
- Property descriptions are detailed

**When to decrease:**
- Queries are often vague or misspelled
- Synonyms should be treated equally

```python
# Aggressive exact matching
boost_exact_match = 2.5

# Conservative (let semantic handle it)
boost_exact_match = 1.2
```

### Metadata Match Boost (1.0-2.0)

**Purpose:** Prioritize properties matching filter criteria.

**When to increase:**
- Users heavily use filters
- Filter matches are strong relevance signals
- Filters are specific (e.g., exact room count)

**When to decrease:**
- Users rarely use filters
- Want to show broader results

```python
# Strong filter adherence
boost_metadata_match = 1.8

# Softer filter influence
boost_metadata_match = 1.1
```

### Quality Signals Boost (1.0-2.0)

**Purpose:** Promote listings with complete data.

**When to increase:**
- Want to incentivize complete listings
- Incomplete listings hurt user experience
- Quality correlates with conversion

**When to decrease:**
- Many good properties have incomplete data
- Don't want to penalize new listings

```python
# Reward complete listings
boost_quality_signals = 1.5

# Neutral quality impact
boost_quality_signals = 1.0
```

## Diversity Penalty Guidelines

The diversity penalty (0.0-1.0) reduces scores of similar consecutive results.

### When to Use High Penalty (< 0.85)

- Show variety in first results page
- Users explore different options
- Prevent "same property" fatigue

```python
diversity_penalty = 0.8  # 20% penalty for similar results
```

### When to Use Low Penalty (> 0.95)

- Relevance is paramount
- Users want best matches regardless of variety
- Similar results are expected

```python
diversity_penalty = 0.98  # Minimal penalty
```

## Personalization Guidelines

### Enable Personalization When:

- Users have accounts and history
- Long-term engagement is a goal
- Personalization improves conversion

### Disable Personalization When:

- Most users are anonymous
- Fresh results are preferred
- Avoiding filter bubbles

### Personalization Weight Guidelines

| Weight | Impact | Use Case |
|--------|--------|----------|
| 0.1 | Subtle | Nudge results slightly |
| 0.2 | Moderate | Default, balanced approach |
| 0.3 | Strong | Heavy personalization |
| 0.4+ | Aggressive | Power users with lots of history |

```python
# Moderate personalization (default)
personalization_enabled = True
personalization_weight = 0.2

# Aggressive personalization
personalization_enabled = True
personalization_weight = 0.35
```

## A/B Testing Workflow

### 1. Create Control and Treatment Configs

```bash
# Control (current production values)
POST /api/v1/ranking/configs
{
    "name": "control_v1",
    "alpha": 0.7,
    "boost_exact_match": 1.5
}

# Treatment (new values to test)
POST /api/v1/ranking/configs
{
    "name": "treatment_semantic_heavy",
    "alpha": 0.8,
    "boost_exact_match": 1.3
}
```

### 2. Create Experiment

```bash
POST /api/v1/ranking/experiments
{
    "name": "semantic_vs_keyword_test",
    "control_config_id": "control_v1",
    "treatment_config_id": "treatment_semantic_heavy",
    "traffic_split": 0.5
}
```

### 3. Run and Monitor

```bash
# Get metrics comparison
GET /api/v1/ranking/metrics/compare?config_ids=control_v1,treatment_semantic_heavy
```

### 4. Analyze Results

Key metrics to compare:
- **CTR:** Higher is better (users find relevant results)
- **MRR:** Higher is better (relevant results ranked higher)
- **Dwell Time:** Longer is better (users engaged with property)
- **Conversion:** Bookings/contacts per search

### 5. Roll Out Winner

```bash
# Activate winning configuration
POST /api/v1/ranking/configs/{winning_config_id}/activate
```

## Common Scenarios

### Scenario 1: Users Not Finding Relevant Results

**Symptoms:** Low CTR, high bounce rate

**Solutions:**
1. Increase `alpha` to improve semantic matching
2. Lower `boost_exact_match` to be less restrictive
3. Enable personalization for returning users

### Scenario 2: Too Many Similar Results

**Symptoms:** Same city/type dominates first page

**Solutions:**
1. Lower `diversity_penalty` to 0.8 or lower
2. Increase result variety

### Scenario 3: Low-Quality Listings Ranking High

**Symptoms:** Incomplete properties get clicks

**Solutions:**
1. Increase `boost_quality_signals` to 1.5+
2. Add minimum quality threshold

### Scenario 4: Users Ignore Filters

**Symptoms:** Filters applied but results don't match

**Solutions:**
1. Increase `boost_metadata_match` to 1.8+
2. Check filter implementation

## Performance Considerations

### Ranking Speed

| Operation | Typical Time | Optimization |
|-----------|-------------|--------------|
| Vector search | 10-50ms | Use ANN index |
| Keyword search | 5-20ms | Cache BM25 index |
| Reranking | 1-5ms | Limit candidates |
| Personalization | 2-10ms | Cache user profiles |
| Explanation | 1-3ms | Compute on demand |

### Recommendations

- Cache active `RankingConfig` (60s TTL)
- Cache user preference profiles (60s TTL)
- Limit reranking to top 100 candidates
- Only compute explanations when requested

## Monitoring Checklist

- [ ] Track search latency (p50, p95, p99)
- [ ] Monitor CTR by ranking config
- [ ] Alert on significant metric changes
- [ ] Review A/B experiment results weekly
- [ ] Update configs based on data

## Related Documentation

- [Ranking Algorithm](./ranking-algorithm.md) - Technical details
- [API Reference](../api/routers/ranking_config.py) - Configuration endpoints
- [Search Metrics](../services/search_metrics_service.py) - Metrics collection
