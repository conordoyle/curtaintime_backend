"""
Database models and connection setup for CurtainTime backend.
Uses SQLAlchemy ORM with PostgreSQL.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
import os
from typing import Generator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine with connection resilience settings
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,          # Test connections before use
    pool_recycle=3600,           # Recycle connections every hour
    pool_timeout=20,             # Timeout for getting connection from pool
    max_overflow=20              # Allow extra connections if needed
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


class Theatre(Base):
    """Theatre venue model."""
    __tablename__ = "theatres"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    config_data = Column(JSON, nullable=True)  # Store original config as JSON
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    shows = relationship("Show", back_populates="theatre")
    scrape_logs = relationship("ScrapeLog", back_populates="theatre")
    scheduled_scrapes = relationship("ScheduledScrape", back_populates="theatre")

    def __repr__(self):
        return f"<Theatre(id='{self.id}', name='{self.name}')>"


class Show(Base):
    """Individual show/performance model."""
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, index=True)
    theatre_id = Column(String, ForeignKey("theatres.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    start_datetime_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    ticket_url = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)  # Store original parsed data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    theatre = relationship("Theatre", back_populates="shows")

    def __repr__(self):
        return f"<Show(id={self.id}, title='{self.title}', theatre='{self.theatre_id}')>"


class ScrapeLog(Base):
    """Log of scraping operations for monitoring and debugging."""
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, index=True)
    theatre_id = Column(String, ForeignKey("theatres.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="running")  # running, success, error, partial_success
    shows_found = Column(Integer, default=0)
    shows_added = Column(Integer, default=0)
    shows_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    raw_markdown = Column(Text, nullable=True)  # Store the raw markdown content
    openai_prompt = Column(Text, nullable=True)  # Store the OpenAI prompt used
    parsed_json = Column(JSON, nullable=True)  # Store the OpenAI JSON response
    scrape_metadata = Column(JSON, nullable=True)  # Store additional metadata

    # Change tracking fields
    change_status = Column(String, nullable=True)  # new, same, changed, removed
    previous_scrape_at = Column(DateTime(timezone=True), nullable=True)
    page_visibility = Column(String, nullable=True)  # visible, hidden
    change_metadata = Column(JSON, nullable=True)  # Store change tracking details

    # Relationships
    theatre = relationship("Theatre", back_populates="scrape_logs")

    def __repr__(self):
        return f"<ScrapeLog(id={self.id}, theatre='{self.theatre_id}', status='{self.status}')>"


class ScheduledScrape(Base):
    """Scheduled scraping configurations for theatres."""
    __tablename__ = "scheduled_scrapes"

    id = Column(Integer, primary_key=True, index=True)
    theatre_id = Column(String, ForeignKey("theatres.id"), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    schedule_type = Column(String, nullable=False, default="daily")  # daily, weekly, custom
    schedule_config = Column(JSON, nullable=True)  # Store schedule details (hour, minute, days, etc.)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    theatre = relationship("Theatre", back_populates="scheduled_scrapes")

    def __repr__(self):
        return f"<ScheduledScrape(id={self.id}, theatre='{self.theatre_id}', enabled={self.enabled})>"


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def drop_db():
    """Drop all database tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped successfully!")


def reset_db():
    """Reset the database by dropping and recreating all tables."""
    drop_db()
    init_db()


# Initialize database on import if running as main
if __name__ == "__main__":
    init_db()
