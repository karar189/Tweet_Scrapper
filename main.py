from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import requests
import logging
from fastapi.middleware.cors import CORSMiddleware
import time

# Enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models for the API responses
class TrendingTopic(BaseModel):
    challenge: str
    reason: str

class Meme(BaseModel):
    title: str
    url: str

class TrendingResponse(BaseModel):
    status: str
    data: List[TrendingTopic]
    message: Optional[str] = None

class MemesResponse(BaseModel):
    status: str
    memes: List[Meme]
    message: Optional[str] = None

# Cache for storing trends and memes
cache = {
    'trends': {'data': None, 'last_updated': 0},
    'memes': {'data': None, 'last_updated': 0},
}

CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)

def get_twitter_trends():
    """Fetch trending topics from Twitter."""
    try:
        # Twitter API endpoint and configuration
        url = "https://api.twitter.com/1.1/trends/place.json"
        woeid = "1"  # Worldwide trends
        
        headers = {
            'Authorization': 'Bearer YOUR_TWITTER_BEARER_TOKEN',
        }

        logger.debug("Fetching Twitter trends...")
        response = requests.get(f"{url}?id={woeid}", headers=headers)
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

def get_trending_memes():
    """Fetch trending memes from a public memes API."""
    try:
        logger.debug("Fetching trending memes...")
        url = "https://api.imgflip.com/get_memes"
        response = requests.get(url)
        if response.status_code == 200:
            memes_data = response.json()
            if memes_data.get('success'):
                memes = memes_data['data']['memes']
                return [
                    {"title": meme['name'], "url": meme['url']}
                    for meme in memes[:5]  # Limit to top 5 memes
                ]
            else:
                logger.error("Memes API did not return success")
                raise HTTPException(status_code=500, detail="Memes API error")
        else:
            logger.error(f"Error fetching memes: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Unable to fetch memes")
    except Exception as e:
        logger.exception("An error occurred while fetching memes")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/trending", response_model=TrendingResponse)
def fetch_trending_topics():
    """Fetch and return trending topics."""
    current_time = time.time()

    # Serve from cache if not expired
    if cache['trends']['data'] and (current_time - cache['trends']['last_updated'] < CACHE_DURATION):
        logger.info("Serving trends from cache")
        return TrendingResponse(
            status="success",
            data=cache['trends']['data'],
            message="Served from cache"
        )

    # Fetch new trends if cache is expired
    logger.info("Fetching new trends from Twitter API")
    trends = get_twitter_trends()
    cache['trends']['data'] = trends
    cache['trends']['last_updated'] = current_time

    return TrendingResponse(
        status="success",
        data=trends,
        message="Fetched from Twitter API"
    )

@app.get("/memes", response_model=MemesResponse)
def fetch_trending_memes():
    """Fetch and return trending memes."""
    current_time = time.time()

    # Serve from cache if not expired
    if cache['memes']['data'] and (current_time - cache['memes']['last_updated'] < CACHE_DURATION):
        logger.info("Serving memes from cache")
        return MemesResponse(
            status="success",
            memes=cache['memes']['data'],
            message="Served from cache"
        )

    # Fetch new memes if cache is expired
    logger.info("Fetching new memes from Memes API")
    memes = get_trending_memes()
    cache['memes']['data'] = memes
    cache['memes']['last_updated'] = current_time

    return MemesResponse(
        status="success",
        memes=memes,
        message="Fetched from Memes API"
    )
