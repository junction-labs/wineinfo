#!/usr/bin/env bash

# build and deploy the wineinfo services to a k3d cluster
# optionally, run in local mode, which means using the current kubectl context
# and not creating a k3d cluster.

set -euo pipefail

# Parse command line arguments
LOCAL_MODE=false
NAMESPACE="default"

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            LOCAL_MODE=true
            shift
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--local] [--namespace NAMESPACE]"
            exit 1
            ;;
    esac
done

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
        k3d cluster create "$cluster_name" -p "8010-8011:30010-30011@loadbalancer" --image rancher/k3s:latest
    fi
}

create_openai_secret() {
    if [ -n "${OPENAI_API_KEY:-}" ]; then
        echo "Creating OpenAI API key secret in namespace ${NAMESPACE}..."
        kubectl create secret generic openai-api-key \
            --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
            --namespace="${NAMESPACE}" \
            --dry-run=client -o yaml | kubectl apply -f -
    else
        echo "OPENAI_API_KEY not set, skipping secret creation"
    fi
}

run_wineinfo() {
    if ! kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
        echo "Creating namespace: ${NAMESPACE}"
        kubectl create namespace "${NAMESPACE}"
    else
        echo "Namespace ${NAMESPACE} already exists"
    fi
    kubectl delete -f ./deploy/wineinfo.yaml -n "${NAMESPACE}" || true
    create_openai_secret
    kubectl apply -f ./deploy/wineinfo.yaml -n "${NAMESPACE}"
}

main() {
    local cluster="junction-wineinfo"

    python_services_docker
    frontend_docker

    if [ "$LOCAL_MODE" = true ]; then
        echo "Using current kubectl context"
    else
        echo "Creating k3d cluster: ${cluster}"
        k3d_cluster "${cluster}"
        import_images "${cluster}"
        kubectl config use-context k3d-"${cluster}"
    fi

    run_wineinfo
}

set -x
main
