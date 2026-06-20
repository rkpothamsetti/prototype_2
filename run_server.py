"""Run Nigha AI API server."""
import os

import uvicorn

from config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.api_port))
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
