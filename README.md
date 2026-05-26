# A-Share 520 MA Analysis System

A technical analysis system for A-shares based on the 5-period and 20-period moving averages (520 Strategy), featuring golden cross scanning, pullback analysis, moving average convergence/divergence detection, and backtesting.

## Tech Stack

| Layer    | Technology                    |
|----------|-------------------------------|
| Frontend | React 18 + TypeScript + Ant Design + ECharts |
| Backend  | Python 3.12 + FastAPI + Uvicorn |
| Database | SQLite (via SQLAlchemy ORM)   |
| Data     | THS HTTP / iFinD SDK / Sina / AKShare |

## Directory Structure

```
├── backend/              # FastAPI backend
│   ├── main.py           # Entry point
│   ├── routers/          # API routes
│   ├── providers/        # Data providers (THS/Sina/AKShare)
│   ├── strategy/         # Strategy engine (golden cross/pullback/backtest)
│   ├── database.py       # SQLite database
│   ├── models.py         # ORM models
│   └── config.py         # Configuration
├── frontend/             # React frontend
│   └── src/
│       ├── pages/        # Page components
│       ├── components/   # UI components
│       └── api/          # API client
├── docs/                 # Documentation
├── Dockerfile            # Docker build
├── docker-compose.yml    # Docker Compose config
├── start.bat             # Windows dev startup
└── stop.bat / stop.ps1  # Windows stop scripts
```

## Docker Deployment (Recommended)

### Prerequisites

- Linux server (tested on Ubuntu / CentOS)
- Docker and Docker Compose

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<repo>.git
cd <repo>

# 2. Build the image
sudo docker compose build

# 3. Start the container
sudo docker compose up -d

# 4. View logs
sudo docker compose logs -f
```

### Management

```bash
# Build image
sudo docker compose build

# Start in background
sudo docker compose up -d

# Check status
sudo docker compose ps

# Stop
sudo docker compose down
```

### Access

Visit `http://<server-public-ip>:8000`

### Data Persistence

`docker-compose.yml` mounts the SQLite database and config files to the host:

- `./backend/stock_analysis.db` — market data
- `./backend/config.json` — user config (data source priority, tokens, etc.)
- `./backend/symbol_cache.json` — stock symbol cache

Data survives container deletion.

### Upgrading

```bash
git pull
sudo docker compose build
sudo docker compose up -d
```

### Manual Docker (without Compose)

```bash
sudo docker build -t stock-analysis .
sudo docker run -d \
  --name stock-analysis \
  -p 8000:8000 \
  -v $(pwd)/backend/stock_analysis.db:/app/backend/stock_analysis.db \
  -v $(pwd)/backend/config.json:/app/backend/config.json \
  -v $(pwd)/backend/symbol_cache.json:/app/backend/symbol_cache.json \
  --restart unless-stopped \
  stock-analysis
```

## Alibaba Cloud Security Group

1. Go to Alibaba Cloud ECS Console → Security Group
2. Add an inbound rule:
   - Port Range: `8000/8000`
   - Source: `0.0.0.0/0` (or your IP only)
   - Protocol: TCP

## Windows Local Development

```bash
start.bat
```

This will install dependencies and start the backend (`:8000`) and frontend dev server (`:5173`).

## License

MIT
