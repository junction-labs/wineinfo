import tempfile
import subprocess
import junction


def kube_search_config(namespace="default"):
    """
    Returns a Junction search config that mirrors the /etc/resolv.conf
    that Kubernetes puts in all Pods by default.
    """
    return {
        "search": [
            f"{namespace}.svc.cluster.local",
            "svc.cluster.local",
            "cluster.local",
        ],
        "ndots": 5,
    }


def service_fqdn(service: junction.config.Service) -> str:
    """
    Returns the fqdn for a junction Service, to be used in
    route matching for it.
    """
    if service["type"].lower == "dns":
        return service["hostname"]
    else:
        return f"{service['name']}.{service['namespace']}.svc.cluster.local"


def kubectl_apply(*manifests):
    """
    Run kubectl apply on each manifest individually.

    Shells out to kubectl and uses your current Kube context.
    """
    for manifest in manifests:
        with tempfile.NamedTemporaryFile(mode="w") as f:
            f.write(manifest)
            f.seek(0)
            subprocess.run(
                [
                    "kubectl",
                    "apply",
                    "-f",
                    f.name,
                ]
            )


def kubectl_patch(*manifests):
    """
    Run kubectl patch on each manifest individually.

    Shells out to kubectl and uses your current Kube context.
    """
    for manifest in manifests:
        with tempfile.NamedTemporaryFile(mode="w") as f:
            f.write(manifest)
            f.seek(0)
            subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "-f",
                    f.name,
                    "--patch-file",
                    f.name,
                ]
            )
