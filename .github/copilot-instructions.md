# TweetCordBot - AI Agent Instructions

## Project Overview
TweetCordBot is a **single-file Python background worker** that monitors a Twitter account and forwards new tweets to Discord via webhook. It's designed to run as a long-lived containerized service with 8-hour polling intervals.

**Key architectural decision**: This is intentionally a minimal, single-file (`main.py`) application with no complex abstractions—all logic lives in one place for simplicity and easy debugging.

## Core Architecture

### Stateful Polling Pattern
- Global `last_tweet_id` variable tracks the most recent tweet seen
- **NEW: Persistent state file** - `logs/last_tweet_id.txt` stores tweet ID across restarts
- On startup, bot loads previous state from disk (no more lost memory!)
- Uses Twitter API v2 with `max_results=5&exclude=retweets,replies`

### Dual Run Modes (NEW)
1. **Continuous Mode** (default): Traditional 8-hour sleep loop
   - Use `RUN_MODE=continuous` or omit (default)
   - Best for Docker Compose deployments
2. **Once Mode**: Run single check and exit
   - Use `RUN_MODE=once`
   - Designed for Kubernetes CronJob scheduling
   - Server-side CRON handles timing, not the bot

### Rate Limiting Strategy
- **429 responses**: Sleep for 905 seconds (15 min + 5 sec buffer) automatically
- Normal operation: 8-hour sleep between polls (`time.sleep(28800)`)
- **Twitter API limits**: Free tier is ~500k tweets/month, this bot uses ~3 requests/day

### Discord Integration
- Uses `fxtwitter.com` (not `twitter.com`) for better Discord embeds with media previews
- Sends tweets in chronological order (oldest first) via `reversed(new_tweets)`
- No retry logic on Discord webhook failures—errors are logged only

## Development Workflows

### Local Development (without Docker)
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real credentials
python main.py
```

### Docker Development
```bash
# Standard run (detached)
docker-compose up -d

# Development mode with live reload (uncomment volumes in docker-compose.yml)
docker-compose down
# Uncomment volumes section in docker-compose.yml first
docker-compose up

# View logs (bot logs every 8 hours or on events)
docker-compose logs -f tweetcord-bot
```

### Testing Changes
**No automated tests exist** (see Testing Philosophy section below). Manual testing workflow:
1. Set `TWITTER_USERNAME` to an active account (e.g., a test account you control)
2. Temporarily reduce `time.sleep(28800)` to `time.sleep(60)` for faster iteration
3. Send a test tweet from the monitored account
4. Check Discord channel for webhook delivery
5. **Revert sleep duration before committing**

**Important**: Avoid excessive API calls during development—free tier has limited quota.

## Environment Variables
All configuration via `.env` file (never committed):
- `BEARER_TOKEN`: Twitter API v2 Bearer Token (NOT API Key/Secret)
- `TWITTER_USERNAME`: Plain username without `@` symbol
- `DISCORD_WEBHOOK_URL`: Full webhook URL (can include `?thread_id=` for thread posting)
- `RUN_MODE`: (Optional) `continuous` (default) or `once` for CronJob mode

**Common mistake**: Using Twitter API v1.1 credentials—this bot requires v2 Bearer Token only.

## Deployment & CI/CD

### GitHub Actions Workflow
- **Trigger**: Push to main, version tags (`v*`), or manual dispatch
- **Multi-arch**: Builds for `linux/amd64` and `linux/arm64`
- **Registry**: Pushes to `ghcr.io/archiruz/tweetcordbot`
- **Tags**: `latest`, `main`, `v1.0.0`, `v1.0` (semantic versioning)

### Production Deployment
```bash
docker pull ghcr.io/archiruz/tweetcordbot:latest
docker run -d --name tweetcord-bot --env-file .env --restart unless-stopped ghcr.io/archiruz/tweetcordbot:latest
```

Or use `docker-compose.yml` with updated image reference.

## Code Conventions

### Logging Strategy
- Uses Python's `logging` module (not print statements)
- `INFO` level for normal operations (startup, new tweets, sleep cycles)
- `ERROR` level for API failures
- `WARNING` for rate limits
- `DEBUG` for "no new tweets" (currently logged as INFO)

### Error Handling Pattern
```python
try:
    response = requests.get(...)
    response.raise_for_status()
    # Process response
except Exception as e:
    logging.error(f"Error message: {e}")
    return None
```
**Note**: Broad exception catching is acceptable here due to simple retry logic (next 8-hour cycle).

### Dependencies
- `requests`: HTTP client (no async/aiohttp—this is a simple sync script)
- `python-dotenv`: Environment variable loading
- Dockerfile uses Alpine Linux for minimal image size (~50MB)

## Common Modifications

### Changing Poll Interval
Modify line 113: `time.sleep(28800)` (seconds)
- 1 hour: `3600`
- 4 hours: `14400`
- 12 hours: `43200`

### Increasing Tweet History
Modify line 46: `max_results=5` (max: 100)
**Warning**: Higher limits increase rate limit usage.

### Adding Filters
The API call already excludes retweets/replies. To include them:
- Remove `&exclude=retweets,replies` from line 47

### Persistent State (Planned Feature)
**Current status**: ✅ **IMPLEMENTED**
**Implementation**: File-based storage in `logs/` directory:
1. Writes `last_tweet_id` to `logs/last_tweet_id.txt` after each update
2. Reads on startup with fallback to None if file doesn't exist
3. Eliminates duplicate tweet skipping on container restarts
4. Docker Compose automatically mounts `./logs` volume
5. Kubernetes requires PersistentVolumeClaim (see `kubernetes/pvc.yaml`)

## Testing Philosophy
**No automated tests currently exist** due to Twitter API rate limits on free tier.
**Planned**: Once dual API keys are available (production + development), add:
- Unit tests for tweet filtering logic
- Mock-based tests for API interactions
- Integration tests using development API key

## Troubleshooting

### Bot stops responding
1. Check if container crashed: `docker-compose ps`
2. Check logs for rate limits: `docker-compose logs tweetcord-bot | grep "Rate limit"`
3. Verify Twitter credentials haven't expired

### Duplicate tweets after restart
**Fixed in v2.0+**: State now persists via `logs/last_tweet_id.txt`
If still seeing duplicates:
- Verify volume mount: `docker-compose config` should show `./logs:/app/logs`
- For Kubernetes: Check PVC is bound with `kubectl get pvc`
- Manually verify state file: `docker exec tweetcord-bot cat /app/logs/last_tweet_id.txt`

### Discord messages not appearing
- Verify webhook URL is still valid (Discord webhooks can be deleted)
- Check for HTTP 404 errors in logs
- Test webhook with: `curl -X POST -H "Content-Type: application/json" -d '{"content":"test"}' WEBHOOK_URL`
