# Firecrawl Change Tracking Integration

## Overview

This feature optimizes your scraping system by using Firecrawl's Change Tracking API to detect when theatre websites haven't changed since the last scrape. When no changes are detected, it skips expensive operations like full scraping and LLM processing.

## How It Works

### Before (Traditional Flow):
1. User requests scrape → Full scrape → LLM parsing → Database update
2. **Cost**: Firecrawl scrape + Gemini API call every time
3. **Time**: ~30-60 seconds per scrape

### After (Optimized Flow):
1. User requests scrape → **Quick change check** → Only proceed if changed
2. **Cost**: Firecrawl change check (~$0.001) + full scrape/Gemini only when changed
3. **Time**: ~5 seconds for unchanged pages, ~30-60 seconds for changed pages

## Setup

### 1. Database Migration
The system automatically creates the necessary database columns:
```sql
ALTER TABLE scrape_logs
ADD COLUMN change_status VARCHAR(50),
ADD COLUMN previous_scrape_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN page_visibility VARCHAR(20),
ADD COLUMN change_metadata JSONB;
```

### 2. Configuration (Optional)
Add change tracking settings to your theatre configuration:

```json
{
  "scraping_strategy": {
    "type": "single_url",
    "base_url": "https://example-theatre.com"
  },
  "change_tracking": {
    "enabled": true,
    "modes": ["git-diff"],
    "tag": "my-theatre"
  }
}
```

## Status Messages

### In Web UI:
- **"Unchanged"** (blue badge): Page content hasn't changed
- **"Success"** (green badge): Page changed, full processing completed
- **Change status indicators:**
  - ✅ **Same content**: Page unchanged, skipped expensive processing
  - ⚠️ **Content changed**: Page updated, full processing triggered
  - ℹ️ **First scrape**: New page, initial baseline created

### In Logs:
```
INFO: Change tracking: same (previous: 2025-09-01T14:00:00Z)
INFO: Skipping LLM parsing for Palace Theatre - page unchanged
```

## Benefits

### Cost Savings:
- **Firecrawl**: Only ~$0.001 per change check vs ~$0.10 per full scrape
- **Gemini**: Completely skipped when pages are unchanged
- **Typical Savings**: 70-90% cost reduction for stable websites

### Performance:
- **Unchanged pages**: ~5 seconds vs 30-60 seconds
- **Changed pages**: Same performance as before
- **User Experience**: Faster feedback for routine monitoring

### Smart Processing:
- **Baseline Creation**: First scrape establishes comparison baseline
- **Incremental Updates**: Only processes when actual changes occur
- **Historical Tracking**: Full change history maintained in database

## Usage Examples

### Monitoring Stable Websites:
```json
{
  "change_tracking": {
    "enabled": true,
    "modes": ["git-diff"],
    "tag": "weekly-calendar"
  }
}
```
**Result**: Daily scrapes cost ~$0.001 each, full processing only when calendar updates

### Real-time Critical Updates:
```json
{
  "change_tracking": {
    "enabled": true,
    "modes": ["git-diff", "json"],
    "tag": "event-schedule"
  }
}
```
**Result**: Immediate detection of new shows/events with structured data extraction

## API Reference

### Change Status Values:
- `"new"`: First time scraping this page
- `"same"`: Content unchanged since last scrape
- `"changed"`: Content has been modified
- `"removed"`: Page no longer accessible
- `"error"`: Change tracking failed

### Visibility Values:
- `"visible"`: Page discoverable via links/sitemap
- `"hidden"`: Page not discoverable but still exists

### Configuration Options:
```json
{
  "change_tracking": {
    "enabled": true,           // Enable/disable change tracking
    "modes": ["git-diff"],     // Tracking modes: git-diff, json
    "tag": "custom-tag"        // Custom tag for tracking isolation
  }
}
```

## Troubleshooting

### No Change Tracking Data:
- Verify Firecrawl API key has change tracking permissions
- Check that page was previously scraped with change tracking enabled
- Ensure `markdown` format is included alongside `changeTracking`

### Unexpected "Changed" Status:
- Page might have dynamic content (timestamps, ads)
- Consider excluding volatile sections from comparison
- Use `tag` parameter to isolate different content types

### Performance Issues:
- Change tracking adds ~2-3 seconds to each scrape
- For very stable content, consider weekly instead of daily monitoring
- Monitor Firecrawl rate limits

## Future Enhancements

### Planned Features:
1. **Custom Comparison Rules**: Define which page sections to ignore
2. **Change Alerts**: Email notifications for important changes
3. **Advanced Diff Analysis**: Structured extraction of specific changes
4. **Bulk Change Tracking**: Monitor multiple pages efficiently

### Integration Ideas:
1. **Scheduled Scraping**: Automatically adjust frequency based on change patterns
2. **Content Archiving**: Store historical versions of changed content
3. **Analytics Dashboard**: Track change frequency and content stability

---

## Quick Start

1. **Enable change tracking** (enabled by default)
2. **Run a scrape** to establish baseline
3. **Monitor the "Change Tracking Summary"** in web UI
4. **Enjoy cost savings** on unchanged pages! 🎉

Change tracking is automatically enabled for all new scrapes. No additional configuration required for basic usage.
