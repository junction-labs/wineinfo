# Client-Side Load Balancing

The recommendations team is having problems. Their data no longer completely
fits in memory, meaning they are seeing spikes in response times. After
analyzing their request logs, the team figured out that if they see more than
**5 distinct queries in a two second window**, every request in the next 5
seconds will fail.

That's not that many queries before the service falls over! Simulate the problem
by running:

```bash
kubectl apply -f deploy/04_ring_hash.yaml
```

We could convince ourselves the problem exists by playing with multiple browser
tabs, but it's easier to test by hitting the wineinfo API directly. This python
program spins up ten threads, each hitting
`http://localhost:8011/wines/recommendations?query=` with their query,
generating a new request every second.

Run it with `python junction/04_generator.py --duration 10`.  You should see
something like this:

```bash
$ python junction/04_generator.py --duration 10
Response Codes:
  200: 10
  500: 100
```

You see pretty quickly that the server goes into failure mode. The thing
the team reaches for in this scenario is to scale the service up. Since we only
need to handle ten unique requests per second, and each server can do 5, scaling
up to 4 replicas should fix the problem. Let's try this:

```bash
kubectl scale --replicas=4 deployment/wineinfo-recs
```

So should everything be better? Lets find out.

```bash
$ python junction/04_generator.py --duration 10
Response Codes:
  200: 41
  500: 69
```

Uh oh.

If we look at a log from one of the pods and do some command line-fu, we see
the problem: even though we have more servers, every single server is still
seeing the whole set of queries:

```bash
$ kubectl logs deployment/wineinfo-recs --tail=1000 | grep GET | cut -c 38- | sort | uniq -c
Found 3 pods, using pod/wineinfo-recs-7567f698cf-trmvq
   3 /recommendations/?query=australia&limit=10
   1 /recommendations/?query=france&limit=10
   4 /recommendations/?query=germany&limit=10
   2 /recommendations/?query=greece&limit=10
   1 /recommendations/?query=italy&limit=10
   1 /recommendations/?query=pinot+noir&limit=10
   3 /recommendations/?query=portugal&limit=10
   1 /recommendations/?query=red&limit=10
   2 /recommendations/?query=rose&limit=10
   2 /recommendations/?query=white&limit=10
```

To fix the issue, it seems like we'll have to limit the number of unique queries
that get sent to each individual server.

Fortunately, Junction implements a consistent hashing algorithm called RingHash,
which allows us to consistently send a shard of traffic to the same server, even
as the service scales up and down. Let's try it.

```bash
$ python ./junction/04_ring_hash.py
service/wineinfo-recs patched
```

```bash
$ python junction/04_generator.py --duration 10
Response Codes:
  200: 110
```

No more failures. Looking at one of the pod's query logs, we can now see it only
gets a subset of the queries:

```bash
$ kubectl logs deployment/wineinfo-recs --tail=30 | grep GET | cut -c 38- | sort | uniq -c
   8 /recommendations/?query=france&limit=10
   7 /recommendations/?query=italy&limit=10
```

## What Just Happened?

To address the issue without throwing even more capacity at it, we needed to
route to each service based on the query. That's a kind of load balancing.

So we configured Junction so that the recommendations service Backend used
consistent hashing based on the `?query` URL parameter. Any time the Junction
client makes that route to this Backend (see the [routing](./02_routing.md) demo
if you need to refresh your memory), it will use the configuration we're
defining.

```python
recs: config.Service = {
    "type": "kube",
    "name": "wineinfo-recs",
    "namespace": "default",
}

backend: config.Backend = {
    "id": {**recs, "port": 80},
    "lb": {
        "type": "RingHash",
        "minRingSize": 1024,
        "hashParams": [{"type": "QueryParam", "name": "query"}],
    },
}
```

This is our first time seeing a Junction Backend, so let's walk through it in
detail.

A backend always has an `id,` which combines a `Service` and a `port.` A
`Service` is a logical target for traffic, and the port is the port on which
traffic comes in. Here, our service is a Kubernetes Service identified with a
`namespace` and a `name.` It could also be an autoscaling group in your cloud
provider or an internal service at your company backed by DNS.

Next, we're configuring `lb`, the load balancer for this Backend. The load
balancer we've declared uses the `RingHash` algorithm, and we've specified that
it should use a URL query parameter with the name `query` as its input.

The RingHash load balancing algorithm we just specified happens is a version of
[consistent hashing](https://en.wikipedia.org/wiki/Consistent_hashing), and it
happens **entirely client-side**. Every time the client makes a request, it
hashes that request's `query` parameter and uses it to pick a server from all of
the backends that make up the recommendations service. Because that hash is
deterministic, it picks the same server every time it sees the same value for a
query parameter.

That kind of consistency is precisely the problem we need to solve to keep our
recommendations service alive and happy!

## Cleaning up for the next step

To restore the Wineinfo shop back to where we started breaking things for the demo, run:

```bash
kubectl delete -f deploy/wineinfo.yaml
kubectl apply -f deploy/wineinfo.yaml
```

Next, head over to [05_argo_rollouts.md](05_argo_rollouts.md).

If you're fully done, you can fully delete your k3d cluster with:

```bash
k3d cluster delete junction-wineinfo
```
