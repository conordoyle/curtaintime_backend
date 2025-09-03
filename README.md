# CurtainTime Backend

**Complete theatre show scraping and management platform** with automated scheduling, AI-powered parsing, and production-ready architecture. Built for scale with Vercel + Railway + Neon + Redis.

## 🎭 **Project Overview**

CurtainTime is a sophisticated theatre scraping platform that:

- **Automatically scrapes** theatre websites for show listings
- **Uses AI (Gemini)** to parse markdown into structured show data
- **Provides web dashboard** for management and monitoring
- **Handles scheduling** with intelligent change tracking
- **Manages images** with optimization and blob storage
- **Runs 24/7** with automated background processing

### 🏗️ **Architecture**

**Frontend (Vercel - Future):**
- FastAPI web application served via Vercel serverless
- User dashboard for theatre and schedule management
- Real-time monitoring and analytics

**Backend Processing (Railway):**
- Celery workers for scraping tasks
- Celery Beat for scheduled execution (every 30 minutes)
- Intelligent change tracking to avoid unnecessary scrapes
- Context-aware scraping (manual vs scheduled behavior)

**Data Layer:**
- **Neon PostgreSQL**: Main database for shows, theatres, schedules
- **Railway Redis**: Message broker and task queue
- **Vercel Blob**: Optimized image storage and CDN

**External Services:**
- **Firecrawl**: Website scraping with JavaScript rendering
- **Google Gemini AI**: Markdown-to-structured-data parsing
- **Railway**: Hosting for background workers
- **Neon**: Serverless PostgreSQL database

## 🚀 Features

### **Core Functionality**
- **REST API**: FastAPI-based endpoints for theatre and show data
- **Background Tasks**: Celery-powered scraping with Redis message broker
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM and connection pooling
- **AI Parsing**: Google Gemini 2.5-pro for intelligent markdown-to-structured-data conversion
- **Image Management**: Vercel Blob storage with automatic optimization and fallbacks
- **Migration Path**: Seamless integration with existing theatre scraper

### **Advanced Scheduling System**
- **Intelligent Scheduling**: Database-driven schedules with multiple preset options
- **Change Tracking**: Firecrawl-powered content change detection
- **Context-Aware Scraping**: Manual vs scheduled scraping behavior
- **Timezone Support**: Full UTC storage with EST display (DST-aware)
- **Flexible Intervals**: Daily, weekly, hourly, and custom intervals
- **Smart Optimization**: Only scrapes when content actually changes

### **Production-Ready Architecture**
- **Microservices Design**: Separated web app and background workers
- **Scalable Deployment**: Vercel + Railway + Neon + Redis stack
- **Error Handling**: Comprehensive logging and graceful failure recovery
- **Connection Resilience**: Database connection pooling with pre-ping
- **Monitoring**: Real-time health checks and performance metrics
- **Security**: Environment variable management and API key protection

### **User Interface**
- **Modern Dashboard**: Bootstrap 5 with responsive design
- **Advanced Scheduling**: Intuitive time picker with preset options
- **Real-time Monitoring**: Live scraping status and history
- **Theatre Management**: Complete CRUD operations for venues
- **Analytics**: Show counts, success rates, and performance metrics
- **Health Monitoring**: System diagnostics and error tracking

## 📋 Prerequisites

### **Required Services**
- **Python 3.8+**: Backend runtime
- **PostgreSQL Database**: Neon (recommended) or Railway PostgreSQL
- **Redis Instance**: Railway Redis (recommended) or any Redis provider
- **Railway Account**: For hosting background workers
- **Vercel Account**: For future web app deployment (optional)

### **Required API Keys**
- **Firecrawl API Key**: For website scraping (`FIRECRAWL_API_KEY`)
- **Gemini API Key**: For AI parsing (`GEMINI_API_KEY`)
- **Vercel Blob Token**: For image storage (`BLOB_READ_WRITE_TOKEN`)

### **Infrastructure Setup**
- **Railway Project**: With Redis and Celery workers
- **Neon Database**: Serverless PostgreSQL
- **Git Repository**: For deployment tracking

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

### **Environment Variables**

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://neondb_owner:your_password@ep-patient-scene-adux8bmy-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# Redis Configuration (Railway)
REDIS_URL=redis://default:your_password@centerbeam.proxy.rlwy.net:28715

# API Keys
FIRECRAWL_API_KEY=fc-your-firecrawl-key-here
GEMINI_API_KEY=AIzaSyB-your-gemini-key-here
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_your_token_here

# Optional: Railway-specific (auto-provided)
RAILWAY_ENVIRONMENT=production
RAILWAY_PROJECT_ID=your-project-id
RAILWAY_SERVICE_ID=your-service-id
```

### **Railway Environment Setup**

For Railway deployment, set these variables in your Railway dashboard:

```bash
# Railway Variables (set via dashboard)
DATABASE_URL=postgresql://...  # From Neon
REDIS_URL=redis://...          # From Railway Redis
FIRECRAWL_API_KEY=fc-...
GEMINI_API_KEY=AIzaSyB...
BLOB_READ_WRITE_TOKEN=vercel_blob_...
```

### **Database Schema**

The system uses these main database tables:
- **theatres**: Theatre venue information and scraping configurations
- **shows**: Individual show listings with metadata
- **scrape_logs**: Scraping operation history and results
- **scheduled_scrapes**: Automated scheduling configurations

### **Scraping Configuration**

Theatres are configured via JSON files in the `configs/` directory:

```json
{
  "theatre_id": "palace_theatre",
  "theatre_name": "Palace Theatre",
  "base_url": "https://palacetheatre.org/calendar-search/",
  "scraping_strategy": {
    "type": "single_url_with_actions",
    "url": "https://palacetheatre.org/calendar-search/",
    "actions": [
      {"type": "wait", "milliseconds": 3000},
      {"type": "click", "selector": "#loadMoreEvents"},
      {"type": "wait", "milliseconds": 2000}
    ]
  },
  "scrape_params": {
    "formats": ["markdown"],
    "onlyMainContent": true,
    "timeout": 30000
  }
}
```

## 🚀 Running the Application

### **Local Development Setup**

#### **1. Start Web Dashboard (Optional)**
```bash
# Quick start script (recommended)
./run_local_server.sh

# Or manually:
# python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard: http://127.0.0.1:8000/dashboard
# API Docs: http://127.0.0.1:8000/docs
```

#### **2. Background Workers (Railway Recommended)**
```bash
# Railway handles this automatically in production
# For local testing only:
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

### **Production Deployment**

#### **Current Setup: Railway Workers Only**
```bash
# Deploy background workers to Railway
cd curtaintime-backend
railway login
railway link  # Connect to existing project
railway up    # Deploy workers and scheduler
```

#### **Future Setup: Vercel + Railway**
```bash
# 1. Deploy web app to Vercel
# 2. Workers remain on Railway
# 3. Update CORS in Vercel for Railway workers
```

### **Architecture Overview**

```
Local Development:
┌─────────────────┐    ┌─────────────────┐
│   FastAPI Web   │    │  Celery Worker  │
│   Dashboard     │◄──►│  (Railway)      │
│                 │    │                 │
│ http://localhost│    │ Scheduled Tasks │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┼───────────────────────► Neon DB
                                 │
                    ┌─────────────────┐
                    │   Railway Redis │
                    │  Message Queue  │
                    └─────────────────┘
```

### **Key Behaviors**

#### **Manual Scraping** (via dashboard)
- Bypasses change tracking for immediate results
- Forces fresh scrape regardless of content changes
- Useful for debugging or urgent updates

#### **Scheduled Scraping** (automated)
- Runs every 30 minutes via Celery Beat
- Uses change tracking to avoid unnecessary work
- Only scrapes when content has actually changed
- Efficient and resource-conscious

## 📚 API Endpoints

### **Public Endpoints**
- `GET /` - API information and status
- `GET /health` - Comprehensive health check
- `GET /theatres` - List all enabled theatres
- `GET /theatres/{id}` - Get specific theatre details
- `GET /shows` - List upcoming shows with filtering
- `GET /theatres/{id}/shows` - Shows for specific theatre

### **Dashboard Endpoints** (Web Interface)
- `GET /dashboard/` - Main dashboard overview
- `GET /dashboard/theatres` - Theatre management interface
- `GET /dashboard/shows` - Show listings and filtering
- `GET /dashboard/schedules` - Schedule management (NEW!)
- `GET /dashboard/scraping` - Scraping history and logs
- `GET /dashboard/health` - System health monitoring

### **Schedule Management** (NEW!)
- `GET /dashboard/schedules` - View all schedules
- `POST /dashboard/schedules/create` - Create new schedule
- `POST /dashboard/schedules/{id}/toggle` - Enable/disable schedule
- `POST /dashboard/schedules/{id}/delete` - Delete schedule
- `POST /dashboard/schedules/run-all` - Manual trigger all schedules

### **Admin Endpoints**
- `POST /admin/scrape/{theatre_id}` - Manual theatre scrape (force_scrape=True)
- `POST /admin/scrape-all` - Full scrape cycle (force_scrape=True)
- `GET /admin/tasks/{task_id}` - Task status monitoring

### **Background Tasks** (Celery)
- `scrape_single_theatre` - Individual theatre scraping
- `scrape_all_theatres` - Bulk theatre scraping
- `dispatch_scheduled_scrapes` - Schedule dispatcher (runs every 30 min)
- `parse_theatre_shows` - AI parsing of scraped content
- `process_show_image` - Image optimization and storage

## 🏗️ Project Structure

```
curtaintime-backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI app with timezone utilities
│   ├── celery_app.py            # Celery configuration with Beat scheduler
│   ├── dashboard_routes.py      # Web dashboard with schedule management
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py          # SQLAlchemy models with connection pooling
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── gemini_parser.py     # AI-powered markdown parsing
│   ├── scrapers/
│   │   ├── __init__.py
│   │   └── theatre_scraper.py   # Firecrawl integration with change tracking
│   ├── services/
│   │   ├── __init__.py
│   │   └── vercel_blob.py       # Image storage and optimization
│   └── tasks/
│       ├── __init__.py
│       ├── images.py            # Image processing tasks
│       ├── parsing.py           # AI parsing tasks with replacement logic
│       └── scheduling.py        # Schedule dispatcher (NEW!)
├── configs/                     # Theatre scraping configurations
├── scripts/                     # Database setup and migration scripts
├── templates/                   # Jinja2 HTML templates
├── DEPLOYMENT_ARCHITECTURE.md   # Architecture documentation
├── Procfile                     # Railway deployment configuration
├── requirements.txt             # Python dependencies with all services
├── run_local_server.sh         # Local development startup script
└── README.md                    # This comprehensive documentation
```

### **Key Files Overview**

| File | Purpose | Key Features |
|------|---------|--------------|
| `app/celery_app.py` | Celery configuration | Beat scheduler, Redis broker |
| `app/tasks/scheduling.py` | Schedule dispatcher | Runs every 30 min, handles due schedules |
| `app/dashboard_routes.py` | Web interface | Schedule management, timezone conversion |
| `Procfile` | Railway deployment | Worker and beat process definitions |
| `run_local_server.sh` | Local development | Quick startup for dashboard |

### **Database Tables**

- **`theatres`**: Venue info, scraping configs, enable/disable status
- **`shows`**: Individual performances with metadata and image URLs
- **`scrape_logs`**: Operation history, success/failure tracking
- **`scheduled_scrapes`**: Automated schedules with flexible intervals

## 🔄 Migration from Existing Scraper

This backend is designed to work alongside your existing `theatre_scraper` system:

1. **Keep existing scraper running** during transition
2. **Database imports your existing configs** automatically
3. **Gradual migration** - move one theatre at a time
4. **Hybrid operation** possible during transition

## 🎯 Advanced Features Implemented

### **Intelligent Scheduling System**

- **Database-Driven Schedules**: All schedules stored in PostgreSQL for reliability
- **Flexible Intervals**: Daily, weekly, hourly, custom intervals with time pickers
- **Preset Options**: Quick setup with "Daily at 2AM", "Weekly (Monday)", etc.
- **Context-Aware Scraping**: Manual vs scheduled behavior differences
- **Real-time Management**: Enable/disable/toggle schedules via dashboard

### **Smart Change Tracking**

- **Firecrawl Integration**: Detects when theatre websites actually change
- **Efficiency Optimization**: Only scrapes when content has changed
- **Manual Override**: Force fresh scrapes when needed (debugging, urgent updates)
- **Automatic Skip**: Saves API costs and processing time

### **Timezone Intelligence**

- **UTC Storage**: Database stores times in UTC for consistency
- **EST Display**: User interface shows times in Eastern Time
- **DST Handling**: Automatically adjusts for Daylight Saving Time
- **Global Ready**: Easy to adapt to other timezones

### **Production-Grade Architecture**

- **Microservices**: Separated web app and background workers
- **Connection Resilience**: Database pooling with pre-ping to handle Neon disconnections
- **Scalable Deployment**: Vercel + Railway + Neon + Redis stack
- **Error Recovery**: Comprehensive logging and graceful failure handling
- **Resource Optimization**: Smart caching and efficient processing

### **Advanced Scraping Features**

- **AI-Powered Parsing**: Google Gemini extracts structured data from markdown
- **Image Optimization**: Automatic processing and Vercel Blob storage
- **Retry Logic**: Automatic retry on failures with exponential backoff
- **Comprehensive Logging**: Detailed operation tracking and debugging

## 🚀 Current Status & Next Steps

### **✅ Completed Features**
- ✅ Railway deployment with Celery workers and beat scheduler
- ✅ Comprehensive scheduling system with presets and custom times
- ✅ Change tracking with manual override capability
- ✅ Timezone conversion (UTC storage, EST display)
- ✅ Database connection resilience with pre-ping
- ✅ Advanced web dashboard with schedule management
- ✅ AI parsing with Gemini integration
- ✅ Image processing and optimization pipeline

### **🎯 Ready for Use**
1. **Railway Workers**: Deployed and running scheduled scrapes
2. **Local Dashboard**: Complete management interface
3. **Database**: Fully configured with all tables
4. **API**: Complete REST endpoints for all operations

### **🔮 Future Enhancements**
1. **Vercel Deployment**: Web app serverless deployment
2. **Advanced Analytics**: Performance metrics and insights
3. **Multi-Region**: Geographic distribution
4. **Alerting**: Email notifications for failures
5. **API Rate Limiting**: Request throttling and management

## 📝 Development Notes

### **Architecture Decisions**
- **SQLAlchemy 2.0**: Modern ORM with async support and improved performance
- **Pydantic V2**: FastAPI-compatible data validation and serialization
- **Celery**: Distributed task queue for background processing
- **Jinja2**: Server-side HTML templating for dashboard
- **Bootstrap 5**: Responsive UI framework

### **Design Patterns**
- **Repository Pattern**: Clean data access layer
- **Service Layer**: Business logic separation
- **Task-Based Architecture**: Async processing for scalability
- **Configuration-Driven**: Flexible theatre scraping configs
- **Microservices**: Separated concerns for maintainability

### **Performance Optimizations**
- **Connection Pooling**: Database connection reuse with pre-ping
- **Change Tracking**: Avoid unnecessary API calls
- **Image Optimization**: Resize and compress for web delivery
- **Caching**: Redis-based task result caching
- **Async Processing**: Non-blocking background operations

## 🔧 Troubleshooting

### **Database Issues**
```bash
# Test database connection
python -c "from app.models.database import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('✅ DB OK')"

# Reset database (CAUTION: destroys data)
python scripts/reset_database.py
```

### **Redis/Celery Issues**
```bash
# Check Redis connectivity
redis-cli -u $REDIS_URL ping

# Test Celery worker
celery -A app.celery_app inspect active

# View Celery logs
railway logs
```

### **API Key Issues**
```bash
# Test Firecrawl
curl -H "Authorization: Bearer $FIRECRAWL_API_KEY" https://api.firecrawl.com/v0/scrape

# Test Gemini
python -c "import google.generativeai as genai; genai.configure(api_key='$GEMINI_API_KEY'); print('✅ Gemini OK')"
```

### **Deployment Issues**
```bash
# Railway deployment logs
railway logs

# Check Railway service status
railway status

# Redeploy if needed
railway up
```

### **Common Errors**

#### **"SSL connection has been closed unexpectedly"**
- **Cause**: Neon connection timeout
- **Fix**: Already handled by `pool_pre_ping=True`
- **Prevention**: Keep Railway workers active

#### **"Change tracking failed"**
- **Cause**: Firecrawl temporary issue
- **Fix**: Automatic retry logic in place
- **Prevention**: Monitor Firecrawl API status

#### **"Schedule not running"**
- **Cause**: Celery Beat not started
- **Fix**: Check Railway Procfile and redeploy
- **Prevention**: Verify Beat process in Railway logs

### **Monitoring Commands**

```bash
# View all logs
railway logs

# Check specific services
railway logs --service zesty-consideration  # Worker
railway logs --service <redis-service>      # Redis

# Monitor task queue
celery -A app.celery_app inspect active
celery -A app.celery_app inspect scheduled
```

### **Performance Tuning**

- **Worker Concurrency**: Adjust in `Procfile` based on load
- **Database Pool Size**: Configure in `database.py` engine settings
- **Redis Memory**: Monitor usage in Railway dashboard
- **API Rate Limits**: Check Firecrawl and Gemini quotas

## 📚 Resources for Future Development

### **Key Documentation**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery User Guide](https://docs.celeryproject.org/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Railway Docs](https://docs.railway.app/)
- [Firecrawl API](https://docs.firecrawl.com/)

### **Architecture References**
- **Microservices**: Separated web/worker concerns
- **Event-Driven**: Celery task queue pattern
- **Database-First**: Schema-driven development
- **Configuration Management**: Environment-based settings
- **Observability**: Comprehensive logging and monitoring

### **Scalability Considerations**
- **Horizontal Scaling**: Add more Railway workers as needed
- **Database Sharding**: Split data across multiple Neon instances
- **CDN Integration**: Vercel for global content delivery
- **Rate Limiting**: API throttling for external services
- **Caching Strategy**: Redis for frequently accessed data

---

## 🎭 **Complete Theatre Scraping Platform**

This is a **production-ready, enterprise-grade theatre scraping system** with:

- ✅ **Automated Scheduling**: Database-driven with flexible intervals
- ✅ **Intelligent Optimization**: Change tracking and smart retries
- ✅ **AI-Powered Parsing**: Google Gemini for data extraction
- ✅ **Production Architecture**: Microservices with Railway + Vercel
- ✅ **Comprehensive Monitoring**: Real-time health and performance
- ✅ **Timezone Intelligence**: UTC storage, EST display with DST
- ✅ **Scalable Design**: Ready for hundreds of theatres

**Perfect for future AI chats and development reference!** 🚀✨

---

*Built with ❤️ for automated theatre data collection*
