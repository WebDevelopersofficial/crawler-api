import json
import asyncio
import sys
import aiohttp

async def start_crawl(session, url):
    """Start a new crawl task."""
    async with session.post(
        "http://localhost:8000/crawl",
        json={"url": url, "max_urls": 100}
    ) as response:
        if response.status == 200:
            result = await response.json()
            return result["task_id"]
        else:
            print(f"Error starting crawl: {response.status}")
            return None

async def stream_results(session, task_id):
    """Stream results from the crawl task."""
    try:
        async with session.get(f"http://localhost:8000/crawl/{task_id}/stream") as response:
            if response.status != 200:
                print(f"Error streaming results: {response.status}")
                return
            
            # Process the SSE stream
            count = 0
            async for line in response.content:
                line = line.decode('utf-8').strip()
                
                if line.startswith('data:'):
                    try:
                        data = json.loads(line[5:])
                        print(f"URL: {data.get('url')} | Status: {data.get('status')}")
                        count += 1
                    except json.JSONDecodeError:
                        print(f"Error parsing JSON: {line[5:]}")
            
            print(f"\nTotal URLs found: {count}")
    except Exception as e:
        print(f"Error during streaming: {str(e)}")

async def main():
    """Main function to run the example client."""
    if len(sys.argv) < 2:
        print("Usage: python example_client.py <url>")
        return
    
    url = sys.argv[1]
    print(f"Starting crawl for {url}...")
    
    async with aiohttp.ClientSession() as session:
        task_id = await start_crawl(session, url)
        if task_id:
            print(f"Crawl started with task ID: {task_id}")
            print("Streaming results:")
            await stream_results(session, task_id)
        else:
            print("Failed to start crawl.")

if __name__ == "__main__":
    asyncio.run(main()) 