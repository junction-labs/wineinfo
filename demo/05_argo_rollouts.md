# Argo Rollouts

In this demo, we integrate Junction with [Argo
Rollouts](https://argoproj.github.io/rollouts/) and demonstrate how Junction
unlocks progressive delivery capabilities.

Progressive delivery is a continuous delivery technique that gradually rolls out
software changes to a subset of users before full release to minimize risk,
enable quick rollbacks. 

Now, this may sound exactly like what we did in the routing demo. That is
correct, except Argo Rollouts allows us to put in place standard policies that
can be followed for all rollouts to production, making sure they all
go through the same safety steps. No more YOLO.

In our case, we are going to put the following policy on the catalog service's 
rollouts:
- Rollout to admin user, require explicit sign off before going further
- Rollout to 25% of traffic, require explicit sign off before going further
- Rollout to all nodes.

In Argo Rollout terms, this is expressed as:

```yaml
      - setCanaryScale:
          replicas: 1
      - setHeaderRoute:
          name: "argo-rollouts"
          match:
          - headerName: x-username
            headerValue:
              exact: admin
      - pause: {}
      - setCanaryScale:
          matchTrafficWeight: true
      - setHeaderRoute:
          name: "argo-rollouts"
      - setWeight: 25
      - pause: {}
      - setWeight: 100
```

## Setting up Argo Rollouts

To install the Argo Rollouts controller, its command line tool, its CRDs, and
its policies for manipulating the Gateway API, run:

```bash
brew install argoproj/tap/kubectl-argo-rollouts
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
kubectl apply -f ./deploy/05_argo_rollouts_install.yaml
kubectl patch deployment argo-rollouts -n argo-rollouts --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/args", "value": ["--loglevel", "debug"]}]'
kubectl rollout restart deploy -n argo-rollouts
```

Now to migrate the catalog service service to use our Argo Rollout
policy rather than a Deployment:

```bash
kubectl apply -f ./deploy/05_argo_rollouts_catalog_migrate.yaml
kubectl argo rollouts status wineinfo-catalog --watch
kubectl delete deployment/wineinfo-catalog
kubectl apply -f ./deploy/05_argo_rollouts_catalog_policy.yaml
```

You can now see the rollout installed with:
```bash
$ kubectl argo rollouts get rollout wineinfo-catalog
Name:            wineinfo-catalog
Namespace:       default
Status:          ✔ Healthy
Strategy:        Canary
  Step:          9/9
  SetWeight:     100
  ActualWeight:  100
Images:          wineinfo-python:latest (stable)
Replicas:
  Desired:       4
  Current:       4
  Updated:       4
  Ready:         4
  Available:     4

NAME                                          KIND        STATUS     AGE  INFO
⟳ wineinfo-catalog                            Rollout     ✔ Healthy  12s
└──# revision:1
   └──⧉ wineinfo-catalog-765b5c6499           ReplicaSet  ✔ Healthy  12s  stable
      ├──□ wineinfo-catalog-765b5c6499-4nlgp  Pod         ✔ Running  12s  ready:1/1
      ├──□ wineinfo-catalog-765b5c6499-jnbq9  Pod         ✔ Running  12s  ready:1/1
      ├──□ wineinfo-catalog-765b5c6499-lj48f  Pod         ✔ Running  12s  ready:1/1
      └──□ wineinfo-catalog-765b5c6499-mjrmb  Pod         ✔ Running  12s  ready:1/1
```

We also switched to our buggy deployment to set up the demo. You can verify
character encoding is once again borked:

![mojibake-homepage](./images/mojibake-search.jpg)

## Argo Rollouts to the (safe) rescue - step 1, admin rollout

Lets kick off the deployment of the fix. Normally we would kick off the rollout 
by patching in a new container version. In our case we are using an environment 
variable to simulate the changed behavior. So lets patch it in:
```bash
kubectl patch rollout wineinfo-catalog --type json -p '[{"op": "remove", "path": "/spec/template/spec/containers/0/env"}]'
```

The Argo Rollouts operator sees this and starts our deployment. You can see it
with `kubectl argo rollouts get rollout wineinfo-catalog`. 

This first step rolls out only to admin user, so go to the UI, change to Admin, 
and verify the bug is fixed:

![normal-homepage](./images/homepage.jpg)

Looking under the covers, you can also see the route it installed with:
```bash
$ kubectl describe httproutes.gateway.networking.k8s.io/wineinfo-catalog
Name:         wineinfo-catalog
Namespace:    default
Labels:       <none>
Annotations:  <none>
API Version:  gateway.networking.k8s.io/v1
Kind:         HTTPRoute
Metadata:
  Creation Timestamp:  2024-12-20T19:33:20Z
  Generation:          15
  Resource Version:    59311
  UID:                 ecb271a0-f5c0-4b44-90c1-404d06c091a9
Spec:
  Parent Refs:
    Group:
    Kind:       Service
    Name:       wineinfo-catalog
    Namespace:  default
  Rules:
    Backend Refs:
      Group:
      Kind:    Service
      Name:    wineinfo-catalog
      Port:    80
      Weight:  100
      Group:
      Kind:    Service
      Name:    wineinfo-catalog-canary
      Port:    80
      Weight:  0
    Matches:
      Path:
        Type:   PathPrefix
        Value:  /
    Backend Refs:
      Group:
      Kind:    Service
      Name:    wineinfo-catalog-canary
      Port:    80
      Weight:  0
    Matches:
      Headers:
        Name:   x-username
        Type:   Exact
        Value:  admin
      Path:
        Type:   PathPrefix
        Value:  /
```

## Argo Rollouts to the (safe) rescue - step 2 and 3

We have verified the fix is working. Promote to the next step with:
```bash
kubectl argo rollouts promote wineinfo-catalog
```

That promotes to 25% of the fleet. Now you should be able to go to a non-admin
user, and see that 25% of the time your search is getting the right result. 

So  finish the deployment to 100% with one more promotion:
```bash
kubectl argo rollouts promote wineinfo-catalog
```

You can see it is go out with with:
```bash
kubectl argo rollouts get rollout wineinfo-catalog --watch
```

Further the other thing we can see, is that Argo has used dynamic tagging so
that the pods are now all running for the non-canary service. Thus we no longer
have to jump service names back and forth with each deployment.

```bash
$ kubectl describe httproutes.gateway.networking.k8s.io/wineinfo-catalog
Name:         wineinfo-catalog
Namespace:    default
Labels:       <none>
Annotations:  <none>
API Version:  gateway.networking.k8s.io/v1
Kind:         HTTPRoute
Metadata:
  Creation Timestamp:  2024-12-24T01:12:34Z
  Generation:          8
  Resource Version:    1457
  UID:                 2aa74963-6ef4-46e0-a635-87655cbf6b63
Spec:
  Parent Refs:
    Group:
    Kind:       Service
    Name:       wineinfo-catalog
    Namespace:  default
  Rules:
    Backend Refs:
      Group:
      Kind:       Service
      Name:       wineinfo-catalog
      Namespace:  default
      Port:       80
      Weight:     100
      Group:
      Kind:       Service
      Name:       wineinfo-catalog-canary
      Namespace:  default
      Port:       80
      Weight:     0
    Matches:
      Path:
        Type:   PathPrefix
        Value:  /
```

## Cleaning up for the next step

This is the current end of the demo. Thanks for trying Junction!

To restore the Wineinfo shop, run:

```bash
kubectl delete -f deploy/05_argo_rollouts_catalog_install.yaml
kubectl delete -f ./deploy/05_argo_rollouts_install.yaml
kubectl delete -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
kubectl delete namespace argo-rollouts
kubectl delete -f deploy/wineinfo.yaml
kubectl apply -f deploy/wineinfo.yaml
```

If you're fully done, you can fully delete your k3d cluster with:

```bash
k3d cluster delete junction-wineinfo
```
