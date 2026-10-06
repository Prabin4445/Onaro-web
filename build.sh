#!/bin/bash
# Cloudflare Pages build: copy site files to dist/, excluding .git and non-deploy files.
# Set Pages "Build command" to: bash build.sh
# Set Pages "Build output directory" to: dist
set -e
rm -rf dist
mkdir -p dist
# Copy everything except dist itself, .git, qa, and non-deploy files
# Use tar to avoid recursive copy issue (dist/ is inside source dir)
tar cf - --exclude='./dist' --exclude='./.git' --exclude='./qa' --exclude='./icons/raw' \
  --exclude='./data/degrees/*.json' --exclude='./data/faculty' \
  --exclude='./data/degrees/__pycache__' --exclude='./build.sh' . | (cd dist && tar xf -)
echo "Built dist/ with $(find dist -type f | wc -l) files"
