#!/usr/bin/env bash

# set up a local k3d cluster with the wineinfo services running in the
# default namespace and ezbake running in the junction namespace.

set -euo pipefail

python_services_docker() {
    docker build \
        --tag wineinfo-python:latest \
        --file python_services/Dockerfile python_services/
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
    kubectl apply -f https://github.com/junction-labs/ezbake/releases/latest/download/install-for-cluster.yml
}

run_wineinfo() {
    kubectl delete -f ./deploy/wineinfo.yaml  || true
    kubectl apply -f ./deploy/wineinfo.yaml
}

main() {
    local cluster="junction-wineinfo"

    k3d_cluster "${cluster}"
    python_services_docker
    frontend_docker
    import_images "${cluster}"

    kubectl config use-context k3d-"${cluster}"
    run_ezbake
    run_wineinfo
}

set -x
main
