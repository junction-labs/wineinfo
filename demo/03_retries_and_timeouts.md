# Retries and Timeouts

Setting retries and timeouts is something that we are all used to doing in
service oriented architectures, usually in static config, deployed with the
client. Junction gives service owners the ability to dynamically change both
settings and retries, with the ability to unit test the configuration before it
is rolled out into production.

> [!NOTE]
>
> The code for this example is in
> [search-retries-and-timeouts.py](../junction/search-retries-and-timeouts.py).

## Background

The search team has a problem, they are seeing load spikes increasing the
latency of 50% of queries. They have tried restarting the service, but to no
avail, it seems to be some sort of noisy neighbor problem and they are waiting
for the Kubernetes team to engage to help. They need to to something to mitigate
the damage sooner.

To enable this scenario, we will use the applications feature flag capability.
Go to `http://localhost:8010/admin` and make the latency start by adding a
feature flag named `search_simulate_latency` with value `1`.

FIXME: image

Now go back to `http://localhost:8010` and do some searches. You should be able
to verify that 50% of requests now have excessive latency.

## Timeouts

To combat the issue, the team decides they need to put in a timeout against the
service, with retries so that it gets to a health server faster. 

```python
search: Target = {
    "name": "wineinfo-search",
    "namespace": "default",
}
route: Route = {
    "vhost": search,
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "timeouts": {"backend_request": 0.1},
            "retry": junction.config.RouteRetry(
                attempts=3, backoff=0.1
            ),
            "backends": [{**search, "port": 80}],
        },
        {
            "backends": [{**search, "port": 80}],
        },
    ],
}
```

Here you see a few things:
* We target a specific method of the service using a path
* We set timeouts on the backend to 0.1 seconds.
* We do up to 5 tries.
* We have to put in place a catch-all route rule so that other paths still get
  sent to the backends

## Testing the route
This is a more trivial case then the last, but still worth testing. Firstly,
lets show that the path matching works even with a query string:

```python
(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-search.default.svc.cluster.local" + 
        RemoteSearchService.SEARCH + "?term=foo",
    headers={},
)
rule = matched["rules"][rule_idx]
assert "timeouts" in rule
assert "retry" in rule
```

Now lets show the fallback route is not getting any timeouts set:

```python
(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-search.default.svc.cluster.local/foo/",
    headers={},
)
rule = matched["rules"][rule_idx]
assert not "timeouts" in rule
assert not "retry" in rule
```

## Run The Example

To apply the example to the cluster and see the changes, activate the virtualenv
you created while setting up WineInfo, and run `python
./junction/search-retries-and-timeouts.py`. You should see something like this:

```bash
$ python ./junction/search-retries-and-timeouts.py
```

Now when you search for things in the UI, while still nor quite as snappy
as before we had the issue, you should see things resolving much faster. Note
you may also see the occasional failure, when all 5 tries hit the unlucky
path, and timeout.

## CleanUp

Finally the Kubernetes team works out the problem. Turns out it was a noisy
neighbor using too much of the disk. For this simulation, that can be done by
going to `http://localhost:8010/admin` and clearing the value.

There is no requirement to roll back the timeout, in fact theres a good argument
a policy should be in place in the steady state. However for the purposes of
this demo, we shall roll back the functionality just to have things clean for
later steps.

```bash
kubectl delete httproute/wineinfo-search
```