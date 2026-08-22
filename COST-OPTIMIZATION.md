# Restauranty – Cost Efficiency & Optimization

## 1. Overview

Cost efficiency is an important part of the Restauranty DevOps architecture.

The goal of cost optimization is not simply to run the cheapest possible infrastructure. The objective is to find a balance between:

- Cost
- Availability
- Performance
- Scalability
- Security
- Observability

Restauranty runs on **Microsoft Azure using Azure Kubernetes Service (AKS)** and includes multiple application services, monitoring and logging components, security tooling, and a locally hosted AI assistant.

Because the current Restauranty environment is primarily a **development and demonstration environment**, several strategies are used to reduce unnecessary cloud resource consumption while still demonstrating production-style DevOps practices.

---

## 2. Main Cost Drivers

The main infrastructure components that can contribute to the cost of Restauranty are:

| Component | Purpose | Main Cost Consideration |
|---|---|---|
| Azure Kubernetes Service | Runs Restauranty workloads | Worker node compute |
| AKS Node Pools / NAP | Provides additional compute capacity | Additional VM/node usage |
| Azure Container Registry | Stores container images | Image storage |
| Persistent Storage | Stores MongoDB data | Persistent disk allocation |
| Ingress / Public IP | Public application access | Azure networking resources |
| Prometheus | Metrics collection | CPU, memory and storage |
| Grafana | Dashboards | Cluster resource usage |
| Grafana Alloy | Telemetry/log collection | CPU and memory |
| Loki | Centralized logging | Storage and retention |
| Ollama | Local AI inference | Significant CPU and memory |
| Cowrie | Honeypot security monitoring | Compute and network usage |

For Restauranty, one of the most important variable costs is the compute capacity required by the AKS worker nodes.

---

# 3. AKS Shutdown Strategy

Restauranty is currently a development environment.

Running AKS continuously when nobody is using the project would consume unnecessary compute resources.

To avoid this, Restauranty includes automated scripts for starting and stopping the AKS development environment.

At the end of a development session the environment can be stopped with:

```bash
./scripts/stop.sh
```

The environment can later be restored with:

```bash
./scripts/start.sh
```

The startup process reconnects to the AKS cluster and waits for the required infrastructure and workloads to become available.

This strategy allows the development environment to be stopped during:

- Nights
- Weekends
- Periods without development
- Periods without demonstrations

This is one of the simplest and most effective cost-saving strategies for a non-production Kubernetes environment.

---

# 4. Node Auto Provisioning (NAP)

Restauranty uses **Azure Kubernetes Service Node Auto Provisioning (NAP)**.

NAP allows AKS to provision additional compute capacity when Kubernetes workloads cannot be scheduled on the existing nodes.

This was demonstrated by a real problem encountered during development.

After restarting the AKS environment, MongoDB remained in:

```text
Pending
```

Running `kubectl describe pod` showed scheduling problems including:

```text
Insufficient cpu
Too many pods
untolerated taints
node volume limits
```

The existing system nodes could not provide suitable capacity for all Restauranty workloads.

With Node Auto Provisioning enabled, AKS was able to create additional node capacity automatically.

The cluster then contained additional capacity such as:

```text
aks-default-xxxxx
```

The scheduling process becomes:

```text
Pod requires resources
        ↓
Existing nodes cannot schedule pod
        ↓
Kubernetes reports FailedScheduling
        ↓
Node Auto Provisioning detects requirement
        ↓
AKS provisions suitable compute capacity
        ↓
Pod is scheduled
        ↓
Application becomes healthy
```

NAP therefore improves both scalability and availability.

However, additional nodes also mean additional Azure compute cost.

NAP should therefore be combined with monitoring and appropriate resource requests to avoid unnecessary node provisioning.

---

# 5. HPA and NAP

Restauranty uses scaling at two different infrastructure levels.

## Horizontal Pod Autoscaler

The Kubernetes **Horizontal Pod Autoscaler (HPA)** controls the number of application pod replicas.

Conceptually:

```text
Application load increases
        ↓
CPU/resource utilization increases
        ↓
HPA detects demand
        ↓
Additional application pods
```

HPA scales the **application layer**.

## Node Auto Provisioning

Node Auto Provisioning operates at the infrastructure level.

```text
More pods are required
        ↓
Existing nodes have insufficient capacity
        ↓
Pods cannot be scheduled
        ↓
NAP provisions additional node capacity
```

NAP scales the **compute layer**.

Together the scaling architecture becomes:

```text
Users
  ↓
Application Traffic
  ↓
HPA
  ↓
More Pods
  ↓
Insufficient Node Capacity
  ↓
NAP
  ↓
Additional AKS Compute
```

This allows Restauranty to increase infrastructure capacity when required instead of permanently provisioning infrastructure for peak demand.

---

# 6. Resource Requests and Limits

Restauranty workloads use Kubernetes resource requests and limits where appropriate.

Example:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 1Gi
```

## Resource Requests

Requests tell Kubernetes how much CPU and memory a container requires for scheduling.

They are important for:

- Pod scheduling
- HPA calculations
- Capacity planning
- Node Auto Provisioning decisions

## Resource Limits

Limits prevent individual workloads from consuming unlimited cluster resources.

Correctly configured requests and limits improve both reliability and cost efficiency.

If requests are configured too high:

```text
Overestimated resources
        ↓
Kubernetes believes more capacity is required
        ↓
Additional nodes may be provisioned
        ↓
Higher infrastructure cost
```

If requests are too low:

```text
Underestimated resources
        ↓
Resource contention
        ↓
Performance or reliability problems
```

The correct strategy is therefore:

```text
Measure
   ↓
Analyze
   ↓
Right-size
   ↓
Monitor
   ↓
Adjust
```

---

# 7. Prometheus-Based Resource Analysis

Restauranty uses **Prometheus** for metrics collection.

The monitoring system provides visibility into resource consumption such as:

- CPU usage
- Memory usage
- Pod resource consumption
- Application metrics

This information can be used to determine whether workloads are correctly sized.

Instead of estimating resource requirements, Prometheus allows optimization decisions to be based on real measurements.

For example, during testing the Restauranty AI Assistant was able to answer:

```text
Which Restauranty pod is using the most CPU right now?
```

and:

```text
Which Restauranty pod is using the most memory right now?
```

The assistant retrieved the relevant Prometheus metrics and identified the highest resource consumer.

This demonstrates **observability-driven cost optimization**.

---

# 8. AI-Assisted Resource Visibility

The Restauranty DevOps AI Assistant integrates operational information from several systems:

```text
Kubernetes API
      │
      ├─────────────┐
      │             │
Prometheus         Loki
      │             │
      └──────┬──────┘
             │
       AI Assistant
             │
             ▼
       Restauranty UI
```

For cost-related analysis, Kubernetes and Prometheus are particularly important.

The assistant can currently provide information about:

- Pod health
- Deployment health
- CPU consumption
- Memory consumption
- HPA state
- Infrastructure status

This provides the foundation for future **FinOps-oriented AI capabilities**.

A future version could answer questions such as:

```text
Which workloads appear over-provisioned?
```

```text
Which deployment could reduce its memory request?
```

```text
Which service consumed the most resources this week?
```

```text
Why did AKS provision another node?
```

The current implementation focuses on visibility and recommendations rather than automatically changing infrastructure.

This keeps cost-related infrastructure changes under human control.

---

# 9. Ollama Cost Trade-Off

Restauranty runs an Ollama model inside the Kubernetes environment.

The AI assistant currently uses a local Llama model for natural-language processing.

This avoids external per-request LLM API charges.

However, local AI inference is not free.

Ollama requires:

- CPU
- Memory
- Kubernetes node capacity

During Restauranty testing, Ollama was observed as one of the largest resource consumers in the namespace.

The architecture therefore has the following trade-off:

```text
External LLM API
       │
       ▼
Possible per-request API cost

            VS

Local Ollama
       │
       ▼
AKS CPU + memory consumption
```

For this project, local inference provides several advantages:

- No external LLM API dependency
- Local processing
- Demonstration of self-hosted AI
- Better control over the AI runtime

For a production system, both approaches should be measured to determine the most cost-effective solution.

---

# 10. Observability Cost

Restauranty includes a complete observability stack:

- Prometheus
- Grafana
- Grafana Alloy
- Loki

Observability provides significant operational value, but monitoring itself consumes infrastructure resources.

For example:

```text
Applications
      ↓
Metrics + Logs
      ↓
Grafana Alloy / Prometheus
      ↓
Loki
      ↓
Storage + Compute
```

Log volume can become particularly expensive if large amounts of application logs are retained indefinitely.

Potential optimizations include:

- Shorter Loki retention in development
- Removing unnecessary debug logging
- Filtering low-value log events
- Monitoring metric cardinality
- Adjusting Prometheus retention
- Monitoring the resource usage of the observability stack itself

A development environment generally does not require the same retention period as production.

---

# 11. Replica Optimization

Multiple replicas improve availability but also consume additional resources.

Restauranty uses multiple replicas for several services to demonstrate Kubernetes availability and scaling.

For example:

```text
restauranty-auth        → multiple replicas
restauranty-client      → multiple replicas
restauranty-discounts   → multiple replicas
restauranty-items       → multiple replicas
```

Each replica consumes CPU and memory.

For a production environment, replica counts should be determined using:

- Actual application traffic
- CPU utilization
- Memory utilization
- Availability requirements
- HPA behavior

Development and production environments do not necessarily require the same minimum replica count.

Reducing minimum replicas in development can therefore reduce compute requirements.

---

# 12. Container Image Optimization

Restauranty services are containerized with Docker and stored in **Azure Container Registry (ACR)**.

Container optimization contributes to both cost efficiency and operational efficiency.

Smaller images provide:

- Reduced registry storage
- Faster CI/CD builds
- Faster image pulls
- Faster pod startup
- Smaller attack surface

Restauranty also uses **Trivy** to scan container images for HIGH and CRITICAL vulnerabilities.

This connects:

```text
Container Optimization
        │
        ├── Security
        ├── Performance
        └── Cost Efficiency
```

Old and unused image tags should eventually be removed from ACR to avoid unnecessary storage.

---

# 13. CI/CD Efficiency

Restauranty uses GitHub Actions for automated CI/CD.

The pipeline performs operations such as:

```text
Git Push
    ↓
GitHub Actions
    ↓
Build Container Images
    ↓
Trivy Security Scan
    ↓
Authenticate to Azure using OIDC
    ↓
Push Images to ACR
    ↓
Deploy to AKS
```

Automation reduces manual deployment work and creates consistent deployments.

Possible future CI/CD optimizations include:

- Building only services that changed
- Docker layer caching
- Avoiding unnecessary rebuilds
- Automatically removing old images
- Preventing deployment when security checks fail
- Avoiding unnecessary pipeline executions

These improvements can reduce both CI/CD execution time and infrastructure usage.

---

# 14. Development vs Production Cost Strategy

Restauranty currently operates primarily as a development and demonstration environment.

Cost strategies should differ between development and production.

## Development Environment

Main priorities:

```text
Low Cost
Fast Startup
Easy Shutdown
Smaller Infrastructure
Short Log Retention
Flexible Scaling
```

Development environments can aggressively reduce unused infrastructure.

## Production Environment

Main priorities would become:

```text
High Availability
Redundancy
Performance
Monitoring
Security
Backups
Disaster Recovery
Predictable Scaling
```

Production cost optimization therefore should not simply select the cheapest possible resources.

The objective should be:

> **Use the minimum infrastructure required to safely meet the application's reliability and performance requirements.**

---

# 15. Current Restauranty Cost Optimization Measures

Restauranty currently demonstrates the following cost-efficiency practices:

| Optimization | Status |
|---|---|
| AKS shutdown when development ends | ✅ Implemented |
| Automated AKS startup | ✅ Implemented |
| Automated AKS shutdown | ✅ Implemented |
| Node Auto Provisioning | ✅ Implemented |
| Horizontal Pod Autoscaling | ✅ Implemented |
| CPU requests | ✅ Implemented |
| Memory requests | ✅ Implemented |
| Resource limits | ✅ Implemented |
| Prometheus monitoring | ✅ Implemented |
| Grafana dashboards | ✅ Implemented |
| Grafana Alloy telemetry collection | ✅ Implemented |
| Loki centralized logging | ✅ Implemented |
| AI-assisted resource analysis | ✅ Implemented |
| Local Ollama inference | ✅ Implemented |
| Automated CI/CD | ✅ Implemented |
| Trivy vulnerability scanning | ✅ Implemented |

These measures demonstrate that cost optimization has been considered throughout the architecture rather than added only at the end of the project.

---

# 16. Real Project Example: Capacity vs Cost

One of the most useful cost optimization lessons came from an actual Restauranty infrastructure problem.

After restarting AKS, MongoDB could not be scheduled.

The investigation showed:

```text
MongoDB Pending
       ↓
kubectl describe pod
       ↓
FailedScheduling
       ↓
Insufficient CPU
Too many pods
Taints
Volume constraints
       ↓
Existing capacity insufficient
```

The immediate solution was to provide additional compute capacity using Node Auto Provisioning.

After additional capacity became available:

```text
New AKS capacity
       ↓
MongoDB scheduled
       ↓
Dependent services recovered
       ↓
Restauranty healthy
```

This demonstrates why cost optimization cannot simply mean reducing the number of nodes.

Too little infrastructure causes application availability problems.

Too much infrastructure wastes money.

The objective is therefore to dynamically maintain enough capacity for the workloads that actually exist.

---

# 17. Future Cost Optimizations

Restauranty could be extended with several additional cost optimization capabilities.

## 17.1 Workload Right-Sizing

Historical Prometheus metrics could be used to compare:

```text
Requested CPU
      VS
Actual CPU Usage
```

and:

```text
Requested Memory
      VS
Actual Memory Usage
```

Workloads that consistently use much less than their requests could potentially be right-sized.

---

## 17.2 Azure Budgets and Alerts

Azure budgets could be configured to monitor project spending.

For example:

```text
Monthly Azure Budget
        ↓
50% → Informational Alert
        ↓
80% → Warning
        ↓
100% → Critical Alert
```

This would prevent unexpected cloud spending.

---

## 17.3 Environment-Specific Scaling

Different Kubernetes configurations could be used for:

```text
Development
Staging
Production
```

For example:

| Environment | Minimum Replicas | Scaling Strategy |
|---|---:|---|
| Development | Low | Cost-focused |
| Staging | Medium | Production-like testing |
| Production | Higher | Availability-focused |

---

## 17.4 Loki Retention

Different log retention policies could be configured per environment.

For example:

```text
Development → short retention
Production  → longer retention
Security    → retention based on security requirements
```

This would reduce unnecessary storage.

---

## 17.5 ACR Cleanup

Unused container image versions could be automatically removed from Azure Container Registry.

This would reduce unnecessary registry storage and make image management cleaner.

---

## 17.6 FinOps Integration

A future version of the Restauranty AI Assistant could integrate Azure cost information with Kubernetes and Prometheus data.

The architecture could become:

```text
Azure Cost Data ─────────┐
                         │
Kubernetes API ──────────┤
                         │
Prometheus Metrics ──────┤
                         │
                         ▼
                Restauranty AI Assistant
                         │
                         ▼
                 Cost Recommendations
```

The assistant could then answer:

```text
What is currently costing the most?
```

```text
Which workloads appear over-provisioned?
```

```text
Why did the cluster require another node?
```

```text
How could Restauranty reduce infrastructure cost?
```

```text
Did our Azure cost increase this week?
```

This would extend the current DevOps AI Assistant toward a **FinOps assistant**.

Any automatic infrastructure changes should still use controlled and approved operations rather than giving the AI unrestricted infrastructure access.

---

# 18. Cost vs Reliability

The most important lesson from Restauranty cost optimization is that reducing cost should not compromise reliability.

For example:

```text
Fewer Nodes
     ↓
Lower Cost
```

but reducing capacity too far can cause:

```text
Insufficient Capacity
       ↓
Pending Pods
       ↓
Unavailable Services
```

Similarly, reducing memory limits too aggressively can result in:

```text
Memory Limit Reached
       ↓
OOMKilled
       ↓
Container Restart
```

Restauranty therefore follows the principle:

> **Optimize based on measurements, not assumptions.**

Prometheus provides resource measurements.

Kubernetes provides workload and infrastructure state.

Grafana provides visualization.

Loki provides operational history.

The Restauranty AI Assistant provides an accessible way to query and interpret this information.

---

# 19. Cost Optimization in the DevOps Lifecycle

Cost efficiency is not treated as an isolated component of Restauranty.

It is connected to the complete DevOps lifecycle:

```text
Application
     ↓
Docker
     ↓
CI/CD
     ↓
Azure Kubernetes Service
     ↓
Resource Requests & Limits
     ↓
HPA
     ↓
Node Auto Provisioning
     ↓
Prometheus + Grafana
     ↓
Grafana Alloy + Loki
     ↓
AI DevOps Assistant
     ↓
Resource Analysis
     ↓
Cost Optimization
```

The project therefore demonstrates how deployment, scaling, observability and cost management are connected.

---

# 20. Conclusion

Restauranty demonstrates that cloud cost optimization is not simply about selecting cheaper infrastructure.

A cost-efficient DevOps platform requires understanding:

- What resources applications actually consume
- When infrastructure should scale
- When infrastructure can be stopped
- Which workloads require additional capacity
- How much observability infrastructure consumes
- How application availability is affected by resource decisions

Restauranty addresses these areas using:

- AKS startup and shutdown automation
- Node Auto Provisioning
- Horizontal Pod Autoscaling
- Resource requests and limits
- Prometheus metrics
- Grafana monitoring
- Grafana Alloy
- Loki centralized logging
- Local Ollama inference
- AI-assisted operational visibility
- Automated CI/CD
- Trivy vulnerability scanning

The project demonstrates an important DevOps principle:

> **The cheapest infrastructure is not necessarily the most cost-efficient infrastructure. The goal is to provide the required reliability and performance using the appropriate amount of resources.**

Restauranty's observability and AI capabilities provide the foundation for future FinOps functionality where **cloud cost, infrastructure utilization, performance and reliability can be analyzed together**.