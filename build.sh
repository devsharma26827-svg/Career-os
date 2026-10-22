#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "=========================================="
echo " Starting JobPulse AI Render Build"
echo "=========================================="

echo "Step 1: Installing backend Python dependencies..."
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

echo "Step 2: Installing frontend dependencies..."
npm --prefix "New Frontend" install

echo "Step 3: Building React production bundle..."
npm --prefix "New Frontend" run build

echo "Step 4: Verifying frontend distribution..."
if [ -f "New Frontend/dist/index.html" ]; then
    echo "Frontend build successfully generated at 'New Frontend/dist/'"
else
    echo "Error: index.html not found in 'New Frontend/dist/'"
    exit 1
fi

echo "=========================================="
echo " Build Completed Successfully!"
echo "=========================================="
