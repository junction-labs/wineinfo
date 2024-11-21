#!/bin/bash

# set up a local k3d cluster with the wineinfo services running in the
# default namespace and ezbake running in the junction namespace.

set -euo pipefail

backend_docker() {
    docker build \
        --tag wineinfo-python:latest \
        --file backend/Dockerfile backend/
}

frontend_docker() {
    docker build \
        --tag wineinfo-frontend:latest \
        --file frontend/Dockerfile frontend/
}

import_images() {
    local cluster=$1;

    k3d image import -c "${cluster}" wineinfo-python:latest
    k3d image import -c "${cluster}" wineinfo-frontend:latest
}


k3d_cluster() {
    local cluster_name=$1;

    if k3d cluster list | grep -q "${cluster_name}"; then
        echo "cluster ${cluster_name} exists"
    else
        k3d cluster create "$cluster_name" -p "8010-8011:30010-30011@loadbalancer"
    fi
}

run_ezbake() {
    kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/experimental-install.yaml
    kubectl apply -f ./deploy/ezbake.yaml
}

run_wineinfo() {
    kubectl apply -f ./deploy/wineinfo.yaml
}

main() {
    local cluster="junction-wineinfo"

    k3d_cluster "${cluster}"
    backend_docker
    frontend_docker
    import_images "${cluster}"

    run_ezbake
    run_wineinfo
}

set -x
main
