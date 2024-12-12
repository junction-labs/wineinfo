# For developers of the demo

## Generating Vector Data

We live in a post-GPT era, of course our application requires a vector database.

Generating the data is best done in your local environment, rather than in a
container. Depending on your CPU or GPU, this may take a while.

In this directory, run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade uv
uv pip install -r backend/requirements.txt
python3 backend/bin/build_data.py
```

## Seeing what the backend app sees

```bash
$ kubectl get pods | grep backend
wineinfo-backend-57778c57c7-7r7j4        1/1     Running   0          42m

$ kubectl exec -ti wineinfo-backend-57778c57c7-vdrlw -- python
```

Then typically:

```python
import junction
client = junction.default_client()
```

Then some options:

```python
client.resolve_http("GET", "http://wineinfo-search.default.svc.cluster.local/search/?foo=bar", {})
client.dump_routes()
client.dump_backends()
```

## Using a locally built ezbake

Build docker image and import it into k3d:

```bash
cd ../ezbake
docker build --tag ezbake:local --file ./scripts/Dockerfile-develop
k3d image import -c junction-wineinfo ezbake:local
cd ../wineinfo
```

Then edit deploy/ezbake.yaml

```diff
-          image: ghcr.io/junction-labs/junction-labs/ezbake:latest
+          image: ezbake:local
```

Then pick it up with:

```bash
kubectl delete -f deploy/ezbake.yaml
kubectl apply -f deploy/ezbake.yaml
```

## Using a locally built junction-client

FIXME

## Developing the demo code with hot reload

The easiest way to develop the demo is using the interactive mode of the various
web servers. run the following in 5 different shells, then, go to
`http://localhost:3000/`:

Frontend (defaults to port 3000):

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 backend/bin/build_data.py
fastapi dev backend/app/backend_app.py --port 8000
```

Persist:

```bash
source .venv/bin/activate
fastapi dev backend/app/persist_app.py --port 8004
```

Recs:

```bash
source .venv/bin/activate
fastapi dev backend/app/recs_app.py --port 8003
```

Search:

```bash
source .venv/bin/activate
fastapi dev backend/app/search_app.py --port 8002
```

Catalog:

```bash
source .venv/bin/activate
fastapi dev backend/app/catalog_app.py --port 8001
```
