import asyncio
import httpx
import time
import argparse
import logging
from typing import Optional
from datetime import datetime

logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def rate_limited_request(
    url: str, 
    client: httpx.AsyncClient, 
    start_time: float,
    period: float
) -> None:
    next_request_time = time.time()
    
    while True:
        scheduled_time = next_request_time
        
        now = time.time()
        if now < scheduled_time:
            await asyncio.sleep(scheduled_time - now)
        
        actual_start = time.time()
        try:
            response = await client.get(url)
            end_time = time.time()
            relative_time = round(scheduled_time - start_time, 3)
            response_time = round(end_time - actual_start, 3)
            
            logger.info(
                f"time:{relative_time}, "
                f"query:{url}, response_time:{response_time}, "
                f"response_code:{response.status_code}"
            )
                
        except Exception as e:
            relative_time = round(scheduled_time - start_time, 3)
            logger.error(
                f"time:{relative_time}, query:{url}, error:{str(e)}"
            )
        
        next_request_time = scheduled_time + period

async def main(duration_seconds: Optional[int] = None, period: float = 1.0):
    urls = [
        f"http://localhost:8011/wines/recommendations?query={i}" for i in range(10)
    ]
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(
                rate_limited_request(urls[i], client, start_time, period)
            )
            for i in range(len(urls))
        ]
        
        if duration_seconds:
            await asyncio.sleep(duration_seconds)
            for task in tasks:
                task.cancel()
            
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                pass
        else:
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run rate-limited parallel HTTP requests')
    parser.add_argument('--duration', type=int, help='Duration to run in seconds', default=None)
    parser.add_argument('--period', type=float, help='Time between requests in seconds', default=1.0)
    args = parser.parse_args()
    
    asyncio.run(main(args.duration, args.period))