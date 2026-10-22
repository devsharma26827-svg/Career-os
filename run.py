import os
import sys

# Ensure backend directory is in sys.path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_cloud = bool(os.environ.get("RENDER")) or bool(os.environ.get("PORT"))
    default_host = "0.0.0.0" if is_cloud else "127.0.0.1"
    host = os.environ.get("HOST", default_host)
    reload = os.environ.get("RELOAD", "false").lower() in ("true", "1") if is_cloud else False

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
