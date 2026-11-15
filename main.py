"""
ASTRAQUANT X / MIRAI — Top-Level Application Entrypoint
Exposes the FastAPI application instance for ASGI servers and cloud runtimes.
"""

from src.api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
