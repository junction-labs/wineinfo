""" """
import os, sys
from typing import List
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir)
    )
)
import junction
from utils import kubectl_apply
from junction.config import Target

recs: Target = {
    "name": "wineinfo-recs",
    "namespace": "default",
}
backend: junction.config.Backend = [
    {
        "id": recs,
        "lb": {
            "type": "RingHash",
            "minRingSize": 1024,
            "hashParams": [{"type": "Header", "name": "x-username"}],
        },
    }
]

kubectl_apply(junction.dump_kube_backend(backend))
