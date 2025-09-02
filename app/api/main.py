"""
FastAPI application for CurtainTime backend.
Provides REST API endpoints for theatre data and scraping operations.
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from ..models.database import get_db, Theatre, Show, ScrapeLog
from ..celery_app import celery_app


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CurtainTime Backend",
    description="Backend API for theatre show scraping and management",
    version="0.1.0",
)



# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API responses
from pydantic import BaseModel


class TheatreResponse(BaseModel):
    id: str
    name: str
    base_url: str
    enabled: bool

    class Config:
        from_attributes = True


class ShowResponse(BaseModel):
    id: int
    theatre_id: str
    title: str
    start_datetime_utc: datetime
    description: Optional[str] = None
    image_url: Optional[str] = None
    ticket_url: Optional[str] = None

    class Config:
        from_attributes = True


class ScrapeLogResponse(BaseModel):
    id: int
    theatre_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    shows_found: Optional[int] = None
    shows_added: Optional[int] = None
    shows_updated: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CurtainTime Backend API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.get("/theatres", response_model=List[TheatreResponse])
async def get_theatres(db: Session = Depends(get_db)):
    """Get all configured theatres."""
    theatres = db.query(Theatre).filter(Theatre.enabled == True).all()
    return theatres


@app.get("/theatres/{theatre_id}", response_model=TheatreResponse)
async def get_theatre(theatre_id: str, db: Session = Depends(get_db)):
    """Get a specific theatre by ID."""
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")
    return theatre


@app.get("/theatres/{theatre_id}/shows", response_model=List[ShowResponse])
async def get_theatre_shows(
    theatre_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get upcoming shows for a specific theatre."""
    shows = (
        db.query(Show)
        .filter(Show.theatre_id == theatre_id)
        .filter(Show.start_datetime_utc >= datetime.utcnow())
        .order_by(Show.start_datetime_utc)
        .limit(limit)
        .all()
    )
    return shows


@app.get("/shows", response_model=List[ShowResponse])
async def get_shows(
    limit: int = 50,
    theatre_id: Optional[str] = None,
    days_ahead: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get upcoming shows with optional filtering."""
    query = db.query(Show).filter(Show.start_datetime_utc >= datetime.utcnow())

    if theatre_id:
        query = query.filter(Show.theatre_id == theatre_id)

    if days_ahead:
        end_date = datetime.utcnow() + timedelta(days=days_ahead)
        query = query.filter(Show.start_datetime_utc <= end_date)

    shows = query.order_by(Show.start_datetime_utc).limit(limit).all()
    return shows


@app.get("/scraping/logs", response_model=List[ScrapeLogResponse])
async def get_scraping_logs(
    limit: int = 20,
    theatre_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get recent scraping logs."""
    query = db.query(ScrapeLog).order_by(ScrapeLog.started_at.desc())

    if theatre_id:
        query = query.filter(ScrapeLog.theatre_id == theatre_id)

    logs = query.limit(limit).all()
    return logs


# Admin endpoints for manual operations

@app.post("/admin/scrape/{theatre_id}")
async def trigger_scrape(theatre_id: str):
    """Manually trigger a scrape for a specific theatre."""
    from ..tasks.scraping import scrape_single_theatre

    # Check if theatre exists
    db = next(get_db())
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    db.close()

    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")

    # Trigger the scraping task
    task = scrape_single_theatre.delay(theatre_id, force_scrape=True)

    return {
        "message": f"Scraping triggered for {theatre.name}",
        "task_id": task.id,
        "theatre_id": theatre_id
    }


@app.post("/admin/scrape-all")
async def trigger_scrape_all():
    """Manually trigger scraping for all enabled theatres."""
    from ..tasks.scraping import scrape_all_theatres

    task = scrape_all_theatres.delay(force_scrape=True)

    return {
        "message": "Full scraping cycle triggered",
        "task_id": task.id
    }


@app.get("/admin/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a Celery task."""
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "error": str(result.info) if result.failed() else None
    }


# Configure Jinja2 templates
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Include dashboard routes
from ..dashboard_routes import router as dashboard_router, set_templates
set_templates(templates)  # Pass templates to dashboard routes
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
