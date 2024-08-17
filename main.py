from fastapi import FastAPI, HTTPException, Query
import httpx
from cachetools import TTLCache
from cachetools.keys import hashkey
import logging

app = FastAPI()

# Initialize cache (TTL of 10 minutes)
cache = TTLCache(maxsize=100, ttl=600)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

async def fetch_hacker_news_top_items(num_items: int):
    async with httpx.AsyncClient() as client:
        top_story_ids = await client.get(HN_TOP_STORIES_URL)
        if top_story_ids.status_code != 200:
            raise HTTPException(status_code=top_story_ids.status_code, detail="Failed to fetch top stories")
        
        top_story_ids = top_story_ids.json()[:num_items]

        # Fetch each story details
        stories = []
        for story_id in top_story_ids:
            story_url = HN_ITEM_URL.format(item_id=story_id)
            story_resp = await client.get(story_url)
            if story_resp.status_code == 200:
                stories.append(story_resp.json())
        return stories

@app.get("/top-news/")
async def get_top_news(num_items: int = Query(10, alias="num")):
    cache_key = hashkey(num_items)
    if cache_key in cache:
        logger.info(f"Returning cached result for {num_items} items")
        return cache[cache_key]

    try:
        top_news = await fetch_hacker_news_top_items(num_items)
        cache[cache_key] = top_news
        logger.info(f"Fetched and cached top {num_items} items")
        return top_news
    except Exception as e:
        logger.error(f"Failed to fetch top news: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching top news")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
