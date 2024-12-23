from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import requests
import logging
from fastapi.middleware.cors import CORSMiddleware
import time
from dotenv import load_dotenv
import os
import uvicorn

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load .env file
load_dotenv()

# Accessing variables
twitter_api_key = os.getenv('TWITTER_API_KEY')
google_api_key = os.getenv('GOOGLE_API_KEY')
api_port = os.getenv('PORT')

#Setting up port
if __name__ == "__main__":
    uvicorn.run("filename:app", host="0.0.0.0", port={api_port}, reload=True)

class TrendingTopic(BaseModel):
    challenge: str
    reason: str

class RedditTrend(BaseModel):
    challenge: str
    reason: str
    subreddit: str
    upvotes: int

class TrendingResponse(BaseModel):
    status: str
    data: List[TrendingTopic]
    message: Optional[str] = None

class RedditTrendingResponse(BaseModel):
    status: str
    data: List[RedditTrend]
    message: Optional[str] = None

# General caches
trends_cache = {
    'data': None,
    'last_updated': 0
}

reddit_cache = {
    'data': None,
    'last_updated': 0
}

# Dedicated Web3 caches
web3_twitter_cache = {
    'data': None,
    'last_updated': 0
}

web3_reddit_cache = {
    'data': None,
    'last_updated': 0
}

CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)
WEB3_KEYWORDS = ["#web3", "#crypto", "#nft"]
WEB3_4CHAN_BOARDS = ["g", "biz"]

def get_twitter_trends():
    """Fetch trending topics from Twitter."""
    try:
        # Twitter API endpoint and configuration
        url = "https://api.twitter.com/1.1/trends/place.json"
        woeid = "1" 

        headers = {
            'Authorization': f'Bearer {twitter_api_key}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://twitter.com',
            'Referer': 'https://twitter.com/',
        }

        # Step 1: Get the guest token
        guest_token_url = "https://api.twitter.com/1.1/guest/activate.json"
        guest_response = requests.post(guest_token_url, headers=headers)
        if guest_response.status_code == 200:
            guest_token = guest_response.json().get('guest_token')
            headers['x-guest-token'] = guest_token
        else:
            logger.error("Failed to get guest token")
            raise HTTPException(status_code=500, detail="Unable to authenticate with Twitter")

        # Step 2: Fetch trends using the token
        logger.debug("Fetching Twitter trends...")
        response = requests.get(f"{url}?id={woeid}", headers=headers)
        logger.debug(f"Response status code: {response.status_code}")

        if response.status_code == 200:
            trends_data = response.json()
            trending_items = []

            if trends_data and len(trends_data) > 0:
                trends = trends_data[0].get('trends', [])
                for trend in trends[:5]:  # Get top 5 trends
                    name = trend.get('name', 'No Name')
                    volume = trend.get('tweet_volume', 'N/A')
                    trending_items.append({
                        "challenge": name,
                        "reason": f"Tweet Volume: {volume}"
                    })
            return trending_items
        else:
            logger.error(f"Error fetching trends: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Unable to fetch trends from Twitter")

    except Exception as e:
        logger.exception("An error occurred while fetching Twitter trends")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_twitter_web3_trends():
    """Fetch Web3-specific trending topics from Twitter."""
    try:
        url = "https://api.twitter.com/1.1/trends/place.json"
        woeid = "1"  # Worldwide trends

        headers = {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://twitter.com',
            'Referer': 'https://twitter.com/',
        }

        guest_token_url = "https://api.twitter.com/1.1/guest/activate.json"
        guest_response = requests.post(guest_token_url, headers=headers)
        if guest_response.status_code == 200:
            guest_token = guest_response.json().get('guest_token')
            headers['x-guest-token'] = guest_token
        else:
            logger.error("Failed to get guest token")
            raise HTTPException(status_code=500, detail="Unable to authenticate with Twitter")

        logger.debug("Fetching Twitter Web3 trends...")
        response = requests.get(f"{url}?id={woeid}", headers=headers)

        if response.status_code == 200:
            trends_data = response.json()
            web3_items = []

            if trends_data and len(trends_data) > 0:
                trends = trends_data[0].get('trends', [])
                for trend in trends:
                    name = trend.get('name', 'No Name')
                    if any(keyword.lower() in name.lower() for keyword in WEB3_KEYWORDS):
                        volume = trend.get('tweet_volume', 'N/A')
                        web3_items.append({
                            "challenge": name,
                            "reason": f"Tweet Volume: {volume}"
                        })
            return web3_items
        else:
            logger.error(f"Error fetching Web3 trends: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Unable to fetch Web3 trends from Twitter")

    except Exception as e:
        logger.exception("An error occurred while fetching Twitter Web3 trends")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_reddit_trends():
    """Fetch trending topics from Reddit."""
    try:
        url = "https://www.reddit.com/r/all/hot.json"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        logger.debug("Fetching Reddit trends...")
        response = requests.get(url, headers=headers)
        logger.debug(f"Response status code: {response.status_code}")

        if response.status_code == 200:
            trends_data = response.json()
            trending_items = []

            posts = trends_data.get('data', {}).get('children', [])
            for post in posts[:5]:  # Get top 5 trending posts
                post_data = post.get('data', {})
                trending_items.append(
                    RedditTrend(
                        challenge=post_data.get('title', 'No Title'),
                        reason=post_data.get('selftext', '')[:100] + '...' if post_data.get('selftext') else 'No description',
                        subreddit=post_data.get('subreddit_name_prefixed', 'r/unknown'),
                        upvotes=post_data.get('ups', 0)
                    )
                )
            return trending_items
        else:
            logger.error(f"Error fetching Reddit trends: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Unable to fetch trends from Reddit")

    except Exception as e:
        logger.exception("An error occurred while fetching Reddit trends")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_reddit_web3_trends():
    """Fetch Web3-specific trending topics from Reddit."""
    try:
        web3_subreddits = ["cryptocurrency", "web3", "nft", "bitcoin", "ethereum"]
        trending_items = []

        for subreddit in web3_subreddits:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=3"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                posts = response.json().get('data', {}).get('children', [])
                for post in posts:
                    post_data = post.get('data', {})
                    
                    # Extract relevant information
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')
                    upvotes = post_data.get('ups', 0)
                    subreddit_name = post_data.get('subreddit_name_prefixed', 'r/unknown')
                    url = post_data.get('url', '')
                    author = post_data.get('author', 'unknown')
                    
                    # Create a more informative reason field
                    reason = f"Posted in {subreddit_name} by u/{author} | {upvotes} upvotes"
                    if selftext:
                        # Add truncated selftext if available
                        truncated_text = selftext[:100] + ('...' if len(selftext) > 100 else '')
                        reason += f"\nContent: {truncated_text}"
                    elif url and not url.endswith('.json'):
                        # Add URL if no selftext and URL is not the API endpoint
                        reason += f"\nLink: {url}"

                    trending_items.append(
                        RedditTrend(
                            challenge=title,
                            reason=reason,
                            subreddit=subreddit_name,
                            upvotes=upvotes
                        )
                    )

            logger.debug(f"Fetched {len(posts)} posts from {subreddit}")

        # Sort trending items by upvotes to show most popular first
        trending_items.sort(key=lambda x: x.upvotes, reverse=True)

        return trending_items
    except Exception as e:
        logger.exception("An error occurred while fetching Reddit Web3 trends")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/trending-tweeter", response_model=TrendingResponse)
def fetch_trending_topics():
    """Fetch and return trending topics."""
    current_time = time.time()

    # Serve from cache if not expired
    if trends_cache['data'] and (current_time - trends_cache['last_updated'] < CACHE_DURATION):
        logger.info("Serving trends from cache")
        return TrendingResponse(
            status="success",
            data=trends_cache['data'],
            message="Served from cache"
        )

    # Fetch new trends if cache is expired
    logger.info("Fetching new trends from Twitter API")
    trends = get_twitter_trends()
    trends_cache['data'] = trends
    trends_cache['last_updated'] = current_time

    return TrendingResponse(
        status="success",
        data=trends,
        message="Fetched from Twitter API"
    )

@app.get("/trending-reddit", response_model=RedditTrendingResponse)
def fetch_reddit_trending():
    """Fetch and return trending topics from Reddit."""
    current_time = time.time()

    # Serve from cache if not expired
    if reddit_cache['data'] and (current_time - reddit_cache['last_updated'] < CACHE_DURATION):
        logger.info("Serving Reddit trends from cache")
        return RedditTrendingResponse(
            status="success",
            data=reddit_cache['data'],
            message="Served from cache"
        )

    # Fetch new trends if cache is expired
    logger.info("Fetching new trends from Reddit API")
    trends = get_reddit_trends()
    reddit_cache['data'] = trends
    reddit_cache['last_updated'] = current_time

    return RedditTrendingResponse(
        status="success",
        data=trends,
        message="Fetched from Reddit API"
    )

@app.get("/trending-tweeter/web3", response_model=TrendingResponse)
def fetch_web3_topics():
    """Fetch and return Web3-related trending topics from Twitter."""
    current_time = time.time()
    
    logger.info("Fetching new Web3 trends from Twitter API")
    try:
        trends = get_twitter_web3_trends()
        web3_twitter_cache['data'] = trends
        web3_twitter_cache['last_updated'] = current_time

        return TrendingResponse(
            status="success",
            data=trends,
            message="Fetched Web3 trends from Twitter API"
        )
    except Exception as e:
        logger.exception("Unexpected error while fetching Web3 topics")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/trending-reddit/web3", response_model=RedditTrendingResponse)
def fetch_reddit_web3_topics():
    """Fetch and return Web3-related trending topics from Reddit."""
    current_time = time.time()
    
    logger.info("Fetching new Web3 trends from Reddit API")
    try:
        trends = get_reddit_web3_trends()
        web3_reddit_cache['data'] = trends
        web3_reddit_cache['last_updated'] = current_time

        return RedditTrendingResponse(
            status="success",
            data=trends,
            message=f"Fetched {len(trends)} Web3 trends from Reddit subreddits"
        )
    except Exception as e:
        logger.exception("Unexpected error while fetching Reddit Web3 topics")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# New Google Trends Controller
class GoogleTrend(BaseModel):
    title: str
    link: str
    snippet: str

class GoogleTrendingResponse(BaseModel):
    status: str
    data: List[GoogleTrend]
    message: Optional[str] = None

@app.get("/trending-google/web3", response_model=GoogleTrendingResponse)
def get_google_web3_trends():
    """Fetch latest Web3 trends or news from Google."""
    try:
        # Google News API or scraping configuration
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "Web3",
            "sortBy": "publishedAt",
            "apiKey": {google_api_key},  # Replace with your API key
            "pageSize": 5,  # Fetch top 5 news articles
        }

        logger.debug("Fetching Web3 trends from Google News...")
        response = requests.get(url, params=params)

        if response.status_code == 200:
            news_data = response.json()
            articles = news_data.get("articles", [])
            google_trends = [
                {
                    "title": article["title"],
                    "link": article["url"],
                    "snippet": article["description"] or "No description available",
                }
                for article in articles
            ]

            return {
                "status": "success",
                "data": google_trends,
                "message": f"Fetched {len(google_trends)} Web3 news articles.",
            }
        else:
            logger.error(f"Google News API error: {response.status_code} {response.text}")
            raise HTTPException(status_code=500, detail="Failed to fetch Google Web3 trends")
    except Exception as e:
        logger.exception("Exception occurred while fetching Google Web3 trends.")
        raise HTTPException(status_code=500, detail=str(e))




# Function to fetch Web3-related threads from 4chan
def get_4chan_web3_trends():
    """Fetch Web3-related posts from 4chan."""
    try:
        # 4chan API endpoint for /g/ (technology) or /biz/ (business) board
        board_url = "https://a.4cdn.org/g/catalog.json"  # Change to /biz/ for business-related content
        response = requests.get(board_url)

        if response.status_code == 200:
            threads_data = response.json()
            web3_threads = []

            # Iterate through threads and filter for Web3-related topics
            for page in threads_data:
                for thread in page.get('threads', []):
                    subject = thread.get('subject', '')
                    if any(keyword in subject.lower() for keyword in WEB3_4CHAN_BOARDS):
                        web3_threads.append({
                            "challenge": subject,
                            "reason": f"Replies: {thread.get('replies', 0)}"
                        })

            return web3_threads
        else:
            logger.error(f"Error fetching 4chan threads: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Unable to fetch trends from 4chan")

    except Exception as e:
        logger.exception("An error occurred while fetching 4chan Web3 trends")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Function to fetch Web3-related threads from 4chan
def get_4chan_web3_trends():
    """Fetch Web3-related posts from 4chan."""
    try:
        board_url = "https://a.4cdn.org/g/catalog.json"  # Change to /biz/ for business-related content
        response = requests.get(board_url)

        if response.status_code == 200:
            threads_data = response.json()
            web3_threads = []

            # Iterate through threads and filter for Web3-related topics
            for page in threads_data:
                for thread in page.get('threads', []):
                    subject = thread.get('subject', '')
                    if any(keyword in subject.lower() for keyword in WEB3_KEYWORDS):
                        # Extracting the necessary information
                        web3_threads.append({
                            "challenge": subject,
                            "reason": f"Replies: {thread.get('replies', 0)}"
                        })

            if not web3_threads:
                return [{"challenge": "No Web3-related threads found", "reason": "N/A"}]
            
            return web3_threads
        else:
            logger.error(f"Error fetching 4chan threads: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Unable to fetch trends from 4chan")

    except Exception as e:
        logger.exception("An error occurred while fetching 4chan Web3 trends")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Endpoint for 4chan Web3 trends
@app.get("/trending-4chan/web3", response_model=TrendingResponse)
async def trending_4chan_web3():
    """Fetch Web3-related trends from 4chan."""
    try:
        # Fetch the Web3 trends from 4chan
        trends = get_4chan_web3_trends()
        
        # Return the response
        return TrendingResponse(status="success", data=trends)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("An error occurred while fetching 4chan Web3 trends")
        raise HTTPException(status_code=500, detail="Failed to fetch 4chan Web3 trends")