# Ring Hash

Junction implements a consistent hashing algorithm called RingHash, allowing you
to consistently send a shard of traffic to the same pod as you scale up and
down.

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
threads, each hitting `http://localhost:8011/wines/recommendations?query=` with
their own query, generating a new request at most every second.


Run it with `python junction/04_generator.py --duration 10`.  You should see
something like this:

```bash
$ python junction/04_generator.py --duration 10
Response Codes:
  200: 10
  500: 100
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
$ python junction/04_generator.py --duration 10
Response Codes:
  200: 41
  500: 69
```

If we look at a log from one of the pods, and do some command line-fu, we see
the expected problem that every single pod is seeing the whole set of queries:

```bash
$ kubectl logs deployment/wineinfo-recs --tail=1000 | grep GET | cut -c 38- | sort | uniq -c
Found 3 pods, using pod/wineinfo-recs-7567f698cf-98lf4
   8 /recommendations/?query=0&limit=10
   2 /recommendations/?query=1&limit=10
   2 /recommendations/?query=2&limit=10
   3 /recommendations/?query=3&limit=10
   1 /recommendations/?query=4&limit=10
   2 /recommendations/?query=5&limit=10
   2 /recommendations/?query=6&limit=10
   3 /recommendations/?query=7&limit=10
   2 /recommendations/?query=8&limit=10
```

## Fixing the issue with Junction 

To address the issue without throwing even more capacity at it, we need to route
based on the query. In Junction, the load balancing algorithm is set on the
backend, as follows: 

```python
recs = junction.config.ServiceKube(type="kube", name="wineinfo-recs", namespace="default")

backend: junction.config.Backend = [
    {
        "id": {**recs, "port": 80},
        "lb": {
            "type": "RingHash",
            "minRingSize": 1024,
            "hashParams": [{"type": "QueryParam", "name": "query"}],
        },
    }
]
```

Install it by running `python junction/04_ring_hash.py`. You should see
something like:

```bash
$ python ./junction/04_ring_hash.py
service/wineinfo-recs patched
```

Now, has this fixed things? Lets try with:

```bash
$ python junction/04_generator.py --duration 10
Response Codes:
  200: 110
```

No more failures. Looking at one of the pods query logs, we can now see it only
gets a subset of the queries:

```bash
$ kubectl logs deployment/wineinfo-recs --tail=30 | grep GET | cut -c 38- | sort | uniq -c
   4  /recommendations/?query=1&limit=10
   4  /recommendations/?query=2&limit=10
   3  /recommendations/?query=6&limit=10
   4  /recommendations/?query=9&limit=10
```

## Whats going on

We all know about sharding, which is taking some parameter of a request, running
it through a hash function, and then using that to choose consistently across N
backends. Unfortunately sharding has 2 problems:
- the first, is now you have that hashing code to maintain in all of your
  clients
- even if you work out how to load the number N dynamically, scaling up is hard
  as changing the value means instantaneously every request goes to a completely
  new host.

Junction in general solves the first problem, and the ring has algorithm solves
the second. For a full writeup, see
https://en.wikipedia.org/wiki/Consistent_hashing.

## Cleaning up

To roll back this demo and leave wineinfo in working order for the next one,
run: 

```bash
kubectl delete -f deploy/wineinfo.yaml
kubectl apply -f deploy/wineinfo.yaml
```
