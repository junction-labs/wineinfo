# Wineinfo - Junction Demo Application

## Project Overview

Wineinfo is a demonstration web application showcasing [Junction](https://github.com/junction-labs/junction-client), a service mesh/routing solution. The application is a wine catalog that demonstrates various search capabilities including traditional full-text search, LLM-based vector search, and persistent user collections.

## Architecture

The application follows a microservices architecture with:
- **Frontend**: Next.js 15 with React 19, TypeScript, and Tailwind CSS
- **Backend Services**: Multiple FastAPI Python services handling specific functionality
- **Deployment**: Runs in a self-contained k3d (Kubernetes in Docker) cluster

### Service Breakdown

The application consists of these distinct services:

1. **Frontend** (`frontend/`)
   - Next.js 15 application with TypeScript
   - Uses Junction client (`@junction-labs/client`) for service routing
   - NextAuth for authentication
   - Radix UI components with Tailwind CSS styling
   - Port: 3000 (dev), 8010 (deployed)

2. **Catalog Service** (`python_services/app/catalog_app.py`)
   - **Unified search service** powered by Turbopuffer
   - Defaults to hybrid mode (BM25 + vector) for best results
   - Optional modes: text-only (fastest), semantic-only (concepts), or hybrid (default)
   - Single `/search/` endpoint - mode parameter is optional
   - Supports filters, numeric ranges, sorting, and pagination
   - Port: 8002

3. **Persist Service** (`python_services/app/persist_app.py`)
   - FastAPI service for saving bottles to user collections
   - SQLite database for wine catalog and user cellars
   - Port: 8001

4. **Sommelier Service** (`python_services/app/sommelier_app.py`)
   - FastAPI service providing AI-powered wine recommendations
   - Uses Anthropic's Claude for natural language interaction
   - Calls catalog service for wine search
   - Tool-based architecture with search capabilities
   - Port: 8003

## Tech Stack

### Frontend
- Next.js 15 with Turbopack
- React 19
- TypeScript 5
- Tailwind CSS
- NextAuth for authentication
- Radix UI for component primitives
- Junction Labs client for service routing

### Backend
- Python 3
- FastAPI framework
- Junction client for service mesh routing
- **Turbopuffer** for unified search (BM25 + vector embeddings)
- **sentence-transformers** for local embedding generation (default, no API needed)
- OpenAI API for embeddings (optional alternative to local)
- Anthropic's Claude API for AI sommelier interactions

### Infrastructure
- Docker for containerization
- k3d (Kubernetes in Docker) for local cluster
- kubectl for cluster management
- Kubernetes manifests for service deployment

## Development Setup

### Prerequisites
- Docker
- kubectl
- k3d (install via `curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash`)

### Quick Start (Deployed)
```bash
./deploy/wineinfo.sh
# Access at http://localhost:8010
```

### Development Mode (with hot reload)

Run each service in a separate terminal:

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # Runs on port 3000
```

**Python Services:**

First, set environment variables:

**Required:**
```bash
export TURBOPUFFER_API_KEY="your-turbopuffer-api-key"
```

**Optional:**
```bash
# For AI sommelier (highly recommended for best experience)
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

**Embeddings Configuration (defaults to local):**
The system uses **local embeddings by default** via sentence-transformers. No configuration needed!

To use OpenAI instead:
```bash
export EMBEDDING_PROVIDER="openai"
export EMBEDDING_MODEL="text-embedding-3-small"
export OPENAI_API_KEY="your-openai-api-key"
```

**Why local embeddings?**
- No API costs or rate limits
- Works offline
- Fast and high quality
- Downloads model once (~90MB), then runs locally

Then install dependencies and run services:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade uv
uv pip install -r python_services/requirements.txt

# Run services:
fastapi dev python_services/app/persist_app.py --port 8001  # Wine storage
fastapi dev python_services/app/catalog_app.py --port 8002  # Unified search
fastapi dev python_services/app/sommelier_app.py --port 8003  # AI sommelier
```

### Building the Search Index

Build the Turbopuffer search index with your wine data:
```bash
source .venv/bin/activate
python3 python_services/bin/build_data.py --lines 1000

# Options:
# --lines N    : Process N wines (0 for all)
# --src PATH   : Path to source CSV file
```

This will:
- Index wines in Turbopuffer with BM25 full-text search
- Generate and store vector embeddings for semantic search
- Populate the persist service with wine data
- Create sample user cellars

## Project Structure

```
wineinfo/
├── frontend/                    # Next.js frontend application
│   ├── app/                    # Next.js app directory
│   ├── components/             # React components
│   └── package.json
├── python_services/            # Python backend services
│   ├── app/
│   │   ├── sommelier_app.py   # Wine recommendation service
│   │   ├── search_app.py      # Full-text search service
│   │   ├── embeddings_app.py  # Vector search service
│   │   ├── persist_app.py     # Collection persistence service
│   │   ├── common/            # Shared utilities
│   │   └── services/          # Service implementations
│   ├── bin/                   # Build scripts
│   │   └── build_data.py      # Vector data generation
│   ├── data/                  # Data files
│   └── requirements.txt
├── deploy/                     # Kubernetes deployment configs
│   ├── wineinfo.sh            # Deployment script
│   └── wineinfo.yaml          # Kubernetes manifests
├── demo/                      # Demo-related files
└── README.md
```

## Key Files

- `frontend/package.json` - Frontend dependencies and scripts
- `python_services/requirements.txt` - Python dependencies
- `deploy/wineinfo.yaml` - Kubernetes service definitions
- `deploy/wineinfo.sh` - Automated deployment script
- `HACKING.md` - Developer documentation for the demo

## Git Information

- Current branch: `sommelier`
- Main branch: `main`
- Recent development focuses on routing demos and sommelier service enhancements

## Important Context for AI Assistants

1. **Junction Integration**: This project heavily uses Junction for service routing and mesh capabilities. The Junction client is integrated in both the frontend and Python services.

2. **Microservices Pattern**: Each backend service is independent and handles a specific domain (search, embeddings, persistence, recommendations).

3. **Development vs Deployment**: The app can run in two modes:
   - Local development with hot reload (each service running separately)
   - Kubernetes deployment via k3d (containerized, production-like)

4. **Vector Search**: The embeddings service uses vector embeddings for semantic search, which requires pre-generated data.

5. **Authentication**: NextAuth is integrated for user authentication, relevant for the persist service (saving collections).

6. **Kubernetes Native**: While it can run locally, the application is designed to demonstrate Kubernetes service mesh patterns.
