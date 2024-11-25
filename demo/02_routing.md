# Simple Routing

Routes are one of the most fundamental building blocks in Junction. They give
you control over where clients send traffic based on the contents of a request.

## Background

The WineInfo catalog team has just done a huge re-write of the catalog service
and moved all the catalog data from PineScaleDB to to ElasticRiak. After months
of migrating, they're ready to start handling new traffic. WineInfo's service
oriented architecture means that they can slowly roll out the new catalog by
first testing it with any logged-in site admins.

Like we mentioned in the introduction, WineInfo is deployed as microservices on
Kubernetes. If we check out the WineInfo cluster we can see a Service and a
Deployment for the catalog service. It's creatively called `wineinfo-catalog`.

```text
$ kubectl get svc/wineinfo-catalog
NAME                       TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/wineinfo-catalog   ClusterIP   10.43.180.24   <none>        80/TCP    11m
$ kubectl get svc/wineinfo-catalog
NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/wineinfo-catalog   1/1     1            1           11m
```

We can also see the next version of the catalog that the team has been working
on. It's creatively called `wineinfo-catalog-next`.

```text
$ kubectl get svc/wineinfo-catalog-next
NAME                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
wineinfo-catalog-next   ClusterIP   10.43.139.203   <none>        80/TCP    10m
$ kubectl get deploy/wineinfo-catalog-next
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
wineinfo-catalog-next   1/1     1            1           10m
```

## Routing with Junction

To roll out the new catalog to just logged-in admins, we're going to use
Junction to build Route for the WineInfo service and deploy it to all of
our services dynamically. This won't involve changing code or rebuilding
container images - we're just writing a little bit of Python to generate and
publish configuration.

Note that our configuration doesn't _have_ to be Python, it could be any
language Junction supports. Since WineInfo is a Python service, it makes sense
for us to keep our configuration in the same language as our source code, people
are comfortable with it.

> [!NOTE]
>
> All of the code for this example is in [catalog-preview.py](../junction/catalog-preview.py).

To reference the catalog Services, we'll use Junction `KubeService` targets.

```python
catalog: Target = {
    "name": "wineinfo-catalog",
    "namespace": "default",
}
catalog_next: Target = {
    "name": "wineinfo-catalog-next",
    "namespace": "default",
}
```

Our goal here is to only route logged-in administrators to the new version of
the catalog service. In our wine info services, when someone is logged in, we
add the 'x-wineinfo-user' header to every request, and pass that along.

We can use that header to identify all traffic from WineInfo admins. To use
Junction to do that, we'll declare a match on headers that only matches when
the "x-wineinfo-user" header has exactly the value "admin".

```python
is_admin: RouteMatch = {"headers": [{"name": "x-wineinfo-user", "value": "admin"}]}
```

To start moving traffic around, we need a Route. A Route is kind of like a
declarative set of routes in an HTTP server. It can match on paths or on things
like headers or query parameters. This Route is going to tell Junction to send
all traffic from admins to the catalog-next service and all other trafic to the
normal catalog service.

Here's the whole Route, before we walk through it bit-by-bit.

```python
route: Route = {
    "vhost": catalog,
    "rules": [
        {
            "matches": [is_admin],
            "backends": [{**catalog_next, "port": 80}],
        },
        {
            "backends": [{**catalog, "port": 80}],
        },
    ],
}
```

### VirtualHosts

All Routes have a VirtualHost, which is what `vhost` is short for. The term
VirtualHost is borrowed from networking, and is an abstract representation of a
place to send traffic. In a Route, a VirtualHost determines the URL hostname
that a Route will match.

```python
catalog: Target = {
    "name": "wineinfo-catalog",
    "namespace": "default",
}

route: Route = {
    "vhost": catalog,
    # ...
}
```

A Kubernetes VirtualHost, like the `catalog` service, represents all of the Pods
in a Kubernetes service, and will match URLs that look like
`${name}.${namespace}.svc.cluster.local`. You can also use a DNS VirtualHost,
which represents a hostname in DNS, to make a route match any valid DNS name
you'd like - the VirtualHost `{"hostname": "example.com"}` would match URLs that
look like `example.com`.

When specifying a VirtualHost, we're allowed - but not required - to specify a a
port. Here, we want this route to apply for all requests, no matter what port
they're using, so we omit the port.

### RouteRules

Every Route has a set of `RouteRules` that determine what actually happens to
traffic.  RouteRules have a set of matches, and if any of them match an outgoing
request, it's sent to one of the backends listed as part of the route.

The first rule in the list only has one match, the `is_admin` match we defined
earlier. It has one backend, port 80 on the `catalog_next` target that we also
defined earlier.

```python
        {
            "matches": [is_admin],
            "backends": [{**catalog_next, "port": 80}],
        },
```

The second rule is a catch-all rule. It has no `matches`, which means it matches
any outgoing request. When this rule matches, it sends requests to the catalog
service on port 80.

```python
        {
            "backends": [{**catalog, "port": 80}],
        },
```

For now, that's all there is to know about Routes. As we get further into exploring
Junction, we'll use Routes to match on other parts of outgoing requests or and to
make our applications a more resilient to failure.

## Testing Routes

Before we do anything with this Route, let's make sure it behaves the way we
expect. Because a Route is just data, and Junction runs client-side, we can test
our Route without actually making HTTP requests or talking to a control plane.

Calling `junction.check_route` with a list of Routes returns the Route that we
matched to make sure we got the hostname right, the index of the rule that
matched so we can check on our matching logic, and the backend that requests
will get routed to.

```python
(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-catalog.default.svc.cluster.local",
    headers={},
)
```

 For this logged-out request (it has no `x-wineinfo-user` header), let's double
 check that:

- The route we got back is the right Route. It should have the catalog service
with no port as its VirtualHost.

- The rule that matched is the last rule in our route.

- The backend is also the `catalog` service listening on port 80.

```python
assert route["vhost"] == {**catalog, "port": None}
assert rule_idx == len(route["rules"]) - 1
assert backend == {**catalog, "port": 80}
```

 Let's try again with an authenticated request. All we have to do is set our
 x-wineinfo-user header to the value "admin" and we're good to go.

 This time the Route should be the same, but:

- The first rule should match, not the last rule.

- The backend should be the `catalog-next` service.

```python
(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="<http://wineinfo-catalog.default.svc.cluster.local>",
    headers={"x-wineinfo-user": "admin"},
)
assert route["vhost"] == {**catalog, "port": None}
assert rule_idx == 0
assert backend == {**catalog_next, "port": 80}
```

Nice! All of our tests pass, so we can deploy our route with confidence.

## Run The Example

Let's go apply this configuration. Once we apply it, any Junction client making
an HTTP request to the catalog Service will start routing requests based on
whether or not they're logged in as an admin.

To apply the example to the cluster and see the changes, activate the virtualenv
you created while setting up WineInfo, and run `python ./junction/catalog-preview.py`.
You should see something like this:

```text
$ python ./junction/catalog-preview.py
httproute.gateway.networking.k8s.io/wineinfo-catalog created
```

Once you apply the changes click around the WineInfo page a little. Try
switching between an `anonymous` user, a `customer` and an `admin`. You might
notice that when you're logged in as an `admin`, things start to look a little
funny. Try searching for "germany".

![mojibake-homepage](./images/mojibake-search.jpg)

Uh oh... maybe the new catalog service isn't ready for primetime yet. Log back in as
a `customer` or an `anonymous` user, and convince yourself that this is a problem
with the new catalog service.

Once you've done that, let's remove the Junction route, so all requests now go
to the current `catalog` service.

```text
kubectl delete httproute/wineinfo-catalog
```

Log back in as an admin, click around, and convince yourself things are back to
normal. Phew.
