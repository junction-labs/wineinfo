import junction
import junction.config as config

from utils import kubectl_patch

embeddings: config.Service = {
    "type": "kube",
    "name": "wineinfo-embeddings",
    "namespace": "default",
}

backend: config.Backend = {
    "id": {**embeddings, "port": 80},
    "lb": {
        "type": "RingHash",
        "min_ring_size": 1024,
        "hash_params": [{"type": "QueryParam", "name": "query"}],
    },
}

kubectl_patch(junction.dump_kube_backend(backend))
