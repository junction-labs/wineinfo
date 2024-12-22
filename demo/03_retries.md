# Retries and Timeouts

The search team needs help; they are seeing load spikes, increasing the
latency of queries. They have contacted their platform team, who 
contacted their cloud provider. They have confirmed a widespread 
cross-zone network packet loss issue but have no ETA on a resolution and say
"timeouts and retries should mitigate address this". Unfortunately, the search
service does not have them.

Simulate the load spikes by running:

```bash
kubectl apply -f deploy/03_retries.yaml
```

To see this issue, go to `http://localhost:8010` and do some searches. You
should be able to feel that 50% of all of your searches have terrible latency.

Setting retries and timeouts is something that we are all used to doing in
service-oriented architectures. Still, usually, it's done in static config and
deployed as a change to a service. Junction allows service owners to
change both without needing to do a new deployment. All we have to do is
update a Route.

```bash
$ python ./junction/03_retries.py
httproute.gateway.networking.k8s.io/wineinfo-search created
```

Go to the UI again and do some more searching. While timeouts/retries are not a
perfect way of avoiding the issue with our cloud vendor; search responses should
feel much better than they did before.

## What Just Happened?

To quickly add retries to the search service, we added another Route. This time,
we matched any request heading for the `search` API call on the search service, and
made sure it has retry and timeout settings.

Because Junction is just code, we're importing parts of our application codebase
(`RemoteSearchService.SERVICE`) so we don't have to remember what the actual
path is, and using a helper function to generate the hostname for our Service.

```python
search: config.Service = {
    "type": "kube",
    "name": "wineinfo-search",
    "namespace": "default",
}

route: config.Route = {
    "id": service_hostname(search).replace(".", "-"),
    "hostnames": [service_hostname(search)],
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "timeouts": {
                "backend_request": 0.1,
            },
            "retry": {
                "attempts": "5",
                "backoff": 0.1,
            },
            "backends": [{**search, "port": 80}],
        },
        {
            "backends": [{**search, "port": 80}],
        },
    ],
}
```

When clients pick up this configuration change, they automatically start
retrying failed requests without the service team having to change anything else
about their code.

In the `timeout` section, we set the policy that each request should
have a timeout of 100ms. If we wanted to set a timeout for _all_ retries, we
could do that too, but that wouldn't solve our problem here.

In the `retry` section, we're setting the policy that all failed requests get 5
total attempts, and that we should do exponential backoff between each request
starting at roughly 100ms.

This Route looks pretty similar to the Routes we used when [shifting
trafic](./02_routing.md) because `retries` and `timeouts` are also just fields
on a Route.

### Unit Testing

This is a more trivial case than the last, but it is still worth testing. First, lets
show that the path matching works, even when we specify a query string:

```python
(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://" + service_hostname(search) + RemoteSearchService.SEARCH + "?term=foo",
    headers={},
)
rule = matched["rules"][rule_idx]
assert rule["timeouts"]["backend_request"] == 0.1
assert rule["retry"]["attempts"] == 5
```

Now let's show the fallback route is not getting retries or timeouts set:

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

## Cleaning up for the next step

To roll back this demo and leave Wineinfo in working order for the next one,
run:

```bash
kubectl delete httproute/wineinfo-search
kubectl apply -f deploy/wineinfo.yaml
```

Next, head over to [04_ring_hash.md](04_ring_hash.md).

If you're fully done, you can fully delete your k3d cluster with:

```bash
k3d cluster delete junction-wineinfo
```
