# Retries and Timeouts

Setting retries and timeouts is something that we are all used to doing in service
oriented architectures, usually in static config, deployed with the client. Junction 
gives service owners the ability to dynamically change both settings and retries,
with the ability to unit test the configuration before it is rolled out into production.

## Background

The search team has a problem, they are seeing load spikes increasing the latency of 50% of queries
They have tried restarting the service, but
to no avail, it seems to be some sort of noisy neighbor problem and they are waiting for the
Kubernetes team to engage to help. They need to to something to mitigate the damage sooner.

## Timeouts

They decide to start with a dynamic timeout, knowing the user will be able to retry
if it happens. 

## Retries

The timeouts are working, but it doesn't look like the Kubernetes team will be able to 
mitigate any time soon, and users are getting frustrated with the need to retry. Thus the
team decides to put in place retries. 

## CleanUp

Finally the Kubernetes team works out the problem. Turns out it was a noisy neighbor using 
too much of the disk. With that, the team rolls back.

```text
kubectl delete httproute/wineinfo-search
```
