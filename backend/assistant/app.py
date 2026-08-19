from fastapi import FastAPI
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

app = FastAPI(
    title="Restauranty AI Assistant",
    version="1.0.0"
)

NAMESPACE = "restauranty"


# ---------------------------------------------------------
# Kubernetes configuration
# ---------------------------------------------------------

try:
    # Used when running inside AKS
    config.load_incluster_config()
    print("Using in-cluster Kubernetes configuration")

except ConfigException:
    # Useful when testing locally
    config.load_kube_config()
    print("Using local kubeconfig")


core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
autoscaling_v2 = client.AutoscalingV2Api()


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "assistant"
    }


# ---------------------------------------------------------
# Pod health
# ---------------------------------------------------------

@app.get("/api/assistant/pods")
def get_pods():

    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE
    )

    result = []

    for pod in pods.items:

        ready = False

        if pod.status.container_statuses:
            ready = all(
                container.ready
                for container in pod.status.container_statuses
            )

        restart_count = 0

        if pod.status.container_statuses:
            restart_count = sum(
                container.restart_count
                for container in pod.status.container_statuses
            )

        result.append({
            "name": pod.metadata.name,
            "phase": pod.status.phase,
            "ready": ready,
            "restarts": restart_count,
            "node": pod.spec.node_name
        })

    return result


# ---------------------------------------------------------
# Simple overall health summary
# ---------------------------------------------------------

@app.get("/api/assistant/status")
def cluster_status():

    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE
    )

    unhealthy = []
    healthy = []

    for pod in pods.items:

        ready = False

        if pod.status.container_statuses:
            ready = all(
                container.ready
                for container in pod.status.container_statuses
            )

        if pod.status.phase == "Running" and ready:
            healthy.append(pod.metadata.name)
        else:
            unhealthy.append({
                "name": pod.metadata.name,
                "phase": pod.status.phase
            })

    return {
        "namespace": NAMESPACE,
        "healthy": len(unhealthy) == 0,
        "totalPods": len(pods.items),
        "healthyPods": len(healthy),
        "unhealthyPods": unhealthy
    }


# ---------------------------------------------------------
# Deployments
# ---------------------------------------------------------

@app.get("/api/assistant/deployments")
def get_deployments():

    deployments = apps_v1.list_namespaced_deployment(
        namespace=NAMESPACE
    )

    result = []

    for deployment in deployments.items:

        result.append({
            "name": deployment.metadata.name,
            "desired": deployment.spec.replicas,
            "ready": deployment.status.ready_replicas or 0,
            "available": deployment.status.available_replicas or 0
        })

    return result


# ---------------------------------------------------------
# HPA
# ---------------------------------------------------------

@app.get("/api/assistant/hpa")
def get_hpa():

    hpas = autoscaling_v2.list_namespaced_horizontal_pod_autoscaler(
        namespace=NAMESPACE
    )

    result = []

    for hpa in hpas.items:

        result.append({
            "name": hpa.metadata.name,
            "minReplicas": hpa.spec.min_replicas,
            "maxReplicas": hpa.spec.max_replicas,
            "currentReplicas": hpa.status.current_replicas,
            "desiredReplicas": hpa.status.desired_replicas
        })

    return result