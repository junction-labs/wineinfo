# Introduction

Welcome to Junction. If you're coming from `README.md` you've already got a full
WineInfo site up and running in a local Kubernetes cluster, and you're ready to
try out Junction.

If you're not coming from `README.md` take a moment to head back there and get
the demo services up and running.

## What's In The Box

The demo cluster you just set up contains two high-level things; a WineInfo
website built with a handful of microservices and a Junction control plane
that's distributing config to all of the clients in the cluster.

The WineInfo site is built for 2024, and contains a Big data catalog service,
a semantic search service, and a recommendations serivce. All of those services
are tied together with an API service that serves up a React frontend.

```text

                        ┌─────────────┐
                        │             │
                        │             │
                        │  Frontend   │
                        │             │
                        │             │
                        └─────┬───────┘
                              │
                              │
                        ┌─────┴───────┐
                        │             │
                        │             │
                        │   Backend   │
                        │             │
                        │             │
                        └─────┬───────┘
                              │
             ┌────────────────┼─────────────────────┐
             │                │                     │
             │                │                     │
             │                │                     │
             │                │                     │
      ┌──────┴──────┐   ┌─────┴───────┐   ┌─────────┴─────────┐
      │             │   │             │   │                   │
      │             │   │             │   │                   │
      │   Catalog   │   │   Search    │   │  Recommendations  │
      │             │   │             │   │                   │
      │             │   │             │   │                   │
      └─────────────┘   └─────────────┘   └───────────────────┘
```

To introduce Junction, we're going to walk through some common tasks you might
have as the WineInfo becomes a successful and growing product organization.
We'll deal with traffic routing to test new features, adding retries to deal
with reliability issues, sharding a service, and more.

To start, head on over to [02_routing.md](02_routing.md).
