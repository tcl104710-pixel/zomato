# Implementation Plan: AI-Powered Restaurant Recommendation System

> **Derived from**: [architecture.md](file:///c:/Users/nagas/Downloads/zomato1/docs/architecture.md) · [context.md](file:///c:/Users/nagas/Downloads/zomato1/docs/context.md)

---

## Phase Overview

### Part 1 — Backend (Phases 0–4)

| Phase | Name                              | Key Deliverable                                                  | Status  |
| ----- | --------------------------------- | ---------------------------------------------------------------- | ------- |
| **0** | Project Scaffolding               | Directory structure, dependencies, env setup                     | ✅ Done |
| **1** | Data Ingestion & Preprocessing    | Cleaned CSV ready for querying (12,140 rows)                     | ✅ Done |
| **2** | Backend API — Core Endpoints      | FastAPI server with filter engine, metadata endpoints            | ✅ Done |
| **3** | Groq LLM Integration              | Working recommendation engine with retry + fallback              | ✅ Done |
| **4** | Backend Hardening & Analytics     | Health endpoint, analytics tracking, logging, tests, error docs  | ✅ Done |

### Part 2 — Frontend (Phases 5–7)

| Phase | Name                              | Key Deliverable                                                  | Status  |
| ----- | --------------------------------- | ---------------------------------------------------------------- | ------- |
| **5** | Frontend Foundation               | Premium dark-themed responsive UI with glassmorphism             | ✅ Done |
| **6** | Frontend — Advanced UX & Polish   | Search history, compare mode, animations, accessibility          | ⬜ TODO |
| **7** | End-to-End Testing & Documentation | Full pipeline tests, README, deployment guide                   | ⬜ TODO |

---

## Part 1 — Backend

---

### Phase 0 — Project Scaffolding

**Goal**: Set up the project structure, install dependencies, and configure environment variables.

#### Directory Structure

```
zomato1/
├── docs/                        # Documentation
│   ├── Problemstatement.txt
│   ├── context.md
│   ├── architecture.md
│   └── implementation-plan.md   ← this file
│
├── data/
│   ├── raw/
│   └── processed/
│
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Settings & API keys (env-based)
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── services/
│   │   ├── data_loader.py       # Dataset loading & caching
│   │   ├── filter_engine.py     # Preference-based filtering
│   │   └── llm_engine.py        # LLM prompt construction & API call
│   └── utils/
│       └── preprocessing.py     # Data cleaning utilities
│
├── frontend/
│   ├── index.html               # Main HTML page
│   ├── styles/
│   │   └── index.css            # Global styles & design system
│   └── scripts/
│       └── app.js               # Frontend logic & API calls
│
├── scripts/
│   └── ingest.py                # One-time data ingestion script
│
├── tests/
│   ├── test_filter_engine.py    # Filter engine unit tests
│   ├── test_api_endpoints.py    # API integration tests
│   └── test_llm_engine.py       # LLM engine tests (mocked)
│
├── .env.example
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

#### Dependencies (`requirements.txt`)

```txt
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pandas>=2.2.0
datasets>=2.20.0
groq>=0.9.0
python-dotenv>=1.0.0
pydantic>=2.7.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

#### ✅ Scaffolding Acceptance Criteria

- [x] All directories and placeholder files exist
- [x] `pip install -r requirements.txt` completes without errors
- [x] `.env` file created with a valid Groq API key

---

### Phase 1 — Data Ingestion & Preprocessing

**Goal**: Download the Zomato dataset from Hugging Face, clean it, and save a processed CSV for runtime use.

#### `scripts/ingest.py`

1. Load dataset using `datasets` library from [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
2. Convert to Pandas DataFrame
3. Apply preprocessing
4. Save cleaned output to `data/processed/zomato_cleaned.csv`

#### `backend/utils/preprocessing.py` — Cleaning Steps

| Step | Action | Detail |
|------|--------|--------|
| 1 | Normalize columns | Lowercase, snake_case column names |
| 2 | Handle missing values | Drop rows with null `restaurant_name` or `location`; fill missing ratings with 0.0 |
| 3 | Parse numeric fields | Convert `average_cost_for_two` to float, `aggregate_rating` to float |
| 4 | Standardize text | Strip whitespace, title-case `location`, lowercase `cuisines` for matching |
| 5 | Deduplicate | Remove exact duplicate rows |
| 6 | Validate ranges | Ensure ratings are 0.0–5.0, costs are non-negative |

#### ✅ Data Ingestion Acceptance Criteria

- [x] `scripts/ingest.py` runs end-to-end without errors
- [x] `data/processed/zomato_cleaned.csv` is generated (12,140 rows)
- [x] Cleaned CSV has consistent types, no critical nulls, no duplicates
- [x] Key fields verified: `restaurant_name`, `location`, `cuisines`, `average_cost_for_two`, `aggregate_rating`

---

### Phase 2 — Backend API — Core Endpoints

**Goal**: Build the FastAPI backend with configuration, data loading, Pydantic schemas, filter engine, and metadata endpoints.

#### `backend/config.py` — Settings

```python
# Key settings exposed from .env
GROQ_API_KEY: str
LLM_MODEL: str          # default: "llama-3.3-70b-versatile"
LLM_TEMPERATURE: float  # default: 0.4
LLM_MAX_TOKENS: int     # default: 1024
DATA_PATH: str           # default: "data/processed/zomato_cleaned.csv"
TOP_N_RESULTS: int       # default: 5
MAX_SHORTLIST: int       # default: 20
BUDGET_RANGES: dict      # low=(0,500), medium=(501,1500), high=(1501,50000)
```

#### `backend/models/schemas.py` — Pydantic Models

```python
class RecommendationRequest(BaseModel):
    location: str
    budget: Literal["low", "medium", "high"]
    cuisine: Optional[str] = None
    min_rating: float = Field(default=3.0, ge=0.0, le=5.0)
    additional_preferences: Optional[str] = None

class RestaurantRecommendation(BaseModel):
    rank: int
    restaurant_name: str
    cuisine: str
    rating: float
    estimated_cost_for_two: float
    explanation: str

class RecommendationResponse(BaseModel):
    recommendations: list[RestaurantRecommendation]
    summary: str
    filters_applied: dict
    total_matches: int
    relaxation_notice: Optional[str] = None
```

#### `backend/services/data_loader.py`

- Load `zomato_cleaned.csv` into Pandas DataFrame on startup
- Cache in memory (module-level singleton)
- Expose helpers: `get_dataframe()`, `get_unique_locations()`, `get_unique_cuisines()`

#### `backend/services/filter_engine.py` — Filter Pipeline

```
Full Dataset
  → filter by location (case-insensitive partial match)
  → filter by budget (map label to cost range)
  → filter by cuisine (case-insensitive substring match, if provided)
  → filter by min_rating (>= threshold)
  → sort by aggregate_rating descending
  → cap at MAX_SHORTLIST (default 20)
```

**Progressive Relaxation** (if < 3 results):
1. Drop cuisine filter → re-run
2. Widen budget by one tier → re-run
3. Lower `min_rating` by 0.5 → re-run
4. Return whatever is available with a relaxation notice

#### `backend/main.py` — FastAPI App

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/recommend` | POST | Accept preferences, return LLM recommendations |
| `/api/meta/locations` | GET | Return distinct locations for dropdown |
| `/api/meta/cuisines` | GET | Return distinct cuisines for dropdown |

#### ✅ API Acceptance Criteria

- [x] `uvicorn backend.main:app --reload` starts without errors
- [x] `GET /api/meta/locations` returns a JSON list of 93 locations
- [x] `GET /api/meta/cuisines` returns a JSON list of 105 cuisines
- [x] `POST /api/recommend` with valid body returns filtered restaurants
- [x] Invalid input returns 422 with clear validation errors

---

### Phase 3 — Groq LLM Integration

**Goal**: Connect the filter engine output to Groq's API and return ranked, explained recommendations.

#### `backend/services/llm_engine.py`

**Responsibilities**:
1. **Build prompt** from user preferences + filtered restaurant shortlist
2. **Call Groq API** using the `groq` Python SDK with JSON mode
3. **Parse JSON response** into `RecommendationResponse` schema
4. **Handle errors** gracefully (retry with backoff, fallback to sorted list)

#### Error Handling

| Error | Strategy |
|-------|----------|
| Groq API key invalid | Log error, return fallback (sorted by rating) |
| Groq rate limited (429) | Retry up to 2x with exponential backoff |
| Connection error | Retry up to 2x, then fallback |
| Malformed JSON from LLM | Retry once with stricter prompt; if still broken, fallback |
| Empty shortlist | Return message "No restaurants match your filters" |

#### ✅ LLM Integration Acceptance Criteria

- [x] `POST /api/recommend` returns LLM-ranked results with explanations
- [x] Response matches `RecommendationResponse` schema
- [x] Fallback works when Groq API is unreachable
- [x] Response time < 5 seconds for typical queries (~2s observed)

---

### Phase 4 — Backend Hardening & Analytics

**Goal**: Add health/status endpoints, request analytics, structured logging, automated tests, and API documentation.

#### 4.1 Health & Status Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Server health check: dataset status, LLM config, uptime |
| `/api/stats` | GET | Query analytics: total requests, avg response time, popular locations |

**`GET /api/health` Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "dataset": {
    "loaded": true,
    "total_restaurants": 12140,
    "total_locations": 93,
    "total_cuisines": 105
  },
  "llm": {
    "configured": true,
    "model": "llama-3.3-70b-versatile",
    "provider": "groq"
  },
  "version": "1.0.0"
}
```

**`GET /api/stats` Response**:
```json
{
  "total_requests": 42,
  "average_response_time_ms": 2340,
  "requests_today": 15,
  "top_locations": [
    {"location": "Koramangala", "count": 8},
    {"location": "Bellandur", "count": 5}
  ],
  "top_cuisines": [
    {"cuisine": "north indian", "count": 12},
    {"cuisine": "chinese", "count": 7}
  ],
  "llm_stats": {
    "total_calls": 38,
    "fallback_count": 4,
    "average_llm_time_ms": 1800
  }
}
```

#### 4.2 Analytics Tracking (`backend/services/analytics.py`)

- Thread-safe in-memory analytics store
- Track: request count, response times, location/cuisine popularity, LLM success/fallback rate
- Middleware to capture per-request timing
- Reset endpoint for development: `POST /api/stats/reset`

#### 4.3 Automated Tests (`tests/`)

| File | Tests |
|------|-------|
| `tests/test_filter_engine.py` | Filter by location, budget, cuisine, rating; progressive relaxation; edge cases |
| `tests/test_api_endpoints.py` | Health check, meta endpoints, recommend endpoint (happy path + errors) |
| `tests/test_llm_engine.py` | Prompt construction, response parsing, fallback on failure (mocked Groq) |

#### 4.4 Enhanced Error Responses

- Structured error JSON with `error_code`, `message`, and `suggestion`
- Rate limiting info in headers

#### ✅ Phase 4 Acceptance Criteria

- [x] `GET /api/health` returns server health with dataset + LLM status
- [x] `GET /api/stats` returns analytics with request counts, popular locations, LLM stats
- [x] Analytics middleware tracks every `/api/recommend` call
- [x] `pytest tests/` passes all tests
- [x] All endpoints documented at `/docs` (Swagger UI)


---

## Part 2 — Frontend

---

### Phase 5 — Frontend Foundation

**Goal**: Build a premium, responsive single-page UI that collects user preferences and displays AI-ranked recommendation cards.

#### Design System

- **Dark-themed glassmorphism** with Zomato-red accents (`hsl(355, 78%, 56%)`)
- **Inter font** from Google Fonts (300–800 weights)
- **Glass surfaces** with `backdrop-filter: blur(16px) saturate(150%)`
- **CSS custom properties** for all design tokens

#### Key Components

| Component | Features |
|-----------|----------|
| **Header** | Sticky, frosted glass, gradient title, pulsing "Powered by Groq" badge |
| **Form** | 2-column grid, custom select/slider, textarea for free-text preferences |
| **Loading** | 3-card shimmer skeleton with `@keyframes shimmer` |
| **Results** | Filter tag pills, AI summary banner, relaxation notice |
| **Cards** | Rank badge, SVG stars, budget indicator (₹/₹₹/₹₹₹), cuisine tags, collapsible explanation |
| **Empty State** | Sad face SVG, message, "Try Different Filters" button |
| **Error Toast** | Fixed bottom, auto-dismiss 6s, slide-up transition |

#### ✅ Phase 5 Acceptance Criteria

- [x] Page loads with populated dropdowns (93 locations, 105 cuisines)
- [x] Loading skeleton appears while awaiting LLM response
- [x] Cards render with stars, budget, cuisine tags, and AI explanations
- [x] Responsive on mobile (1-column) and desktop (2-column)
- [x] Dark theme, glassmorphism, gradient accents, staggered animations
- [x] Error toast and empty state work correctly

---

### Phase 6 — Frontend — Advanced UX & Polish

**Goal**: Add search history, compare mode, enhanced animations, accessibility improvements.

#### 6.1 Search History

- Store last 5 searches in `localStorage`
- "Recent Searches" dropdown below the form
- One-click re-run of past queries

#### 6.2 Compare Mode

- Checkbox on each card to select for comparison
- Side-by-side comparison panel (max 3 restaurants)
- Highlight differences in rating, cost, cuisine

#### 6.3 Enhanced Animations

- Page transition effects
- Card flip animation on hover for mobile
- Confetti effect on #1 ranked restaurant

#### 6.4 Accessibility

- ARIA labels on all interactive elements
- Keyboard navigation (Tab/Enter/Escape)
- Screen reader support for stars and budget
- `prefers-reduced-motion` media query

#### ✅ Phase 6 Acceptance Criteria

- [ ] Search history persists across page reloads
- [ ] Compare mode works with up to 3 restaurants
- [ ] Keyboard-only navigation works end-to-end
- [ ] Passes WAVE accessibility audit

---

### Phase 7 — End-to-End Testing & Documentation

**Goal**: Full pipeline validation, comprehensive README, and deployment guide.

#### 7.1 E2E Test Scenarios

| # | Scenario | Input | Expected |
|---|----------|-------|----------|
| 1 | Happy path | Bellandur, medium, 4.0 | 5 ranked cards |
| 2 | No cuisine | Koramangala, low, 3.0 | Results across all cuisines |
| 3 | No matches | "Timbuktu", high | Empty state or relaxation |
| 4 | Specific cuisine | Indiranagar, Italian, 3.5 | Italian restaurants ranked |
| 5 | LLM failure | Invalid API key | Fallback sorted list |

#### 7.2 Documentation

- `README.md` with setup, usage, architecture overview
- API docs auto-generated at `/docs` (Swagger UI)
- Environment variable reference

#### ✅ Phase 7 Acceptance Criteria

- [ ] All E2E scenarios pass
- [ ] README has complete setup instructions
- [ ] Project builds and runs from clean clone

---

## Quick Start

```bash
# 1. Clone & install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env and add your Groq API key

# 3. Ingest data
python scripts/ingest.py

# 4. Run
python -m uvicorn backend.main:app --reload

# 5. Open http://localhost:8000
```
