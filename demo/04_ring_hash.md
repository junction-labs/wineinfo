# Ring Hash

We all know about sharding, which is taking some parameter of a request, running
it through a hash function, and then using that to choose consistently across N
backends. Unfortunately sharding has 2 problems:
- the first, is now you have that hashing code to maintain in all of your
  clients
- even if you work out how to load the number N dynamically, changing it is hard
 as instantaneously every request goes to a completely new host.

Enter consistent hashing. Junction implements a consistent hashing algorithm
called RingHash, allowing you to consistently send traffic to the same place as
you scale up and down.

## Background

The recommendations team is having problems. Their data no longer completely
fits in memory, meaning they are seeing spikes in response times. To simulate 
this problem, we  are going to use a feature flag that enacts this algorithm 
in the recommendations service:

```
if in a sliding window of the last 2 seconds you see more than 10 different queries:
  fail the next 5 seconds of queries (pretending this is the process restarting)
```

Yes these numbers are absurdly low, we choose them just to make the demo easier
to understand.

To enable this failure mode, go to `http://localhost:8010/admin` and make the latency 
start by adding a feature flag named `recs_simulate_overload` with value `10`.

To see this failure in action, we could play with many browser tabs. However
it is easier to hit our backend APIs directly. This python program
spins up 10 threads, each doing a different query against hitting http://localhost:8011/wines/recommendations?query=,
generating a new request at most every single. i.e. Loading our service with 
10 requests per second.


Run it with ``.  You should see something like this:

```
time: 0.5, thread: 1, query: foo, response-time: 0.1, response_code: 200
```

You see pretty quickly that the server goes into failure mode.


## Scale Up

The natural tools team reach for in this state is scaling up. Since we only need to handle
20 requests in 2 seconds, scaling up to 3 replicas should fix the problem. Lets try that with:

```bash
kubectl scale --replicas=5 deployment/wineinfo-recs
```

So should everything be better? Lets find out.

```bash
```

However, as this merely sprays queries between servers, we still have the same problem.
To stop the issue we need to hash on the query.

## Ring Hash

```python
    recs: Target = {
        "name": "wineinfo-recs",
        "namespace": "default",
    }
    backends: List[junction.config.Backend] = [
        {
            "id": recs,
            "lb": {
                "type": "RingHash",
                "minRingSize": 1024,
                "hashParams": [{"type": "Header", "name": "x-queryhash"}],
            },
        }
    ]
```

You see x-queryhash as a header here. This is a header that backend_app
generates before it calls into the recommendations service.


Install it by running this command:
``

Now, has this fixes things? Lets try with:

```
```

## Clean Up

First lets get rif of the feature flag by going to `http://localhost:8010/admin`
and setting  `recs_simulate_overload` to ``.

Next, lets scale down the deployment:
```
kubectl scale --replicas=1 deployment/wineinfo-recs
```

Finally, while there is no harm in leaving the ring hash in place, we will leave
things clean for the demo. Unlike the earlier tests of routes, RingHash is a
behavior of the backend service. To clean it up we must do
```
```
