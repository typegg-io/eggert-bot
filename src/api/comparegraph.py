import urllib.parse
import aiohttp
from config import API_URL

async def fetch_comparison_data(user1_id: str, user2_id: str, metric: str):
    url = f"{API_URL}/compare?firstUser={urllib.parse.quote(user1_id)}&secondUser={urllib.parse.quote(user2_id)}&metric={metric}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"API returned status {response.status}"}
