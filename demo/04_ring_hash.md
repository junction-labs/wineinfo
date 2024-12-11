# Ring Hash

Junction implements a consistent hashing algorithm called RingHash, allowing you
to consistently send traffic to the same place as you scale up and down.

To enable this demo, reconfigure Kubernetes with:
```bash
kubectl apply -f deploy/04_ring_hash.yaml
```

> [!NOTE]
>
> All of the code for this example is in
> [03_retries](../junction/04_ring_hash.py).


## Background

The recommendations team is having problems. Their data no longer completely
fits in memory, meaning they are seeing spikes in response times. To simulate
this problem, we use a environment variable that enacts this algorithm in the
recommendations service:

```
if in a sliding window of the last 2 seconds you see more than 5 different queries:
  fail the next 5 seconds of queries (pretending this is the process restarting)
```

To see this failure in action, we could play with many browser tabs. However it
is easier to hit our backend APIs directly. This python program spins up 10
threads, each doing a different query against hitting
`http://localhost:8011/wines/recommendations?query=`, generating a new request
at most every second. i.e. Loading our service with 10 requests per second.


Run it with `python junction/generate-reqs-requests.py --duration 3`.  You
should see something like this:

```bash
$ python junction/generate-reqs-requests.py --duration 3
time: 0.5, thread: 1, query: foo, response-time: 0.1, response_code: 200
FIXMEFIXME
```

You see pretty quickly that the server goes into failure mode. The natural tools
team reach for in this state is scaling up. Since we only need to handle 10
unique requests per second, and each server can do 5, scaling up to 3 replicas
seems like it should fix the problem. Lets try that with:

```bash
kubectl scale --replicas=3 deployment/wineinfo-recs
```

So should everything be better? Lets find out.

```bash
$ python junction/generate-reqs-requests.py --duration 3
time: 0.5, thread: 1, query: foo, response-time: 0.1, response_code: 200
FIXMEFIXME
```

What we see is, as we are still spraying queries between servers, we still have
the same problem. To address the issue without throwing even more capacity at
it, we need to route based on the query.

## Fixing the issue with Junction 

In Junction, the load balancing algorithm is set on the backend. 

```python
recs_url = "http://wineinfo-recs.default.svc.cluster.local"

backend: junction.config.Backend = [
    {
        "id": jct_backend(recs_url),
        "lb": {
            "type": "RingHash",
            "minRingSize": 1024,
            "hashParams": [{"type": "Header", "name": "x-username"}],
        },
    }
]
```

Install it by running `python junction/generate-reqs-requests.py`. 

Now, has this fixed things? Lets try with:

```bash
$ python junction/generate-reqs-requests.py --duration 3
time: 0.5, thread: 1, query: foo, response-time: 0.1, response_code: 200
FIXMEFIXME
```

No more failures. 

## Whats going on

First thing is its on the backend

Second thing is consistent hashing itself.

We all know about sharding, which is taking some parameter of a request, running
it through a hash function, and then using that to choose consistently across N
backends. Unfortunately sharding has 2 problems:
- the first, is now you have that hashing code to maintain in all of your
  clients
- even if you work out how to load the number N dynamically, changing it is hard
 as instantaneously every request goes to a completely new host.

Enter consistent hashing. 

## Cleaning up

To roll back this demo and leave wineinfo in working order for the next one,
run: 

```bash
kubectl apply -f deploy/wineinfo.yaml
```
