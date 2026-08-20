import os
import time
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


app = FastAPI(
    title="Restauranty AI Assistant",
    version="1.6.0"
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
# External service configuration
# =========================================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://ollama:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:1b"
)

LOKI_URL = os.getenv(
    "LOKI_URL",
    "http://loki-gateway.monitoring.svc.cluster.local"
)

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"
)


# =========================================================
# Request models
# =========================================================

class ChatRequest(BaseModel):
    message: str


# =========================================================
# Health
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
            "healthy": (
                ready >= desired
                and available >= desired
            )
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

    historical_failed_pods = [
        pod
        for pod in pods
        if pod["phase"] == "Failed"
    ]

    current_pod_problems = [
        pod
        for pod in pods
        if (
            pod["phase"] not in [
                "Running",
                "Succeeded",
                "Failed"
            ]
            or (
                pod["phase"] == "Running"
                and not pod["ready"]
            )
        )
    ]

    return {
        "namespace": NAMESPACE,

        "healthy": (
            len(unhealthy_deployments) == 0
            and len(current_pod_problems) == 0
        ),

        "deployments": deployments,
        "unhealthyDeployments": unhealthy_deployments,
        "currentPodProblems": current_pod_problems,
        "historicalFailedPods": historical_failed_pods
    }


def find_pod_info(pod_name):

    pods = get_current_pods()

    for pod in pods:
        if pod["name"] == pod_name:
            return pod

    return None


# =========================================================
# Loki
# =========================================================

def query_loki(query, minutes=30, limit=100):

    end_ns = int(time.time() * 1_000_000_000)

    start_ns = (
        end_ns
        - minutes
        * 60
        * 1_000_000_000
    )

    try:

        response = requests.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": query,
                "start": start_ns,
                "end": end_ns,
                "limit": limit,
                "direction": "backward"
            },
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        logs = []

        streams = (
            data
            .get("data", {})
            .get("result", [])
        )

        for stream in streams:

            labels = stream.get(
                "stream",
                {}
            )

            for timestamp, line in stream.get(
                "values",
                []
            ):

                logs.append({
                    "timestamp": timestamp,
                    "app": labels.get("app"),
                    "pod": labels.get("pod"),
                    "container": labels.get("container"),
                    "namespace": labels.get("namespace"),
                    "line": line
                })

        return logs

    except requests.RequestException as exc:

        print(
            f"Loki query failed: {str(exc)}"
        )

        return []


# =========================================================
# Prometheus
# =========================================================

def query_prometheus(query):

    try:

        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={
                "query": query
            },
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") != "success":
            return []

        return (
            data
            .get("data", {})
            .get("result", [])
        )

    except requests.RequestException as exc:

        print(
            f"Prometheus query failed: {str(exc)}"
        )

        return []


# =========================================================
# CPU metrics
# =========================================================

def get_pod_cpu_usage():

    query = """
sum by (pod) (
  rate(
    container_cpu_usage_seconds_total{
      namespace="restauranty",
      container!="",
      container!="POD"
    }[5m]
  )
)
"""

    raw_results = query_prometheus(query)

    result = []

    for item in raw_results:

        pod = (
            item
            .get("metric", {})
            .get("pod")
        )

        value = item.get("value", [])

        if len(value) < 2:
            continue

        try:
            cpu_cores = float(value[1])

        except (ValueError, TypeError):
            continue

        cpu_millicores = cpu_cores * 1000

        result.append({
            "pod": pod,
            "cores": round(
                cpu_cores,
                6
            ),
            "millicores": round(
                cpu_millicores,
                2
            ),
            "display": (
                f"{cpu_millicores:.2f}m CPU"
            )
        })

    result.sort(
        key=lambda x: x["millicores"],
        reverse=True
    )

    return result


# =========================================================
# Memory metrics
# =========================================================

def get_pod_memory_usage():

    query = """
sum by (pod) (
  container_memory_working_set_bytes{
    namespace="restauranty",
    container!="",
    container!="POD"
  }
)
"""

    raw_results = query_prometheus(query)

    result = []

    for item in raw_results:

        pod = (
            item
            .get("metric", {})
            .get("pod")
        )

        value = item.get("value", [])

        if len(value) < 2:
            continue

        try:
            memory_bytes = float(value[1])

        except (ValueError, TypeError):
            continue

        memory_mib = (
            memory_bytes
            / 1024
            / 1024
        )

        result.append({
            "pod": pod,
            "bytes": int(
                memory_bytes
            ),
            "MiB": round(
                memory_mib,
                2
            ),
            "display": (
                f"{memory_mib:.2f} MiB"
            )
        })

    result.sort(
        key=lambda x: x["MiB"],
        reverse=True
    )

    return result


# =========================================================
# Restart metrics
# =========================================================

def get_pod_restart_metrics():

    query = """
sum by (pod) (
  kube_pod_container_status_restarts_total{
    namespace="restauranty"
  }
)
"""

    raw_results = query_prometheus(query)

    result = []

    for item in raw_results:

        pod = (
            item
            .get("metric", {})
            .get("pod")
        )

        value = item.get("value", [])

        if len(value) < 2:
            continue

        try:
            restarts = int(
                float(value[1])
            )

        except (ValueError, TypeError):
            continue

        result.append({
            "pod": pod,
            "restarts": restarts
        })

    result.sort(
        key=lambda x: x["restarts"],
        reverse=True
    )

    return result


# =========================================================
# Metrics summary
# =========================================================

def get_metrics_summary():

    cpu = get_pod_cpu_usage()
    memory = get_pod_memory_usage()
    restarts = get_pod_restart_metrics()

    highest_cpu = (
        cpu[0]
        if cpu
        else None
    )

    highest_memory = (
        memory[0]
        if memory
        else None
    )

    restarted_pods = [
        item
        for item in restarts
        if item["restarts"] > 0
    ]

    return {
        "cpu": cpu,
        "memory": memory,
        "restarts": restarts,

        "highestCpuPod":
            highest_cpu,

        "highestMemoryPod":
            highest_memory,

        "podsWithRestarts":
            restarted_pods
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
# Ollama endpoint
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
            detail=(
                "Ollama is unavailable: "
                f"{str(exc)}"
            )
        )


# =========================================================
# Loki endpoints
# =========================================================

@app.get("/api/assistant/logs")
def recent_logs():

    logs = query_loki(
        '{namespace="restauranty"}',
        minutes=30,
        limit=50
    )

    return {
        "timeRangeMinutes": 30,
        "count": len(logs),
        "logs": logs
    }


@app.get("/api/assistant/errors")
def recent_errors():

    logs = query_loki(
        (
            '{namespace="restauranty"} '
            '|~ "(?i)error|exception|failed|500"'
        ),
        minutes=30,
        limit=100
    )

    return {
        "timeRangeMinutes": 30,
        "count": len(logs),
        "logs": logs
    }


@app.get("/api/assistant/security")
def security_events():

    logs = query_loki(
        (
            '{namespace="honeypot", app="cowrie"} '
            '|~ "login attempt|CMD:|New connection:"'
        ),
        minutes=60,
        limit=100
    )

    return {
        "timeRangeMinutes": 60,
        "count": len(logs),
        "logs": logs
    }


# =========================================================
# Prometheus endpoint
# =========================================================

@app.get("/api/assistant/metrics")
def metrics():

    return get_metrics_summary()


# =========================================================
# Chat
# =========================================================

@app.post("/api/assistant/chat")
def chat(request: ChatRequest):

    question = request.message.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )


    question_lower = question.lower()


    # =====================================================
    # Deterministic metric answers
    # =====================================================

    if (
        "most memory" in question_lower
        or "highest memory" in question_lower
        or "using the most memory" in question_lower
    ):

        metrics = get_metrics_summary()

        highest = metrics.get(
            "highestMemoryPod"
        )

        if not highest:

            return {
                "question": question,
                "model": "deterministic",
                "logEventsUsed": 0,
                "metricsUsed": True,
                "answer": (
                    "No memory metrics are "
                    "currently available."
                )
            }

        pod_info = find_pod_info(
            highest["pod"]
        )

        healthy = (
            pod_info is not None
            and pod_info["phase"] == "Running"
            and pod_info["ready"]
        )

        health_text = (
            "healthy"
            if healthy
            else "not currently healthy"
        )

        return {
            "question": question,
            "model": "deterministic",
            "logEventsUsed": 0,
            "metricsUsed": True,
            "answer": (
                f'{highest["pod"]} is currently '
                f'using the most memory at '
                f'{highest["display"]}. '
                f'The pod is {health_text}.'
            )
        }


    if (
        "most cpu" in question_lower
        or "highest cpu" in question_lower
        or "using the most cpu" in question_lower
    ):

        metrics = get_metrics_summary()

        highest = metrics.get(
            "highestCpuPod"
        )

        if not highest:

            return {
                "question": question,
                "model": "deterministic",
                "logEventsUsed": 0,
                "metricsUsed": True,
                "answer": (
                    "No CPU metrics are "
                    "currently available."
                )
            }

        pod_info = find_pod_info(
            highest["pod"]
        )

        healthy = (
            pod_info is not None
            and pod_info["phase"] == "Running"
            and pod_info["ready"]
        )

        health_text = (
            "healthy"
            if healthy
            else "not currently healthy"
        )

        return {
            "question": question,
            "model": "deterministic",
            "logEventsUsed": 0,
            "metricsUsed": True,
            "answer": (
                f'{highest["pod"]} is currently '
                f'using the most CPU at '
                f'{highest["display"]}. '
                f'The pod is {health_text}.'
            )
        }


    if (
        "restart" in question_lower
        or "restarts" in question_lower
    ):

        metrics = get_metrics_summary()

        restarted = metrics.get(
            "podsWithRestarts",
            []
        )

        if not restarted:

            return {
                "question": question,
                "model": "deterministic",
                "logEventsUsed": 0,
                "metricsUsed": True,
                "answer": (
                    "No Restauranty pods currently "
                    "report container restarts."
                )
            }

        lines = []

        for item in restarted:

            lines.append(
                f'{item["pod"]}: '
                f'{item["restarts"]} restart(s)'
            )

        return {
            "question": question,
            "model": "deterministic",
            "logEventsUsed": 0,
            "metricsUsed": True,
            "answer": (
                "Pods with restarts: "
                + "; ".join(lines)
            )
        }


    # =====================================================
    # Live Kubernetes context
    # =====================================================

    cluster_summary = (
        get_cluster_summary()
    )

    hpa_status = (
        get_hpa_status()
    )


    # =====================================================
    # Tool routing
    # =====================================================

    log_context = []

    metric_context = {}


    log_keywords = [
        "log",
        "logs",
        "error",
        "errors",
        "failed",
        "failure",
        "exception",
        "500"
    ]


    security_keywords = [
        "honeypot",
        "attack",
        "attacks",
        "attacker",
        "attackers",
        "ssh",
        "security",
        "cowrie"
    ]


    metric_keywords = [
        "cpu",
        "memory",
        "ram",
        "usage",
        "resource",
        "resources",
        "metric",
        "metrics",
        "performance",
        "load"
    ]


    # =====================================================
    # Loki context
    # =====================================================

    if any(
        word in question_lower
        for word in security_keywords
    ):

        log_context = query_loki(
            (
                '{namespace="honeypot", app="cowrie"} '
                '|~ "login attempt|CMD:|New connection:"'
            ),
            minutes=60,
            limit=50
        )


    elif any(
        word in question_lower
        for word in log_keywords
    ):

        log_context = query_loki(
            (
                '{namespace="restauranty"} '
                '|~ "(?i)error|exception|failed|500"'
            ),
            minutes=30,
            limit=50
        )


    # =====================================================
    # Prometheus context
    # =====================================================

    if any(
        word in question_lower
        for word in metric_keywords
    ):

        metric_context = (
            get_metrics_summary()
        )


    # =====================================================
    # System prompt
    # =====================================================

    system_prompt = """
You are the Restauranty DevOps AI Assistant.

You answer questions using live data from the
Restauranty Azure Kubernetes Service environment.

You may receive:

- Kubernetes pod and deployment state
- HPA state
- Loki logs
- Prometheus metrics

Rules:

1. Only use supplied live data.

2. Never invent pod names, resource usage,
   logs, errors, replicas or events.

3. CPU and memory values have already been
   calculated and converted by Python.

4. Never perform your own unit conversions.

5. If a metric contains a "display" field,
   use that exact value.

6. CPU values are provided in millicores.

7. Memory values are provided in MiB.

8. Clearly distinguish current problems
   from historical events.

9. Historical failed pods do not automatically
   mean Restauranty is currently unhealthy.

10. Never claim an error exists unless it appears
    in the Kubernetes state or Loki logs.

11. If no relevant logs exist, simply say no
    matching recent events were found.

12. When discussing security events, mention
    relevant source IPs, login attempts and
    executed commands when present.

13. Do not omit relevant events simply because
    another event appears more important.

14. Keep answers concise.

15. Do not repeat the user's question.

16. Do not give unrelated CPU information when
    asked about memory, or memory information
    when asked about CPU.

17. Do not say "No matching recent events were found"
    unless the user's question is actually about
    logs, errors, or security events.

You currently have read-only infrastructure access.
"""


    # =====================================================
    # Prompt
    # =====================================================

    prompt = f"""
{system_prompt}


USER QUESTION:

{question}


LIVE KUBERNETES STATUS:

{cluster_summary}


LIVE HPA STATUS:

{hpa_status}


RELEVANT LOKI LOGS:

{log_context}


NORMALIZED PROMETHEUS METRICS:

{metric_context}
"""


    # =====================================================
    # Ollama
    # =====================================================

    try:

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",

            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
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
            "logEventsUsed": len(log_context),
            "metricsUsed": bool(metric_context),
            "answer": answer.strip()
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
            detail=(
                "Ollama took too long to answer"
            )
        )


    except requests.RequestException as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama request failed: "
                f"{str(exc)}"
            )
        )