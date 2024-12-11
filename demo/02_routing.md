# Simple Routing

Routes are one of the most fundamental building blocks in Junction. They give
you control over where clients send traffic based on the contents of a request.

To enable this demo, reconfigure Kubernetes with:
```bash
kubectl apply -f deploy/02_routing.yaml
```

> [!NOTE]
>
> All of the code for this example is in
> [02_routing](../junction/02_routing.py).

## Background

The WineInfo catalog team has just done a huge re-write of the catalog service
and moved all the catalog data from PineScaleDB to to ElasticRiak. In YOLO mode,
they rolled it into production. But now we are getting bug reports from
customers in Germany.

In the UI, try searching for "germany".

![mojibake-homepage](./images/mojibake-search.jpg) FIXME

Looks like they got the character encoding wrong. You engage the team and they
prepare a fix, but this time you want to test its rending production catalog
data correctly before customers are exposed to it. 

## Fixing the issue with Junction 

This junction config will route the "admin" user to the new service
catalog_next.

```python
catalog_url = "http://wineinfo-catalog.default.svc.cluster.local"
catalog_next_url = "http://wineinfo-catalog-next.default.svc.cluster.local"
is_admin: RouteMatch = {"headers": [{"name": "x-username", "value": "admin"}]}

route: Route = {
    "hostnames": [ jct_url(catalog) ],
    "rules": [
        {
            "matches": [is_admin],
            "backends": [ catalog_next ],
        },
        {
            "backends": [ catalog],
        },
    ],
}

kubectl_apply(junction.dump_kube_route(route))
```

To see it in action, activate the virtualenv you created while setting up
WineInfo, and run `python ./junction/02_routing.py`. You should see something
like this:

```bash
$ python ./junction/02_routing.py.
httproute.gateway.networking.k8s.io/wineinfo-catalog created
```

Now go to the UI again, and you should see while other customers are still
seeing the bad data, if you switch to admin, you do indeed see that things are
now fixed.

![mojibake-homepage](./images/mojibake-search.jpg) FIXME


## Whats going on

### Kube setup

Like we mentioned in the introduction, WineInfo is deployed as microservices on
Kubernetes. If we check out the WineInfo cluster we can see a Service and a
Deployment for the catalog service. It's creatively called `wineinfo-catalog`.

```bash
$ kubectl get svc/wineinfo-catalog
NAME                       TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/wineinfo-catalog   ClusterIP   10.43.180.24   <none>        80/TCP    11m
$ kubectl get deployment/wineinfo-catalog
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
wineinfo-catalog   1/1     1            1           90m
```

We can also see the next version of the catalog that has the fix. It's
creatively called `wineinfo-catalog-next`.

```bash
$ kubectl get svc/wineinfo-catalog-next
NAME                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
wineinfo-catalog-next   ClusterIP   10.43.139.203   <none>        80/TCP    10m
$ kubectl get deploy/wineinfo-catalog-next
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
wineinfo-catalog-next   1/1     1            1           10m
```

### Routes

To start moving traffic around, we need a Route. A Route is kind of like a
declarative set of routes in an HTTP server. It can match on paths or on things
like headers or query parameters. This Route is going to tell Junction to send
all traffic from admins to the catalog-next service and all other traffic to the
normal catalog service.

Here's the whole Route again, before we walk through it bit-by-bit.

```python
catalog_url = "http://wineinfo-catalog.default.svc.cluster.local"
catalog_next_url = "http://wineinfo-catalog-next.default.svc.cluster.local"

route: Route = {
    "hostnames": [ "foo.cd" ],
    "rules": [
        {
            "matches": [is_admin],
            "backends": [service: catalog_next, port: 80, weight, 1],
        },
        {
            "backends": [jct_backend(catalog_url)],
        },
    ],
}
```

Routes are the handing point for junction integration, hooking via the hostname
passed in a HTTP request. The jct_route_hostname() is nothing but a helper
function to extract the hostname from a URL. If we didn't care about
duplication, we could have just written
`"wineinfo-catalog.default.svc.cluster.local"` directly.

Routes also are allowed - but not required - to specify a list of ports. Here,
we want this route to apply for all requests, no matter what port they're using,
so we omit the port.

### RouteRules

Every Route has a set of `RouteRules` that determine what actually happens to
traffic.  RouteRules have a set of matches, and if any of them match an outgoing
request, it's sent to one of the backends listed as part of the route.

Our goal here was to only route logged-in administrators to the new version of
the catalog service. In our wine info services, when someone is logged in, we
add the 'x-username' header to every request, and pass that along.

We can use that header to identify all traffic from WineInfo admins. To use
Junction to do that, we'll declare a match on headers that only matches when the
"x-username" header has exactly the value "admin".

```python
is_admin: RouteMatch = {"headers": [{"name": "x-username", "value": "admin"}]}
```

The first rule in the list only has one match, the `is_admin` match we defined
earlier, routing to he backend at `catalog_next_url`.

```python
        {
            "matches": [is_admin],
            "backends": [jct_backend(catalog_next_url)],
        },
```

The second rule is a catch-all rule. It has no `matches`, which means it matches
any outgoing request. When this rule matches, it sends requests to the service
on `catalog_url`.

```python
        {
            "backends": [jct_backend(catalog_url)],
        },
```

For now, that's all there is to know about Routes. As we get further into
exploring Junction, we'll use Routes to match on other parts of outgoing
requests or and to make our applications a more resilient to failure.

### Backends

In the last section, you might notice the "jct_backend()" method. This is a
little helper method that extracts information from the URL, and loads it into a
Dictionary. 

Junction supports two types of Backend. The first is where the IP's are looked
up in DNS in the client. The second is where the IP's are pulled from Kubernetes
and sent down to the client directly. For services in Kubernetes, the second is
the recommended option, but junction wants to give full control to configure
either behavior.

Thus, if we wanted to keep the default behavior, but be explicit around
specifying a backend, we would do:

```python
backend = {
    "type": "Kube",
    "name": "wineinfo-catalog",
    "namespace": "default",
    "port": 80,
}
```

If we for some reason wanted to flip to DNS lookups on the IP, we could change
the behavior with:

```python
backend = {
    "type": "Dns",
    "hostname": "wineinfo-catalog.default.svc.cluster.local",
    "port": 80,
}
```

Note that unlike routes, backends require a port. That is because we need to
know where to send the traffic.

## Testing Routes

Because a Route is just data, and Junction runs client-side, we can test our
Route without actually making HTTP requests or talking to a control plane.

Calling `junction.check_route` with a list of Routes returns the Route that we
matched to make sure we got the hostname right, the index of the rule that
matched so we can check on our matching logic, and the backend that requests
will get routed to.

```python
(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url=catalog_url,
    headers={},
)
```

 For this logged-out request (it has no `x-username` header), let's double check
 that:

- The rule that matched is the last rule in our route.

- The backend is also the `catalog` service listening on port 80.

```python
assert rule_idx == len(route["rules"]) - 1
assert backend == jct_backend(catalog_url)
```

 Let's try again with an authenticated request. All we have to do is set our
 x-username header to the value "admin" and we're good to go.

 This time the Route should be the same, but:

- The first rule should match, not the last rule.

- The backend should be the `catalog-next` service.

```python
(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url=catalog_url,
    headers={"x-username": "admin"},
)
assert rule_idx == 0
assert backend == jct_backend(catalog_next_url)
```

Nice! All of our tests pass, so we can deploy our route with confidence.

## Running in production

```
kubectl_apply(junction.dump_kube_route(route))
```

## Cleaning up

To roll back this demo and leave wineinfo in working order for the next one,
run: 

```bash
kubectl delete httproute/wineinfo-catalog
kubectl apply -f deploy/wineinfo.yaml
```

Next head on over to [03_retries.md](03_retries.md).