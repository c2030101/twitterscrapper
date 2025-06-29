import asyncio
import json
import time
from datetime import datetime, timedelta
from random import randint, uniform
from configparser import ConfigParser
import os
import logging
from pathlib import Path

try:
    from twikit import Client, TooManyRequests, BadRequest, Unauthorized
except ImportError:
    print("Please install twikit: pip install twikit")
    exit(1)

# Configuration
MINIMUM_TWEETS = 50
QUERY = '(ai) min_faves:100 since:2025-5-10 -filter:links -filter:replies'
COOKIES_FILE = 'cookies.json'
CONFIG_FILE = 'config.ini'
OUTPUT_FILE = 'buildinpublicbest.json'
LOG_FILE = 'scraper.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TwitterScraper:
    def __init__(self):
        self.client = None
        self.config = None
        self.tweet_data_list = []
        self.load_config()
        
    def load_config(self):
        """Load configuration from config.ini file"""
        self.config = ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            self.create_config_template()
            logger.error(f"Please fill in your credentials in {CONFIG_FILE}")
            exit(1)
            
        self.config.read(CONFIG_FILE)
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not self.config.get('X', field, fallback=''):
                logger.error(f"Missing {field} in {CONFIG_FILE}")
                exit(1)
    
    def create_config_template(self):
        """Create a template config file"""
        config = ConfigParser()
        config.add_section('X')
        config.set('X', 'username', 'your_username')
        config.set('X', 'email', 'your_email@example.com') 
        config.set('X', 'password', 'your_password')
        
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        
        logger.info(f"Created {CONFIG_FILE} template. Please fill in your credentials.")

    async def initialize_client(self):
        """Initialize and authenticate the Twitter client"""
        # Use a more common user agent to avoid detection
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.client = Client(language='en-US', user_agent=user_agent)
        
        # Try to load existing cookies first
        if os.path.exists(COOKIES_FILE):
            try:
                self.client.load_cookies(COOKIES_FILE)
                logger.info("Loaded existing cookies")
                
                # Test if cookies are still valid
                await self.test_authentication()
                return
                
            except Exception as e:
                logger.warning(f"Failed to load cookies or cookies expired: {e}")
                # Remove invalid cookies file
                os.remove(COOKIES_FILE)
        
        # If no valid cookies, perform fresh login
        await self.login()
    
    async def test_authentication(self):
        """Test if current authentication is valid"""
        try:
            # Try a simple operation to test auth
            await self.client.search_tweet(QUERY, 'Latest', count=1)
            logger.info("Authentication test successful")
        except (Unauthorized, BadRequest) as e:
            logger.error(f"Authentication test failed: {e}")
            raise
    
    async def login(self):
        """Perform login with retry logic"""
        username = self.config['X']['username']
        email = self.config['X']['email']
        password = self.config['X']['password']
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting login (attempt {attempt + 1}/{max_retries})")
                
                await self.client.login(
                    auth_info_1=username,
                    auth_info_2=email,
                    password=password,
                    cookies_file=COOKIES_FILE
                )
                
                logger.info("Login successful! Cookies saved.")
                return
                
            except BadRequest as e:
                if "LoginFlow is currently not accessible" in str(e):
                    logger.error("Twitter login flow not accessible. This may be due to:")
                    logger.error("1. Account suspension or restrictions")
                    logger.error("2. Too many login attempts")
                    logger.error("3. Account requires additional verification")
                    logger.error("Try again later or check your account status")
                elif "We were unable to confirm you're human" in str(e):
                    logger.error("Human verification required. Try:")
                    logger.error("1. Logging in manually via browser first")
                    logger.error("2. Completing any pending verifications")
                    logger.error("3. Waiting before retrying")
                else:
                    logger.error(f"Login failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected login error: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(30)

    async def get_tweets_batch(self, tweets=None):
        """Get a batch of tweets with proper error handling"""
        try:
            if tweets is None:
                logger.info("Searching for initial tweets...")
                tweets = await self.client.search_tweet(QUERY, 'Top', count=20)
            else:
                # Random delay between requests
                wait_time = uniform(5, 15)
                logger.info(f"Getting next batch after {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                tweets = await tweets.next()
            
            return tweets
            
        except TooManyRequests as e:
            rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
            current_time = datetime.now()
            wait_time = (rate_limit_reset - current_time).total_seconds()
            
            logger.warning(f"Rate limit reached. Waiting until {rate_limit_reset} ({wait_time:.0f} seconds)")
            await asyncio.sleep(max(wait_time + 10, 60))  # Add buffer time
            
            # Retry the request
            return await self.get_tweets_batch(tweets)
            
        except BadRequest as e:
            if "authorization" in str(e).lower():
                logger.error("Authorization error. Re-authenticating...")
                await self.initialize_client()
                return await self.get_tweets_batch(tweets)
            else:
                logger.error(f"Bad request error: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error getting tweets: {e}")
            raise

    def extract_tweet_data(self, tweet):
        """Extract minimal data from a tweet object for LLM tone analysis"""
        try:
            # Only extract what's needed for tone analysis
            tweet_data = {
                'username': getattr(tweet.user, 'name', '') if hasattr(tweet, 'user') else '',
                'text': getattr(tweet, 'text', ''),
                'likes': getattr(tweet, 'favorite_count', 0)
            }
            
            # Skip tweets without text or username
            if not tweet_data['text'] or not tweet_data['username']:
                return None
            
            return tweet_data
            
        except Exception as e:
            logger.error(f"Error extracting tweet data: {e}")
            return None

    # Remove helper methods that are no longer needed
    # (hashtags, mentions, urls extraction methods removed since we only need username, text, likes)

    def save_data(self):
        """Save collected data to JSON file"""
        # Load existing data if file exists
        existing_data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                logger.info(f"Loaded {len(existing_data)} existing tweets")
            except Exception as e:
                logger.error(f"Error loading existing data: {e}")
        
        # Combine with new data
        all_data = existing_data + self.tweet_data_list
        
        # Remove duplicates based on text content (since we don't have tweet ID anymore)
        seen_texts = set()
        unique_data = []
        for tweet in all_data:
            text = tweet.get('text', '')
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_data.append(tweet)
        
        # Save to file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(unique_data)} unique tweets to {OUTPUT_FILE}")
        
        # Also create a backup
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{OUTPUT_FILE}"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, indent=2, ensure_ascii=False)

    async def scrape_tweets(self):
        """Main scraping function"""
        try:
            await self.initialize_client()
            
            tweet_count = 0
            tweets = None
            consecutive_errors = 0
            max_consecutive_errors = 5
            
            logger.info(f"Starting to scrape tweets with query: '{QUERY}'")
            logger.info(f"Target: {MINIMUM_TWEETS} tweets")
            
            while tweet_count < MINIMUM_TWEETS:
                try:
                    tweets = await self.get_tweets_batch(tweets)
                    
                    if not tweets:
                        logger.warning("No more tweets found")
                        break
                    
                    batch_count = 0
                    for tweet in tweets:
                        tweet_data = self.extract_tweet_data(tweet)
                        if tweet_data:
                            self.tweet_data_list.append(tweet_data)
                            tweet_count += 1
                            batch_count += 1
                    
                    logger.info(f"Collected {batch_count} tweets (Total: {tweet_count}/{MINIMUM_TWEETS})")
                    
                    # Reset consecutive errors on success
                    consecutive_errors = 0
                    
                    # Save data periodically
                    if tweet_count % 50 == 0:
                        self.save_data()
                        logger.info(f"Intermediate save completed at {tweet_count} tweets")
                    
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error in batch processing (attempt {consecutive_errors}): {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Too many consecutive errors. Stopping.")
                        break
                    
                    # Wait before retrying
                    wait_time = min(60 * consecutive_errors, 300)  # Max 5 minutes
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
            
            # Final save
            self.save_data()
            
            logger.info(f"Scraping completed! Collected {tweet_count} tweets.")
            logger.info(f"Data saved to {OUTPUT_FILE}")
            
        except Exception as e:
            logger.error(f"Fatal error in scraping: {e}")
            # Save whatever data we have
            if self.tweet_data_list:
                self.save_data()
                logger.info("Saved partial data before exit")
            raise

async def main():
    """Main function"""
    scraper = TwitterScraper()
    
    try:
        await scraper.scrape_tweets()
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        if scraper.tweet_data_list:
            scraper.save_data()
            logger.info("Saved data before exit")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())