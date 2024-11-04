# `wineinfo`

A webapp with React frontend and FastAPI backend services to demonstrate Junction.

## Running the demo

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 backend/app/build_data.py

docker build --tag wineinfo-frontend --file scripts/Dockerfile-frontend --load frontend
docker build --tag wineinfo-backend --file scripts/Dockerfile-backend --load backend
docker build --tag wineinfo-catalog --file scripts/Dockerfile-catalog --load backend
docker build --tag wineinfo-search --file scripts/Dockerfile-search --load backend
docker build --tag wineinfo-recs --file scripts/Dockerfile-recs --load backend
kubectl apply -f scripts/latest-ezbake.yml
kubectl apply -f scripts/k8s_frontend.yml
kubectl apply -f scripts/k8s_backend.yml
kubectl apply -f scripts/k8s_catalog.yml
kubectl apply -f scripts/k8s_search.yml
kubectl apply -f scripts/k8s_recs.yml
```

## Developing the demo

The easiest way to develop the demo is using the interactive mode of the various so,
run the following in 5 different shell windows:

Frontend:
```
cd frontend
npm install
npm run dev
```

Backend:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 backend/app/build_data.py
fastapi dev backend/app/backend.py
```

Recs:
```
source .venv/bin/activate
fastapi dev backend/app/recs_app.py --port 8003
```

Search:
```
source .venv/bin/activate
fastapi dev backend/app/search_app.py --port 8002
```

Catalog:
```
source .venv/bin/activate
fastapi dev backend/app/catalog_app.py --port 8001
```

Then, go to `http://localhost:3000/`.
