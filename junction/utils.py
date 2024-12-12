import tempfile
import subprocess
import junction

def service_hostname(service: junction.config.Service) -> str:
    """
    Returns the hostname for a junction Service, to be used in 
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
