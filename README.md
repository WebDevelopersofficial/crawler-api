# Web Crawler API

A FastAPI-based web crawler that works as an API service to crawl an entire website and return all discovered URLs, similar to premium sitemap generators.

## Features

- Recursively crawls entire websites
- Returns only internal links (same domain)
- Avoids duplicate URLs
- Optional robots.txt respect
- Skips common file extensions (.jpg, .png, .css, .js, etc.)
- Follows redirects
- Uses async crawling for speed
- Real-time streaming of results
- Simple JSON API

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the API

Start the FastAPI server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Start a Crawl

`POST /crawl`

Request body:

```json
{
  "url": "https://example.com",
  "respect_robots_txt": false,
  "max_urls": 1000
}
```

Response:

```json
{
  "task_id": "123456789",
  "message": "Crawl started"
}
```

### Stream Results

`GET /crawl/{task_id}/stream`

This endpoint returns Server-Sent Events (SSE) with real-time crawl results.

Each event has the format:

```json
{
  "url": "https://example.com/about",
  "status": 200,
  "new": true
}
```

### Get All Results

`GET /crawl/{task_id}`

Returns all results from a crawl task.

## Testing with Postman

1. To start a crawl, send a POST request to `/crawl` with a JSON body containing the URL.
2. To stream results, use the "EventSource" feature in Postman and connect to `/crawl/{task_id}/stream`.

## Deploying to Render.com

This application is ready to be deployed to Render.com:

1. Push your code to a Git repository
2. Create a new Web Service in Render
3. Connect your repository
4. Set the build command to `pip install -r requirements.txt`
5. Set the start command to `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy! 