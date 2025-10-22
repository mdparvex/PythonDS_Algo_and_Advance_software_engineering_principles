# Prometheus & Grafana — Production Monitoring for Django Microservices

This guide explains how to set up **Prometheus** and **Grafana** to monitor **Django REST microservices** in a production-grade architecture. It includes an overview of the monitoring stack, real-world implementation details, and best practices for scaling, alerting, and observability.

---

## 1. Introduction

Modern distributed systems need **centralized observability** to detect performance bottlenecks, track service health, and visualize metrics. Prometheus and Grafana together form a powerful open-source solution for metrics monitoring and alerting.

**Prometheus**: A time-series database that scrapes metrics from your services at intervals and stores them for querying.

**Grafana**: A visualization tool that reads data from Prometheus and other sources to build dashboards and send alerts.

**Why use Prometheus + Grafana for Django microservices?**
- Scalable metric collection across multiple microservices.
- Fine-grained visibility into request latency, error rates, DB queries, cache hits, etc.
- Alerting based on SLOs (Service Level Objectives).
- Real-time dashboards for DevOps and developers.

---

## 2. Monitoring Architecture

```
                     ┌────────────────────────┐
                     │     Django App (API)   │
                     │  ┌──────────────────┐  │
Scrape metrics  ───▶  │ /metrics endpoint  │  │
                     │  └──────────────────┘  │
                     └──────────┬─────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Prometheus    │
                       │  (scrapes + TSDB)│
                       └────────┬─────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │    Grafana      │
                       │ (dashboards)    │
                       └─────────────────┘
```

In a **microservice environment**, each service exposes metrics at `/metrics`, and Prometheus scrapes them periodically.

---

## 3. Django Integration

### 3.1 Install Prometheus Client

Each Django microservice integrates the `django-prometheus` library:

```bash
pip install django-prometheus
```

### 3.2 Update settings.py

```python
INSTALLED_APPS = [
    ...,
    'django_prometheus',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...,
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

### 3.3 Update urls.py

```python
from django.urls import path, include

urlpatterns = [
    path('', include('myapp.urls')),
    path('', include('django_prometheus.urls')),
]
```

This exposes a `/metrics` endpoint where Prometheus scrapes metrics such as:
- HTTP request duration
- Database query count
- Cache operations

---

## 4. Docker-Compose for Monitoring Stack

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - '9090:9090'

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - ./infra/grafana/dashboards:/var/lib/grafana/dashboards
    ports:
      - '3000:3000'
    depends_on:
      - prometheus
```

---

## 5. Prometheus Configuration

`infra/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'user-service'
    static_configs:
      - targets: ['user:8000']

  - job_name: 'order-service'
    static_configs:
      - targets: ['order:8000']
```

Prometheus scrapes each service at `/metrics` every 15 seconds.

---

## 6. Grafana Dashboard Setup

### 6.1 Add Prometheus as a Data Source
- Go to **Grafana → Settings → Data Sources**.
- Add a new source → Choose **Prometheus**.
- URL: `http://prometheus:9090`.

### 6.2 Create Dashboards
Create visual panels using PromQL queries like:

#### Example Metrics
| Metric | Description | Query |
|---------|-------------|--------|
| Request rate | Total number of HTTP requests per second | `rate(django_http_requests_total_by_method_total[1m])` |
| Error rate | 5xx responses | `rate(django_http_requests_total_by_status_total{status="500"}[5m])` |
| Response time | 95th percentile latency | `histogram_quantile(0.95, sum(rate(django_http_request_duration_seconds_bucket[5m])) by (le))` |

You can save dashboards for different microservices and environments (staging, production).

---

## 7. Alerts & Notifications

Define alert rules in Prometheus:

```yaml
rule_files:
  - "alert.rules.yml"
```

Example alert rule (`infra/prometheus/alert.rules.yml`):
```yaml
groups:
- name: django_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(django_http_requests_total_by_status_total{status="500"}[5m]) > 0.05
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in Django service"
      description: "More than 5% of requests are failing with 500 errors."
```

You can integrate **Alertmanager** for Slack, Email, or PagerDuty notifications.

---

## 8. Production-Level Enhancements

### 8.1 Separate environments
Use environment labels (dev/staging/prod) in metrics via service configuration.

### 8.2 High Availability (HA)
- Run multiple Prometheus instances for redundancy.
- Use Thanos or Cortex for long-term storage and federation.

### 8.3 Security
- Restrict access to `/metrics` with authentication (e.g., Nginx reverse proxy).
- Secure Grafana with OAuth or LDAP.

### 8.4 Persistent Storage
Mount volumes to persist Prometheus and Grafana data:
```yaml
volumes:
  - prometheus_data:/prometheus
  - grafana_data:/var/lib/grafana
```

---

## 9. Example: Complete Observability Stack
Combine with ELK stack for logs and Prometheus+Grafana for metrics.

```
               ┌──────────────┐
               │   Django API │
               │  (REST App)  │
               └──────┬───────┘
                      │
        Logs → ELK    │   Metrics → Prometheus
                      │
                      ▼
               ┌──────────────┐
               │   Grafana    │
               │ Dashboards + │
               │ Alerting     │
               └──────────────┘
```

---

## 10. Troubleshooting
| Issue | Possible Cause | Solution |
|--------|----------------|-----------|
| No data in Grafana | Wrong Prometheus URL | Verify datasource configuration |
| Prometheus scrape failed | `/metrics` endpoint unreachable | Check container network or port exposure |
| High cardinality | Too many unique label combinations | Use limited label sets in metrics |

---

## 11. Scaling the Stack
For large systems:
- Use **Prometheus Federation** or **Thanos** for multi-cluster metrics aggregation.
- Use **Grafana Loki** for log aggregation alongside metrics.
- Store metrics long-term in S3-compatible storage with Thanos sidecar.

---

## 12. Next Steps
- Integrate **Alertmanager** with Slack for production alerts.
- Deploy this stack with Kubernetes (Prometheus Operator, Helm charts).
- Implement **Application Performance Monitoring (APM)** using Grafana Tempo or Jaeger.

---

## 13. Key Takeaways
- Prometheus + Grafana = metrics + visualization.
- Combine with ELK = logs + metrics for full observability.
- Django + django-prometheus offers native integration.
- Dashboards and alerts help proactively maintain healthy microservices.

---

This setup gives you a **real-world production monitoring architecture** for Django REST microservices, combining metrics, visualization, and alerting in one consistent ecosystem.

---

**🌩️ AWS CloudWatch - Overview**

**CloudWatch** is Amazon's **managed monitoring and observability service** for AWS resources and applications.

It automatically monitors:

- EC2 instances (CPU, disk, network, status checks)
- RDS databases
- ECS/EKS clusters
- Load balancers
- Lambda functions
- Any AWS service metrics

It can also collect:

- **Custom metrics** (you can push your own Django app metrics)
- **Logs** (via CloudWatch Logs agent)
- **Alarms** (for thresholds and notifications via SNS, Slack, etc.)

✅ **Advantages:**

- **No infrastructure management** - AWS runs it for you.
- **Native AWS integration** (works out of the box with EC2, RDS, EKS, etc.)
- **Long-term metric retention** (months to years)
- **Event-driven alerts and automation** (SNS, Lambda, etc.)
- **Good for infrastructure-level observability**.

❌ **Limitations:**

- Not as flexible for **custom application metrics** (e.g., Django request latency, DB query time).
- Visualization is less powerful than Grafana.
- Data granularity and retention depend on pricing tiers.
- Harder to integrate with non-AWS workloads (e.g., self-hosted Redis, Docker metrics, etc.).

**📈 Prometheus - Overview**

**Prometheus** is an **open-source monitoring and alerting system**, great for **application-level metrics**.

It excels at:

- Scraping metrics from **Django microservices** (/metrics)
- Real-time, **high-resolution data collection** (per second/minute)
- Advanced **PromQL queries**
- Deep **custom instrumentation** (app logic, database queries, etc.)
- Pairing with **Grafana** for beautiful dashboards

✅ **Advantages:**

- Fine-grained application metrics (beyond what CloudWatch provides)
- Integrates easily with Django, Celery, Redis, PostgreSQL
- Flexible alerting via Alertmanager
- Works both in AWS and on-prem environments

❌ **Limitations:**

- You must manage its storage, scaling, and retention yourself
- Limited long-term storage (default is a few weeks)
- No automatic AWS integration (needs exporters or CloudWatch bridge)

**⚙️ Prometheus + CloudWatch - Best of Both Worlds (Production Setup)**

In **production Django microservices**, many teams **combine** both systems:

| **Layer** | **Tool** | **Purpose** |
| --- | --- | --- |
| **Infrastructure (EC2, RDS, EKS, ELB)** | **CloudWatch** | AWS-native monitoring (CPU, network, memory, scaling) |
| **Application (Django microservices)** | **Prometheus** | Custom metrics: requests/sec, errors, latency |
| **Visualization** | **Grafana** | Unified dashboards combining Prometheus + CloudWatch |
| **Alerting** | **Alertmanager / CloudWatch Alarms** | Alert routing via Slack, Email, PagerDuty |

**📊 How it fits together**

```scss
[EC2 / RDS / ECS] → CloudWatch
[Django / Redis / Postgres / Celery] → Prometheus → Grafana
CloudWatch + Prometheus → Grafana unified view
Alerts → Alertmanager / SNS
```

**🔗 Integration option:**

You can **import CloudWatch metrics into Prometheus** via the **CloudWatch Exporter**:

scrape_configs:
```yaml
scrape_configs:
  - job_name: 'cloudwatch'
    static_configs:
      - targets: ['cloudwatch-exporter:9106']
```

This way, Prometheus and Grafana see all your metrics (AWS + Django) in one place.

**✅ Recommendation for Django Microservices on AWS**

| **Use Case** | **Recommended Tool** |
| --- | --- |
| Monitor EC2 CPU, memory, disk | **CloudWatch** or **Node Exporter** |
| Monitor RDS, S3, Load Balancer | **CloudWatch** |
| Monitor Django API requests, latency, DB query time | **Prometheus** (django-prometheus) |
| Create unified dashboards | **Grafana** (connects to both Prometheus and CloudWatch) |
| Alerts for app errors, latency | **Prometheus Alertmanager** |
| Alerts for EC2 resource exhaustion | **CloudWatch Alarms** |

**🧠 Summary**

| **Feature** | **CloudWatch** | **Prometheus** |
| --- | --- | --- |
| AWS-native integration | ✅   | ❌   |
| Application-level metrics | ⚠️ (limited) | ✅   |
| Custom instrumentation | ⚠️  | ✅   |
| Long-term storage | ✅   | ⚠️ (limited) |
| Query language | CloudWatch Logs Insights | PromQL |
| Visualization | Basic | Grafana |
| Setup complexity | Easy | Moderate |
| Cost | Pay-per-metric | Self-hosted (infra cost) |

**🚀 Recommended Real-World Setup for You**

For your Django microservices on AWS:

- **Use Prometheus + Grafana** for Django app, Redis, PostgreSQL, and Celery metrics.
- **Use CloudWatch** for EC2, RDS, and AWS-native service health.
- **Integrate both into Grafana** to visualize everything in one dashboard.
- Use **Alertmanager** (Prometheus) and **CloudWatch Alarms** for full coverage alerting.