import re
from twikit import Client, TooManyRequests
import time
from datetime import datetime
import json
from configparser import ConfigParser
from random import randint

# Constants
MINIMUM_TWEETS = 5  # Reduced for testing
LIKES_THRESHOLD = 1
TARGET_USER = "Crypto_VorteXBT"
QUERY = f"from:{TARGET_USER}"

# Rate limiting constants
MIN_WAIT = 15  # Minimum seconds between requests
MAX_WAIT = 30  # Maximum seconds between requests
BATCH_MIN_WAIT = 30  # Minimum seconds between batches
BATCH_MAX_WAIT = 45  # Maximum seconds between batches


def get_tweets(tweets, client):
    if tweets is None:
        print(f'{datetime.now()} - Getting tweets...')
        print(f'Using query: {QUERY}')
        tweets = client.search_tweet(QUERY, product='Latest')
    else:
        wait_time = randint(BATCH_MIN_WAIT, BATCH_MAX_WAIT)
        print(f'{datetime.now()} - Getting next tweets after {wait_time} seconds...')
        time.sleep(wait_time)
        tweets = tweets.next()
    return tweets


def is_reply(tweet):
    return hasattr(tweet, 'in_reply_to') and tweet.in_reply_to is not None


def get_parent_tweet(in_reply_to_id, client):
    try:
        # Only try the first query method to reduce API calls
        query = f"id:{in_reply_to_id}"
        print(f'{datetime.now()} - Searching for parent tweet with query: {query}')
        parent_tweets = client.search_tweet(query, product='Latest')

        if parent_tweets:
            for tweet in parent_tweets:
                if str(tweet.id) == str(in_reply_to_id):
                    return tweet

        return None
    except Exception as e:
        print(f'{datetime.now()} - Error fetching parent tweet: {str(e)}')
        if "Rate limit exceeded" in str(e):
            # Add extra wait time when rate limit is hit
            wait_time = randint(45, 60)  # Longer wait when rate limited
            print(f'{datetime.now()} - Rate limit hit, waiting {wait_time} seconds')
            time.sleep(wait_time)
    return None


def create_metrics_dict(tweet):
    """Create a simplified metrics dictionary with only like_count and reply_count"""
    return {
        'like_count': getattr(tweet, 'favorite_count', 0),
        'reply_count': getattr(tweet, 'reply_count', 0)
    }


def main():
    # Authentication setup
    config = ConfigParser()
    config.read('config.ini')
    client = Client(language='en-US')
    client.load_cookies('cookies.json')

    tweet_count = 0
    tweets = None
    conversation_data = []

    while tweet_count < MINIMUM_TWEETS:  # Only continue until minimum tweets reached
        try:
            tweets = get_tweets(tweets, client)
            if not tweets:
                break

            for tweet in tweets:
                if tweet_count >= MINIMUM_TWEETS:  # Exit if we have enough tweets
                    break

                if not is_reply(tweet):
                    continue

                likes = getattr(tweet, 'favorite_count', 0)
                if likes < LIKES_THRESHOLD:
                    continue

                # Add base wait time between tweet processing
                wait_time = randint(MIN_WAIT, MAX_WAIT)
                print(f'{datetime.now()} - Waiting {wait_time} seconds before next request')
                time.sleep(wait_time)

                parent_tweet = get_parent_tweet(tweet.in_reply_to, client)

                if parent_tweet:
                    conversation = {
                        'parent_tweet': {
                            'text': parent_tweet.text,
                            'metrics': create_metrics_dict(parent_tweet)
                        },
                        'reply': {
                            'text': tweet.text,
                            'metrics': create_metrics_dict(tweet)
                        }
                    }
                    conversation_data.append(conversation)
                    tweet_count += 1
                    print(f'{datetime.now()} - Collected {tweet_count}/{MINIMUM_TWEETS} tweets')

        except TooManyRequests as e:
            rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
            wait_time = (rate_limit_reset - datetime.now()).total_seconds()
            print(f'{datetime.now()} - Rate limit exceeded, waiting {wait_time} seconds')
            time.sleep(wait_time + randint(5, 10))  # Add a small buffer

    # Save results
    output_file = f'fortyIQVortex.json'
    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(conversation_data, json_file, indent=4, ensure_ascii=False)

    print(f'{datetime.now()} - Scraping completed. Collected {len(conversation_data)} conversations')


if __name__ == "__main__":
    main()