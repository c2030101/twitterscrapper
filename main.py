from twikit import Client, TooManyRequests
import time
from datetime import datetime
import csv
from configparser import ConfigParser
from random import randint

minimum_tweets=500
#For more complicated search, go on twitter, advanced search, enter requirements, and copy and past that search into query.
query = 'SStock Market min_faves:5 lang:en until:2024-09-25 since:2024-09-01'


def get_tweets(tweets):
    if tweets is None:
        print(f'{datetime.now()} - Getting tweets...')
        # get tweets
        tweets = client.search_tweet(query, product='Top')
    else:
        wait_time = randint(10,20)
        print(f'{datetime.now()} - Getting next tweets after {wait_time} seconds...')
        time.sleep(wait_time)
        tweets = tweets.next()

    return tweets


# login credentials

config = ConfigParser()
config.read('config.ini')
username = config['X']['username']
email = config['X']['email']
password = config['X']['password']

#Create csv file
with open('tweets.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Tweet_count', 'Username', 'Text', 'Created at', 'Retweets', 'Likes'])

# Autheticate to X.com
# 1) Use the login credentials 2) Use cookies.
client = Client(language='en-US')
#client.login(auth_info_1=username, auth_info_2=email, password=password)
#client.save_cookies('cookies.json')
client.load_cookies('cookies.json')

tweet_count = 0
tweets=None

while tweet_count < minimum_tweets:
    try:
        tweets = get_tweets(tweets)
    except TooManyRequests as e:
        rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
        print(f'{datetime.now()} - rate limit reached. waiting until {rate_limit_reset} ')
        wait_time = rate_limit_reset - datetime.now()
        time.sleep(wait_time.total_seconds())
        continue


    if not tweets:
        print(f'{datetime.now()} - No more tweets found on topic')
        break



    for tweet in tweets:
        tweet_count += 1
        tweet_data = [tweet_count, tweet.user.name, tweet.text, tweet.created_at, tweet.retweet_count,
                      tweet.favorite_count]

        with open('tweets.csv', 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(tweet_data)

    print(f'{datetime.now()} - Got {tweet_count} tweets')

print(f'{datetime.now()} - Done! Got {tweet_count} tweets found')
