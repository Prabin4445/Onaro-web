#!/bin/bash
# Cloudflare Pages build: copy site files to dist/, excluding .git, qa, and other non-deploy files.
# Set Pages "Build command" to: bash build.sh
# Set Pages "Build output directory" to: dist
set -e
rm -rf dist
mkdir -p dist
# Copy everything except .git, qa, and build artifacts
rsync -a --exclude='.git' --exclude='qa' --exclude='icons/raw' \
  --exclude='data/degrees/*.json' --exclude='data/faculty' \
  --exclude='data/degrees/__pycache__' --exclude='build.sh' \
  ./ dist/
echo "Built dist/ with $(find dist -type f | wc -l) files"
