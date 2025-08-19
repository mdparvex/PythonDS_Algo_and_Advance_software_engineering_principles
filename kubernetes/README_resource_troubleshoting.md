Here’s the **text-based troubleshooting flowchart** again, but now with the **exact kubectl (and related) commands** beside every action so you can copy-paste directly while troubleshooting.

# 🛠 Kubernetes Resource Troubleshooting Flow with Commands

```pgsql
START
  |
  v
Check Deployment/Pod Status
  |  → kubectl get pods -n <namespace>
  |
  +--> Are pods in Pending state?
  |       |
  |       +--> YES: Check Node capacity
  |       |         |  → kubectl describe pod <pod-name> -n <namespace>
  |       |         |  → kubectl describe node <node-name>
  |       |         |
  |       |         +--> Node has enough resources?
  |       |               |
  |       |               +--> NO: Add more nodes (cluster scaling)
  |       |               |        → kubectl get nodes
  |       |               |        → kubectl scale nodegroup <group> --replicas=<n>
  |       |               |
  |       |               +--> YES: Check taints/tolerations, affinity rules
  |       |                        → kubectl describe pod <pod-name> | grep -i Tolerations
  |       |
  |       +--> NO: Continue
  |
  +--> Are pods in CrashLoopBackOff / OOMKilled?
  |       |  → kubectl describe pod <pod-name> -n <namespace>
  |       |
  |       +--> YES: Check resource requests/limits
  |       |         |  → kubectl get pod <pod-name> -o yaml | grep -A5 resources
  |       |         |
  |       |         +--> Too low? Increase requests/limits
  |       |         |        → kubectl edit deployment <deploy-name> -n <namespace>
  |       |         |
  |       |         +--> Still crashing? Debug logs, check app issues
  |       |                  → kubectl logs <pod-name> -n <namespace> --previous
  |       |
  |       +--> NO: Continue
  |
  +--> Are pods Running but high latency/CPU/Memory usage?
  |       |  → kubectl top pod -n <namespace>
  |       |
  |       +--> YES: Scale pods horizontally (increase replicas)
  |       |        → kubectl scale deployment <deploy-name> --replicas=<n> -n <namespace>
  |       |
  |       +--> Still high usage?
  |              |
  |              +--> Optimize app resource usage (profiling, caching, DB tuning)
  |              |        → Not a kubectl command (depends on app profiling tools)
  |              |
  |              +--> If not enough: Add more nodes (cluster scaling)
  |                       → kubectl get nodes
  |                       → kubectl scale nodegroup <group> --replicas=<n>
  |
  +--> Is traffic load uneven across pods?
          |
          +--> YES: Check Service and Ingress load balancing rules
          |        → kubectl describe svc <service-name> -n <namespace>
          |        → kubectl describe ingress <ingress-name> -n <namespace>
          |
          +--> NO: Continue
  |
END

```

### 🔑 Quick Reference to Commands

- **Check pods** → kubectl get pods -n &lt;ns&gt;
- **Describe pod** → kubectl describe pod &lt;pod&gt; -n &lt;ns&gt;
- **Check logs** → kubectl logs &lt;pod&gt; -n &lt;ns&gt; --previous
- **Resource usage** → kubectl top pod -n &lt;ns&gt;
- **Scale deployment** → kubectl scale deployment &lt;deploy&gt; --replicas=N -n &lt;ns&gt;
- **Edit resources** → kubectl edit deployment &lt;deploy&gt; -n &lt;ns&gt;
- **Check nodes** → kubectl get nodes / kubectl describe node &lt;node&gt;   

Here’s a **comprehensive, well-structured technical documentation** on **Kubernetes Resource Troubleshooting**, covering pod failures, debugging, resource scaling, and best practices.

# **Kubernetes Resource Troubleshooting Guide**

## ****1\. Overview****

Kubernetes efficiently schedules workloads across nodes, but pods may **fail or underperform** due to resource constraints, misconfigurations, or cluster limitations. Proper troubleshooting ensures **high availability, performance, and cost-efficiency**.

This guide covers:

- Common reasons for pod failures.
- Debugging techniques.
- Scaling decisions for pods and nodes.
- Best practices for resource management.

## ****2\. Common Reasons for Pod Failures****

| **Failure Type** | **Reason** | **Symptoms / Events** | **Solution / Debugging** |
| --- | --- | --- | --- |
| **CrashLoopBackOff** | Application container crashes repeatedly. | kubectl get pods shows CrashLoopBackOff. | \- Check logs: kubectl logs &lt;pod-name&gt;  <br>\- Inspect livenessProbe failures  <br>\- Fix app code or configuration. |
| **OOMKilled** | Container exceeded memory limit. | kubectl describe pod shows OOMKilled event. | \- Increase container memory limit.  <br>\- Optimize application memory usage. |
| **ImagePullBackOff / ErrImagePull** | Image not found, incorrect tag, or registry authentication failure. | kubectl describe pod shows image pull errors. | \- Verify image name and tag.  <br>\- Check image registry credentials / secrets. |
| **Pending** | Pod cannot be scheduled due to insufficient resources or node constraints. | kubectl describe pod shows 0/3 nodes are available. | \- Check node resources: kubectl describe nodes.  <br>\- Increase CPU/memory requests or add nodes. |
| **NodeNotReady** | Node is unhealthy, disconnected, or under pressure. | Pods stuck in Pending or Terminating. | \- Check node status: kubectl get nodes  <br>\- Reboot node, cordon/drain, or troubleshoot node. |
| **Terminating / Stuck Pods** | Pod is waiting for graceful shutdown or finalizers. | kubectl get pods shows Terminating. | \- Check finalizers: kubectl get pod &lt;pod-name&gt; -o json  <br>\- Force delete: kubectl delete pod &lt;pod-name&gt; --grace-period=0 --force. |
| **Evicted** | Pod evicted due to resource pressure (memory, disk, CPU). | kubectl get events shows Evicted. | \- Check node usage: kubectl describe node  <br>\- Increase node resources or adjust requests/limits. |
| **Failed Liveness/Readiness Probes** | Application not responding to probes. | kubectl describe pod shows probe failures. | \- Check probe configuration.  <br>\- Ensure app responds within timeout. |

## ****3\. Debugging Steps****

### ****Step 1: Inspect Pod Status****
```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### ****Step 2: Check Node Resources****
```bash
kubectl get nodes
kubectl describe node <node-name>
```

- Look for **CPU/Memory pressure** or **disk pressure**.
- Check node events.

### ****Step 3: Check Events****

```bash
kubectl get events --sort-by='.lastTimestamp'
```

- Identify recent warnings, evictions, or errors.

### ****Step 4: Resource Usage Metrics****

Requires **metrics-server**:

```bash
kubectl top pods
kubectl top nodes
```

- Compare current usage vs. resource **requests/limits**.

### ****Step 5: Examine Configurations****

- Pod resource requests & limits:

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"

```

- Misconfigured requests can lead to scheduling issues.

### ****Step 6: Network / Service Issues****

- Check service connectivity:
```bash
kubectl exec -it <pod-name> -- curl http://<service>
kubectl get svc
```

## ****4\. When to Increase Resources****

| **Scenario** | **Action** |
| --- | --- |
| CPU or memory usage > 80% | Increase pod requests/limits or scale replicas. |
| Pods stuck in Pending | Increase cluster node CPU/memory or add more nodes. |
| Frequent OOMKilled or Evictions | Increase memory limit or node resources. |
| High request per pod / traffic load | Add replicas via **HPA** or scale cluster nodes. |
| Persistent storage pressure | Increase PV size or add nodes with storage. |

## ****5\. Scaling Recommendations****

### ****Pod Autoscaling****

- **Horizontal Pod Autoscaler (HPA):** Scale pods based on CPU, memory, or custom metrics.
- **Vertical Pod Autoscaler (VPA):** Adjust pod resource requests/limits automatically.
- **Cluster Autoscaler:** Add/remove nodes based on pod scheduling needs.

### ****Best Practices****

1. Set **requests** and **limits** for all pods.
2. Monitor metrics continuously using **Prometheus + Grafana**.
3. Use **readiness/liveness probes** to prevent routing traffic to unhealthy pods.
4. Avoid overprovisioning resources—use autoscaling where possible.
5. Regularly audit cluster nodes for capacity bottlenecks.

## ****6\. Quick Troubleshooting Flow****

```sql
Pod Fails / Stuck / Pending
        |
        v
Check Pod Status:
kubectl describe pod <pod-name>
        |
        +--> CrashLoopBackOff? --> Check Logs / Fix App
        |
        +--> OOMKilled? --> Increase Memory / Optimize App
        |
        +--> Pending? --> Check Node Resources / Requests
        |
        +--> Terminating? --> Check Finalizers / Force Delete
        |
        +--> ImagePullBackOff? --> Check Image Name / Registry
        |
        +--> Evicted? --> Increase Node Resources / Adjust Requests
        |
Check Metrics:
kubectl top pods/nodes
kubectl get events

```

## ****7\. References & Commands****

### ****Useful Commands****

| **Command** | **Purpose** |
| --- | --- |
| kubectl get pods | List pods and their status |
| kubectl describe pod &lt;name&gt; | Detailed pod events and state |
| kubectl logs &lt;pod-name&gt; | View pod logs |
| kubectl get events | Check recent cluster events |
| kubectl top pods | View pod CPU/memory usage |
| kubectl top nodes | View node CPU/memory usage |
| kubectl delete pod &lt;name&gt; --grace-period=0 --force | Force delete stuck pod |
| kubectl get nodes | Check cluster node resources |
| kubectl describe node &lt;name&gt; | Inspect node for pressure or issues |

✅ **Summary:**

- Pod failures often relate to **resources, image issues, or configuration errors**.
- Use **kubectl describe, logs, top, and events** for debugging.
- Scale **pods** with HPA/VPA and **nodes** with Cluster Autoscaler.
- Follow best practices: requests/limits, probes, monitoring, and autoscaling.   

Let’s design a **step-by-step, production-ready Kubernetes setup workflow** for your scenario: 1 API deployment + 3 Celery workers, starting small, measuring usage, and scaling optimally for high-concurrency workloads. I’ll make it **practical, sequential, and detailed**.

# **Production-Ready Kubernetes Setup Workflow for High-Concurrency Workloads**

## ****1\. Initial Setup (Staging Environment)****

### ****Step 1.1: Provision Nodes****

- Start with **2 nodes** (as you have), sufficient for initial testing.
- Node specs: 2 vCPU, 2 GB RAM (temporary for staging, upgrade later for production).

```text
Node1: API + some pods
Node2: Celery workers + some pods
```

### ****Step 1.2: Deploy Cluster****

- Use a managed Kubernetes service (DigitalOcean, EKS, GKE, AKS) or kubeadm.
- Ensure **metrics-server** is installed for monitoring pod/node usage.
```bash
kubectl apply -f <https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml>
```
- Deploy **ingress controller** (Nginx/Traefik) for API routing.

## ****2\. Deploy Applications (Initial Test)****

### ****Step 2.1: Single Replica for All Deployments****

- Start with 1 pod each for API and 3 Celery workers.
- YAML example for API:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: your-api-image:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"

```

- Apply similar minimal requests/limits for Celery workers.

### ****Step 2.2: Deploy to Staging****

```bash
kubectl apply -f api-deployment.yaml
kubectl apply -f celery-worker1.yaml
kubectl apply -f celery-worker2.yaml
kubectl apply -f celery-worker3.yaml
```

## ****3\. Measure Resource Usage****

### ****Step 3.1: Monitor Pods****
```bash
kubectl top pods
kubectl top nodes
```
- Record **CPU/memory usage** under typical load.
- Stress test staging app with load testing tools (e.g., Locust, JMeter).

### ****Step 3.2: Identify Max Usage****

- Observe **peak CPU and memory per pod**.
- Identify if nodes are hitting **memory pressure** or **CPU saturation**.

## ****4\. Set Resource Requests and Limits****

- Use metrics from Step 3 to configure **optimized resource requests/limits**.

```yaml
resources:
  requests:
    cpu: "500m"    # Minimum guaranteed
    memory: "512Mi"
  limits:
    cpu: "1000m"   # Maximum allowed
    memory: "1Gi"
```

- Requests = baseline usage; Limits = maximum expected usage.

Proper requests/limits prevent OOMKilled and help scheduler make better decisions.

## ****5\. Decide Number of Replicas****

- Base on **CPU/memory capacity and expected traffic**.

### ****Step 5.1: Example Calculation****

- Suppose API pod uses max **500m CPU, 512Mi RAM**.
- Node has 2 vCPU (2000m) and 2 GB RAM.
- Available allocatable: ~1900m CPU, 1.6 GB RAM.

```text
Node CPU / Pod CPU = 1900 / 500 ≈ 3 pods per node (CPU-bound)
Node RAM / Pod RAM = 1600 / 512 ≈ 3 pods per node (memory-bound)
```

- Start replicas below max, e.g., 2-3 API pods per node.
- For Celery workers, do the same calculation based on measured usage.

### ****Step 5.2: Load Testing to Validate****

- Simulate **peak traffic** on staging.
- Monitor CPU/memory usage per pod.
- Adjust replicas if CPU or memory is saturated.

## ****6\. Configure Autoscaling****

### ****Step 6.1: Horizontal Pod Autoscaler (HPA)****

- Auto-scale pods based on CPU/memory or custom metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

- Do the same for Celery worker deployments (if tasks are queued).

### ****Step 6.2: Vertical Pod Autoscaler (Optional)****

- Adjust pod requests automatically based on usage.
```bash
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vpa-v0.14.0/vpa-v1-crds.yaml
```

- VPA is helpful if traffic pattern fluctuates a lot.

### ****Step 6.3: Cluster Autoscaler****

- Automatically add/remove nodes if pods cannot be scheduled.
- DigitalOcean Example:
```bash
doctl kubernetes cluster update <cluster-name> --enable-autoscaling --min-nodes 2 --max-nodes 5
```

- Monitor node usage with kubectl top nodes and HPA events.

## ****7\. Monitoring and Alerts****

- **Prometheus + Grafana** for metrics.
- Track:
  - CPU/Memory usage per pod
  - Node status
  - Pod restarts/OOMKilled
  - Queue length for Celery workers
- **Set alerts** for:
  - Node NotReady
  - Pod OOMKilled
  - CPU > 80% or Memory > 80%

## ****8\. Staging Verification Flow****

1. Deploy single pod per deployment with minimal resources.
2. Simulate traffic load (peak + average) using Locust/JMeter.
3. Record CPU/memory usage per pod.
4. Set requests/limits based on 80-90% of observed peak.
5. Configure HPA min/max replicas.
6. Apply load again → check HPA triggers scaling correctly.
7. Ensure nodes do not reach pressure limits.
8. Adjust node count or resource allocation if pods cannot schedule.
9. Verify Celery workers scale with queue length (optional: custom metrics HPA).

## ****9\. Production Setup Recommendations****

| **Component** | **Recommendation** |
| --- | --- |
| Node Specs | 4-8 vCPU, 8-16 GB RAM per node (depends on traffic) |
| API Replicas | Start with 2-3 per node, scale via HPA |
| Celery Workers | 2-3 per node, adjust per queue length |
| Resource Requests | 70-80% of measured peak usage |
| Resource Limits | 100-120% of measured peak usage |
| Autoscaling | HPA for pods, Cluster Autoscaler for nodes, optional VPA |
| Monitoring | Prometheus/Grafana, alerts on CPU/memory/node status |
| Taints & Affinity | Separate heavy workloads on dedicated nodes if needed |
| Load Testing | Always simulate peak traffic in staging |

## ****10\. Summary Flowchart (Text Version)****

```pgsql
[Start: Minimal Deployment on Staging]
       |
       v
[Monitor CPU/Memory Usage via metrics-server]
       |
       v
[Set Resource Requests/Limits Based on Observed Usage]
       |
       v
[Run Load Test → Measure Peak Usage]
       |
       v
[Decide Initial Replica Count per Deployment]
       |
       v
[Apply HPA for Pods, Optional VPA]
       |
       v
[Deploy to Production Nodes]
       |
       v
[Monitor Nodes/Pods Metrics]
       |
       v
[If Node Pressure High → Scale Nodes via Cluster Autoscaler]
       |
       v
[Adjust Replica Count / Resources as Needed]
       |
       v
[Continuous Monitoring & Alerts]
```

✅ **Key Takeaways**

1. Start **small in staging**, measure usage, then configure resources.
2. Use **HPA for pods** and **Cluster Autoscaler** for nodes.
3. Monitor continuously and tune **requests, limits, replicas, and node specs**.
4. Staging validation is **critical** before production deployment.