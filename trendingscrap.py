import re
from twikit import Client, TooManyRequests
import time
from datetime import datetime
import json
from configparser import ConfigParser
from random import randint

minimum_tweets =300
query = 'stock market -filter:replies'
def get_tweets(tweets):
    if tweets is None:
        print(f'{datetime.now()} - Getting tweets...')
        tweets = client.search_tweet(query, product='Top')
    else:
        wait_time = randint(10, 20)
        print(f'{datetime.now()} - Getting next tweets after {wait_time} seconds...')
        time.sleep(wait_time)
        tweets = tweets.next()
    return tweets

# Login credentials
config = ConfigParser()
config.read('config.ini')
username = config['X']['username']
email = config['X']['email']
password = config['X']['password']

# Authenticate to X.com
client = Client(language='en-US')
client.load_cookies('cookies.json')

tweet_count = 0
tweets = None

# Initialize list to store tweet data
tweet_data_list = []

while tweet_count < minimum_tweets:
    try:
        tweets = get_tweets(tweets)
    except TooManyRequests as e:
        rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
        print(f'{datetime.now()} - Rate limit reached. Waiting until {rate_limit_reset}')
        wait_time = rate_limit_reset - datetime.now()
        time.sleep(wait_time.total_seconds())
        continue

    if not tweets:
        print(f'{datetime.now()} - No more tweets found on topic')
        break

    for tweet in tweets:
        tweet_count += 1

        # Extract likes (favorite count)
        likes = getattr(tweet, 'favorite_count', 0)

        # Create a dictionary for the tweet data
        tweet_data = {
            'username': tweet.user.name,
            'text': tweet.text,
            'likes': likes
        }

        # Append the tweet data to the list
        tweet_data_list.append(tweet_data)

    print(f'{datetime.now()} - Got {tweet_count} tweets')

# Load existing data from the JSON file if it exists
try:
    with open('ahmedalbalaghicomplete.json', 'r', encoding='utf-8') as json_file:
        existing_data = json.load(json_file)
        tweet_data_list = existing_data + tweet_data_list
except FileNotFoundError:
    pass  # No existing data, start fresh

# Write the collected tweet data to a JSON file
with open('ahmedalbalaghicomplete.json', 'w', encoding='utf-8') as json_file:
    json.dump(tweet_data_list, json_file, indent=4, ensure_ascii=False)

print(f'{datetime.now()} - Done! Got {tweet_count} tweets.')
