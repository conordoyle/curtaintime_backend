# CurtainTime Deployment Architecture

## 🎯 **Overview: Vercel Storefront + Railway Warehouse**

This document outlines the **best-practice deployment architecture** for CurtainTime, utilizing Vercel for the web interface and Railway for background processing.

## 🏗️ **Architecture Components**

### **Vercel (Frontend Storefront)**
- **Purpose**: Hosts the FastAPI web application and dashboard
- **Technology**: Serverless Python functions
- **Strengths**: Global CDN, instant scaling, excellent for web apps
- **Cost**: Generous free tier, pay-as-you-go scaling

### **Railway (Backend Warehouse)**
- **Purpose**: Runs Celery workers, scheduler, and Redis
- **Technology**: Persistent containers with 24/7 uptime
- **Strengths**: Perfect for background jobs, scheduled tasks
- **Cost**: Pay for uptime, ideal for continuous processes

### **Supporting Services**
- **Neon**: PostgreSQL database (already configured)
- **Redis**: Message broker (hosted on Railway)

## 📋 **Current Setup (Local Development)**

### **Local Environment**
```bash
# Web App (FastAPI)
./curtaintime-backend/run_local_server.sh

# Background Workers (when needed)
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info
```

## 🚀 **Production Deployment Plan**

### **Phase 1: Railway Backend (Current Focus)**

**Files to Create:**
```
curtaintime-backend/
├── Procfile                    # Railway deployment config
├── requirements.txt           # Python dependencies
└── .env.example              # Environment variable template
```

**Procfile Content:**
```procfile
worker: celery -A app.celery_app worker --loglevel=info --concurrency=2
beat: celery -A app.celery_app beat --loglevel=info
```

**Environment Variables (Railway):**
```bash
DATABASE_URL=postgresql://...  # From Neon
REDIS_URL=redis://...          # From Railway Redis
GEMINI_API_KEY=...            # For AI parsing
FIRECRAWL_API_KEY=...         # For web scraping
```

### **Phase 2: Vercel Frontend (Future)**

**Files to Create:**
```
curtaintime-backend/
├── vercel.json               # Vercel deployment config
└── api/
    └── main.py              # FastAPI app entry point
```

**vercel.json Content:**
```json
{
  "builds": [
    {
      "src": "app/api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/api/main.py"
    }
  ]
}
```

**Environment Variables (Vercel):**
```bash
DATABASE_URL=postgresql://...  # From Neon
REDIS_URL=redis://...          # From Railway
VERCEL_URL=https://your-app.vercel.app  # Auto-provided
```

## 🔧 **Setup Instructions**

### **Step 1: Git Repository Setup**

```bash
# Navigate to backend directory
cd /Users/Conor/MerrimackLocal/CurtainTime!/curtaintime-backend

# Initialize new git repo
git init

# Create .gitignore
echo "*.env" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: CurtainTime backend with scheduling"
```

### **Step 2: Railway Deployment**

```bash
# Create Railway project
railway login
railway init curtaintime-backend

# Connect to existing git repo
railway link

# Set environment variables
railway variables set DATABASE_URL="your_neon_connection_string"
railway variables set REDIS_URL="your_redis_connection_string"
railway variables set GEMINI_API_KEY="your_gemini_key"
railway variables set FIRECRAWL_API_KEY="your_firecrawl_key"

# Deploy
railway up
```

### **Step 3: Local Development**

```bash
# Run web app locally
./run_local_server.sh

# Monitor Railway logs
railway logs

# Check Railway services
railway status
```

## 📊 **Data Flow**

```
User Request → Vercel (FastAPI) → Railway (Celery Worker) → Neon DB
                    ↓
             Dashboard UI ← Railway (Results) ← Firecrawl (Scraped Data)
```

## 🔒 **Security Considerations**

### **Environment Variables**
- ✅ `DATABASE_URL`: Neon PostgreSQL connection
- ✅ `REDIS_URL`: Railway Redis instance
- ✅ `GEMINI_API_KEY`: Google AI API key
- ✅ `FIRECRAWL_API_KEY`: Firecrawl scraping service

### **CORS Configuration**
```python
# In app/api/main.py
origins = [
    "http://localhost:8000",           # Local development
    "https://your-app.vercel.app",     # Vercel production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📈 **Scaling Strategy**

### **Vercel Scaling**
- **Automatic**: Serverless functions scale to zero/demand
- **Global**: CDN ensures fast response times worldwide
- **Cost**: Pay only for actual usage

### **Railway Scaling**
- **Manual**: Adjust worker concurrency in Procfile
- **Persistent**: 24/7 uptime for scheduled tasks
- **Cost**: Predictable based on resource allocation

## 🎯 **Migration Path**

### **Phase 1 (Current): Railway Only**
- ✅ Deploy Celery workers and scheduler to Railway
- ✅ Keep web app local for development
- ✅ Test automated scraping and scheduling

### **Phase 2 (Future): Add Vercel**
- ✅ Deploy FastAPI to Vercel serverless
- ✅ Update CORS to allow Vercel domain
- ✅ Shut down local web server

## 🔍 **Monitoring & Troubleshooting**

### **Railway Monitoring**
```bash
# View logs
railway logs

# Check service status
railway status

# View environment
railway variables
```

### **Local Monitoring**
```bash
# Web app logs (in terminal where you run the server)
# Celery logs (in separate terminals when running locally)
```

## 💡 **Best Practices**

1. **Environment Separation**: Never commit `.env` files
2. **Service Isolation**: Keep web and worker concerns separate
3. **Cost Optimization**: Use free tiers where possible
4. **Monitoring**: Set up alerts for Railway service health
5. **Backup Strategy**: Regular Neon database backups

## 📚 **Resources**

- [Railway Documentation](https://docs.railway.app/)
- [Vercel Python Guide](https://vercel.com/docs/concepts/functions/serverless-functions/python)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/optimizing.html)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

**Status**: Ready for Phase 1 deployment to Railway 🚀
