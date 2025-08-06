# `wineinfo`

A sample web application demonstrating [Junction][junction].

The app is a wine catalog that's built with a nextjs frontend and multiple
FastAPI Python services to handle traditional full-text search, LLM-based
vector search, and saving bottles to a collection. 

## Environment Set Up

To make it easy to run without being a Kubernetes whiz, it runs in a self-contained 
[`k3d`][k3d] cluster.

To start, you'll need `docker` and `kubectl` installed. This
README won't cover installing them. Once you've gotten both `docker` and
`kubectl` set up, install `k3d` by running:

```bash
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
```

or check out the [official k3d installation instructions][k3d-install]

[junction]: https://github.com/junction-labs/junction-client
[k3d]: https://k3d.io/
[k3d-install]: https://k3d.io/v5.7.4/#install-script

## Start wineinfo

Once you've installed `k3d` (check that it works by running `k3d version`) you
can start the applcation:

```bash
./deploy/wineinfo.sh
```
Once you're done, point your browser at <http://localhost:8010>, and you should
see the working Wineinfo site. 
