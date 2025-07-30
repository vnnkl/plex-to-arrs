# 🎬 Plex Watchlist to Radarr/Sonarr Sync

Automatically sync your Plex watchlist to Radarr (movies) and Sonarr (TV shows) with Docker scheduling support.

## ✨ Features

- **📺 Complete Sync**: Movies → Radarr, TV Shows → Sonarr
- **🎯 Smart Detection**: Only adds new items, skips existing
- **⚙️ Configurable Quality**: Customizable quality profiles
- **🐳 Docker Ready**: Containerized with daily scheduling
- **📊 Detailed Logging**: Full sync reports and error handling
- **🔄 Automated**: Set-and-forget hourly synchronization with smart caching

## 🚀 Quick Start (Docker)

1. **Clone and configure**:
   ```bash
   git clone <repo-url>
   cd plex-to-arrs
   cp .env.example .env
   # Edit .env with your server URLs and API keys
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Check logs**:
   ```bash
   docker-compose logs -f
   # Or check: ./logs/sync.log
   ```

## ⚙️ Configuration

Create a `.env` file with your settings:

```bash
# Plex Configuration
PLEX_TOKEN=your_plex_token_here

# Radarr Configuration (Movies)
RADARR_URL=http://your-radarr-server:7878/api/v3
RADARR_API_KEY=your_radarr_api_key
RADARR_QUALITY_PROFILE=4  # 4=HD-1080p (see options below)

# Sonarr Configuration (TV Shows)  
SONARR_URL=http://your-sonarr-server:8989/api/v3
SONARR_API_KEY=your_sonarr_api_key
SONARR_QUALITY_PROFILE=4  # 4=HD-1080p (see options below)

# TMDB Configuration
TMDB_API_KEY=your_tmdb_api_key

# Optional Settings
RUN_ON_STARTUP=false      # Run sync immediately when container starts
CACHE_REFRESH_HOURS=24    # How often to refresh cache from servers (hours)
TZ=Europe/Amsterdam       # Your timezone for proper scheduling
```

### 🌐 Server URL Configuration

**Important**: Configure your server URLs to match your setup:
- **Local**: `http://localhost:7878/api/v3` (if Radarr runs on same machine)
- **Network**: `http://192.168.1.100:7878/api/v3` (if on different machine)  
- **Domain**: `http://radarr.yournas.local:7878/api/v3` (if using hostnames)
- **External**: `http://your-external-domain.com:7878/api/v3` (if public)

**Standard Ports:**
- Radarr: `7878`
- Sonarr: `8989`

### 🎭 Quality Profile Options

**Radarr (Movies):**
- `1` = Any
- `3` = HD-720p  
- `4` = HD-1080p
- `5` = Ultra-HD
- `9` = Remux + WEB 1080p *(highest quality)*

**Sonarr (TV Shows):**
- `1` = Any
- `3` = HD-720p
- `4` = HD-1080p  
- `5` = Ultra-HD
- `9` = WEB-1080p

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```bash
# Deploy with hourly scheduling (smart caching included)
docker-compose up -d

# View logs
docker-compose logs -f plex-to-arrs

# Manual sync
docker-compose exec plex-to-arrs python plex_to_arr.py
```

### Manual Docker Build
```bash
# Build image
docker build -t plex-to-arrs .

# Run with scheduling
docker run -d --name plex-to-arrs \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  plex-to-arrs
```

## 📋 Manual Usage (Without Docker)

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run sync
python plex_to_arr.py

# Dry run (preview only)
DRY_RUN=true python plex_to_arr.py

# Generate curl commands
GENERATE_CURL=true python plex_to_arr.py
```

## 📊 Monitoring & Logs

- **Container logs**: `docker-compose logs -f`
- **Sync logs**: `./logs/sync.log`
- **Cache file**: `./logs/sync_cache.json`
- **Scheduling**: Hourly (with smart caching to avoid redundant API calls)

## 🔧 API Keys Setup

### Plex Token
1. Visit: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/

### Radarr API Key
1. Radarr → Settings → General → Security → API Key

### Sonarr API Key  
1. Sonarr → Settings → General → Security → API Key

### TMDB API Key
1. Visit: https://www.themoviedb.org/settings/api
2. Create account → Request API key

## 🛠️ Customization

### Change Sync Schedule
Edit the cron schedule in `Dockerfile`:
```dockerfile
# Hourly (default)
RUN echo "0 * * * * cd /app && python plex_to_arr.py >> /app/logs/sync.log 2>&1" | crontab -

# Every 6 hours  
RUN echo "0 */6 * * * cd /app && python plex_to_arr.py >> /app/logs/sync.log 2>&1" | crontab -

# Daily at 6 AM
RUN echo "0 6 * * * cd /app && python plex_to_arr.py >> /app/logs/sync.log 2>&1" | crontab -
```

### Cache Management
```bash
# Adjust cache refresh interval in .env
CACHE_REFRESH_HOURS=12    # Refresh cache every 12 hours
CACHE_REFRESH_HOURS=168   # Refresh cache weekly
```

### Different Quality Profiles
Update your `.env` file with desired profile IDs.

## 🐛 Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs plex-to-arrs
```

### Test API Connections
```bash
# Test in dry run mode
docker-compose exec plex-to-arrs python -c "
import os; 
print('PLEX_TOKEN:', 'OK' if os.getenv('PLEX_TOKEN') else 'MISSING')
print('RADARR_API_KEY:', 'OK' if os.getenv('RADARR_API_KEY') else 'MISSING')
"
```

### Manual Sync
```bash
docker-compose exec plex-to-arrs python plex_to_arr.py
```

## 📈 Example Output

```
============================================================
🎬 PLEX WATCHLIST TO RADARR/SONARR SYNC
⏰ Started at: 2025-01-30 14:00:01
============================================================
📋 Loading sync cache...
💾 Found 14 previously synced items
📡 Fetching Plex watchlist...
📋 Found 16 items in Plex watchlist
✅ 14 items already synced (skipping)
🆕 2 new items to process

🎯 Processing 2 new items:
------------------------------------------------------------
[1/2] 📺 The Father (2020) - Type: movie  
✅ Added movie 'The Father' to Radarr successfully.

============================================================
📊 SUMMARY
============================================================
🎬 New movies processed: 1
📺 New TV shows processed: 1
🆕 Items newly synced: 2
💾 Total cached items: 16
📋 Total watchlist items: 16
🎉 Successfully synced 2 new items!
```

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.
