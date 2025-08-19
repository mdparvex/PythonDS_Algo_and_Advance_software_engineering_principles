Absolutely! Here’s a **well-structured technical documentation** on using **Horizontal Pod Autoscaler (HPA) in Kubernetes to auto-scale based on HTTP traffic**. I’ll include **concepts, prerequisites, architecture, setup, YAML examples, and workflow**.

# **Kubernetes Horizontal Pod Autoscaler (HPA) for HTTP Traffic**

## ****1\. Overview****

Horizontal Pod Autoscaler (HPA) in Kubernetes automatically scales the number of pods in a deployment or replica set based on observed metrics. While HPA natively supports CPU and memory metrics, scaling based on **HTTP traffic** requires **custom/external metrics** exposed via **Prometheus and Prometheus Adapter**.

**Benefits of HPA based on traffic:**

- Automatically adjusts pods according to load.
- Prevents underutilization or overloading of resources.
- Improves application availability and responsiveness.
- Optimizes cloud resource costs.

## ****2\. Prerequisites****

Before configuring HPA for HTTP traffic, ensure the following:

1. **Kubernetes Cluster**: Running version >= 1.18.
2. **Metrics Server**: For CPU/memory metrics (optional if only using custom metrics).
3. **Prometheus**: To collect metrics like HTTP requests per second.
4. **Prometheus Adapter**: To expose custom metrics to Kubernetes HPA.
5. **Application metrics**: App should expose metrics in Prometheus format (e.g., http_requests_total).

Check Metrics Server:
```bash
kubectl get deployment metrics-server -n kube-system
```

Install Metrics Server if not present:
```bash
kubectl apply -f <https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml>
```
## ****3\. Architecture & Flow****

### ****Flow of Auto-Scaling Based on HTTP Traffic****

1. **Application** exposes HTTP metrics (http_requests_total) via Prometheus client library.
2. **Prometheus** scrapes the application metrics.
3. **Prometheus Adapter** exposes these metrics as Kubernetes External Metrics.
4. **HPA Controller** queries the adapter for the metric (e.g., http_requests_per_second).
5. **HPA Controller** compares the metric against the defined threshold.
6. If the metric exceeds threshold → **scale up** pods.  
    If the metric falls below threshold → **scale down** pods.

```pgsql
+-----------------+      +-------------+      +-------------------+
|   Application   | ---> | Prometheus  | ---> | Prometheus Adapter|
| (metrics HTTP)  |      |  Scraping   |      | Exposes to HPA    |
+-----------------+      +-------------+      +-------------------+
                                                        |
                                                        v
                                               +-----------------+
                                               | HPA Controller  |
                                               +-----------------+
                                                        |
                                                        v
                                               +-----------------+
                                               |  Deployment     |
                                               |  (Pods scale)   |
                                               +-----------------+

```

## ****4\. Application Metric Example****

Your application should expose a Prometheus metric:

```prometheus
# TYPE http_requests_total counter
http_requests_total{app="my-app"} 345

```

To calculate **requests per second**, Prometheus uses the rate() function:
```prometheus
rate(http_requests_total\[1m\])
```
Prometheus Adapter can map this metric as http_requests_per_second for HPA consumption.

## ****5\. HPA YAML Configuration****

Here’s a **ready-to-use HPA configuration** based on HTTP traffic:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: External
      external:
        metric:
          name: http_requests_per_second
          selector:
            matchLabels:
              app: my-app
        target:
          type: Value
          value: "100"  # Scale up if requests/sec > 100

```

**Explanation:**

- minReplicas / maxReplicas: Limits the scaling range.
- scaleTargetRef: The deployment that HPA will scale.
- metrics.type: External: Uses external/custom metrics from Prometheus Adapter.
- metric.name: Name of the metric exposed by Prometheus Adapter.
- target.value: Threshold for scaling.

Apply the YAML:
```bash
kubectl apply -f hpa-http-traffic.yaml
```
## ****6\. Monitoring HPA****

Check HPA status:
```bash
kubectl get hpa
kubectl describe hpa my-app-hpa
```
**Output:**

```perl
NAME         REFERENCE         TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
my-app-hpa   Deployment/my-app  120/100      2         10        3          5m

```

- TARGETS shows the current metric vs target.
- REPLICAS shows the number of pods currently running.

## ****7\. Scaling Simulation****

You can simulate traffic to observe HPA behavior:

1. Generate HTTP requests (e.g., with hey or ab tool):

```bash
hey -z 1m -c 50 http://<my-app-service>

```

1. Watch HPA:
```bash
kubectl get hpa -w
```
Pods should scale up or down automatically according to load.

## ****8\. Best Practices****

- Set reasonable min/max replicas to avoid over/under-scaling.
- Use **Prometheus Adapter** for custom metrics.
- Combine CPU/memory metrics with HTTP metrics for better scaling decisions.
- Monitor and tune thresholds (target.value) based on real traffic patterns.

✅ **Conclusion**

Kubernetes HPA combined with Prometheus and Prometheus Adapter allows **automatic scaling of pods based on HTTP traffic**, ensuring high availability and efficient resource usage. This setup can be extended to other custom metrics such as latency, queue length, or external system metrics.

Let’s go **step by step** on how to use **Horizontal Pod Autoscaler (HPA)** in Kubernetes to auto-scale based on traffic (CPU/memory or custom metrics). I’ll include commands, examples, and explanations.

**1\. Prerequisites**

- You have a **Kubernetes cluster** up and running.
- Your deployment is already created (e.g., my-app).
- Metrics server is installed in the cluster. HPA relies on metrics server for CPU/memory metrics.

Check metrics server:
```bash
kubectl get deployment metrics-server -n kube-system
```
If not installed, install it:
```bash
kubectl apply -f <https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml>
```
**2\. Basic HPA using CPU utilization**

Suppose you have a deployment called my-app:

```bash
kubectl get deployments
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
my-app    3/3     3            3           10m

```

Create an HPA:
```bash
kubectl autoscale deployment my-app --cpu-percent=50 --min=2 --max=10
```
Explanation:

- \--cpu-percent=50 → Target CPU utilization per pod is 50%. HPA will scale up if CPU >50%.
- \--min=2 → Minimum 2 pods.
- \--max=10 → Maximum 10 pods.

Check HPA:
```bash
kubectl get hpa
```
Example output:

```bash
NAME      REFERENCE        TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
my-app    Deployment/my-app   30%/50%   2         10        3         1m
```

**3\. Simulate traffic**

You can simulate CPU load to see HPA in action:

```bash
kubectl exec -it <pod-name> -- /bin/sh
# Inside pod:
stress --cpu 1 --timeout 300

```

Then watch HPA:
```bash
kubectl get hpa -w
```
You will see pods scaling up automatically.

**4\. HPA using memory or custom metrics**

**Memory-based scaling**
```bash
kubectl autoscale deployment my-app --min=2 --max=10 --metric memory --target 200Mi
```

Here, HPA scales based on memory usage > 200Mi.

**Custom metrics (like requests per second)**

1. Install **Prometheus Adapter** to provide custom metrics.
2. Define HPA YAML with metrics field:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: External
    external:
      metric:
        name: http_requests_per_second
      target:
        type: Value
        value: "100"

```

**5\. HPA YAML example**

To auto-scale based on **HTTP requests per second**, we need to use **custom metrics** because HPA cannot scale by HTTP traffic natively. Typically, this requires **Prometheus + Prometheus Adapter** to expose metrics like http_requests_per_second.

Here’s a **ready-to-use HPA YAML** for a deployment called my-app:

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: External
      external:
        metric:
          name: http_requests_per_second
          selector:
            matchLabels:
              app: my-app
        target:
          type: Value
          value: "100"   # Scale up if total requests/sec > 100


**Explanation**

- minReplicas / maxReplicas: Limits of pod scaling.
- scaleTargetRef: The deployment this HPA will scale.
- metrics.type: External: Tells HPA to use external/custom metrics.
- metric.name: Name of the metric from Prometheus Adapter.
- selector.matchLabels: Optional, if you want to filter metrics for a specific deployment.
- target.value: HPA will scale if the metric exceeds this value (100 requests/sec in this example).

**Setup Requirements**

1. **Prometheus** installed in your cluster.
2. **Prometheus Adapter** installed to expose custom metrics to Kubernetes HPA.
3. Your app should **export metrics** in Prometheus format. For HTTP requests, you can use **Prometheus client libraries** (Python, Go, Node.js, etc.) with a metric like http_requests_total.

Example metric in Prometheus:
```prometheus
http_requests_per_second{app="my-app"}
```

1. After that, Kubernetes HPA can fetch this metric via Prometheus Adapter.

Apply it:
```bash
kubectl apply -f hpa.yaml
```
**6\. Check HPA status**

```bash
kubectl get hpa my-app-hpa
kubectl describe hpa my-app-hpa

```

You’ll see:

- Current replicas
- Target metrics
- Scaling events

✅ **Summary:**

1. Ensure metrics-server is running.
2. Create HPA via CLI or YAML.
3. Set min/max replicas and target metric (CPU, memory, or custom).
4. Monitor scaling using kubectl get hpa -w.
5. Optional: Use custom metrics for advanced traffic-based scaling.