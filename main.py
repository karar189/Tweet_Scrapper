from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import requests
import logging
from fastapi.middleware.cors import CORSMiddleware
import time

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

class TrendingTopic(BaseModel):
    challenge: str
    reason: str

class TrendingResponse(BaseModel):
    status: str
    data: List[TrendingTopic]
    message: Optional[str] = None

trends_cache = {
    'data': None,
    'last_updated': 0
}

CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)

def get_twitter_trends():
    """Fetch trending topics from Twitter."""
    try:
        # Twitter API endpoint and configuration
        url = "https://api.twitter.com/1.1/trends/place.json"
        woeid = "1"  # Worldwide trends
        
        headers = {
            'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
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
                for trend in trends[:3]:  # Get top 3 trends
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

@app.get("/trending", response_model=TrendingResponse)
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
