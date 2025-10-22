Here's a **well-structured technical documentation** on OpenTelemetry (OTel) including a detailed overview and a real-world example (with code) you can use for production-level microservices. I'll explain it step-by-step to ensure you understand and can apply it in your own setups.

## Table of Contents

- What is OpenTelemetry
- Why use OpenTelemetry (benefits & real-world motivation)
- Key concepts & components
  - Signals: traces, metrics, logs
  - Resource / Span / Context / Baggage
  - Collector / SDKs / Exporters
- Architecture overview
- Production-level example: microservices scenario (e.g., Django + others)
  - Setup & instrumentation
  - Collector deployment
  - Exporting to back-ends (e.g., Jaeger, Prometheus)
- Configuration details, best practices & operational concerns
  - Sampling & performance
  - Semantic conventions & consistent naming
  - Security, data volume, cost management
  - Vendor-neutrality / avoiding lock-in
- Observability workflows & how OTel fits into your stack
- When **not** to use OTel or caveats
- Summary & next steps

## 1\. What is OpenTelemetry

OpenTelemetry is an open-source observability framework designed to **standardize** how telemetry data (traces, metrics, logs) is generated, collected, and exported from your applications and infrastructure. [OpenTelemetry+2Better Stack+2](https://opentelemetry.io/docs/what-is-opentelemetry/?utm_source=chatgpt.com)

Key points:

- It is vendor- and tool-agnostic: you instrument once, and decision of backend is separate. [Elastic+1](https://www.elastic.co/what-is/opentelemetry?utm_source=chatgpt.com)
- It combines the efforts of previous projects OpenTracing and OpenCensus and is now part of the Cloud Native Computing Foundation (CNCF). [Wikipedia+1](https://en.wikipedia.org/wiki/Cloud_Native_Computing_Foundation?utm_source=chatgpt.com)
- It defines APIs, SDKs, semantic conventions, a protocol (OTLP), instrumentation libraries, and a Collector component. [OpenTelemetry+1](https://opentelemetry.io/docs/specs/otel/overview/?utm_source=chatgpt.com)

## 2\. Why use OpenTelemetry

### Motivation & benefits

Modern applications, especially microservices, distributed, cloud-native systems, produce complex interactions. Observability becomes more challenging. OTel solves several problems:

- A **unified approach** to instrumentation for metrics, traces, and logs rather than siloed tools. [Better Stack+1](https://betterstack.com/community/guides/observability/what-is-opentelemetry/?utm_source=chatgpt.com)
- **Vendor neutrality**: you instrument once, you can change backend later without needing to re-write instrumentation. [Elastic+1](https://www.elastic.co/what-is/opentelemetry?utm_source=chatgpt.com)
- **Cross-language & cross-framework support**: allows consistent telemetry across different services written in different languages. [Better Stack](https://betterstack.com/community/guides/observability/what-is-opentelemetry/?utm_source=chatgpt.com)
- **Better correlation**: Traces, metrics, and logs correlated allows root-cause analysis across microservices.
- **Flexibility and future-proofing**: standard format makes it easier to adopt new observability backends or on-prem systems.

### Real-world scenario

Imagine you have a Django microservice (API), another service in Go, some background jobs in Python, and infrastructure on Kubernetes + AWS. Without OTel you might instrument each service with different tools. With OTel you use one instrumentation library, send data into a collector, export to Jaeger for traces, Prometheus for metrics, maybe Elasticsearch for logs. This unified telemetry gives you full visibility when a user request fails: you have the trace of calls, the metrics for each service, and the logs.

## 3\. Key Concepts & Components

### Signals: Traces, Metrics, Logs

- **Traces**: A trace is a set of spans representing operations across services. Example: a user request triggers calls in several services, you want to trace the entire flow. [OpenTelemetry+1](https://opentelemetry.io/docs/specs/otel/overview/?utm_source=chatgpt.com)
- **Metrics**: Quantitative measurements (counters, gauges, histograms) e.g., request latency, errors per second. [OpenTelemetry](https://opentelemetry.io/docs/specs/otel/overview/?utm_source=chatgpt.com)
- **Logs**: Time-stamped events. OTel is adding logs signal support to unify with traces/metrics. [Better Stack](https://betterstack.com/community/guides/observability/what-is-opentelemetry/?utm_source=chatgpt.com)

### Resource, Span, Context, Baggage

- **Span**: Represents a single operation within a trace; has start time, end time, attributes, events, status. [OpenTelemetry](https://opentelemetry.io/docs/specs/otel/overview/?utm_source=chatgpt.com)
- **SpanContext**: Identifies the trace and span identifiers that get propagated across process boundaries. [OpenTelemetry](https://opentelemetry.io/docs/specs/otel/overview/?utm_source=chatgpt.com)
- **Resource**: Describes the entity that produced telemetry (service name, version, host, region).
- **Baggage**: Key/value pairs propagated with context to carry additional metadata across a distributed system. [OpenTelemetry](https://opentelemetry.io/docs/specs/otel/overview/?utm_source=chatgpt.com)

### Instrumentation libraries / SDKs / APIs

- **APIs**: Language-specific interfaces to create spans, metrics, etc.
- **SDKs**: Implementation of APIs, handles batching, exporting, configuration.
- **Instrumentation libraries**: Pre-built for common frameworks (Django, Flask, gRPC, Redis, SQL) so you don't have to manually instrument everything.
- **Automatic instrumentation**: Plug-and-play for many frameworks (with limitations) so minimal code change is needed. [Elastic](https://www.elastic.co/what-is/opentelemetry?utm_source=chatgpt.com)

### Collector / Exporters

- **OpenTelemetry Collector**: A separate service (agent or gateway) that receives telemetry data, optionally processes/filters it (batching, sampling, enrichment), and exports to observability backends. [OpenTelemetry+1](https://opentelemetry.io/docs/what-is-opentelemetry/?utm_source=chatgpt.com)
- **Exporters**: Components that send telemetry to destinations (e.g., Jaeger, Prometheus, Zipkin, Elasticsearch). Because instrumentation uses a standard protocol (OTLP), switching backend is easier.

## 4\. Architecture Overview

Here's a high-level architecture for a microservices environment using OpenTelemetry:

```scss
[ Microservice A ] ─▶ Instrumentation (OTel SDK) ─▶ [OTLP] ─▶
[ Microservice B ] ─▶ Instrumentation                     │
                                                          ▼
                                               [ OpenTelemetry Collector ]
                                                          │
                    ┌──────────────┬───────────────────────┴───────────────────┐
                    ▼              ▼                                   ▼
            [Jaeger/Tempo]   [Prometheus (Push/Remote)]            [Elasticsearch/Logging/Other]
              (traces)             (metrics)                          (logs)
                                                          │
                                                          ▼
                                                  [ Grafana / Other UI ]
```

- Each service uses OTel SDK to instrument code.
- SDK exports to Collector (or directly to backend).
- Collector handles batching, filtering, sampling, then exports to one or more backends.
- Dashboards/analysis tools visualize.

## 5\. Production-Level Example: Django Microservices Scenario

Let's walk through a realistic example: You have a Django REST microservice (User Service), maybe other services, you want observability via traces + metrics.

### 5.1 Project Setup for Django

#### Install dependencies

```bash
pip install opentelemetry-api \
            opentelemetry-sdk \
            opentelemetry-instrumentation-django \
            opentelemetry-exporter-otlp \
            opentelemetry-exporter-jaeger \
            opentelemetry-instrumentation-psycopg2 \
            opentelemetry-instrumentation-requests
```

#### Django Settings (partial)

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'opentelemetry.instrumentation.django',
]

MIDDLEWARE = [
    'opentelemetry.instrumentation.django.middleware.OpenTelemetryMiddleware',
    # ... other middleware
]

# Configure SDK
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

resource = Resource(attributes={
    "service.name": "user-service",
    "service.version": "1.0.0",
    "deployment.environment": "production"
})
trace.set_tracer_provider(TracerProvider(resource=resource))
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True))
trace.get_tracer_provider().add_span_processor(span_processor)
```

This sets up tracing for incoming Django requests automatically via the Django instrumentation library. You can also instrument your database, HTTP client calls, background tasks, etc.

### 5.2 Instrumenting custom spans & metrics

In one of your views:

```python
from opentelemetry import trace, metrics
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("user_service_meter")

request_counter = meter.create_counter(
    name="user_requests_total",
    description="Total number of user requests",
)

def get(self, request, *args, **kwargs):
    with tracer.start_as_current_span("get_user_details") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", request.path)
        request_counter.add(1, {"endpoint": "get_user"})
        # your logic here
        ...
    return Response({...})
```

### 5.3 Deploy Collector

Use the OpenTelemetry Collector (in Docker Compose or Kubernetes). Example collector-config.yaml:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

processors:
  batch:

exporters:
  jaeger:
    endpoint: "jaeger:14250"
  prometheus:
    endpoint: "0.0.0.0:9464"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

### 5.4 Export to Backends

- **Tracing**: Use Jaeger (or Tempo) to view distributed traces.
- **Metrics**: Use Prometheus (via Collector's Prometheus exporter) or push metrics to Grafana Cloud.
- **Logs**: If desired, you can correlate logs with traces and metrics by including span IDs as attributes in the log output or using the Collector's logs pipeline.

### 5.5 Dashboards & Alerts

Once metrics and tracing data are in your backend, build dashboards:

- Latency P95 for user-service requests
- Error count by endpoint
- Database query latency
- Trace waterfall view showing downstream calls

Set alerts e.g., "Requests P95 latency > 2s for 5 minutes" or "error rate > 5%".

## 6\. Configuration Details & Best Practices

### Sampling & Performance

Tracing all requests in high-volume environments may be cost-prohibitive. Use sampling strategies: head sampling, tail sampling, rate limiting. Some spans and metrics may be filtered in the Collector. [Reddit](https://www.reddit.com/r/OpenTelemetry/comments/wac55q?utm_source=chatgpt.com)

### Semantic Conventions & Naming

Use the official semantic conventions (service.name, http.method, db.system) so that telemetry is consistent. This facilitates searching/aggregation.

### Security & Data Volume

- Protect your OTLP endpoints (TLS, authentication).
- Be careful about PII in spans/attributes.
- Use batching and compression; discard high-cardinality labels to avoid backend overload.
- Use the Collector to add processors (filtering, sampling, enriching) to manage data volume.

### Vendor-Neutrality & Flexibility

Since you're using OpenTelemetry, you can switch instrumentation backend (Jaeger → Tempo, Prometheus → Mimir) without rewriting your instrumentation code. That future-proofs your stack.

## 7\. Observability Workflows & How OTel Fits

In a full observability stack you'll have:

- **Logs** (Elasticsearch, Loki)
- **Metrics** (Prometheus + Grafana)
- **Tracing** (Jaeger, Tempo)  
    OpenTelemetry sits at the instrumentation and collection layer. It ensures you emit telemetry in a standard format. The Collector then routes that data to whichever backend(s) you choose.

This means you can correlate across signals: e.g., a high error rate (metric) triggers an alert → inspect the traces for that error → examine logs for that trace.

## 8\. When Not to Use OTel / Caveats

- If you only need very basic monitoring/metrics in a single monolith, simpler tools may suffice.
- Instrumentation adds overhead; you must be mindful of CPU/memory cost of telemetry collection.
- If backend services (e.g., telemetry storage) are not scaled, telemetry data might overwhelm them.
- Some languages or features may still be in earlier maturity stages. [Better Stack](https://betterstack.com/community/guides/observability/what-is-opentelemetry/?utm_source=chatgpt.com)

## 9\. Summary & Next Steps

OpenTelemetry gives you a future-proof, vendor-neutral way to instrument your services for observability. By adding traces, metrics, and logs uniformly across services, you gain deep visibility into distributed systems.

**Next steps for you:**

- Pick one service (e.g., your Django API) and instrument it with OTel SDK + Collector.
- Select backends: Jaeger for traces, Prometheus for metrics.
- Build dashboards and alerts for key metrics/requests.
- Expand instrumentation to other services and correlate end-to-end.
- Monitor data volume and use sampling strategies to control cost/performance.


---

# OpenTelemetry Working Example — Django + Collector + Jaeger + Prometheus + Grafana

**What you’ll get:** a runnable example (Docker Compose) that instruments a simple Django service with OpenTelemetry (traces + metrics), sends telemetry to an OpenTelemetry Collector, and exports traces to Jaeger and metrics to Prometheus. Grafana is included for dashboards.

This is designed to be easy to run locally and to demonstrate a production-like layout you can adapt for real deployments.

---

## Repository layout (suggested)
```
otel-example/
├─ docker-compose.yml
├─ collector/
│  └─ collector-config.yaml
├─ infra/
│  └─ prometheus.yml
├─ grafana/
│  └─ provisioning/ (datasource + dashboards)
├─ services/
│  └─ user-service/
│     ├─ Dockerfile
│     ├─ requirements.txt
│     ├─ manage.py
│     ├─ core/
│     │  ├─ settings.py
│     │  ├─ urls.py
│     │  └─ wsgi.py
│     └─ users/
│        ├─ views.py
│        └─ apps.py
└─ README.md
```

---

## 1) docker-compose.yml (root)
```yaml
version: '3.8'
services:
  otel-collector:
    image: otel/opentelemetry-collector:0.71.0
    command: ["--config", "/etc/otel-collector-config/collector-config.yaml"]
    volumes:
      - ./collector/collector-config.yaml:/etc/otel-collector-config/collector-config.yaml:ro
    ports:
      - "4317:4317"    # OTLP grpc
      - "4318:4318"    # OTLP http
      - "9464:9464"    # Prometheus metrics from collector
    restart: unless-stopped

  jaeger:
    image: jaegertracing/all-in-one:1.44
    environment:
      - COLLECTOR_ZIPKIN_HTTP_PORT=9411
    ports:
      - "16686:16686"  # Jaeger UI
      - "14268:14268"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:9.5.6
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=jaeger-grafana-plugin
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"

  user-service:
    build: ./services/user-service
    env_file: ./services/user-service/.env
    depends_on:
      - otel-collector
      - prometheus
    ports:
      - "8000:8000"
    volumes:
      - ./services/user-service:/app
```

Notes: Collector image tag may be updated; use a stable version in production. This compose runs everything locally for demo.

---

## 2) Collector config (collector/collector-config.yaml)
```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

processors:
  batch:
  memory_limiter:
    check_interval: 1s
    limit_mib: 400
    spike_limit_mib: 80

exporters:
  jaeger:
    endpoint: "http://jaeger:14268/api/traces"
  prometheus:
    endpoint: "0.0.0.0:9464"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

This collector accepts OTLP from the Django app and forwards traces to Jaeger and metrics to Prometheus (collector exposes Prometheus metrics on 9464 for scraping).

---

## 3) Prometheus config (infra/prometheus.yml)
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:9464']

  - job_name: 'user-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['user-service:8000']
```

Prometheus scrapes both the collector (for pipeline metrics) and the Django app's `/metrics` endpoint (if exposed by the SDK/middleware).

---

## 4) Grafana provisioning (grafana/provisioning)
Create provisioning files to auto-add Prometheus datasource and a simple dashboard (two files):
- `datasources/prometheus.yml`
- `dashboards/sample-dashboard.yml` and `dashboards/sample-dashboard.json`

### grafana/provisioning/datasources/prometheus.yml
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

You can add a Jaeger datasource manually in Grafana UI, or use provisioning for Jaeger too.

---

## 5) user-service: Dockerfile (services/user-service/Dockerfile)
```dockerfile
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "core.wsgi:application", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
```

---

## 6) user-service: requirements.txt
```
django>=4.2
djangorestframework
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation-django
opentelemetry-instrumentation-psycopg2
opentelemetry-instrumentation-requests
opentelemetry-exporter-otlp
prometheus-client
python-json-logger
gunicorn
```

`prometheus-client` enables exposing application metrics if you choose to use the metrics SDK directly.

---

## 7) Django settings: basic instrumentation (services/user-service/core/settings.py)
Add the Django instrumentation and initialize SDK early (call in wsgi.py or a dedicated startup module). Example using OTLP exporter pointed to the collector:

```python
# core/settings.py (only relevant additions shown)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # OpenTelemetry's middleware can be added but we will initialize instrumentation in wsgi.py
]

# Logging (JSON) to include trace/span ids
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(asctime)s %(levelname)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}
```

### Initialize OpenTelemetry in `services/user-service/core/wsgi.py` (or `asgi.py`) **before** Django starts handling requests

```python
# core/wsgi.py (add at top before get_wsgi_application import)
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor

resource = Resource.create({
    "service.name": "user-service",
    "service.version": "0.1.0",
})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
span_processor = BatchSpanProcessor(notlp_exporter)
provider.add_span_processor(span_processor)
trace.set_tracer_provider(provider)

# auto-instrument Django
DjangoInstrumentor().instrument()

# continue normal wsgi setup
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

This auto‑instruments incoming HTTP requests and common libraries. You can add instrumentation for DBs and HTTP clients similarly.

---

## 8) user-service: sample view with manual spans and metrics (services/user-service/users/views.py)
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from opentelemetry import trace
from prometheus_client import Counter

tracer = trace.get_tracer(__name__)
request_counter = Counter('user_requests_total', 'Total user requests')

class UserDetail(APIView):
    def get(self, request, pk):
        request_counter.inc()
        with tracer.start_as_current_span('get_user_details') as span:
            span.set_attribute('user.id', int(pk))
            # pretend to fetch user
            user = {'id': pk, 'email': f'user{pk}@example.com'}
            return Response(user)
```

This demonstrates adding a custom span and a Prometheus counter. The Counter will be exposed by the Django app if you mount a metrics endpoint (see below).

---

## 9) Expose metrics endpoint (Prometheus) in Django
Add a simple endpoint to expose Prometheus metrics collected by `prometheus-client`. Example in `core/urls.py`:

```python
from django.urls import path, include
from django.http import HttpResponse
from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST

urlpatterns = [
    path('users/', include('users.urls')),
    path('metrics/', lambda request: HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)),
]
```

Prometheus will scrape `http://user-service:8000/metrics` (configured in `infra/prometheus.yml`). Note: in production, use the OpenTelemetry metrics SDK and Collector for metrics instead of direct prometheus_client exposure if you want unified pipelines.

---

## 10) Running locally
1. Clone the repo into `otel-example`.
2. `cd otel-example`
3. `docker-compose up --build`

Open:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger UI: http://localhost:16686
- Test service: http://localhost:8000/users/1

Trigger a few requests to see traces in Jaeger and metrics in Prometheus/Grafana.

---

## 11) Grafana dashboards & sample queries
Create panels in Grafana using Prometheus datasource.

**Request rate** (per second):
```
rate(user_requests_total[1m])
```

**Traces**: Add Jaeger datasource in Grafana (Configuration → Data sources → Jaeger) with URL `http://jaeger:16686`. Use Explore → Traces to view trace spans.

**Latency P95** (if measured via histogram):
```
histogram_quantile(0.95, sum(rate(http_server_duration_seconds_bucket[5m])) by (le))
```

---

## 12) Production considerations / hardening
- **Authentication & TLS**: Do not expose OTLP endpoints publicly. Use TLS and auth between services and collector. In prod use collector as sidecar/gateway with mTLS.
- **Sampling**: Use tail or probabilistic sampling in the Collector to reduce data volume.
- **Rate limits & memory**: Use memory_limiter and limits in Collector config to avoid OOM.
- **Scaling**: Run Collector in gateway mode (central) and/or as sidecars per host. Use Kafka/SQS for buffering if needed.
- **PII & attributes**: Avoid storing sensitive data in span attributes.
- **Long-term storage**: For traces use Tempo or Jaeger with object storage backend; for metrics use Thanos or Cortex for long-term metrics.

---

## 13) Extending the example
- Add automatic instrumentation for DB (psycopg2) and HTTP clients (requests) with `instrumentation` packages.
- Use the OTLP metrics exporter and remove direct `prometheus-client` approach if you want metrics via Collector.
- Add a second service (order-service) and demonstrate distributed traces across services.

---

## 14) Troubleshooting
- No traces in Jaeger: check that the Django app can reach `otel-collector:4317` and that Collector has exporter to Jaeger.
- Prometheus not scraping: `docker-compose logs prometheus` and `curl http://localhost:9090/targets`.
- High cardinality/volume: reduce attributes or implement sampling.

---

## 15) Useful commands
- `docker-compose logs -f otel-collector` - watch collector logs
- `docker-compose exec user-service python manage.py shell` - test instrumentation from shell
- `docker-compose ps` - check services

---

## 16) Next steps I can provide
- A downloadable ZIP with all files ready to `docker-compose up`.
- Add Kubernetes manifests and a Helm chart for deploying collector + services with mTLS.
- Add step-by-step instructions to forward logs correlated with traces (log injection of trace ids).

If you'd like the ZIP or Kubernetes manifests, tell me which and I’ll generate them.

