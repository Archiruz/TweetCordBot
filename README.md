# TweetCordBot

A background worker that monitors a Twitter account and sends new tweets to a Discord channel via webhook.

## Features

- Monitors a specified Twitter account for new tweets
- Fetches up to 5 tweets every 8 hours
- Sends new tweets to Discord via webhook
- Runs as a containerized background service
- Prevents duplicate tweet notifications
- **Persistent state tracking** - survives container restarts
- **Dual deployment modes** - continuous or CronJob-based

## Setup

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Twitter API Configuration
BEARER_TOKEN=your_twitter_bearer_token_here

# Twitter username to monitor (without @ symbol)
TWITTER_USERNAME=username_to_monitor

# Discord Webhook URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url_here

# Run Mode (optional, defaults to "continuous")
# - "continuous": Traditional mode with 8-hour sleep loop (for Docker Compose)
# - "once": Run a single check and exit (for Kubernetes CronJob)
RUN_MODE=continuous
```

### 2. Twitter API Setup

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new app or use an existing one
3. Generate a Bearer Token
4. Add the Bearer Token to your `.env` file

### 3. Discord Webhook Setup

1. Go to your Discord server settings
2. Navigate to Integrations > Webhooks
3. Create a new webhook
4. Copy the webhook URL and add it to your `.env` file

## Running with Docker Compose

### Build and Run

```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Using Pre-built Images from GitHub Container Registry

If you prefer to use the pre-built image from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/your-username/tweetcordbot:latest

# Run the container
docker run -d \
  --name tweetcord-bot \
  --env-file .env \
  --restart unless-stopped \
  ghcr.io/your-username/tweetcordbot:latest
```

Replace `your-username` with your GitHub username.

## GitHub Actions CI/CD

This repository includes a GitHub Actions workflow that automatically builds and pushes Docker images to GitHub Container Registry (ghcr.io).

### Workflow Features

- **Automatic builds** on push to main/master branches
- **Tag-based releases** (e.g., `v1.0.0`)
- **Multi-platform builds** (linux/amd64, linux/arm64)
- **Pull request validation** (builds but doesn't push)
- **Manual trigger** support via GitHub Actions UI
- **Build caching** for faster subsequent builds

### How to Use

1. **Push to main branch**: Automatically builds and pushes `latest` tag
2. **Create a release tag**: 
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. **Manual trigger**: Go to Actions tab → "Build and Push Docker Image" → "Run workflow"

### Image Tags

The workflow creates multiple tags:
- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `v1.0.0` - Specific version tags
- `v1.0` - Major.minor version tags

### Development Mode

For development with live code reloading, uncomment the development volumes in `docker-compose.yml`:

```yaml
volumes:
  - .:/app
command: python -m pip install --upgrade pip && python main.py
```

## Running Locally (without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your `.env` file as described above

3. Run the application:
   ```bash
   python main.py
   ```

## How It Works

### Persistent State Tracking

The bot now maintains state across restarts using a file-based system:
- Last seen tweet ID is stored in `logs/last_tweet_id.txt`
- On startup, the bot loads the previous state
- Docker Compose automatically mounts `./logs` directory for persistence
- **No more duplicate tweets after container restarts!**

### Monitoring Flow

1. The bot fetches the user ID for the specified Twitter username
2. Loads the last seen tweet ID from `logs/last_tweet_id.txt` (if exists)
3. Every 8 hours (or on single run), it fetches the 5 most recent tweets
4. Compares new tweets against the last seen tweet ID
5. Any new tweets are sent to Discord in chronological order
6. Saves the latest tweet ID to disk
7. In continuous mode, sleeps for 8 hours before the next check

## Deployment Options

### Option 1: Docker Compose (Continuous Mode)

Best for simple deployments or single-host environments:

```bash
docker-compose up -d
```

The bot runs continuously with 8-hour sleep cycles. State persists in `./logs` directory.

### Option 2: Kubernetes CronJob (Recommended for Production)

Best for Kubernetes clusters - runs on a schedule without keeping a pod alive:

**Advantages:**
- No wasted resources during sleep periods
- Kubernetes-native scheduling
- Automatic cleanup of old jobs
- Better for cluster restarts

**See full deployment guide:** [`kubernetes/DEPLOYMENT.md`](kubernetes/DEPLOYMENT.md)

**Quick Start:**
```bash
# Create secrets
kubectl create secret generic tweetcordbot-secrets \
  --from-literal=bearer-token="YOUR_TOKEN" \
  --from-literal=twitter-username="YOUR_USERNAME" \
  --from-literal=discord-webhook-url="YOUR_WEBHOOK_URL"

# Deploy
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/cronjob.yaml

# Monitor
kubectl get cronjobs
kubectl logs -l app=tweetcordbot --tail=50
```

## Logs

The application logs all activities including:
- Tweet monitoring status
- New tweet detection
- Discord webhook delivery status
- Error messages

View logs with:
```bash
docker-compose logs -f tweetcord-bot
```

## Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**: The bot includes automatic rate limit handling and will wait 15 minutes before retrying.

2. **Invalid Bearer Token**: Ensure your Twitter Bearer Token is correct and has the necessary permissions.

3. **Discord Webhook Failed**: Verify your Discord webhook URL is correct and the webhook is still active.

4. **User Not Found**: Make sure the Twitter username exists and is spelled correctly (without @ symbol).

5. **Duplicate tweets after restart**: 
   - Ensure the `logs/` directory is properly mounted (Docker Compose does this automatically)
   - For Kubernetes, verify PVC is bound: `kubectl get pvc`
   - Check state file exists: `docker exec tweetcord-bot cat /app/logs/last_tweet_id.txt`

### Checking Status

```bash
# Docker Compose
docker-compose ps
docker-compose logs --tail=50 tweetcord-bot
docker-compose restart

# Kubernetes CronJob
kubectl get cronjobs
kubectl get jobs --sort-by=.metadata.creationTimestamp
kubectl logs -l app=tweetcordbot --tail=50
kubectl create job --from=cronjob/tweetcordbot-cronjob manual-test
```
