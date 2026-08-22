import os
import time
import re
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


app = FastAPI(
    title="Restauranty AI Assistant",
    version="1.9.0"
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


ITEMS_URL = os.getenv(
    "ITEMS_URL",
    "http://items:3003"
)

DISCOUNTS_URL = os.getenv(
    "DISCOUNTS_URL",
    "http://discounts:3002"
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
# Loki error filtering
# =========================================================

ANSI_ESCAPE = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)


def clean_log_line(line):
    return ANSI_ESCAPE.sub("", line or "").strip()


def is_real_error_log(log):
    """
    Deterministically validate application error logs.

    This prevents harmless values such as 0.500 ms or 500000.0
    from being misclassified as HTTP 500 errors.
    """

    line = clean_log_line(
        log.get("line", "")
    )

    line_lower = line.lower()

    if "/api/assistant/errors" in line_lower:
        return False

    error_indicators = [
        "error:",
        "exception",
        "traceback",
        "failed",
        "fatal",
        "panic",
        "unhandled rejection",
        "connection refused",
        "connection reset",
        "timed out",
        "timeout",
    ]

    if any(
        indicator in line_lower
        for indicator in error_indicators
    ):
        return True

    if re.search(
        r'HTTP/\d(?:\.\d)?[" ]+\s*5\d\d\b',
        line,
        re.IGNORECASE,
    ):
        return True

    if re.search(
        r'\b(?:GET|POST|PUT|PATCH|DELETE)\s+\S+\s+5\d\d\b',
        line,
        re.IGNORECASE,
    ):
        return True

    if re.search(
        r'\b(?:status|statuscode)\b[^0-9]{0,8}5\d\d\b',
        line,
        re.IGNORECASE,
    ):
        return True

    return False


def get_recent_error_logs(minutes=30, limit=200):

    candidate_logs = query_loki(
        '{namespace="restauranty"}',
        minutes=minutes,
        limit=limit
    )

    return [
        log
        for log in candidate_logs
        if is_real_error_log(log)
    ]


def build_error_summary(error_logs, cluster_summary, minutes=30):

    if not error_logs:
        return (
            f"No matching recent application errors were found "
            f"in the last {minutes} minutes."
        )

    counts = {}

    for log in error_logs:
        app_name = (
            log.get("app")
            or log.get("container")
            or "unknown"
        )

        counts[app_name] = (
            counts.get(app_name, 0) + 1
        )

    ordered = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0])
    )

    event_text = "; ".join(
        f"{app_name}: {count} event(s)"
        for app_name, count in ordered
    )

    if cluster_summary.get("healthy"):
        current_health = (
            "All Restauranty deployments are currently healthy "
            "and available."
        )
    else:
        unhealthy = [
            deployment.get("name")
            for deployment
            in cluster_summary.get(
                "unhealthyDeployments",
                []
            )
        ]

        pod_problems = [
            pod.get("name")
            for pod
            in cluster_summary.get(
                "currentPodProblems",
                []
            )
        ]

        current = [
            item
            for item in (
                unhealthy + pod_problems
            )
            if item
        ]

        if current:
            current_health = (
                "Current Kubernetes problems: "
                + ", ".join(current)
                + "."
            )
        else:
            current_health = (
                "Kubernetes currently reports a health issue."
            )

    return (
        f"I found {len(error_logs)} recent application error "
        f"event(s) in the last {minutes} minutes. "
        f"{event_text}. {current_health}"
    )


# =========================================================
# Cowrie security helpers
# =========================================================

def get_security_events(minutes=60, limit=200):

    logs = query_loki(
        (
            '{namespace="honeypot", app="cowrie"} '
            '|~ "login attempt|CMD:|New connection:"'
        ),
        minutes=minutes,
        limit=limit
    )

    events = []

    for log in logs:

        line = clean_log_line(
            log.get("line", "")
        )

        event_type = "other"

        if "New connection:" in line:
            event_type = "connection"

        elif "login attempt" in line:
            if "succeeded" in line.lower():
                event_type = "login_success"
            else:
                event_type = "login_attempt"

        elif "CMD:" in line:
            event_type = "command"

        source_ip = None

        match = re.search(
            r'(\d{1,3}(?:\.\d{1,3}){3})',
            line
        )

        if match:
            source_ip = match.group(1)

        events.append({
            **log,
            "eventType": event_type,
            "sourceIp": source_ip,
            "cleanLine": line
        })

    return events


def build_security_summary(events, minutes=60):

    if not events:
        return (
            f"No honeypot security events were detected "
            f"in the last {minutes} minutes."
        )

    connections = [
        event
        for event in events
        if event["eventType"] == "connection"
    ]

    login_successes = [
        event
        for event in events
        if event["eventType"] == "login_success"
    ]

    login_attempts = [
        event
        for event in events
        if event["eventType"] == "login_attempt"
    ]

    commands = [
        event
        for event in events
        if event["eventType"] == "command"
    ]

    source_ips = sorted({
        event["sourceIp"]
        for event in events
        if event.get("sourceIp")
    })

    parts = [
        (
            f"{len(events)} honeypot security event(s) "
            f"were detected in the last {minutes} minutes."
        )
    ]

    if connections:
        parts.append(
            f"{len(connections)} connection attempt(s)."
        )

    if login_attempts:
        parts.append(
            f"{len(login_attempts)} failed or unsuccessful "
            f"login attempt(s)."
        )

    if login_successes:
        parts.append(
            f"{len(login_successes)} successful honeypot login(s)."
        )

    if commands:
        parts.append(
            f"{len(commands)} attacker command event(s)."
        )

    if source_ips:
        parts.append(
            "Source IPs: "
            + ", ".join(source_ips)
            + "."
        )

    return " ".join(parts)


def build_command_summary(events, minutes=60):

    command_events = [
        event
        for event in events
        if event["eventType"] == "command"
    ]

    if not command_events:
        return (
            f"No attacker commands were recorded "
            f"in the last {minutes} minutes."
        )

    commands = []

    for event in command_events:

        line = event["cleanLine"]

        if "CMD:" in line:
            command = (
                line.split(
                    "CMD:",
                    1
                )[1]
                .strip()
            )

            if command:
                commands.append(command)

    if not commands:
        return (
            f"{len(command_events)} attacker command event(s) "
            f"were detected in the last {minutes} minutes."
        )

    unique_commands = list(
        dict.fromkeys(commands)
    )

    return (
        f"Attacker commands recorded in the last "
        f"{minutes} minutes: "
        + "; ".join(unique_commands)
    )


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
# Restauranty application API helpers
# =========================================================

def get_json(url, timeout=15):

    try:

        response = requests.get(
            url,
            timeout=timeout
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "Restauranty application API request failed: "
                f"{str(exc)}"
            )
        )


def get_restauranty_items():
    return get_json(
        f"{ITEMS_URL}/api/items/items"
    )


def get_restauranty_dietary():
    return get_json(
        f"{ITEMS_URL}/api/items/dietary"
    )


def get_restauranty_coupons():
    return get_json(
        f"{DISCOUNTS_URL}/api/discounts/coupons"
    )


def get_restauranty_campaigns():
    return get_json(
        f"{DISCOUNTS_URL}/api/discounts/campaign"
    )


def normalize_collection(data):

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for key in [
            "items",
            "dietary",
            "categories",
            "coupons",
            "campaigns",
            "data"
        ]:
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


def first_text_value(item, keys):

    if not isinstance(item, dict):
        return None

    for key in keys:

        value = item.get(key)

        if value not in [
            None,
            "",
            []
        ]:
            return str(value)

    return None


def summarize_named_collection(
    data,
    collection_name,
    name_keys
):

    collection = normalize_collection(
        data
    )

    if not collection:
        return (
            f"No {collection_name} were returned "
            f"by the Restauranty application API."
        )

    names = []

    for item in collection:

        value = first_text_value(
            item,
            name_keys
        )

        if value:
            names.append(value)

    if names:

        return (
            f"Restauranty currently has "
            f"{len(collection)} {collection_name}: "
            + ", ".join(names)
            + "."
        )

    return (
        f"Restauranty currently has "
        f"{len(collection)} {collection_name}."
    )


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
# Restauranty application read-only endpoints
# =========================================================

@app.get("/api/assistant/app/items")
def app_items():
    return {
        "source": "items-service",
        "readOnly": True,
        "data": get_restauranty_items()
    }


@app.get("/api/assistant/app/dietary")
def app_dietary():
    return {
        "source": "items-service",
        "readOnly": True,
        "data": get_restauranty_dietary()
    }


@app.get("/api/assistant/app/coupons")
def app_coupons():
    return {
        "source": "discounts-service",
        "readOnly": True,
        "data": get_restauranty_coupons()
    }


@app.get("/api/assistant/app/campaigns")
def app_campaigns():
    return {
        "source": "discounts-service",
        "readOnly": True,
        "data": get_restauranty_campaigns()
    }


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

    logs = get_recent_error_logs(
        minutes=30,
        limit=200
    )

    return {
        "timeRangeMinutes": 30,
        "count": len(logs),
        "logs": logs
    }


@app.get("/api/assistant/security")
def security_events():

    events = get_security_events(
        minutes=60,
        limit=200
    )

    return {
        "timeRangeMinutes": 60,
        "count": len(events),
        "events": events
    }


# =========================================================
# Prometheus endpoint
# =========================================================

@app.get("/api/assistant/metrics")
def metrics():

    return get_metrics_summary()


# =========================================================
# Direct Llama chat
# =========================================================

@app.post("/api/assistant/model-chat")
def model_chat(request: ChatRequest):

    question = request.message.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    try:

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": question,
                "stream": False,
                "options": {
                    "temperature": 0.3
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
            "mode": "direct",
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
            detail="Ollama took too long to answer"
        )

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama request failed: "
                f"{str(exc)}"
            )
        )


# =========================================================
# DevOps Chat
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
    # Deterministic Restauranty application read answers
    # =====================================================

    dietary_question = (
        any(
            word in question_lower
            for word in [
                "dietary",
                "category",
                "categories"
            ]
        )
        and not any(
            word in question_lower
            for word in [
                "create",
                "add",
                "delete",
                "remove",
                "update",
                "edit"
            ]
        )
    )

    if dietary_question:

        data = get_restauranty_dietary()

        return {
            "question": question,
            "model": "deterministic",
            "source": "items-service",
            "readOnly": True,
            "logEventsUsed": 0,
            "metricsUsed": False,
            "answer": summarize_named_collection(
                data,
                "dietary categories",
                [
                    "name",
                    "title",
                    "category",
                    "dietary"
                ]
            ),
            "data": data
        }


    coupon_question = (
        (
            "coupon" in question_lower
            or "coupons" in question_lower
        )
        and not any(
            word in question_lower
            for word in [
                "create",
                "add",
                "delete",
                "remove",
                "update",
                "edit"
            ]
        )
    )

    if coupon_question:

        data = get_restauranty_coupons()

        return {
            "question": question,
            "model": "deterministic",
            "source": "discounts-service",
            "readOnly": True,
            "logEventsUsed": 0,
            "metricsUsed": False,
            "answer": summarize_named_collection(
                data,
                "coupons",
                [
                    "name",
                    "title",
                    "code",
                    "coupon"
                ]
            ),
            "data": data
        }


    campaign_question = (
        (
            "campaign" in question_lower
            or "campaigns" in question_lower
        )
        and not any(
            word in question_lower
            for word in [
                "create",
                "add",
                "delete",
                "remove",
                "update",
                "edit"
            ]
        )
    )

    if campaign_question:

        data = get_restauranty_campaigns()

        return {
            "question": question,
            "model": "deterministic",
            "source": "discounts-service",
            "readOnly": True,
            "logEventsUsed": 0,
            "metricsUsed": False,
            "answer": summarize_named_collection(
                data,
                "campaigns",
                [
                    "name",
                    "title",
                    "campaign"
                ]
            ),
            "data": data
        }


    items_question = (
        (
            "menu item" in question_lower
            or "menu items" in question_lower
            or "items" in question_lower
            or "item" in question_lower
        )
        and not any(
            word in question_lower
            for word in [
                "create",
                "add",
                "delete",
                "remove",
                "update",
                "edit"
            ]
        )
    )

    if items_question:

        data = get_restauranty_items()

        return {
            "question": question,
            "model": "deterministic",
            "source": "items-service",
            "readOnly": True,
            "logEventsUsed": 0,
            "metricsUsed": False,
            "answer": summarize_named_collection(
                data,
                "menu items",
                [
                    "name",
                    "title",
                    "item"
                ]
            ),
            "data": data
        }


    # =====================================================
    # Deterministic application-error answers
    # =====================================================

    error_question = (
        any(
            phrase in question_lower
            for phrase in [
                "error",
                "errors",
                "exception",
                "exceptions",
                "failed request",
                "failed requests",
                "application failure",
                "application failures"
            ]
        )
        and not any(
            word in question_lower
            for word in [
                "honeypot",
                "attack",
                "attacker",
                "security",
                "cowrie"
            ]
        )
    )

    if error_question:

        cluster_summary = (
            get_cluster_summary()
        )

        error_logs = get_recent_error_logs(
            minutes=30,
            limit=200
        )

        return {
            "question": question,
            "model": "deterministic",
            "logEventsUsed": len(error_logs),
            "metricsUsed": False,
            "answer": build_error_summary(
                error_logs,
                cluster_summary,
                minutes=30
            )
        }


    # =====================================================
    # Deterministic security answers
    # =====================================================

    security_question = any(
        word in question_lower
        for word in [
            "honeypot",
            "attack",
            "attacks",
            "attacker",
            "attackers",
            "ssh",
            "security",
            "cowrie"
        ]
    )

    if security_question:

        events = get_security_events(
            minutes=60,
            limit=200
        )

        command_question = any(
            word in question_lower
            for word in [
                "command",
                "commands",
                "execute",
                "executed"
            ]
        )

        if command_question:
            answer = build_command_summary(
                events,
                minutes=60
            )
        else:
            answer = build_security_summary(
                events,
                minutes=60
            )

        return {
            "question": question,
            "model": "deterministic",
            "logEventsUsed": len(events),
            "metricsUsed": False,
            "answer": answer
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

        log_context = get_recent_error_logs(
            minutes=30,
            limit=200
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

SOURCE PRIORITY:

1. Kubernetes state is authoritative for CURRENT
   pod and deployment health.

2. Prometheus is authoritative for CURRENT
   CPU and memory measurements.

3. Loki contains HISTORICAL log events.
   A Loki error does not mean the application
   is currently unhealthy.

4. When Loki shows a previous failure but
   Kubernetes currently reports the workload
   as healthy, explicitly describe the event
   as historical and say that the workload
   is currently healthy.

5. Never describe a deployment or pod as
   currently unhealthy unless the supplied
   Kubernetes state shows it is currently
   unhealthy, unavailable, pending, failed,
   or not ready.

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

9. Historical failed pods or historical Loki
   errors do not automatically mean Restauranty
   is currently unhealthy.

10. If Kubernetes shows all deployments healthy,
    never say that a deployment currently has
    unhealthy replicas solely because an older
    Loki log contains an error.

11. When asked for recent errors, report what
    actually appears in Loki and distinguish
    those errors from the current cluster state.

12. If no relevant logs exist, simply say no
    matching recent events were found.

13. When discussing security events, mention
    relevant source IPs, login attempts and
    executed commands when present.

14. Do not omit relevant events simply because
    another event appears more important.

15. Keep answers concise.

16. Do not repeat the user's question.

17. Do not give unrelated CPU information when
    asked about memory, or memory information
    when asked about CPU.

18. Do not say "No matching recent events were found"
    unless the user's question is actually about
    logs, errors, or security events.

19. If historical logs conflict with current
    Kubernetes health, explain both:
    what happened historically and what the
    current state is now.
    
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