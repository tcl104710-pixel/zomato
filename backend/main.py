"""
Zomato AI Restaurant Recommender -- FastAPI Entry Point.

Serves the recommendation API, health/stats endpoints, and static frontend.
"""

import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.config import settings
from backend.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
)
from backend.services import data_loader
from backend.services.filter_engine import filter_restaurants
from backend.services.llm_engine import get_recommendations
from backend.services.analytics import analytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- App setup ---
app = FastAPI(
    title="Zomato AI Restaurant Recommender",
    description="AI-powered restaurant recommendations using Groq LLM",
    version="1.0.0",
)

# CORS middleware (allow all origins in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# --- Exception Handlers (Phase 4.4) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Structured error response for input validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Invalid request parameters.",
            "suggestion": "Check the location, budget, or rating fields.",
            "details": exc.errors()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Structured error response for standard HTTP exceptions."""
    headers = exc.headers or {}
    if exc.status_code == 429:
        headers["Retry-After"] = "60"
        headers["X-RateLimit-Limit"] = "100"
        headers["X-RateLimit-Remaining"] = "0"
        
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "suggestion": "Please try again or contact support."
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "suggestion": "The team has been notified. Please try again later."
        }
    )



# --- Startup event ---
@app.on_event("startup")
async def startup_event():
    """Pre-load dataset into memory on server start."""
    try:
        df = data_loader.load_data()
        logger.info(
            f"Server ready -- {df.shape[0]} restaurants loaded, "
            f"{df['location'].nunique()} locations, "
            f"serving on http://localhost:8000"
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        logger.error("The server will start but /api/recommend will return 503.")

    # Log LLM configuration status
    if settings.GROQ_API_KEY:
        logger.info(f"LLM configured: model={settings.LLM_MODEL}")
    else:
        logger.warning(
            "GROQ_API_KEY not set. LLM ranking will be unavailable; "
            "fallback (rating-sorted) results will be used."
        )


# --- Health & Status Endpoints ---

@app.get("/api/health")
async def health_check():
    """
    Server health check.

    Returns dataset status, LLM configuration, and uptime.
    """
    # Dataset status
    dataset_info = {"loaded": False, "total_restaurants": 0, "total_locations": 0, "total_cuisines": 0}
    try:
        df = data_loader.get_dataframe()
        dataset_info = {
            "loaded": True,
            "total_restaurants": df.shape[0],
            "total_locations": df["location"].nunique(),
            "total_cuisines": len(data_loader.get_unique_cuisines()),
        }
    except FileNotFoundError:
        pass

    # LLM status
    llm_info = {
        "configured": bool(settings.GROQ_API_KEY),
        "model": settings.LLM_MODEL,
        "provider": "groq",
    }

    return {
        "status": "healthy" if dataset_info["loaded"] else "degraded",
        "uptime_seconds": analytics.get_uptime_seconds(),
        "dataset": dataset_info,
        "llm": llm_info,
        "version": app.version,
    }


@app.get("/api/stats")
async def get_stats():
    """
    Request analytics.

    Returns aggregate statistics: total requests, response times,
    popular locations/cuisines, and LLM success rates.
    """
    return analytics.get_stats()


@app.post("/api/stats/reset")
async def reset_stats():
    """Reset all analytics data. Useful during development."""
    analytics.reset()
    return {"message": "Analytics data reset successfully."}


# --- API Endpoints ---

@app.post("/api/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest):
    """
    Get AI-ranked restaurant recommendations based on user preferences.

    Pipeline:
      1. Filter the dataset by location, budget, cuisine, and rating.
      2. Send the shortlist to the Groq LLM for intelligent ranking.
      3. Return ranked recommendations with explanations.
      4. On LLM failure, return fallback results sorted by rating.
    """
    request_start = time.time()

    try:
        data_loader.get_dataframe()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded. Run 'python scripts/ingest.py' first.",
        )

    # Step 1: Apply filters
    result = filter_restaurants(request)

    if result.total_matches == 0:
        # Record analytics even for empty results
        elapsed_ms = (time.time() - request_start) * 1000
        analytics.record_request(
            location=request.location,
            cuisine=request.cuisine,
            response_time_ms=elapsed_ms,
            used_llm=False,
            llm_fallback=False,
        )
        return RecommendationResponse(
            recommendations=[],
            summary="No restaurants match your filters. Try adjusting your preferences.",
            filters_applied=result.filters_applied,
            total_matches=0,
            relaxation_notice=result.relaxation_notice,
        )

    # Step 2 & 3: Get LLM-ranked recommendations (with automatic fallback)
    llm_start = time.time()
    recommendations, summary = get_recommendations(request, result.df)
    llm_elapsed_ms = (time.time() - llm_start) * 1000

    # Detect fallback (summary contains the fallback marker)
    is_fallback = "AI ranking was unavailable" in summary

    # Record analytics
    total_elapsed_ms = (time.time() - request_start) * 1000
    analytics.record_request(
        location=request.location,
        cuisine=request.cuisine,
        response_time_ms=total_elapsed_ms,
        used_llm=True,
        llm_fallback=is_fallback,
        llm_time_ms=llm_elapsed_ms,
    )

    return RecommendationResponse(
        recommendations=recommendations,
        summary=summary,
        filters_applied=result.filters_applied,
        total_matches=result.total_matches,
        relaxation_notice=result.relaxation_notice,
    )


@app.get("/api/meta/locations")
async def get_locations():
    """Return distinct locations available in the dataset."""
    try:
        locations = data_loader.get_unique_locations()
        return {"locations": locations, "count": len(locations)}
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded. Run 'python scripts/ingest.py' first.",
        )


@app.get("/api/meta/cuisines")
async def get_cuisines():
    """Return distinct cuisines available in the dataset."""
    try:
        cuisines = data_loader.get_unique_cuisines()
        return {"cuisines": cuisines, "count": len(cuisines)}
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded. Run 'python scripts/ingest.py' first.",
        )


# --- Static file serving (frontend) ---
# Must be LAST so it doesn't intercept API routes
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
