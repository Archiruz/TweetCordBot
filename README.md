# TweetCordBot

A background worker that monitors a Twitter account and sends new tweets to a Discord channel via webhook.

## Features

- Monitors a specified Twitter account for new tweets
- Fetches up to 5 tweets every 8 hours
- Sends new tweets to Discord via webhook
- Runs as a containerized background service
- Prevents duplicate tweet notifications

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

1. The bot fetches the user ID for the specified Twitter username
2. Every 8 hours, it fetches the 5 most recent tweets from the account
3. It compares new tweets against the last seen tweet ID
4. Any new tweets are sent to Discord in chronological order
5. The bot sleeps for 8 hours before the next check

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

### Checking Status

```bash
# Check if container is running
docker-compose ps

# View recent logs
docker-compose logs --tail=50 tweetcord-bot

# Restart the service
docker-compose restart
```
