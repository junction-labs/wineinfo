# Retries and Timeouts

Setting retries and timeouts is something that we are all used to doing in
service oriented architectures, usually in static config, deployed with the
client. Junction gives service owners the ability to dynamically change both
settings and retries.

To enable this demo, reconfigure Kubernetes with:
```bash
kubectl apply -f deploy/03_retries.yaml
```

> [!NOTE]
>
> All of the code for this example is in
> [03_retries](../junction/03_retries.py).

## Background

The search team has a problem, they are seeing load spikes increasing the
latency of 50% of queries. They have contacted their platform team, who in turn
contacted their cloud provider. They have confirmed a widespread issue with
cross-zone network packet loss, but have no ETA on a resolution, partly because
they say "surely you have timeouts and retries set to address this".
Unfortunately for us the answer from the search team is "no".

To see this issue, go to `http://localhost:8010` and do some searches. You
should be able to verify that 50% of requests now have terrible latency.

## Fixing the issue with Junction 

```python
search_url = "http://wineinfo-search.default.svc.cluster.local"

route: Route = {
    "hostnames": [ jct_route_hostname(search_url) ],
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "timeouts": {"backend_request": 0.1},
            "retry": junction.config.RouteRetry(
                attempts=5, backoff=0.1
            ),
            "backends": [ jct_backend(search_url) ],
        },
        {
            "backends": [ jct_backend(search_url) ],
        },
    ],
}
```

To see it in action, activate the virtualenv you created while setting up
WineInfo, and run `python ./junction/02_routing.py`. You should see something
like this:

```bash
$ python ./junction/03_retries.py.
httproute.gateway.networking.k8s.io/wineinfo-search created
```

Go to the UI again, and do some searches. While the timeouts/retries are not a
perfect way of avoiding cross-zone traffic, you should see much better responses
then before.

## Whats going on

Coming back to our junction config:

```python
search_url = "http://wineinfo-search.default.svc.cluster.local"

route: Route = {
    "hostnames": [ jct_route_hostname(search_url) ],
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "timeouts": {"backend_request": 0.1},
            "retry": junction.config.RouteRetry(
                attempts=5, backoff=0.1
            ),
            "backends": [ jct_backend(search_url) ],
        },
        {
            "backends": [ jct_backend(search_url) ],
        },
    ],
}
```

We see a few things:
* We target a specific method of the service using a path, as that is the only
  one seeing issues and we want to limit the blast radius of a change
* We set timeouts on the backend to 0.2 seconds, a relatively high value since
  our dashboards tell us in normal state, 99.99% of queries complete in this
  time.
* We do up to 3 tries
* Between those tries, we use exponential backoff to avoid the situation where
  our retries of "costly queries" is what overloads the service
* We put in place a catch-all route rule so that other paths still get sent to
  the backends

### Unit Testing

This is a more trivial case then the last, but still worth testing. Firstly,
lets show that the path matching works with a query string:

```python
(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url=search_url + RemoteSearchService.SEARCH + "?term=foo",
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
    url=search_url + "/foo/",
    headers={},
)
rule = matched["rules"][rule_idx]
assert not "timeouts" in rule
assert not "retry" in rule
```

## Cleaning up

To roll back this demo and leave wineinfo in working order for the next one,
run: 

```bash
kubectl delete httproute/wineinfo-search
kubectl apply -f deploy/wineinfo.yaml
```

Next head on over to [04_ring_hash.md](04_ring_hash.md).