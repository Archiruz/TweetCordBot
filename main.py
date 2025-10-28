import requests
import time
from dotenv import load_dotenv
import os
import logging
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Load environment variables from .env file
load_dotenv()

# Twitter API credentials
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
# The Twitter username to monitor
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
# Discord webhook URL (with thread ID if applicable)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
# Run mode: "continuous" (default, 8-hour loop) or "once" (single run for CronJob)
RUN_MODE = os.getenv("RUN_MODE", "continuous")

# State file path for persistent storage
STATE_DIR = Path("logs")
STATE_FILE = STATE_DIR / "last_tweet_id.txt"

last_tweet_id = None


def load_last_tweet_id():
    """Load the last tweet ID from persistent storage."""
    global last_tweet_id
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                last_tweet_id = f.read().strip()
                if last_tweet_id:
                    logging.info(f"Loaded last tweet ID from state: {last_tweet_id}")
                else:
                    last_tweet_id = None
        except Exception as e:
            logging.error(f"Error loading state file: {e}")
            last_tweet_id = None
    else:
        logging.info("No state file found. Starting fresh.")
        last_tweet_id = None


def save_last_tweet_id(tweet_id):
    """Save the last tweet ID to persistent storage."""
    global last_tweet_id
    try:
        STATE_DIR.mkdir(exist_ok=True)
        with open(STATE_FILE, "w") as f:
            f.write(tweet_id)
        last_tweet_id = tweet_id
        logging.info(f"Saved last tweet ID to state: {tweet_id}")
    except Exception as e:
        logging.error(f"Error saving state file: {e}")


def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["data"]["id"]
    except Exception as e:
        logging.error(f"Error fetching user ID: {e}")
    return None


def get_recent_tweets(user_id):
    url = (
        f"https://api.twitter.com/2/users/{user_id}/tweets?"
        f"max_results=5&exclude=retweets,replies&tweet.fields=created_at"
    )
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            logging.warning("Rate limit exceeded. Waiting 15 minutes...")
            time.sleep(905)  # Wait for 15 minutes + 5 seconds buffer
            return None
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"]
    except Exception as e:
        logging.error(f"Error fetching tweets: {e}")
    return None


def send_to_discord(webhook_url, tweet, username):
    tweet_url = f"https://fxtwitter.com/{username}/status/{tweet['id']}"
    message = {"content": f"New tweet from @{username}:\n{tweet_url}"}
    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        logging.info(f"Sent tweet {tweet['id']} to Discord.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending to Discord: {e}")


def tweet_monitor_worker():
    global last_tweet_id
    
    # Load previous state
    load_last_tweet_id()
    
    user_id = get_user_id(TWITTER_USERNAME)
    if not user_id:
        logging.error("Could not fetch user ID. Exiting tweet monitor.")
        return
    logging.info(f"Starting tweet monitor for @{TWITTER_USERNAME} (user_id={user_id})")

    while True:
        tweets = get_recent_tweets(user_id)
        if tweets:
            new_tweets = []
            for tweet in tweets:
                if tweet["id"] != last_tweet_id:
                    new_tweets.append(tweet)
                else:
                    # Stop at the first tweet we've already seen
                    break

            if new_tweets:
                logging.info(f"Found {len(new_tweets)} new tweets")
                # Send oldest first
                for tweet in reversed(new_tweets):
                    logging.info(f"New tweet detected: {tweet['id']}")
                    send_to_discord(DISCORD_WEBHOOK_URL, tweet, TWITTER_USERNAME)
                # Update to the most recent tweet and save state
                save_last_tweet_id(tweets[0]["id"])
            else:
                logging.info("No new tweets found.")
        else:
            logging.info("No tweets found.")

        # Check run mode - if "once", exit after single check
        if RUN_MODE == "once":
            logging.info("Run mode is 'once'. Exiting after single check.")
            break

        # Sleep for 8 hours (28800 seconds)
        logging.info("Sleeping for 8 hours...")
        time.sleep(28800)


if __name__ == "__main__":
    logging.info(f"Starting TweetCordBot background worker (mode: {RUN_MODE})...")
    tweet_monitor_worker()
