#!/bin/bash
# Cloudflare Pages build: copy site files to dist/, excluding .git and non-deploy files.
# Set Pages "Build command" to: bash build.sh
# Set Pages "Build output directory" to: dist
set -e
rm -rf dist
mkdir -p dist
# Copy everything, then remove excluded paths (no rsync in Pages build env)
cp -a . dist/
rm -rf dist/.git dist/qa dist/icons/raw dist/build.sh
rm -f dist/data/degrees/*.json
rm -rf dist/data/faculty dist/data/degrees/__pycache__
echo "Built dist/ with $(find dist -type f | wc -l) files"
