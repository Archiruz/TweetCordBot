import requests
import time
from dotenv import load_dotenv
import os
import threading
from flask import Flask, jsonify

# Load environment variables from .env file
load_dotenv()

# Twitter API credentials
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
# The Twitter username to monitor
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
# Discord webhook URL (with thread ID if applicable)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

last_tweet_id = None

def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["data"]["id"]
    except Exception as e:
        print(f"Error fetching user ID: {e}")
    return None

def get_latest_tweet(user_id):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&exclude=retweets,replies&tweet.fields=created_at"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            print("Rate limit exceeded. Waiting 15 minutes...")
            time.sleep(900)
            return None
        response.raise_for_status()
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]
    except Exception as e:
        print(f"Error fetching tweets: {e}")
    return None

def send_to_discord(webhook_url, tweet, username):
    tweet_url = f"https://fxtwitter.com/{username}/status/{tweet['id']}"
    message = {
        "content": f"New tweet from @{username}:\n{tweet_url}"
    }
    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Discord: {e}")

def tweet_monitor_worker():
    global last_tweet_id
    user_id = get_user_id(TWITTER_USERNAME)
    if not user_id:
        print("Could not fetch user ID. Exiting tweet monitor thread.")
        return
    while True:
        latest_tweet = get_latest_tweet(user_id)
        if latest_tweet and latest_tweet["id"] != last_tweet_id:
            send_to_discord(DISCORD_WEBHOOK_URL, latest_tweet, TWITTER_USERNAME)
            last_tweet_id = latest_tweet["id"]
        time.sleep(900)

# Flask app for health check endpoint
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    # Start tweet monitor in a background thread
    t = threading.Thread(target=tweet_monitor_worker, daemon=True)
    t.start()
    # Start Flask app
    app.run(host="0.0.0.0", port=8080)
