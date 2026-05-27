#!/usr/bin/env bash
set -euo pipefail

REPO="crpi-m1pdy3u1ypkkbct5.cn-hangzhou.personal.cr.aliyuncs.com/opencode_meowfan/stock-analysis"
PORT=8000
DATA_DIR="/opt/stock-analysis/data"
VERSION="latest"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    *) echo "Usage: $0 [--port 8000] [--data-dir /opt/stock-analysis/data] [--version latest]"; exit 1 ;;
  esac
done

if ! command -v docker &>/dev/null; then
  echo "Error: Docker not found. Install it first: https://docs.docker.com/engine/install/"
  exit 1
fi

mkdir -p "$DATA_DIR"

echo "Pulling image ${REPO}:${VERSION} ..."
docker pull "${REPO}:${VERSION}"

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

# Ensure mounted files exist (Docker bind mount requires the host path to exist)
touch "$DATA_DIR/stock_analysis.db"
if [[ -d "$DATA_DIR/symbol_cache.json" ]]; then
  rm -rf "$DATA_DIR/symbol_cache.json"
fi
if [[ ! -f "$DATA_DIR/symbol_cache.json" ]]; then
  echo '[]' > "$DATA_DIR/symbol_cache.json"
fi

echo "Starting container on port $PORT ..."
docker run -d \
  --name stock-analysis \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -v "$DATA_DIR/stock_analysis.db:/app/backend/stock_analysis.db" \
  -v "$DATA_DIR/config.json:/app/backend/config.json" \
  -v "$DATA_DIR/symbol_cache.json:/app/backend/symbol_cache.json" \
  "${REPO}:${VERSION}"

echo "Done! Visit http://localhost:${PORT}"
