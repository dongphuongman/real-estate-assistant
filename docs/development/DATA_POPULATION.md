# Data Population Guide

## Overview

The seed script (`apps/api/alembic/seed.py`) populates the system with sample data for local development and demo purposes. It is **idempotent** — safe to run multiple times.

## Data Architecture

The project uses two data stores:

| Store | Technology | What it holds |
|-------|-----------|---------------|
| **ChromaDB** | Vector store | Properties (Pydantic `Property` models) |
| **PostgreSQL** | Relational DB | Users, saved searches, notification prefs, favorites, collections |

Properties are stored as vector-embedded documents in ChromaDB for semantic search, not as SQLAlchemy rows in PostgreSQL.

## Running the Seed

```bash
cd apps/api

# Seed all data (idempotent — skips existing records)
python -m alembic.seed

# Clear everything first, then seed fresh
python -m alembic.seed --clear
```

## What Gets Seeded

### ChromaDB (Properties)

25 sample properties across 3 cities:

| City | Count | Price Range |
|------|-------|-------------|
| Krakow | 15 | 250k–680k PLN |
| Warsaw | 6 | 480k–1.4M PLN |
| Munich | 4 | 250k–1.2M EUR |

Property types: apartment, house, townhouse.
Listing types: sale, rent.

### PostgreSQL (Relational)

| Table | Records |
|-------|---------|
| `users` | 2 (Alice Demo, Bob Agent) |
| `saved_searches` | 2 (one per user) |
| `notification_preferences` | 2 (one per user) |

Sample users:
- `alice@example.com` (user role) — password: `demo-password`
- `bob@example.com` (agent role) — password: `demo-password`

## Auto-Seed on Startup

The Docker Compose configuration (`deploy/compose/docker-compose.yml`) supports auto-seeding via the `SEED_ON_STARTUP` environment variable:

```yaml
environment:
  SEED_ON_STARTUP: "true"
```

When enabled, the backend runs the seed script on startup if ChromaDB is empty.

## Programmatic Usage

```python
from alembic.seed import seed_all

# Seed all data
await seed_all()

# Clear and re-seed
await seed_all(clear=True)
```

## Extending Sample Data

To add more sample properties, edit the `SAMPLE_PROPERTIES` list in `apps/api/alembic/seed.py`. Each entry is a dict matching the `Property` Pydantic schema fields:

```python
{
    "id": "prop-XXX",
    "title": "Property Title",
    "city": "CityName",
    "price": 500000,
    "currency": "PLN",
    "rooms": 3,
    "area_sqm": 80,
    "property_type": "apartment",  # apartment | house | townhouse
    "listing_type": "sale",        # sale | rent
    # ... optional fields
}
```
