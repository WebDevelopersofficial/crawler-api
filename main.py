import asyncio
import re
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, AnyHttpUrl, validator
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Web Crawler API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CrawlRequest(BaseModel):
    url: str
    respect_robots_txt: bool = False
    max_urls: int = 1000

    @validator('url')
    def validate_url(cls, v):
        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            return v
        except Exception:
            raise ValueError("Invalid URL format")

# Global variables to store crawl state
crawl_tasks = {}
crawl_results = {}

# File extensions to skip
SKIP_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
    '.css', '.js', '.ico', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov',
    '.flv', '.wmv', '.woff', '.woff2', '.ttf', '.eot'
}

def is_valid_url(url: str, base_domain: str) -> bool:
    """Check if URL is valid and belongs to the same domain."""
    try:
        parsed = urlparse(url)
        # Skip URLs with file extensions to ignore
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
            return False
        
        # Check if same domain (internal link)
        return parsed.netloc == base_domain and bool(parsed.scheme)
    except:
        return False

async def fetch_url(session: aiohttp.ClientSession, url: str) -> tuple:
    """Fetch URL and return content and status code."""
    try:
        async with session.get(url, allow_redirects=True, timeout=10) as response:
            if response.status == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                content = await response.text()
                return content, response.status
            return None, response.status
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None, 0

async def extract_links(html_content: str, base_url: str) -> List[str]:
    """Extract links from HTML content."""
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'lxml')
    base_domain = urlparse(base_url).netloc
    links = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        absolute_url = urljoin(base_url, href)
        
        if is_valid_url(absolute_url, base_domain):
            links.append(absolute_url)
    
    return links

async def crawl_site(url: str, respect_robots: bool, max_urls: int, task_id: str):
    """Crawl website starting from the given URL."""
    base_domain = urlparse(url).netloc
    discovered_urls = set()
    crawled_urls = set()
    queue = asyncio.Queue()
    
    # Add the initial URL
    await queue.put(url)
    discovered_urls.add(url)
    
    # Create a ClientSession that will be used for all requests
    async with aiohttp.ClientSession() as session:
        # Process URLs from the queue until it's empty or max_urls is reached
        while not queue.empty() and len(crawled_urls) < max_urls:
            # Process up to 5 URLs concurrently
            tasks = []
            for _ in range(min(5, queue.qsize())):
                if queue.empty():
                    break
                current_url = await queue.get()
                if current_url not in crawled_urls:
                    tasks.append(crawl_url(session, current_url, queue, discovered_urls, crawled_urls, base_domain, task_id))
            
            if tasks:
                await asyncio.gather(*tasks)
    
    # Mark crawl as complete
    crawl_results[task_id]["complete"] = True

async def crawl_url(session, url, queue, discovered_urls, crawled_urls, base_domain, task_id):
    """Crawl a single URL and add new URLs to the queue."""
    if url in crawled_urls:
        return
    
    # Add the URL to crawled set
    crawled_urls.add(url)
    
    # Fetch URL content
    content, status = await fetch_url(session, url)
    
    # Add result to crawl_results
    crawl_results[task_id]["urls"].append({
        "url": url,
        "status": status,
        "new": True
    })
    
    # Extract and process links
    if content:
        links = await extract_links(content, url)
        for link in links:
            if link not in discovered_urls and link not in crawled_urls:
                discovered_urls.add(link)
                await queue.put(link)
                
                # Add newly discovered URL to results
                crawl_results[task_id]["urls"].append({
                    "url": link,
                    "status": None,  # Not crawled yet
                    "new": True
                })

@app.post("/crawl")
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start a new crawl task and return task ID."""
    task_id = str(hash(f"{request.url}_{asyncio.get_event_loop().time()}"))
    
    # Initialize crawl results
    crawl_results[task_id] = {
        "urls": [],
        "complete": False
    }
    
    # Start crawling in the background
    background_tasks.add_task(
        crawl_site, 
        str(request.url), 
        request.respect_robots_txt, 
        request.max_urls, 
        task_id
    )
    
    return {"task_id": task_id, "message": "Crawl started"}

@app.get("/crawl/{task_id}/stream")
async def stream_results(task_id: str):
    """Stream crawl results as Server-Sent Events."""
    if task_id not in crawl_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    async def event_generator():
        # Send all current results
        sent_urls = set()
        while True:
            # Check if there are new URLs to send
            for url_data in crawl_results[task_id]["urls"]:
                url = url_data["url"]
                if url not in sent_urls:
                    sent_urls.add(url)
                    yield {"data": url_data}
            
            # Check if crawl is complete
            if crawl_results[task_id]["complete"] and len(sent_urls) == len(crawl_results[task_id]["urls"]):
                break
                
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
    
    return EventSourceResponse(event_generator())

@app.get("/crawl/{task_id}")
async def get_results(task_id: str):
    """Get all results from a crawl task."""
    if task_id not in crawl_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "urls": crawl_results[task_id]["urls"],
        "complete": crawl_results[task_id]["complete"],
        "count": len(crawl_results[task_id]["urls"])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 