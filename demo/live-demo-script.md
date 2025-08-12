# WineInfo Demo Script

## Setup:
- Run junction control plane in orbstack:
```bash
cd ../cloud
docker build -t junction/transistor:latest -f Dockerfile.transistor .
docker build -t junction/relay:latest      -f Dockerfile.relay .
docker build -t junction/db-init:latest    -f Dockerfile.db-init .
docker build -t junction/init-utils:latest -f Dockerfile.init-utils .
helm install junction ./junction-chart/ \
  --namespace junction --create-namespace \
  --set-file relay.kubeconfig.content=$HOME/.kube/config
```
- Add "orbstack" cluster in Junction UI http://0.0.0.0:8764/ 
- Set up wineinfo in orbstack:
```bash
./deploy/wineinfo.sh --local --namespace wineinfo --nextauth-url "http://localhost:30010/"
```

Wineinfo UI should not be visible at http://localhost:30010/


## 1. Multicluster
- spin up a new cluster
- start up a sommelier in it rather than above
- show it

To work:
- need a add cluster button so can add creds after the fact
- need to make relay contactable from kind (maybe it already is??)

## 2. Routing/traffic splitting 

The problem is, customer 2 complains that the sommelier only recommends really expensive wine. but we can't repro it with development data/setup. So we move to preprod where we have a copy of all their data

### 2.1 Enable the bug 

```bash
kubectl apply --namespace wineinfo -f demo/deploy/02_routing_enable.yaml
```

Show we can now repro it, how for customer 1 "a nice cheap red" returns a different list than for customer 2.

### 2.2 Deploy the sandbox

```bash
kubectl apply --namespace wineinfo -f demo/deploy/02_routing_sandbox.yaml
```

Show that in comes up in the Junction UI.

### 2.3 Create the route

Go to the Junction UI, and create this route:

   <details>
      <summary>Route JSON</summary>
      
      ```json
      {
        "id": "wineinfo-sommelier",
        "tags": {},
        "hostnames": [
          "wineinfo-sommelier.wineinfo.svc.cluster.local"
        ],
        "ports": [ 80 ],
        "rules": [
          {
            "matches": [
              {
                "headers": [
                  {
                    "type": "RegularExpression",
                    "name": "baggage",
                    "value": ".*user-id=2(,|$).*"
                  }
                ]
              }
            ],
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-sommelier-sandbox-1",
                "namespace": "wineinfo",
                "port": 80,
                "weight": 1
              }
            ]
          },
          {
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-sommelier",
                "namespace": "wineinfo",
                "port": 80,
                "weight": 1
              }
            ]
          }
        ]
      }
      ```
   </details>

Show how it looks visually.

Now, show that the sandbox is running only for customer 2.

### 2.4 Make the fix
Run this once: 
```bash
brew install fswatch
```

Then this: 
```bash
fswatch -o python_services/app | while read f; do
    docker build \
        --tag wineinfo-python:latest \
        --file python_services/Dockerfile python_services/ && \
    kubectl rollout --namespace wineinfo restart deployment/wineinfo-sommelier-sandbox-1
done
```

Then go into your IDE in sommelier_service_impl. Show the problematic code in _fallback_chat(). 
Delete it and save. Show customer 2 now works. Now make a typo and save and show the error. 
Then flip to customer 1 and show they are unaffected,

## 3. Advanced routing functionality

Features:
* Timeouts
* Retries

### 3.1 Simulate latency spikes in search 

```bash
kubectl apply --namespace wineinfo -f demo/deploy/03_retries.yaml
```
Show latency issues in WineInfo UI

### 3.2 Create a Route

Create route in Junction UI with timeouts and automatic retries (show that we could also make the default route have timeouts and automatic retries, instead of using a path match)
   <details>
      <summary>Route JSON</summary>
      
      ```json
      {
        "id": "wineinfo-search",
        "tags": {},
        "hostnames": [
          "wineinfo-search.wineinfo.svc.cluster.local"
        ],
        "ports": [],
        "rules": [
          {
            "matches": [
              {
                "path": {
                  "type": "Exact",
                  "value": "/catalog_search/"
                }
              }
            ],
            "timeouts": {
              "backend_request": 0.1
            },
            "retry": {
              "attempts": 5,
              "backoff": 0.1
            },
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-search",
                "namespace": "wineinfo",
                "port": 80,
                "weight": 1
              }
            ]
          },
          {
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-search",
                "namespace": "wineinfo",
                "port": 80,
                "weight": 1
              }
            ]
          }
        ]
      }
      ```
      
      With just the default route:
      ```json
      {
        "id": "wineinfo-search",
        "tags": {},
        "hostnames": [
          "wineinfo-search.default.svc.cluster.local"
        ],
        "ports": [],
        "rules": [
          {
            "timeouts": {
              "backend_request": 0.1
            },
            "retry": {
              "attempts": 5,
              "backoff": 0.1
            },
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-search",
                "namespace": "default",
                "port": 80,
                "weight": 1
              }
            ]
          }
        ]
      }
      ```
   </details>

Test fix by running a bunch of searches and seeing latency is decreased

## 4 Load Balancing

### 4.1 Simulate semantic search service load failure: 

```bash
kubectl apply --namespace wineinfo -f demo/deploy/04_ring_hash.yaml
```
  
Show the failures by making repeated request semantic search with distinct queries (5 reqs in two seconds or more)

Also show failures with the Load Testing widget by logging in as admin user


### 4.2 Upscale embeddings service: 

```bash
kubectl scale --namespace wineinfo --replicas=4 deployment/wineinfo-embeddings
```

Show problem has gotten better, but still exists using Load Testing functionality in recommendations UI in Wineinfo

### 4.3 Add a load balancing policy to the wineinfo-embeddings service via the Junction UI
    <details>
      <summary>Service JSON</summary>
         
      ```json
      {
        "id": {
          "type": "kube",
          "name": "wineinfo-embeddings",
          "namespace": "wineinfo"
        },
        "backends": [
          {
            "port": 80,
            "lb": {
              "type": "RingHash",
              "min_ring_size": 1024,
              "hash_params": [
                {
                  "type": "QueryParam",
                  "name": "query"
                }
              ]
            }
          }
        ]
      }
      ```
    </details>

Run a load test in the recommendations UI in Wineinfo again to show ring hash is working

## Wrap up

Explain that all of these features can be mixed and matched.
