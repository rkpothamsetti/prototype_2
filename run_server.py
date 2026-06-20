"""Run Nigha AI API server."""
import uvicorn

from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=False,
    )
