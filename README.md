# Twitter Scraper

A Python-based Twitter scraper built with `twikit` that collects tweets based on specific search criteria for AI/sentiment analysis.

## Features

- Scrapes tweets based on customizable search queries
- Handles rate limiting and authentication automatically
- Saves data in JSON format with backup functionality
- Extracts minimal tweet data (username, text, likes) for analysis
- Robust error handling and retry logic

## Setup

### Prerequisites

- Python 3.7+
- A Twitter account

### Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd twitterscrapper-1
```

2. Install required packages:
```bash
pip install twikit
```

3. Set up your Twitter credentials:
```bash
cp config.ini.template config.ini
```

4. Edit `config.ini` with your Twitter credentials:
```ini
[X]
username = your_twitter_username
password = your_twitter_password
email = your_email@example.com
```

## Usage

### Basic Scraping

Run the main scraper:
```bash
python twitterscrap.py
```

The scraper will:
- Authenticate with Twitter using your credentials
- Search for tweets matching the configured query
- Save results to JSON files with automatic backups
- Handle rate limiting automatically

### Configuration

You can modify the search parameters in `twitterscrap.py`:

```python
MINIMUM_TWEETS = 50  # Target number of tweets to collect
QUERY = '(ai) min_faves:100 since:2025-5-10 -filter:links -filter:replies'
OUTPUT_FILE = 'buildinpublicbest.json'
```

### Output

The scraper generates:
- Main output file (e.g., `buildinpublicbest.json`)
- Automatic timestamped backups
- Log files for debugging

## Files

- `twitterscrap.py` - Main scraper implementation
- `main.py` - Alternative scraper version
- `config.ini.template` - Template for Twitter credentials
- `config.ini` - Your actual credentials (not included in repo)
- `cookies.json` - Authentication cookies (not included in repo)

## Security

⚠️ **Important**: Never commit your `config.ini` or `cookies.json` files to version control as they contain sensitive authentication data.

## License

This project is for educational purposes. Please respect Twitter's Terms of Service and rate limits. 