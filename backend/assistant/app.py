import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from openai import OpenAI


app = FastAPI(
    title="Restauranty AI Assistant",
    version="1.1.0"
)

NAMESPACE = "restauranty"


# =========================================================
# Kubernetes configuration
# =========================================================

try:
    config.load_incluster_config()
    print("Using in-cluster Kubernetes configuration")

except ConfigException:
    config.load_kube_config()
    print("Using local kubeconfig")


core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
autoscaling_v2 = client.AutoscalingV2Api()


# =========================================================
# OpenAI client
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# Request models
# =========================================================

class ChatRequest(BaseModel):
    message: str


# =========================================================
# Health endpoint
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "assistant"
    }


# =========================================================
# Helpers
# =========================================================

def get_current_deployments():
    deployments = apps_v1.list_namespaced_deployment(
        namespace=NAMESPACE
    )

    result = []

    for deployment in deployments.items:

        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        available = deployment.status.available_replicas or 0

        result.append({
            "name": deployment.metadata.name,
            "desired": desired,
            "ready": ready,
            "available": available,
            "healthy": ready >= desired and available >= desired
        })

    return result


def get_current_pods():
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


def get_hpa_status():
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


def get_cluster_summary():

    deployments = get_current_deployments()
    pods = get_current_pods()

    unhealthy_deployments = [
        deployment
        for deployment in deployments
        if not deployment["healthy"]
    ]

    failed_pods = [
        pod
        for pod in pods
        if pod["phase"] == "Failed"
    ]

    currently_unhealthy_pods = [
        pod
        for pod in pods
        if pod["phase"] not in ["Running", "Succeeded", "Failed"]
        or (
            pod["phase"] == "Running"
            and not pod["ready"]
        )
    ]

    return {
        "namespace": NAMESPACE,
        "healthy": len(unhealthy_deployments) == 0
        and len(currently_unhealthy_pods) == 0,

        "deployments": deployments,

        "unhealthyDeployments": unhealthy_deployments,

        "currentPodProblems": currently_unhealthy_pods,

        # Failed pods are kept as historical information,
        # but do not automatically mark the live deployment unhealthy.
        "historicalFailedPods": failed_pods
    }


# =========================================================
# Kubernetes endpoints
# =========================================================

@app.get("/api/assistant/status")
def cluster_status():
    return get_cluster_summary()


@app.get("/api/assistant/pods")
def get_pods():
    return get_current_pods()


@app.get("/api/assistant/deployments")
def get_deployments():
    return get_current_deployments()


@app.get("/api/assistant/hpa")
def get_hpa():
    return get_hpa_status()


# =========================================================
# Chat endpoint
# =========================================================

@app.post("/api/assistant/chat")
def chat(request: ChatRequest):

    if not openai_client:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured"
        )

    question = request.message.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # For now we always give the model live Kubernetes context.
    # Later we will add proper tool selection for Loki,
    # Prometheus and Restauranty actions.

    cluster_summary = get_cluster_summary()
    hpa_status = get_hpa_status()

    system_prompt = """
You are the Restauranty DevOps AI Assistant.

You answer questions about the live Restauranty AKS environment.

Important rules:

- Only use the supplied live Kubernetes data.
- Do not invent pod, deployment, replica or health information.
- Historical failed pods do not mean the application is currently unhealthy
  if all active deployments have their desired replicas available.
- Explain problems briefly and clearly.
- If everything is healthy, say so directly.
- You currently have read-only infrastructure access.
- You cannot create, modify or delete Kubernetes resources.
"""

    response = openai_client.responses.create(
        model="gpt-5.6",
        instructions=system_prompt,
        input=f"""
User question:
{question}

Live deployment and pod status:
{cluster_summary}

Live HPA status:
{hpa_status}
"""
    )

    return {
        "question": question,
        "answer": response.output_text
    }