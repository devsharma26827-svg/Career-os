import os
import sys

# Ensure backend directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app, resolve_frontend_dist

def verify():
    print("=" * 60)
    print(" Verifying Single-Service Render Configuration")
    print("=" * 60)

    # 1. Check frontend_dist resolution
    dist = resolve_frontend_dist()
    print(f"1. Frontend dist directory: {dist}")
    assert dist is not None, "Failed to resolve frontend dist directory"
    assert os.path.isdir(dist), f"Dist directory does not exist: {dist}"
    assert os.path.isfile(os.path.join(dist, "index.html")), "index.html not found in dist"
    print("   [PASS] Frontend dist and index.html verified.")

    client = TestClient(app)

    # 2. Check Root Route (/) serves React index.html
    root_res = client.get("/")
    assert root_res.status_code == 200, f"Expected 200 on /, got {root_res.status_code}"
    assert "<!doctype html>" in root_res.text.lower() or "<html" in root_res.text.lower(), "Root did not return HTML"
    assert '<div id="root">' in root_res.text, "Root HTML missing React #root div"
    print("   [PASS] GET / correctly serves React index.html.")

    # 3. Check /health returns JSON ok
    health_res = client.get("/health")
    assert health_res.status_code == 200, f"Expected 200 on /health, got {health_res.status_code}"
    assert health_res.json() == {"status": "ok"}, f"Expected ok status, got {health_res.json()}"
    print("   [PASS] GET /health returns {'status': 'ok'}.")

    # 4. Check /docs returns 200
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200, f"Expected 200 on /docs, got {docs_res.status_code}"
    assert "swagger" in docs_res.text.lower(), "Docs page missing Swagger content"
    print("   [PASS] GET /docs serves Swagger UI.")

    # 5. Check /redoc returns 200
    redoc_res = client.get("/redoc")
    assert redoc_res.status_code == 200, f"Expected 200 on /redoc, got {redoc_res.status_code}"
    print("   [PASS] GET /redoc serves ReDoc UI.")

    # 6. Check /openapi.json returns 200 OpenAPI schema
    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200, f"Expected 200 on /openapi.json, got {openapi_res.status_code}"
    assert "openapi" in openapi_res.json(), "Invalid OpenAPI JSON schema"
    print("   [PASS] GET /openapi.json returns OpenAPI JSON.")

    # 7. Check valid API route /api/v1/jobs/locations
    loc_res = client.get("/api/v1/jobs/locations")
    assert loc_res.status_code == 200, f"Expected 200 on API route, got {loc_res.status_code}"
    assert isinstance(loc_res.json(), list), "Expected list of locations"
    print("   [PASS] GET /api/v1/jobs/locations returns API data.")

    # 8. Check invalid API route returns 404 JSON, NOT HTML!
    invalid_api_res = client.get("/api/v1/nonexistent_test_route_404")
    assert invalid_api_res.status_code == 404, f"Expected 404, got {invalid_api_res.status_code}"
    assert "html" not in invalid_api_res.headers.get("content-type", ""), "API 404 must NOT return HTML"
    assert invalid_api_res.json() == {"detail": "Not Found"}, f"Expected Not Found detail, got {invalid_api_res.json()}"
    print("   [PASS] Invalid API routes strictly return 404 JSON (no HTML fallback).")

    # 9. Check React SPA fallback routes
    for spa_path in ["/dashboard", "/applications", "/saved-jobs", "/insights", "/interview-prep"]:
        spa_res = client.get(spa_path)
        assert spa_res.status_code == 200, f"Expected 200 on SPA route {spa_path}, got {spa_res.status_code}"
        assert '<div id="root">' in spa_res.text, f"SPA route {spa_path} did not return index.html"
        print(f"   [PASS] SPA Route {spa_path} correctly serves React index.html.")

    # 10. Check static asset serving
    assets_dir = os.path.join(dist, "assets")
    if os.path.isdir(assets_dir):
        files = os.listdir(assets_dir)
        if files:
            sample_asset = files[0]
            asset_res = client.get(f"/assets/{sample_asset}")
            assert asset_res.status_code == 200, f"Failed to fetch asset /assets/{sample_asset}"
            print(f"   [PASS] Static asset /assets/{sample_asset} served successfully.")

    print("=" * 60)
    print(" ALL SINGLE-SERVICE RENDER CHECKS VERIFIED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    verify()
