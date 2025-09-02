# CurtainTime Backend

Backend API service for theatre show scraping and management. Built with FastAPI, SQLAlchemy, and Celery.

## 🚀 Features

- **REST API**: FastAPI-based endpoints for theatre and show data
- **Background Tasks**: Celery-powered scraping with Redis
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Parsing**: Gemini AI for markdown-to-structured-data conversion
- **Image Storage**: Vercel Blob for optimized image hosting
- **Migration Path**: Seamless integration with existing theatre scraper

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL database (Railway, Neon, or local)
- Redis instance (Railway or other provider)
- Firecrawl API key
- Gemini API key (optional, for AI parsing)

## 🛠️ Installation

1. **Clone and setup**:
   ```bash
   cd curtaintime-backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment setup**:
   ```bash
   cp env_template.txt .env
   # Edit .env with your actual credentials
   ```

3. **Database initialization**:
   ```bash
   python scripts/init_db.py
   ```

## 🔧 Configuration

Edit your `.env` file with:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://user:pass@host:6379
FIRECRAWL_API_KEY=fc-your-key-here
GEMINI_API_KEY=your-gemini-key-here
BLOB_READ_WRITE_TOKEN=vercel_blob_token
```

## 🚀 Running the Application

### Development Server
```bash
# Start FastAPI server
python -m app.api.main

# Server will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Background Workers
```bash
# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat scheduler
celery -A app.celery_app beat --loglevel=info
```

### Production Deployment
```bash
# Using Railway (recommended)
railway login
railway link
railway up
```

## 📚 API Endpoints

### Public Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /theatres` - List all theatres
- `GET /shows` - List upcoming shows
- `GET /theatres/{id}/shows` - Shows for specific theatre

### Admin Endpoints
- `POST /admin/scrape/{theatre_id}` - Trigger manual scrape
- `POST /admin/scrape-all` - Trigger full scrape cycle
- `GET /admin/tasks/{task_id}` - Check task status

## 🏗️ Project Structure

```
curtaintime-backend/
├── app/
│   ├── api/           # FastAPI endpoints
│   ├── models/        # Database models
│   ├── scrapers/      # Scraping services
│   ├── parsers/       # AI parsing services
│   ├── services/      # External services (Blob, etc.)
│   └── tasks/         # Celery background tasks
├── configs/           # Theatre configurations
├── scripts/           # Database setup scripts
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## 🔄 Migration from Existing Scraper

This backend is designed to work alongside your existing `theatre_scraper` system:

1. **Keep existing scraper running** during transition
2. **Database imports your existing configs** automatically
3. **Gradual migration** - move one theatre at a time
4. **Hybrid operation** possible during transition

## 🎯 Next Steps

1. **Set up infrastructure** (Railway/Neon + Redis)
2. **Configure environment variables**
3. **Run database initialization**
4. **Test API endpoints**
5. **Implement scraping tasks** (next phase)
6. **Add AI parsing** (next phase)
7. **Migrate production data**

## 📝 Development Notes

- Uses SQLAlchemy 2.0 with modern patterns
- Pydantic models for API serialization
- Comprehensive logging and error handling
- Designed for horizontal scaling
- Ready for production deployment

## 🔧 Troubleshooting

**Database connection issues**:
- Verify DATABASE_URL format
- Check PostgreSQL credentials
- Ensure database exists

**Redis connection issues**:
- Verify REDIS_URL format
- Check Redis server status
- Confirm network connectivity

**API key issues**:
- Firecrawl: Check account and billing
- Gemini: Verify API key permissions

---

🎭 **Ready to transform your theatre scraping into a production-ready backend!**
