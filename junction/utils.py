from typing import Sequence

import tempfile
import subprocess


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
