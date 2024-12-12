# Simple Routing

Routes are one of the most fundamental building blocks in Junction. They give
you control over where clients send traffic based on the contents of a request.
In this demo we use routing to show a release candidate to a selected audience.

To enable this demo, reconfigure Kubernetes with:
```bash
kubectl apply -f deploy/02_routing.yaml
```

> [!NOTE]
>
> All of the code for this example is in
> [02_routing](../junction/02_routing.py).

## Background

The WineInfo catalog team has just done a huge rewrite of the catalog service
and moved all the catalog data from PineScaleDB to to ElasticRiak. In YOLO mode,
they rolled it into production. But now we are hearing bug reports from
customers in Europe about character encoding.

In the UI, try searching for "germany". You should see something like:

![mojibake-homepage](./images/mojibake-search.jpg) FIXME

Looks like they got the character encoding wrong! The team prepares a fix, but
this time you want to test its rendering catalog data correctly in production,
before all customers are exposed to it, by just routing the "admin" users to the
release candidate service. 

## Fixing the issue with Junction 

Junction needs to route requests for the "admin" user to the release candidate
service named catalog-next. This is the Junction configuration to do so:

```python
catalog = junction.config.ServiceKube(type="kube", name="wineinfo-catalog", namespace="default")
catalog_next = junction.config.ServiceKube(type="kube", name="wineinfo-catalog-next", namespace="default")
is_admin = junction.config.RouteMatch(headers = [{"name": "x-username", "value": "admin"}])

route: junction.config.Route = {
    "id": service_hostname(catalog).replace(".", "-"),
    "hostnames": [ service_hostname(catalog) ],
    "rules": [
        {
            "matches": [is_admin],
            "backends": [{ **catalog_next, "port": 80 }],
        },
        {
            "backends": [{ **catalog, "port": 80 }],
        },
    ],
}

kubectl_apply(junction.dump_kube_route(route=route, namespace="default"))
```

To see it in action, activate the virtualenv you created while setting up
WineInfo, and run `python ./junction/02_routing.py`. You should see:

```bash
$ python ./junction/02_routing.py
httproute.gateway.networking.k8s.io/wineinfo-catalog-default-svc-cluster-local created
```

Now go to the UI again, and you should see while other customers are still
seeing the bad data, if you switch to admin, you do indeed see that things are
fixed.

![mojibake-homepage](./images/mojibake-search.jpg) FIXME

Hooray! We are now happy to deploy this more broadly.

## Whats going on

### Kube setup

Like we mentioned in the introduction, WineInfo is deployed as microservices on
Kubernetes. If we check out the WineInfo cluster we can see a Service and a
Deployment for the catalog service. It's called `wineinfo-catalog`.

```bash
$ kubectl get svc/wineinfo-catalog
NAME                       TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/wineinfo-catalog   ClusterIP   10.43.180.24   <none>        80/TCP    11m
$ kubectl get deployment/wineinfo-catalog
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
wineinfo-catalog   1/1     1            1           90m
```

We can also see the release candidate that has the fix. It's called
`wineinfo-catalog-next`.

```bash
$ kubectl get svc/wineinfo-catalog-next
NAME                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
wineinfo-catalog-next   ClusterIP   10.43.139.203   <none>        80/TCP    10m
$ kubectl get deploy/wineinfo-catalog-next
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
wineinfo-catalog-next   1/1     1            1           10m
```

### Routes

To start moving traffic around with Junction, we need a Route. A Route can match
on URL paths, headers or query parameters, and configure specific behavior.

Here's the whole Route again, before we walk through it bit-by-bit.

```python
catalog = junction.config.ServiceKube(type="kube", name="wineinfo-catalog", namespace="default")
catalog_next = junction.config.ServiceKube(type="kube", name="wineinfo-catalog-next", namespace="default")
is_admin = junction.config.RouteMatch(headers = [{"name": "x-username", "value": "admin"}])

route: junction.config.Route = {
    "id": service_hostname(catalog).replace(".", "-"),
    "hostnames": [ service_hostname(catalog) ],
    "rules": [
        {
            "matches": [is_admin],
            "backends": [{ **catalog_next, "port": 80 }],
        },
        {
            "backends": [{ **catalog, "port": 80 }],
        },
    ],
}
```

One thing we see here, is routes first match the hostname passed in a HTTP
request. In this case the name for the hostname is the same as the name for the
catalog service. But any particular hostname would work. Routes also are
allowed, but not required - to specify a list of ports. Here, we want this route
to apply for all requests, no matter what port they're using, so we omit the
port.

### RouteRules

Every Route has a set of `RouteRules` to match traffic within them.  
RouteRules have a set of matches, and if any of them match an outgoing request,
it's sent to one of the backends listed as part of the route.

Our goal here is to only route logged-in administrators to the new version of
the catalog service. In our wineinfo services, when someone is logged in, we add
the 'x-username' header to every request, and pass that along. We can use that
header to identify all traffic from WineInfo admins. To use Junction to do that,
we'll declare a match on headers that only matches when the "x-username" header
has exactly the value "admin".

```python
is_admin = junction.config.RouteMatch(headers = [{"name": "x-username", "value": "admin"}])
```

The first rule in the rules list only has one match, on `is_admin` routing to
the `catalog_next` service.

```python
        {
            "matches": [is_admin],
            "backends": [{ **catalog_next, "port": 80 }],
        },
```

The second rule is a catch-all rule. It has no `matches`, which means it matches
any outgoing request. When this rule matches, it sends requests to the `catalog_url`
service.

```python
        {
            "backends": [{ **catalog, "port": 80 }],
        },
```

For now, that's all there is to know about Routes. As we get further into
exploring Junction, we'll use Routes to match on other parts of outgoing
requests or and to make our applications a more resilient to failure.

### Backend Services

Junction supports two types of Backend services. The first is where the IP's are
looked up in DNS in the client. The second is where the IP's are pulled from
Kubernetes and sent down to the client directly. For services in Kubernetes, the
second is the recommended option, but junction wants to give full control to
configure either behavior.

If we for some reason wanted to flip to DNS lookups of the IPs, we could change
the behavior with:

```python
catalog = junction.config.ServiceDns(type="dns", hostname="wineinfo-catalog.default.svc.cluster.local")
catalog_next = junction.config.ServiceDns(type="dns", hostname="wineinfo-catalog-next.default.svc.cluster.local")
```

Note that unlike routes, backends require a port. That is because we need to
know where to send the traffic.

## Unit Testing

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
    url="http://" + service_hostname(catalog) + "/",
    headers={},
)
assert rule_idx == len(route["rules"]) - 1
assert backend == { **catalog, "port": 80 }
```

This double checks that:
- The rule that matched is the last rule in our route.
- The backend is also the `catalog` service listening on port 80.

 Let's try again with an authenticated request. All we have to do is set our
 x-username header to the value "admin" and we're good to go.

```python
(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://" + service_hostname(catalog) + "/",
    headers={"x-username": "admin"},
)
assert rule_idx == 0
assert backend == { **catalog_next, "port": 80 }
```

Here we check:
- The first rule should match, not the last rule.
- The backend should be the `catalog-next` service.

Nice! All of our unit tests pass, so we can deploy our route with confidence.

## Running in production

Within the script the command that does the deployment is:

```
kubectl_apply(junction.dump_kube_route(route))
```

Here we see the `dump_kube_route` method, which emits a API Gateway HTTPRoute
configuration for our Junction config. `kubectl_apply` just calls kubectl to apply
the config, installing it on the cluster, so that `ezbake` can pick it up and 
feed it to all the junction clients.

## Cleaning up

To roll back this demo and leave the application in working order for the next
demo, run: 

```bash
kubectl delete httproute.gateway.networking.k8s.io/wineinfo-catalog-default-svc-cluster-local
kubectl apply -f deploy/wineinfo.yaml
```

Next, head on over to [03_retries.md](03_retries.md).
