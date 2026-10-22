"""Local real-app server; use uv --env-file .env to supply private configuration."""

import os
from urllib.parse import urlsplit
import uvicorn
from torob.api import create_app

if __name__ == "__main__":
    origin = urlsplit(os.environ["PUBLIC_ORIGIN"])
    if origin.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("This helper binds loopback only")
    uvicorn.run(create_app(), host="127.0.0.1", port=origin.port or 8651, log_level="warning")
