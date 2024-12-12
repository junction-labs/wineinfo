# Retries and Timeouts

Setting retries and timeouts is something that we are all used to doing in
service oriented architectures, usually in static config, deployed with the
client. Junction gives service owners the ability to change both without needing
to do a new deployment.

To enable this demo, reconfigure Kubernetes with:
```bash
kubectl apply -f deploy/03_retries.yaml
```

> [!NOTE]
>
> All of the code for this example is in
> [03_retries](../junction/03_retries.py).

## Background

The search team has a problem, they are seeing load spikes, increasing the
latency of queries. They have contacted their platform team, who in turn
contacted their cloud provider. They have confirmed a widespread issue with
cross-zone network packet loss, but have no ETA on a resolution, and say
"timeouts and retries should mitigate address this". Unfortunately the search
service does not have them.

To see this issue, go to `http://localhost:8010` and do some searches. You
should be able to verify that 50% of requests now have terrible latency.

## Fixing the issue with Junction 

This config set timeouts on the RemoteSearchService.SEARCH method to 0.1 seconds
initially, with exponential backoff doing up to 5 attempts.

```python
search = junction.config.ServiceKube(type="kube", name="wineinfo-search", namespace="default")

route: junction.config.Route = {
    "id": service_hostname(search),
    "hostnames": [ service_hostname(search) ],
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "timeouts": {"backend_request": 0.1},
            "retry": junction.config.RouteRetry(
                attempts=5, backoff=0.1
            ),
            "backends": [ { **search, "port": 80 } ],
        },
        {
            "backends": [ { **search, "port": 80 } ],
        },
    ],
}
```

To see it in action, activate the virtualenv you created while setting up
WineInfo, and run `python ./junction/03_retries.py`. You should see something
like this:

```bash
$ python ./junction/03_retries.py
httproute.gateway.networking.k8s.io/wineinfo-search-default-svc-cluster-local created
```

Go to the UI again, and do some searches. While the timeouts/retries are not a
perfect way of avoiding cross-zone traffic, you should see much better responses
then before.

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
kubectl delete httproute/wineinfo-search-default-svc-cluster-local
kubectl apply -f deploy/wineinfo.yaml
```

Next head on over to [04_ring_hash.md](04_ring_hash.md).
