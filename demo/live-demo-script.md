# WineInfo Demo Script

## Routing/traffic splitting

Features:

* Testing in production
* Feature flagging @ network level

Steps:

1. Deploy WineInfo: `kubectl apply -f deploy/wineinfo.yaml`
2. Deploy bugged catalog service with bug via kubectl
   > For demo purposes this just sets the `CATALOG_DEMO_MOJIBAKE` env var to `true` for wineinfo-catalog deployment
   <details>
      <summary>New catalog deployment yaml</summary>
      
      > This can be deployed by piping it to `kubectl apply -f -` with `echo`: `echo '<YAML>' | kubectl apply -f -`.
   
      ```yml
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: wineinfo-catalog
        labels:
          app: wineinfo
      spec:
        replicas: 1
        selector:
          matchLabels:
            app: wineinfo
            service: catalog
        template:
          metadata:
            labels:
              app: wineinfo
              service: catalog
          spec:
            containers:
            - name: main
              image: wineinfo-python:latest
              imagePullPolicy: IfNotPresent
              command: ["fastapi", "run", "/app/catalog_app.py", "--host", "0.0.0.0", "--port", "80"]
              envFrom:
              - configMapRef:
                  name: wineinfo-config
              env:
              - name: CATALOG_DEMO_MOJIBAKE
                value: "true"
      ```
   </details>
   
3. Show encoding bug in WineInfo UI
4. Deploy new catalog service with bug fix via kubectl
   <details>
      <summary>Catalog next deployment yaml</summary>
      
      > This can be deployed by piping it to `kubectl apply -f -` with `echo`: `echo '<YAML>' | kubectl apply -f -`.
      
      ```yml
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: wineinfo-catalog-next
        labels:
          app: wineinfo
      spec:
        replicas: 1
        selector:
          matchLabels:
            app: wineinfo
            service: catalog-next
        template:
          metadata:
            labels:
              app: wineinfo
              service: catalog-next
          spec:
            containers:
            - name: main
              image: wineinfo-python:latest
              imagePullPolicy: IfNotPresent
              command: ["fastapi", "run", "/app/catalog_app.py", "--host", "0.0.0.0", "--port", "80"]
              envFrom:
              - configMapRef:
                  name: wineinfo-config
      ---
      apiVersion: v1
      kind: Service
      metadata:
        name: wineinfo-catalog-next
      spec:
        type: ClusterIP
        selector:
          app: wineinfo
          service: catalog-next
        ports:
          - port: 80
      ```
   </details>
   
5. Create route that routes traffic to catalog-next for admin user in Junction UI
   <details>
      <summary>Route JSON</summary>
      
      ```json
      {
        "id": "wineinfo-catalog",
        "tags": {},
        "hostnames": [
          "wineinfo-catalog.default.svc.cluster.local"
        ],
        "ports": [],
        "rules": [
          {
            "matches": [
              {
                "headers": [
                  {
                    "type": "RegularExpression",
                    "name": "baggage",
                    "value": ".*username=admin(,|$).*"
                  }
                ]
              }
            ],
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-catalog-next",
                "namespace": "default",
                "port": 80,
                "weight": 1
              }
            ]
          },
          {
            "backends": [
              {
                "type": "kube",
                "name": "wineinfo-catalog",
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
6. Test fix in production by logging in as admin user

## Advanced routing functionality

Features:

* Timeouts
* Retries

Steps:

7. Simulate latency spikes in search: `kubectl apply -f demo/deploy/03_retries.yaml` 
   > For demo purposes this just sets the `SEARCH_DEMO_LATENCY` env var to `true` for wineinfo-search deployment
8. Show latency issues in WineInfo UI
9. Create route in Junction UI with timeouts and automatic retries (show that we could also make the default route have timeouts and automatic retries, instead of using a path match)
   <details>
      <summary>Route JSON</summary>
      
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
            "matches": [
              {
                "path": {
                  "type": "Exact",
                  "value": "/search/"
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
                "namespace": "default",
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
                "namespace": "default",
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
11. Test fix by running a bunch of searches and seeing latency is decreased

## Load Balancing

Features:

* Client-side load balancing

Steps:

11. Simulate Recommendations service load failure: `kubectl apply -f demo/deploy/04_ring_hash.yaml` 
    > For demo purposes this just sets the `RECS_DEMO_FAILURE` env var to `true` for the wineinfo-recs deployment
12. Show the failures by making repeated request to the recommendation server with distinct queries (5 reqs in two seconds or more)
    1. Also show failures with the Load Testing widget in recommendations tab by logging in as admin user
14. Upscale recommendation service: `kubectl scale --replicas=4 deployment/wineinfo-recs`
15. Show problem has gotten better, but still exists using Load Testing functionality in recommendations UI in Wineinfo
16. Add a load balancing policy to the wineinfo-recs service via the Junction UI
    <details>
      <summary>Service JSON</summary>
         
      ```json
      {
        "id": {
          "type": "kube",
          "name": "wineinfo-recs",
          "namespace": "default"
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
17. Run a load test in the recommendations UI in Wineinfo again to show ring hash is working

## Wrap up

Explain that all of these features can be mixed and matched.
