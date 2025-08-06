# For developers of the demo

## Generating New Vector Data

Generating the data is best done in your local environment, rather than in a
container. Depending on your CPU or GPU, this may take a while.

In this directory, run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade uv
uv pip install -r python_services/requirements.txt
python3 python_services/bin/build_data.py
```

## Querying junction from a running container

```
kubectl exec -ti $(kubectl get po -o=name -l app=wineinfo,service=persist) -- python
```

Then typically:

```python
import junction
client = junction.default_client()
```

Then some options:

```python
client.resolve_http(http://wineinfo-search.default.svc.cluster.local/search/?foo=bar")
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

Persist:

```bash
source .venv/bin/activate
fastapi dev python_services/app/persist_app.py --port 8004
```

Embeddings:

```bash
source .venv/bin/activate
fastapi dev python_services/app/embeddings_app.py --port 8003
```

Search:

```bash
source .venv/bin/activate
fastapi dev python_services/app/search_app.py --port 8002
```

Sommelier:

```bash
source .venv/bin/activate
fastapi dev python_services/app/sommelier_app.py --port 8001
```
