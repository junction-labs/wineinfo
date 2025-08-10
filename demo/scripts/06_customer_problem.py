#!/usr/bin/env python3
"""
Demo: Customer Problem - Expensive Wine Recommendations

This demo simulates a customer reporting that the AI sommelier is recommending
expensive wines even when they ask for budget-friendly options. We'll use Junction
routing to route their traffic to a "fixed" version of the service.

Scenario:
1. Customer reports: "I asked for wines under $30 but got $200+ recommendations"
2. We can't reproduce in preprod (normal behavior)
3. We route their specific traffic to a "broken" version to reproduce
4. We fix the issue and route them to the fixed version
"""

import os
import sys
import subprocess
import time
import json
from typing import Dict, Any

# Add the parent directory to the path so we can import junction
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'junction-python'))

from junction import config

def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Command failed: {result.stderr}")
        sys.exit(1)
    return result

def create_routing_config() -> Dict[str, Any]:
    """Create the Junction routing configuration"""
    
    # Define the services
    sommelier_service = config.Service(
        type="kube",
        name="wineinfo-sommelier",
        namespace="default"
    )
    
    sommelier_broken = config.Service(
        type="kube", 
        name="wineinfo-sommelier-broken",
        namespace="default"
    )
    
    sommelier_fixed = config.Service(
        type="kube",
        name="wineinfo-sommelier-fixed", 
        namespace="default"
    )
    
    # Create route to broken service for customer traffic
    customer_route = config.Route(
        name="customer-problem-route",
        service=sommelier_service,
        destination=sommelier_broken,
        match=config.RouteMatch(
            headers=[{
                "type": "RegularExpression",
                "name": "baggage", 
                "value": ".*customer_id=customer_123(,|$).*"
            }]
        )
    )
    
    # Create route to fixed service for admin testing
    admin_route = config.Route(
        name="admin-fixed-route", 
        service=sommelier_service,
        destination=sommelier_fixed,
        match=config.RouteMatch(
            headers=[{
                "type": "RegularExpression",
                "name": "baggage",
                "value": ".*username=admin(,|$).*"
            }]
        )
    )
    
    return {
        "routes": [customer_route, admin_route],
        "services": [sommelier_service, sommelier_broken, sommelier_fixed]
    }

def deploy_services():
    """Deploy the different versions of the sommelier service"""
    
    print("🚀 Deploying sommelier service versions...")
    
    # Deploy the broken version (with expensive bias enabled)
    broken_deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment", 
        "metadata": {
            "name": "wineinfo-sommelier-broken",
            "namespace": "default"
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "wineinfo-sommelier-broken"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "wineinfo-sommelier-broken"
                    }
                },
                "spec": {
                    "containers": [{
                        "name": "sommelier",
                        "image": "wineinfo-sommelier:latest",
                        "env": [
                            {"name": "ENABLE_EXPENSIVE_BIAS", "value": "true"},
                            {"name": "OPENAI_API_KEY", "valueFrom": {"secretKeyRef": {"name": "openai-secret", "key": "api-key"}}}
                        ],
                        "ports": [{"containerPort": 8000}]
                    }]
                }
            }
        }
    }
    
    # Deploy the fixed version (normal behavior)
    fixed_deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "wineinfo-sommelier-fixed", 
            "namespace": "default"
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": "wineinfo-sommelier-fixed"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "wineinfo-sommelier-fixed"
                    }
                },
                "spec": {
                    "containers": [{
                        "name": "sommelier",
                        "image": "wineinfo-sommelier:latest", 
                        "env": [
                            {"name": "ENABLE_EXPENSIVE_BIAS", "value": "false"},
                            {"name": "OPENAI_API_KEY", "valueFrom": {"secretKeyRef": {"name": "openai-secret", "key": "api-key"}}}
                        ],
                        "ports": [{"containerPort": 8000}]
                    }]
                }
            }
        }
    }
    
    # Create services
    broken_service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "wineinfo-sommelier-broken",
            "namespace": "default"
        },
        "spec": {
            "selector": {
                "app": "wineinfo-sommelier-broken"
            },
            "ports": [{"port": 80, "targetPort": 8000}]
        }
    }
    
    fixed_service = {
        "apiVersion": "v1", 
        "kind": "Service",
        "metadata": {
            "name": "wineinfo-sommelier-fixed",
            "namespace": "default"
        },
        "spec": {
            "selector": {
                "app": "wineinfo-sommelier-fixed"
            },
            "ports": [{"port": 80, "targetPort": 8000}]
        }
    }
    
    # Write configs to files
    with open("demo/deploy/06_customer_problem_broken.yaml", "w") as f:
        import yaml
        yaml.dump(broken_deployment, f)
        yaml.dump(broken_service, f)
    
    with open("demo/deploy/06_customer_problem_fixed.yaml", "w") as f:
        import yaml
        yaml.dump(fixed_deployment, f)
        yaml.dump(fixed_service, f)
    
    # Deploy to Kubernetes
    run_command("kubectl apply -f demo/deploy/06_customer_problem_broken.yaml")
    run_command("kubectl apply -f demo/deploy/06_customer_problem_fixed.yaml")
    
    print("✅ Services deployed successfully!")

def deploy_junction_routes():
    """Deploy the Junction routing configuration"""
    
    print("🔀 Deploying Junction routes...")
    
    routing_config = create_routing_config()
    
    # Write the routing config to a file
    with open("demo/deploy/06_customer_problem_routes.yaml", "w") as f:
        import yaml
        yaml.dump(routing_config, f)
    
    # Deploy the routes
    run_command("kubectl apply -f demo/deploy/06_customer_problem_routes.yaml")
    
    print("✅ Junction routes deployed successfully!")

def main():
    """Main demo function"""
    
    print("🍷 Customer Problem Demo: Expensive Wine Recommendations")
    print("=" * 60)
    
    print("\n📋 Scenario:")
    print("Customer reports: 'I asked for wines under $30 but got $200+ recommendations'")
    print("We can't reproduce in preprod (normal behavior)")
    print("We'll route their traffic to a 'broken' version to reproduce the issue")
    print("Then we'll fix it and route them to the fixed version")
    
    print("\n🚀 Step 1: Deploying service versions...")
    deploy_services()
    
    print("\n🔀 Step 2: Deploying Junction routes...")
    deploy_junction_routes()
    
    print("\n✅ Demo setup complete!")
    print("\n📝 Next steps:")
    print("1. Test as customer (customer_id=customer_123): Ask for budget wines")
    print("2. Test as admin (username=admin): Verify fixed behavior")
    print("3. Show how Junction routing solved the problem!")
    
    print("\n🔧 To test:")
    print("- Customer view: Add 'customer_id=customer_123' to baggage header")
    print("- Admin view: Add 'username=admin' to baggage header")
    print("- Normal view: No special headers")

if __name__ == "__main__":
    main() 