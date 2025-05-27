from main import app

# This file needs to properly expose the ASGI application for Gunicorn to use
# We need to create a proper ASGI application instance

# Import the ASGI middleware for compatibility with Gunicorn
from uvicorn.middleware.asgi_wsgi import ASGIMiddleware

# Create a WSGI-compatible version of the ASGI application
application = ASGIMiddleware(app)

# This file is just a wrapper to make Render.com happy
# It expects app.py with 'app' variable by default 