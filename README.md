# 🍽️ Zomato AI Restaurant Recommender

An AI-powered restaurant recommendation system that combines real-world Zomato data with Groq LLM to deliver personalized, explained restaurant suggestions.

## ✨ Features

- **Smart Filtering** — Filter by location, budget, cuisine, and minimum rating
- **AI-Powered Ranking** — Groq LLM ranks and explains why each restaurant fits your preferences
- **Beautiful UI** — Dark-themed, responsive interface with animated recommendation cards
- **Fallback Safety** — Graceful degradation when LLM is unavailable

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | HTML + CSS + Vanilla JS |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Data | Pandas + Hugging Face Datasets |

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd zomato1
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

### 3. Ingest Dataset

```bash
python scripts/ingest.py
```

This downloads and preprocesses the Zomato dataset from Hugging Face.

### 4. Start the Server

```bash
uvicorn backend.main:app --reload
```

### 5. Open the App

Visit [http://localhost:8000](http://localhost:8000) in your browser.

## 📁 Project Structure

```
zomato1/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings & env loading
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── services/
│   │   ├── data_loader.py   # Dataset loading & caching
│   │   ├── filter_engine.py # Preference-based filtering
│   │   └── llm_engine.py    # Groq LLM prompt & API call
│   └── utils/
│       └── preprocessing.py # Data cleaning utilities
├── frontend/
│   ├── index.html           # Main UI page
│   ├── styles/
│   │   └── index.css        # Global styles (dark theme)
│   └── scripts/
│       └── app.js           # Frontend logic & API calls
├── scripts/
│   └── ingest.py            # One-time data ingestion
├── data/
│   ├── raw/                 # Original dataset (gitignored)
│   └── processed/           # Cleaned CSV
├── docs/                    # Documentation
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recommend` | POST | Get AI-ranked restaurant recommendations |
| `/api/meta/locations` | GET | List available locations |
| `/api/meta/cuisines` | GET | List available cuisines |

## 📄 License

This project is for educational purposes.
