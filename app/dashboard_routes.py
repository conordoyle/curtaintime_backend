"""
Dashboard routes for theatre scraping system management.
Provides web interface for monitoring and controlling the scraper.
"""
import logging
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import pytz
import json
import os

# Configure logging
logger = logging.getLogger(__name__)

from .models.database import SessionLocal, Theatre, Show, ScrapeLog, ScheduledScrape, get_db
from .scrapers.theatre_scraper import TheatreScraper
from .tasks.scraping import scrape_single_theatre
from .tasks.scheduling import _calculate_next_run
from datetime import datetime

router = APIRouter()

# Timezone utilities
UTC = pytz.UTC
EST = pytz.timezone('US/Eastern')

def utc_to_est(utc_dt):
    """Convert UTC datetime to EST"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = UTC.localize(utc_dt)
    return utc_dt.astimezone(EST)

# Global variable to hold templates - will be set from main app
templates = None

def set_templates(templates_instance):
    """Set the templates instance from the main app."""
    global templates
    templates = templates_instance


# Dashboard Home
@router.get("/")
async def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """Main dashboard overview page."""
    from datetime import datetime

    # Get statistics
    total_theatres = db.query(Theatre).count()
    active_theatres = db.query(Theatre).filter(Theatre.enabled == True).count()
    total_shows = db.query(Show).count()
    recent_shows = db.query(Show).filter(
        Show.start_datetime_utc >= datetime.utcnow()
    ).count()

    # Recent scraping activity
    recent_logs = db.query(ScrapeLog).order_by(
        ScrapeLog.started_at.desc()
    ).limit(5).all()

    # Convert UTC times to EST for display
    for log in recent_logs:
        if log.started_at:
            log.started_at_est = utc_to_est(log.started_at)

    # System health
    failed_scrapes = db.query(ScrapeLog).filter(
        ScrapeLog.status == "error"
    ).count()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "total_theatres": total_theatres,
            "active_theatres": active_theatres,
            "total_shows": total_shows,
            "recent_shows": recent_shows,
            "failed_scrapes": failed_scrapes
        },
        "recent_logs": recent_logs,
        "now": utc_to_est(datetime.utcnow())
    })


# Theatres Management
@router.get("/theatres")
async def theatres_list(request: Request, db: Session = Depends(get_db)):
    """List all theatres with management options."""
    theatres = db.query(Theatre).order_by(Theatre.name).all()

    # Add show counts for each theatre
    for theatre in theatres:
        theatre.show_count = db.query(Show).filter(
            Show.theatre_id == theatre.id
        ).count()

        # Recent scrape status
        recent_log = db.query(ScrapeLog).filter(
            ScrapeLog.theatre_id == theatre.id
        ).order_by(ScrapeLog.started_at.desc()).first()

        theatre.last_scrape = recent_log.started_at if recent_log else None
        theatre.last_scrape_est = utc_to_est(recent_log.started_at) if recent_log else None
        theatre.last_status = recent_log.status if recent_log else "never"

    return templates.TemplateResponse("theatres.html", {
        "request": request,
        "theatres": theatres
    })


@router.post("/theatres/{theatre_id}/scrape")
async def trigger_theatre_scrape(theatre_id: str, db: Session = Depends(get_db)):
    """Trigger a manual scrape for a specific theatre."""
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")

    try:
        # Check if Redis/Celery is available, otherwise do synchronous scraping
        import os
        redis_url = os.getenv('REDIS_URL', '')

        if redis_url and not redis_url.startswith('redis://username:password@hostname'):
            # Use async Celery task
            task = scrape_single_theatre.delay(theatre_id, force_scrape=True)
            message = f"Scrape+queued+for+{theatre.name}+(async)"
        else:
            # Do synchronous scraping
            from .scrapers.theatre_scraper import TheatreScraper
            from .parsers.openai_parser import OpenAIParser
            from .models.database import ScrapeLog
            import json

            # Get API keys from environment
            firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
            if not firecrawl_key:
                raise Exception("FIRECRAWL_API_KEY not found in environment variables")

            scraper = TheatreScraper(firecrawl_api_key=firecrawl_key)
            parser = OpenAIParser()

            # Create scrape log
            scrape_log = ScrapeLog(
                theatre_id=theatre_id,
                status="running",
                shows_found=0,
                shows_added=0,
                shows_updated=0
            )
            db.add(scrape_log)
            db.commit()

            try:
                # Scrape the theatre
                result = scraper.scrape_with_config(theatre, theatre.config_data or {})
                markdown_content = result.markdown_content if result else ""

                if markdown_content:
                    scrape_log.raw_markdown = markdown_content
                    scrape_log.status = "success"

                    # Parse the content
                    print(f"🔍 Parsing markdown content ({len(markdown_content)} chars)...")
                    shows_data = parser.parse_theatre_markdown(markdown_content, theatre.name, scrape_log.id)
                    print(f"✅ Parsed {len(shows_data) if shows_data else 0} shows")

                    if shows_data:
                        # Replace all shows for this theatre with newly parsed data
                        try:
                            # Count existing shows for logging
                            existing_count = db.query(Show).filter(Show.theatre_id == theatre_id).count()
                            print(f"📊 Found {existing_count} existing shows for theatre {theatre_id}")

                            # Delete all existing shows for this theatre
                            deleted_count = db.query(Show).filter(Show.theatre_id == theatre_id).delete()
                            print(f"🗑️  Deleted {deleted_count} existing shows")

                            # Insert all new shows
                            replaced_count = 0
                            for show_data in shows_data:
                                print(f"💾 Adding show: {show_data.title}")
                                new_show = Show(
                                    theatre_id=theatre_id,
                                    title=show_data.title,
                                    start_datetime_utc=show_data.start_datetime,
                                    description=show_data.description,
                                    image_url=show_data.image_url,
                                    ticket_url=show_data.ticket_url
                                )
                                db.add(new_show)
                                replaced_count += 1

                            scrape_log.shows_found = len(shows_data)
                            scrape_log.shows_added = replaced_count
                            scrape_log.shows_updated = 0  # No updates in replace mode
                            scrape_log.scrape_metadata = {
                                "parsed_shows": len(shows_data),
                                "shows_deleted": deleted_count
                            }
                            print(f"✅ Successfully replaced {replaced_count} shows, deleted {deleted_count} shows")

                        except Exception as e:
                            print(f"❌ Error during show replacement: {str(e)}")
                            db.rollback()
                            raise
                    else:
                        scrape_log.scrape_metadata = {"error": "No shows parsed"}
                else:
                    scrape_log.status = "error"
                    scrape_log.error_message = "No content scraped"

                scrape_log.completed_at = datetime.utcnow()
                db.commit()

                message = f"Scrape+completed+for+{theatre.name}+(sync)"

            except Exception as e:
                print(f"❌ Scrape error for {theatre.name}: {e}")
                import traceback
                traceback.print_exc()
                scrape_log.status = "error"
                scrape_log.error_message = str(e)
                scrape_log.completed_at = datetime.utcnow()
                db.commit()
                message = f"Scrape+failed+for+{theatre.name}:+{str(e).replace(' ', '+')}"

    except Exception as e:
        message = f"Error+triggering+scrape+for+{theatre.name}:+{str(e)}"

    return RedirectResponse(
        url=f"/dashboard/theatres?message={message}",
        status_code=303
    )


# Theatre CRUD Routes

@router.get("/theatres/create")
async def create_theatre_form(request: Request):
    """Show form to create a new theatre."""
    return templates.TemplateResponse("theatre_form.html", {
        "request": request,
        "title": "Create Theatre",
        "action": "create",
        "theatre": None
    })


@router.post("/theatres/create")
async def create_theatre(
    request: Request,
    theatre_id: str = Form(...),
    theatre_name: str = Form(...),
    base_url: str = Form(...),
    enabled: bool = Form(False),
    config_json: str = Form(""),
    db: Session = Depends(get_db)
):
    """Create a new theatre."""
    try:
        # Validate theatre_id doesn't exist
        existing = db.query(Theatre).filter(Theatre.id == theatre_id).first()
        if existing:
            return templates.TemplateResponse("theatre_form.html", {
                "request": request,
                "title": "Create Theatre",
                "action": "create",
                "theatre": None,
                "error": f"Theatre ID '{theatre_id}' already exists"
            })

        # Parse config JSON if provided
        config_data = None
        if config_json.strip():
            try:
                config_data = json.loads(config_json)
            except json.JSONDecodeError:
                return templates.TemplateResponse("theatre_form.html", {
                    "request": request,
                    "title": "Create Theatre",
                    "action": "create",
                    "theatre": None,
                    "error": "Invalid JSON configuration"
                })

        # Create theatre
        theatre = Theatre(
            id=theatre_id,
            name=theatre_name,
            base_url=base_url,
            config_data=config_data,
            enabled=enabled
        )

        db.add(theatre)
        db.commit()
        db.refresh(theatre)

        return RedirectResponse(
            url=f"/dashboard/theatres?message=Theatre+{theatre_name}+created+successfully",
            status_code=303
        )

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("theatre_form.html", {
            "request": request,
            "title": "Create Theatre",
            "action": "create",
            "theatre": None,
            "error": f"Error creating theatre: {str(e)}"
        })


@router.get("/theatres/{theatre_id}/edit")
async def edit_theatre_form(request: Request, theatre_id: str, db: Session = Depends(get_db)):
    """Show form to edit an existing theatre."""
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")

    return templates.TemplateResponse("theatre_form.html", {
        "request": request,
        "title": f"Edit Theatre: {theatre.name}",
        "action": "edit",
        "theatre": theatre,
        "config_json": json.dumps(theatre.config_data, indent=2) if theatre.config_data else ""
    })


@router.post("/theatres/{theatre_id}/edit")
async def update_theatre(
    request: Request,
    theatre_id: str,
    theatre_name: str = Form(...),
    base_url: str = Form(...),
    enabled: bool = Form(False),
    config_json: str = Form(""),
    db: Session = Depends(get_db)
):
    """Update an existing theatre."""
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")

    try:
        # Parse config JSON if provided
        config_data = None
        if config_json.strip():
            try:
                config_data = json.loads(config_json)
            except json.JSONDecodeError:
                return templates.TemplateResponse("theatre_form.html", {
                    "request": request,
                    "title": f"Edit Theatre: {theatre.name}",
                    "action": "edit",
                    "theatre": theatre,
                    "config_json": config_json,
                    "error": "Invalid JSON configuration"
                })

        # Update theatre
        theatre.name = theatre_name
        theatre.base_url = base_url
        theatre.config_data = config_data
        theatre.enabled = enabled
        theatre.updated_at = datetime.utcnow()

        db.commit()

        return RedirectResponse(
            url=f"/dashboard/theatres?message=Theatre+{theatre_name}+updated+successfully",
            status_code=303
        )

    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("theatre_form.html", {
            "request": request,
            "title": f"Edit Theatre: {theatre.name}",
            "action": "edit",
            "theatre": theatre,
            "config_json": config_json,
            "error": f"Error updating theatre: {str(e)}"
        })


@router.post("/theatres/{theatre_id}/delete")
async def delete_theatre(theatre_id: str, db: Session = Depends(get_db)):
    """Delete a theatre."""
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")

    try:
        # Delete associated shows and scrape logs first
        db.query(Show).filter(Show.theatre_id == theatre_id).delete()
        db.query(ScrapeLog).filter(ScrapeLog.theatre_id == theatre_id).delete()

        # Delete theatre
        theatre_name = theatre.name
        db.delete(theatre)
        db.commit()

        return RedirectResponse(
            url=f"/dashboard/theatres?message=Theatre+{theatre_name}+deleted+successfully",
            status_code=303
        )

    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url=f"/dashboard/theatres?error=Error+deleting+theatre+{theatre.name}",
            status_code=303
        )


@router.post("/theatres/{theatre_id}/toggle")
async def toggle_theatre(theatre_id: str, db: Session = Depends(get_db)):
    """Toggle theatre enabled/disabled status."""
    theatre = db.query(Theatre).filter(Theatre.id == theatre_id).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")

    try:
        theatre.enabled = not theatre.enabled
        theatre.updated_at = datetime.utcnow()
        db.commit()

        status = "enabled" if theatre.enabled else "disabled"
        return RedirectResponse(
            url=f"/dashboard/theatres?message=Theatre+{theatre.name}+{status}",
            status_code=303
        )

    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url=f"/dashboard/theatres?error=Error+toggling+theatre+status",
            status_code=303
        )


@router.get("/theatres/import")
async def import_theatres_form(request: Request):
    """Show form to import theatres from config files."""
    import os
    from pathlib import Path

    # Find available config files
    config_dir = Path("../theatre_scraper/configs")
    available_configs = []

    if config_dir.exists():
        for config_file in config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                available_configs.append({
                    "id": config.get("theatre_id", config_file.stem),
                    "name": config.get("theatre_name", config_file.stem),
                    "file": config_file.name
                })
            except:
                continue

    return templates.TemplateResponse("import_theatres.html", {
        "request": request,
        "available_configs": available_configs
    })


@router.post("/theatres/import")
async def import_theatres(request: Request, selected_configs: List[str] = Form([]), db: Session = Depends(get_db)):
    """Import selected theatres from config files."""
    imported_count = 0
    errors = []

    for config_id in selected_configs:
        try:
            # Load config file
            config_file = f"../theatre_scraper/configs/{config_id}.json"
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            theatre_id = config_data["theatre_id"]

            # Check if theatre already exists
            existing = db.query(Theatre).filter(Theatre.id == theatre_id).first()
            if existing:
                errors.append(f"{theatre_id}: Already exists")
                continue

            # Create theatre
            theatre = Theatre(
                id=theatre_id,
                name=config_data["theatre_name"],
                base_url=config_data["base_url"],
                config_data=config_data,
                enabled=config_data.get("enabled", True)
            )

            db.add(theatre)
            imported_count += 1

        except Exception as e:
            errors.append(f"{config_id}: {str(e)}")

    db.commit()

    message = f"Imported {imported_count} theatres successfully"
    if errors:
        message += f" ({len(errors)} errors)"

    return RedirectResponse(
        url=f"/dashboard/theatres?message={message.replace(' ', '+')}",
        status_code=303
    )


# Shows Browser
@router.get("/shows")
async def shows_browser(
    request: Request,
    theatre_id: Optional[str] = None,
    days_ahead: Optional[str] = "365",
    db: Session = Depends(get_db)
):
    """Browse all shows with filtering options."""
    query = db.query(Show)

    if theatre_id:
        query = query.filter(Show.theatre_id == theatre_id)

    # Convert days_ahead to int if provided, otherwise None for all future shows
    days_ahead_int = None
    if days_ahead and days_ahead.strip():
        try:
            days_ahead_int = int(days_ahead)
        except ValueError:
            days_ahead_int = 365  # fallback to 365 days

    # Always filter for future events only
    start_date = datetime.utcnow()
    if days_ahead_int:
        # Show future events within the specified days ahead
        end_date = datetime.utcnow() + timedelta(days=days_ahead_int)
        query = query.filter(Show.start_datetime_utc >= start_date, Show.start_datetime_utc <= end_date)
    else:
        # Show all future events
        query = query.filter(Show.start_datetime_utc >= start_date)

    shows = query.order_by(Show.start_datetime_utc).all()

    # Get theatre info for display
    theatres = db.query(Theatre).all()
    theatre_dict = {t.id: t for t in theatres}

    return templates.TemplateResponse("shows.html", {
        "request": request,
        "shows": shows,
        "theatres": theatres,
        "theatre_dict": theatre_dict,
        "selected_theatre": theatre_id,
        "days_ahead": days_ahead_int
    })


# Scheduled Scraping Management
@router.get("/schedules")
async def scheduled_scraping_management(
    request: Request,
    theatre_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Manage scheduled scraping for theatres."""
    query = db.query(ScheduledScrape)

    if theatre_id:
        query = query.filter(ScheduledScrape.theatre_id == theatre_id)

    schedules = query.all()
    theatres = db.query(Theatre).all()
    theatre_dict = {t.id: t for t in theatres}

    # Convert UTC times to EST for display
    for schedule in schedules:
        if schedule.last_run:
            schedule.last_run_est = utc_to_est(schedule.last_run)
        if schedule.next_run:
            schedule.next_run_est = utc_to_est(schedule.next_run)

    # Get current system status
    redis_available = False
    try:
        import os
        redis_url = os.getenv('REDIS_URL', '')
        if redis_url and not redis_url.startswith('redis://username:password@hostname'):
            redis_available = True
    except:
        pass

    return templates.TemplateResponse("schedules.html", {
        "request": request,
        "schedules": schedules,
        "theatres": theatres,
        "theatre_dict": theatre_dict,
        "selected_theatre": theatre_id,
        "redis_available": redis_available
    })


@router.post("/schedules/create")
async def create_schedule(
    request: Request,
    theatre_id: str = Form(...),
    schedule_preset: str = Form("daily-2am"),
    custom_hour: int = Form(2),
    custom_minute: int = Form(0),
    day_of_week: int = Form(0),
    enabled: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Create a new scheduled scraping job."""
    # Check if schedule already exists
    existing = db.query(ScheduledScrape).filter(
        ScheduledScrape.theatre_id == theatre_id
    ).first()

    if existing:
        return RedirectResponse(
            url="/dashboard/schedules?message=Schedule+already+exists+for+this+theatre",
            status_code=303
        )

    # Convert preset to schedule_type and config
    schedule_type = "daily"
    schedule_config = {}

    # Preset mappings
    preset_map = {
        'custom': {'type': 'daily', 'config': {'hour': custom_hour, 'minute': custom_minute}},
        'daily-2am': {'type': 'daily', 'config': {'hour': 2, 'minute': 0}},
        'daily-6am': {'type': 'daily', 'config': {'hour': 6, 'minute': 0}},
        'daily-12pm': {'type': 'daily', 'config': {'hour': 12, 'minute': 0}},
        'daily-6pm': {'type': 'daily', 'config': {'hour': 18, 'minute': 0}},
        'daily-10pm': {'type': 'daily', 'config': {'hour': 22, 'minute': 0}},
        'weekly-mon-2am': {'type': 'weekly', 'config': {'hour': 2, 'minute': 0, 'day_of_week': 0}},
        'weekly-fri-6pm': {'type': 'weekly', 'config': {'hour': 18, 'minute': 0, 'day_of_week': 4}},
        'hourly': {'type': 'hourly', 'config': {'minute': custom_minute}},
        'every-4-hours': {'type': 'every-4-hours', 'config': {'hour': custom_hour, 'minute': custom_minute}},
        'every-12-hours': {'type': 'every-12-hours', 'config': {'hour': custom_hour, 'minute': custom_minute}},
    }

    if schedule_preset in preset_map:
        preset_config = preset_map[schedule_preset]
        schedule_type = preset_config['type']
        schedule_config = preset_config['config']
    else:
        # Fallback for unknown presets
        schedule_type = "daily"
        schedule_config = {'hour': custom_hour, 'minute': custom_minute}

    # Handle weekly presets with custom day selection
    if schedule_preset.startswith('weekly') and schedule_preset != 'weekly-mon-2am' and schedule_preset != 'weekly-fri-6pm':
        schedule_config['day_of_week'] = day_of_week

    # Convert EDT schedule config to UTC for storage
    schedule_config_utc = schedule_config.copy()
    if 'hour' in schedule_config_utc:
        # Convert EDT hour to UTC hour (EDT is UTC-4)
        edt_hour = schedule_config_utc['hour']
        utc_hour = (edt_hour + 4) % 24
        schedule_config_utc['hour'] = utc_hour
        logger.info(f"Converting EDT {edt_hour}:{schedule_config_utc.get('minute', 0):02d} to UTC {utc_hour}:{schedule_config_utc.get('minute', 0):02d} for schedule storage")

    schedule = ScheduledScrape(
        theatre_id=theatre_id,
        enabled=enabled,
        schedule_type=schedule_type,
        schedule_config=schedule_config_utc  # Store UTC config
    )

    # Calculate and set the next_run time immediately
    now = datetime.utcnow().replace(tzinfo=UTC)
    schedule.next_run = _calculate_next_run(schedule, now)

    db.add(schedule)
    db.commit()

    logger.info(f"Created scheduled scrape: theatre={theatre_id}, type={schedule_type}, config={schedule_config_utc}, next_run={schedule.next_run}, enabled={enabled}")

    return RedirectResponse(
        url="/dashboard/schedules?message=Schedule+created+successfully",
        status_code=303
    )


@router.post("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Enable/disable a scheduled scraping job."""
    schedule = db.query(ScheduledScrape).filter(ScheduledScrape.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.enabled = not schedule.enabled
    db.commit()

    status = "enabled" if schedule.enabled else "disabled"
    logger.info(f"Toggled scheduled scrape {schedule_id}: theatre={schedule.theatre_id}, now {status}")

    return RedirectResponse(
        url=f"/dashboard/schedules?message=Schedule+{status}",
        status_code=303
    )


@router.post("/schedules/{schedule_id}/delete")
async def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a scheduled scraping job."""
    schedule = db.query(ScheduledScrape).filter(ScheduledScrape.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    logger.info(f"Deleted scheduled scrape {schedule_id}: theatre={schedule.theatre_id}")

    db.delete(schedule)
    db.commit()

    return RedirectResponse(
        url="/dashboard/schedules?message=Schedule+deleted+successfully",
        status_code=303
    )


@router.post("/schedules/run-all")
async def run_all_scheduled_scrapes(db: Session = Depends(get_db)):
    """Manually trigger all enabled scheduled scrapes."""
    schedules = db.query(ScheduledScrape).filter(ScheduledScrape.enabled == True).all()

    triggered_count = 0
    for schedule in schedules:
        try:
            # Use async Celery task if Redis is available, otherwise synchronous
            import os
            redis_url = os.getenv('REDIS_URL', '')

            if redis_url and not redis_url.startswith('redis://username:password@hostname'):
                # Use async Celery task - manual trigger so force_scrape=True
                from .tasks.scraping import scrape_single_theatre
                task = scrape_single_theatre.delay(schedule.theatre.id, force_scrape=True)
                print(f"✅ Scheduled scrape queued for {schedule.theatre.name} (task: {task.id})")
                triggered_count += 1
            else:
                # Fallback to synchronous scraping
                from .scrapers.theatre_scraper import TheatreScraper
                from .parsers.openai_parser import OpenAIParser

                firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
                if firecrawl_key:
                    scraper = TheatreScraper(firecrawl_api_key=firecrawl_key)
                    parser = OpenAIParser()

                    result = scraper.scrape_with_config(schedule.theatre, schedule.theatre.config_data or {})
                    if result:
                        print(f"✅ Scheduled scrape completed for {schedule.theatre.name}")
                        triggered_count += 1
        except Exception as e:
            print(f"❌ Error in scheduled scrape for {schedule.theatre.name}: {e}")

    return RedirectResponse(
        url=f"/dashboard/schedules?message=Triggered+{triggered_count}+scheduled+scrapes",
        status_code=303
    )


# API endpoints for scrape log data
@router.get("/api/scrape-logs/{log_id}/raw-markdown")
async def get_raw_markdown(log_id: int, db: Session = Depends(get_db)):
    """Get raw markdown content for a scrape log."""
    log = db.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Scrape log not found")

    return {"raw_markdown": log.raw_markdown}


@router.get("/api/scrape-logs/{log_id}/openai-response")
async def get_openai_response(log_id: int, db: Session = Depends(get_db)):
    """Get OpenAI JSON response for a scrape log."""
    log = db.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Scrape log not found")

    return {"parsed_json": log.parsed_json}


@router.get("/api/scrape-logs/{log_id}/openai-prompt")
async def get_openai_prompt(log_id: int, db: Session = Depends(get_db)):
    """Get OpenAI prompt used for a scrape log."""
    log = db.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Scrape log not found")

    return {"openai_prompt": log.openai_prompt}


# Scraping History
@router.get("/scraping")
async def scraping_history(
    request: Request,
    theatre_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """View scraping history and logs."""
    query = db.query(ScrapeLog)

    if theatre_id:
        query = query.filter(ScrapeLog.theatre_id == theatre_id)

    if status_filter:
        query = query.filter(ScrapeLog.status == status_filter)

    logs = query.order_by(ScrapeLog.started_at.desc()).limit(100).all()

    # Get theatre info
    theatres = db.query(Theatre).all()
    theatre_dict = {t.id: t for t in theatres}

    # Convert UTC times to EST for display
    for log in logs:
        if log.started_at:
            log.started_at_est = utc_to_est(log.started_at)
        if log.completed_at:
            log.completed_at_est = utc_to_est(log.completed_at)

    # Status summary
    status_counts = {}
    for log in logs:
        status_counts[log.status] = status_counts.get(log.status, 0) + 1

    return templates.TemplateResponse("scraping.html", {
        "request": request,
        "logs": logs,
        "theatres": theatres,
        "theatre_dict": theatre_dict,
        "selected_theatre": theatre_id,
        "status_filter": status_filter,
        "status_counts": status_counts
    })


# System Health
@router.get("/health")
async def system_health(request: Request, db: Session = Depends(get_db)):
    """System health and diagnostics page."""
    # Database health
    try:
        db.execute("SELECT 1")
        db_health = "✅ Healthy"
    except Exception as e:
        db_health = f"❌ Error: {e}"

    # Recent activity
    recent_logs = db.query(ScrapeLog).order_by(
        ScrapeLog.started_at.desc()
    ).limit(10).all()

    # Convert UTC times to EST for display
    for log in recent_logs:
        if log.started_at:
            log.started_at_est = utc_to_est(log.started_at)

    # Show statistics
    total_shows = db.query(Show).count()
    shows_with_images = db.query(Show).filter(
        Show.image_url.isnot(None)
    ).count()

    # Theatre statistics
    theatre_stats = []
    theatres = db.query(Theatre).all()
    for theatre in theatres:
        show_count = db.query(Show).filter(Show.theatre_id == theatre.id).count()

        # Get last scrape time for theatre
        recent_log = db.query(ScrapeLog).filter(
            ScrapeLog.theatre_id == theatre.id
        ).order_by(ScrapeLog.started_at.desc()).first()

        theatre_stats.append({
            "theatre": theatre,
            "show_count": show_count,
            "last_scrape_est": utc_to_est(recent_log.started_at) if recent_log else None
        })

    return templates.TemplateResponse("health.html", {
        "request": request,
        "db_health": db_health,
        "recent_logs": recent_logs,
        "total_shows": total_shows,
        "shows_with_images": shows_with_images,
        "theatre_stats": theatre_stats
    })


# API Documentation
@router.get("/api-docs")
async def api_docs(request: Request):
    """API documentation and testing page."""
    return templates.TemplateResponse("api_docs.html", {
        "request": request
    })
