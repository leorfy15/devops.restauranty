import os
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


app = FastAPI(
    title="Restauranty AI Assistant",
    version="1.2.0"
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
# Ollama configuration
# =========================================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://ollama:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:1b"
)


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
# Kubernetes helpers
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
        if pod["phase"] not in [
            "Running",
            "Succeeded",
            "Failed"
        ]
        or (
            pod["phase"] == "Running"
            and not pod["ready"]
        )
    ]

    return {
        "namespace": NAMESPACE,

        "healthy":
            len(unhealthy_deployments) == 0
            and len(currently_unhealthy_pods) == 0,

        "deployments": deployments,

        "unhealthyDeployments":
            unhealthy_deployments,

        "currentPodProblems":
            currently_unhealthy_pods,

        # Historical failed pods remain visible,
        # but don't automatically mark the live
        # application unhealthy.
        "historicalFailedPods":
            failed_pods
    }


# =========================================================
# Kubernetes API endpoints
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
# Ollama status
# =========================================================

@app.get("/api/assistant/ollama")
def ollama_status():

    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=10
        )

        response.raise_for_status()

        return {
            "status": "connected",
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
            "ollama": response.json()
        }

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable: {str(exc)}"
        )


# =========================================================
# Chat endpoint
# =========================================================

@app.post("/api/assistant/chat")
def chat(request: ChatRequest):

    question = request.message.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    cluster_summary = get_cluster_summary()
    hpa_status = get_hpa_status()

    system_prompt = """
You are the Restauranty DevOps AI Assistant.

You answer questions about the live Restauranty
Azure Kubernetes Service environment.

You are provided with live Kubernetes information.

Rules:

- Only use the infrastructure information supplied to you.
- Never invent pod, deployment, HPA or health information.
- Historical failed pods do not mean Restauranty is currently
  unhealthy when the active deployments have the expected
  replicas available.
- Clearly distinguish current problems from historical failures.
- Explain problems briefly and clearly.
- If everything is healthy, say so directly.
- You currently have read-only infrastructure access.
- You cannot modify or delete Kubernetes resources.
"""

    prompt = f"""
{system_prompt}

USER QUESTION:

{question}


LIVE KUBERNETES STATUS:

{cluster_summary}


LIVE HPA STATUS:

{hpa_status}
"""

    try:

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()

        data = response.json()

        answer = data.get(
            "response",
            "Ollama returned no response."
        )

        return {
            "question": question,
            "model": OLLAMA_MODEL,
            "answer": answer
        }

    except requests.exceptions.ConnectionError:

        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot connect to Ollama at "
                f"{OLLAMA_URL}"
            )
        )

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=504,
            detail="Ollama took too long to answer"
        )

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=503,
            detail=f"Ollama request failed: {str(exc)}"
        )