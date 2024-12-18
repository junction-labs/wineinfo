# Introduction

Welcome to Junction. If you're coming from `README.md` you've already got a full
WineInfo site up and running in a local Kubernetes cluster, and you're ready to
try out Junction.

If you're not coming from `README.md` take a moment to head back there and get
the demo services running.

## What's In The Box

The demo cluster you just set up contains two high-level things: a WineInfo
website built with a handful of microservices and a Junction control plane
that's distributing config to all of the clients in the cluster.

The WineInfo site is built for 2024, so of course, our informational wine
website includes microservices and vector search.

The site is made up of a Big Data catalog service, a semantic search service, a
recommendations (recs) service, and a persistent store based on SQLite. 
Those services are tied together with an API service that serves up a React
frontend.

```text
                   ┌─────────────┐
                   │  Frontend   │
                   └─────┬───────┘
                   ┌─────┴───────┐
                   │   Backend   ├──────────────┐
                   └─────┬───────┘              │
        ┌────────────────┼────────────────┐     │
 ┌──────┴──────┐   ┌─────┴───────┐   ┌────┴───┐ │
 │   Catalog   │   │   Search    │   │  Recs  │ │
 └──────┬──────┘   └─────┬───────┘   └────┬───┘ │
        └────────────────┼────────────────┘     │
                         │                      │
                    ┌────┴──────┐               │
                    │  Persist  ├───────────────┘
                    └───────────┘
```

To introduce Junction, we will walk through some everyday tasks you might
have as WineInfo becomes a successful and growing product and organization.
We'll deal with traffic routing to test new features, adding retries to deal
with reliability issues, sharding a service, and more.

Our Wineinfo microservices are written in Python, so this entire demo
is written in Python to stay consistent. Keep in mind as you're reading
that any of these services or configurations could be done in any
language supported by Junction - there's nothing Python-specific about it.

To start, head over to [02_routing.md](02_routing.md).
