"""
JobPulse AI - Health Check and Service Verification
Polls backend (http://127.0.0.1:8000/health) and frontend (http://localhost:5173)
Records diagnostic logs to logs/run.log and tracks active PIDs in logs/pids.txt.
"""
import sys
import time
import urllib.request
import urllib.error
import os
import subprocess
from datetime import datetime

MAX_ATTEMPTS = 30
POLL_INTERVAL = 1.0

BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health"
FRONTEND_URL = "http://localhost:5173"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "run.log")
PID_FILE = os.path.join(LOG_DIR, "pids.txt")

def log_message(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def check_endpoint(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JobPulse-HealthMonitor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 304)
    except Exception:
        return False

def discover_pids():
    """Discover process IDs listening on ports 8000 and 5173 and save to pids.txt."""
    pids = {}
    try:
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        )
        for line in output.splitlines():
            line = line.strip()
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    addr = parts[1]
                    pid = parts[4]
                    if addr.endswith(":8000") and "backend" not in pids:
                        pids["backend"] = pid
                    elif addr.endswith(":5173") and "frontend" not in pids:
                        pids["frontend"] = pid
    except Exception:
        pass

    if pids:
        try:
            with open(PID_FILE, "w", encoding="utf-8") as f:
                for service, pid in pids.items():
                    f.write(f"{service}:{pid}\n")
            log_message(f"[INFO] Active service PIDs recorded: {pids}")
        except Exception:
            pass

def main():
    log_message("[HEALTH] Starting service health verification...")
    backend_ready = False
    frontend_ready = False

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if not backend_ready:
            backend_ready = check_endpoint(BACKEND_HEALTH_URL)
            if backend_ready:
                log_message(f"    [OK] Backend API is responsive at {BACKEND_HEALTH_URL}")

        if not frontend_ready:
            frontend_ready = check_endpoint(FRONTEND_URL)
            if frontend_ready:
                log_message(f"    [OK] Frontend UI is responsive at {FRONTEND_URL}")

        if backend_ready and frontend_ready:
            log_message("[HEALTH] [SUCCESS] All JobPulse AI services are active, healthy and ready.")
            discover_pids()
            return 0

        time.sleep(POLL_INTERVAL)

    # If timed out:
    log_message("[HEALTH] [TIMEOUT] Service startup verification timed out after 30 seconds.")
    if not backend_ready:
        log_message("    [FAIL] Backend did not respond at http://127.0.0.1:8000/health")
        log_message("           Check the 'JobPulse AI - Backend Server' console window for errors.")
    if not frontend_ready:
        log_message("    [FAIL] Frontend did not respond at http://localhost:5173")
        log_message("           Check the 'JobPulse AI - Frontend Server' console window for errors.")

    return 1

if __name__ == "__main__":
    sys.exit(main())
