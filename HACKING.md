# For developers of the demo

## Environment Setup

Required environment variables:

```bash
# Required for catalog service (search backend)
export TURBOPUFFER_API_KEY="your-turbopuffer-api-key"
# For AI sommelier (Claude-powered wine recommendations)
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

Optional:
``` bash
# For embedding provider (defaults to "local")
export EMBEDDING_PROVIDER="local"  # or "openai"
# specify model
export EMBEDDING_MODEL="all-MiniLM-L6-v2"
# For OpenAI embeddings (only needed if EMBEDDING_PROVIDER="openai")
export OPENAI_API_KEY="your-openai-api-key"
```

## Building the Search Index

Index generation uses Turbopuffer and creates both full-text and vector embeddings.
This is best done in your local environment.

**Note:** The first time you run this with local embeddings, sentence-transformers will
download the model (~90MB for all-MiniLM-L6-v2). Subsequent runs will use the cached model.

In this directory, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade uv
uv pip install -r python_services/requirements.txt

# Index 1000 wines (adjust --lines as needed, 0 = all)
python3 python_services/bin/build_data.py --lines 1000
```

## Developing the demo code with hot reload

The easiest way to develop the demo is using the interactive mode of the various
web servers. Run the following in 4 different shells:

**Frontend** (defaults to port 3000):

```bash
cd frontend
npm install
npm run dev
```

Then go to `http://localhost:3000/`

**Persist Service** (wine storage - port 8001):

```bash
source .venv/bin/activate
fastapi dev python_services/app/persist_app.py --port 8001
```

**Catalog Service** (unified search - port 8002):

```bash
source .venv/bin/activate
fastapi dev python_services/app/catalog_app.py --port 8002
```

**Sommelier Service** (AI recommendations - port 8003):

```bash
source .venv/bin/activate
  fastapi dev python_services/app/sommelier_app.py --port 8003
```
