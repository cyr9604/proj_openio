#!/usr/bin/env bash
set -euo pipefail

GITEE_USER="meowfan"
PORT=8000
DATA_DIR="/opt/stock-analysis/data"
VERSION="1.0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    *) echo "Usage: $0 [--port 8000] [--data-dir /opt/stock-analysis/data] [--version 1.0]"; exit 1 ;;
  esac
done

if ! command -v docker &>/dev/null; then
  echo "Error: Docker not found. Install it first: https://docs.docker.com/engine/install/"
  exit 1
fi

# Required tools
for cmd in curl cat rm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: $cmd not found"
    exit 1
  fi
done

mkdir -p "$DATA_DIR"
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

BASE_URL="https://gitee.com/${GITEE_USER}/proj_openio/releases/download/${VERSION}"

echo "Downloading image parts from Gitee Releases ..."
for part in stock-analysis.tar.partaa stock-analysis.tar.partab stock-analysis.tar.partac; do
  url="${BASE_URL}/${part}"
  echo "  $url"
  curl -fsSL -o "$part" "$url" || {
    echo "Error: failed to download $part"
    exit 1
  }
done

echo "Combining parts ..."
cat stock-analysis.tar.part* > stock-analysis.tar
echo "Loading Docker image ..."
docker load -i stock-analysis.tar

cd /
rm -rf "$TMP_DIR"

if [[ ! -f "$DATA_DIR/config.json" ]]; then
  cat > "$DATA_DIR/config.json" <<-CONFIG
{
  "priority": ["ths_http", "ths_sdk", "sina", "akshare"],
  "ths_http_token": "",
  "ths_http_refresh_token": "",
  "ths_sdk_enabled": false,
  "default_adjust": "forward"
}
CONFIG
  echo "Created default config.json"
fi

docker rm -f stock-analysis 2>/dev/null || true

echo "Starting container on port $PORT ..."
docker run -d \
  --name stock-analysis \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -v "$DATA_DIR/stock_analysis.db:/app/backend/stock_analysis.db" \
  -v "$DATA_DIR/config.json:/app/backend/config.json" \
  -v "$DATA_DIR/symbol_cache.json:/app/backend/symbol_cache.json" \
  stock-analysis:latest

echo "Done! Visit http://localhost:${PORT}"
