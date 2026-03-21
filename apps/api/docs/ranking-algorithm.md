# Search Result Ranking Algorithm

This document describes the multi-stage ranking pipeline used by the AI Real Estate Assistant.

## Overview

The ranking system uses a hybrid approach combining semantic search (vector embeddings) with keyword matching (BM25), followed by reranking with various boost factors and personalization.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Search Request                                │
│  - Query text                                                     │
│  - Filters (city, price, rooms, etc.)                            │
│  - Optional: include_explanation=true                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Stage 1: Hybrid Search                           │
│                                                                  │
│  Vector Search (α)          Keyword Search (1-α)                │
│  ┌─────────────────┐        ┌─────────────────┐                 │
│  │   Embeddings    │        │      BM25       │                 │
│  │   (ChromaDB)    │        │   (Whoosh)      │                 │
│  └────────┬────────┘        └────────┬────────┘                 │
│           │                          │                          │
│           └──────────┬───────────────┘                          │
│                      ▼                                          │
│            Hybrid Score = α × V + (1-α) × K                     │
│                                                                  │
│  Default: α = 0.7 (configurable via RankingConfig)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Stage 2: Property Reranker                       │
│                                                                  │
│  Boost Factors (applied multiplicatively):                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Exact Match Boost      │ × 1.5 (configurable)              ││
│  │ Metadata Match Boost   │ × 1.3 (configurable)              ││
│  │ Quality Signals Boost  │ × 1.2 (configurable)              ││
│  │ Diversity Penalty      │ × 0.9 (configurable)              ││
│  │ Personalization Boost  │ × (1 + user_weight)               ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Final Score = Hybrid × Boosts × (1 - Diversity Penalty)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Stage 3: Personalization (Optional)              │
│                                                                  │
│  Applied when:                                                   │
│  - User is authenticated                                        │
│  - personalization_enabled = true in config                     │
│  - User has ≥ 3 interactions (views/favorites)                  │
│                                                                  │
│  Boost Components:                                               │
│  - City preference: +0.3 × weight                               │
│  - Price range match: +0.2                                      │
│  - Rooms match: +0.15                                           │
│  - Property type match: +0.2                                    │
│  - Amenity match: +0.1 × weight (max 0.3)                       │
│                                                                  │
│  Total Boost = Sum × personalization_weight                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Final Results                               │
│                                                                  │
│  - Sorted by final score (descending)                           │
│  - Optional: Ranking explanation per result                     │
└─────────────────────────────────────────────────────────────────┘
```

## Ranking Components

### 1. Hybrid Search Score

The hybrid score combines two search methods:

| Method | Weight | Description |
|--------|--------|-------------|
| Vector Search | α (default 0.7) | Semantic similarity using embeddings |
| Keyword Search | 1-α (default 0.3) | BM25 text matching |

**Formula:** `hybrid_score = α × semantic_score + (1-α) × keyword_score`

### 2. Exact Match Boost

Applied when query terms appear exactly in property title or description.

**Default:** 1.5× multiplier

**Example:** Query "Warsaw apartment" matches property with "Modern Apartment Warsaw Center"

### 3. Metadata Match Boost

Applied when property matches user filter criteria.

**Default:** 1.3× multiplier

**Criteria checked:**
- City match
- Property type match
- Room count match
- Price range match

### 4. Quality Signals Boost

Applied based on data completeness.

**Default:** 1.2× multiplier

**Quality factors:**
| Factor | Weight | Condition |
|--------|--------|-----------|
| Price | 0.2 | Price is present |
| Area | 0.2 | Area in sqm is present |
| Images | 0.1 | has_images = true |
| Description | 0.2 | Description > 200 chars |
| Location | 0.1 | Lat/Lon present |
| Extra metadata | 0.2 | Parking, garden, floor, etc. |

### 5. Diversity Penalty

Applied to ensure varied results (different cities, price ranges).

**Default:** 0.9 (10% penalty for similar consecutive results)

### 6. Personalization Boost

Applied based on user behavior history.

**Default:** Disabled (personalization_enabled = false)

**When enabled:**
- Weight: 0.2 (configurable)
- Requires minimum 3 user interactions
- Based on viewed/favorited properties

## Configuration

All ranking weights are configurable via the `RankingConfig` database model.

### Default Configuration

```python
DEFAULT_RANKING_CONFIG = {
    "alpha": 0.7,
    "boost_exact_match": 1.5,
    "boost_metadata_match": 1.3,
    "boost_quality_signals": 1.2,
    "diversity_penalty": 0.9,
    "weight_recency": 0.1,
    "weight_price_match": 0.15,
    "weight_location": 0.1,
    "personalization_enabled": False,
    "personalization_weight": 0.2,
}
```

### Managing Configurations

Use the Ranking Config API:

```bash
# List all configurations
GET /api/v1/ranking/configs

# Get active configuration
GET /api/v1/ranking/configs/active

# Create new configuration
POST /api/v1/ranking/configs
{
    "name": "aggressive_personalization",
    "description": "Higher weight on user preferences",
    "alpha": 0.6,
    "personalization_enabled": true,
    "personalization_weight": 0.3
}

# Activate a configuration
POST /api/v1/ranking/configs/{config_id}/activate
```

## Ranking Explanation

When `include_explanation=true` is passed in the search request, each result includes a detailed breakdown of the ranking score.

### Example Response

```json
{
    "results": [
        {
            "property": {...},
            "score": 0.85,
            "explanation": {
                "property_id": "prop-123",
                "final_score": 0.85,
                "rank": 1,
                "semantic_score": 0.9,
                "keyword_score": 0.7,
                "hybrid_score": 0.84,
                "exact_match_boost": 0.8,
                "metadata_match_boost": 0.7,
                "quality_boost": 0.6,
                "personalization_boost": 0.0,
                "diversity_penalty": 1.0,
                "components": [
                    {
                        "name": "semantic_similarity",
                        "value": 0.9,
                        "weight": 0.7,
                        "contribution": 0.63,
                        "description": "Vector similarity score weighted at 70%"
                    },
                    {
                        "name": "keyword_match",
                        "value": 0.7,
                        "weight": 0.3,
                        "contribution": 0.21,
                        "description": "Keyword match (BM25) weighted at 30%"
                    },
                    {
                        "name": "exact_match",
                        "value": 0.8,
                        "weight": 1.5,
                        "contribution": 1.2,
                        "description": "Boost for exact keyword matches in title/description"
                    }
                ]
            }
        }
    ],
    "count": 1
}
```

## A/B Testing

The ranking system supports A/B testing through the `ABExperiment` and `ABExperimentAssignment` models.

### Setting Up an Experiment

1. Create two ranking configurations (control and treatment)
2. Create an experiment linking them
3. Users are automatically assigned based on session ID hash

### Experiment Assignment

- Deterministic: Same session always gets same variant
- 50/50 split by default (configurable)
- Tracked via `experiment_id` in search events

## Metrics Collection

Search quality metrics are collected for evaluation:

| Metric | Description |
|--------|-------------|
| CTR | Click-through rate (clicks / results shown) |
| MRR | Mean Reciprocal Rank (position of first click) |
| NDCG | Normalized Discounted Cumulative Gain |
| Dwell Time | Time spent viewing property |

These metrics can be compared across ranking configurations to evaluate performance.

## See Also

- [Ranking Tuning Guide](./ranking-tuning-guide.md) - Best practices for adjusting weights
- [API Reference](../api/routers/ranking_config.py) - Configuration endpoints
- [Personalization Service](../services/personalization_service.py) - User preference tracking
