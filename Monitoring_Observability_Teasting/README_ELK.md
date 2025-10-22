# ELK Stack (Elasticsearch, Logstash, Kibana) — A Production-Level Guide with Django Microservices

## 1. Introduction
The **ELK stack** (Elasticsearch, Logstash, Kibana) is a robust open-source suite used for **log aggregation**, **searching**, **monitoring**, and **visualization**. In production, it helps centralize logs across microservices, enabling fast debugging, analytics, and security insights.

### Components Overview
- **Elasticsearch** — Distributed search and analytics engine that stores logs as structured JSON documents.
- **Logstash** — Data processing pipeline that ingests, transforms, and ships logs to Elasticsearch.
- **Kibana** — Visualization dashboard for exploring and analyzing Elasticsearch data.

Optional Add-on:
- **Beats (e.g., Filebeat, Metricbeat)** — Lightweight log shippers that forward logs from containers, servers, or applications to Logstash/Elasticsearch.

---

## 2. ELK Stack Architecture

```
Django App → Gunicorn Logs → Filebeat → Logstash → Elasticsearch → Kibana
```

Each Django microservice writes logs to local files. **Filebeat** collects these logs and forwards them to **Logstash**. Logstash parses, filters, and sends the data to **Elasticsearch**, which indexes the logs for **Kibana** dashboards.

---

## 3. Why Use ELK with Django Microservices

| Challenge | Solution with ELK |
|------------|-------------------|
| Scattered logs across containers | Centralized storage in Elasticsearch |
| Hard to debug distributed issues | Search and correlate logs by request ID or service |
| No real-time visibility | Live dashboards in Kibana |
| Manual log parsing | Logstash automation & structured filtering |

---

## 4. Setting Up ELK Stack with Docker Compose

### docker-compose.yml
```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.4
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.13.4
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"   # Beats input
      - "9600:9600"   # Monitoring
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.13.4
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.13.4
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
      - ./django_logs:/usr/share/filebeat/logs
    depends_on:
      - logstash
```

---

## 5. Logstash Configuration

### logstash/pipeline/logstash.conf
```conf
input {
  beats {
    port => 5044
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] %{GREEDYDATA:log_message}" }
  }
  date {
    match => [ "timestamp", "ISO8601" ]
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "django-logs-%{+YYYY.MM.dd}"
  }
  stdout { codec => rubydebug }
}
```

This pipeline reads logs from Filebeat, parses them with Grok patterns, and stores them in Elasticsearch.

---

## 6. Filebeat Configuration

### filebeat/filebeat.yml
```yaml
filebeat.inputs:
  - type: log
    paths:
      - /usr/share/filebeat/logs/*.log
    fields:
      service: django-app

output.logstash:
  hosts: ["logstash:5044"]
```

Filebeat ships logs from Django’s log directory to Logstash.

---

## 7. Django Logging Configuration for ELK

### settings.py
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/app/logs/django_app.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'app_logger': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

Each Django microservice writes logs to a file under `/app/logs/`. Filebeat then forwards them to Logstash.

---

## 8. Real Example — Django Microservice Logging Flow

Suppose we have two microservices:
- **User Service** — Handles user authentication
- **Order Service** — Manages customer orders

Each writes logs like:
```log
2025-10-22 08:35:10 [INFO] order.views: Order 123 processed for user 45
```

Logstash will parse it into structured fields:
```json
{
  "@timestamp": "2025-10-22T08:35:10.000Z",
  "level": "INFO",
  "service": "order-service",
  "log_message": "Order 123 processed for user 45"
}
```

In **Kibana**, you can:
- Filter logs by `service:order-service`
- Visualize error trends per service
- Create dashboards showing average response time, failure rates, etc.

---

## 9. Optimizing for Production

### a) Elasticsearch Index Management
Use **ILM (Index Lifecycle Management)** to auto-rotate logs daily and delete old indices.

```bash
PUT _ilm/policy/django-logs-policy
{
  "policy": {
    "phases": {
      "delete": { "min_age": "30d", "actions": { "delete": {} } }
    }
  }
}
```

### b) Log Enrichment
Enrich logs with metadata:
```conf
filter {
  mutate {
    add_field => { "environment" => "production" }
  }
}
```

### c) Security
- Enable TLS between Logstash ↔ Elasticsearch.
- Protect Kibana with credentials (xpack).
- Use API tokens for Elasticsearch ingestion.

### d) Scalability
- Run Elasticsearch in a cluster mode.
- Use separate pipelines per microservice.
- Store logs in AWS S3 or Glacier for archival.

---

## 10. Monitoring the ELK Stack
- Use Kibana’s **Stack Monitoring** to visualize node health.
- Enable **Metricbeat** for system-level metrics.
- Use **Alerting (Watcher)** to trigger Slack/email alerts on error spikes.

---

## 11. Troubleshooting Tips
| Issue | Cause | Fix |
|--------|--------|-----|
| Logstash not receiving logs | Wrong port or firewall | Check `5044` port and Docker network |
| Logs not showing in Kibana | Incorrect index pattern | Create `django-logs-*` pattern in Kibana |
| High Elasticsearch memory | Default JVM limits | Tune `ES_JAVA_OPTS` and shard count |

---

## 12. Conclusion
The **ELK stack** provides a centralized, scalable logging solution for Django microservices. By integrating Django’s logging with Filebeat → Logstash → Elasticsearch → Kibana, developers gain real-time visibility into application behavior, drastically improving debugging, monitoring, and performance tuning.

---

## 13. References
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash Configuration Guide](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Kibana User Guide](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Beats (Filebeat) Documentation](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
- [Django Logging Framework](https://docs.djangoproject.com/en/stable/topics/logging/)

---

# Django REST Microservices with ELK — Production-ready Example

This document provides a simple, opinionated microservices scaffold using Django REST Framework and the ELK stack (Elasticsearch, Logstash, Kibana). It includes: repository layout, Docker Compose for local & production-like testing, Dockerfiles, example Django apps (user-service and order-service), Postgres, Redis, Gunicorn + Nginx, Filebeat → Logstash → Elasticsearch, and deployment & operational guidance.

---

## 1. Goals
- Minimal realistic microservices example: **user-service** + **order-service** (Django REST).
- Centralized logging using **Filebeat → Logstash → Elasticsearch → Kibana**.
- Production-worthy components: Gunicorn, Nginx, Postgres, Redis, environment configs, secrets handling notes, and ILM for logs.
- CI/CD and operational tips (migrations, backups, scaling).

---

## 2. Repository layout
```
project-root/
├─ infra/
│  ├─ docker-compose.yml
│  ├─ nginx/
│  │  └─ nginx.conf
│  ├─ logstash/
│  │  └─ pipeline/logstash.conf
│  └─ filebeat/
│     └─ filebeat.yml
├─ services/
│  ├─ user-service/
│  │  ├─ Dockerfile
│  │  ├─ manage.py
│  │  ├─ requirements.txt
│  │  └─ users/  (Django app)
│  └─ order-service/
│     ├─ Dockerfile
│     ├─ manage.py
│     ├─ requirements.txt
│     └─ orders/ (Django app)
├─ compose_env/         # sample env files for compose
└─ README.md
```

---

## 3. infra/docker-compose.yml (development / staging mimic)
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.4
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - '9200:9200'

  logstash:
    image: docker.elastic.co/logstash/logstash:8.13.4
    volumes:
      - ./infra/logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - '5044:5044'
    depends_on: [elasticsearch]

  kibana:
    image: docker.elastic.co/kibana/kibana:8.13.4
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - '5601:5601'
    depends_on: [elasticsearch]

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.13.4
    user: root
    volumes:
      - ./infra/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
      - ./logs:/var/log/django
    depends_on: [logstash]

  nginx:
    image: nginx:1.25
    ports:
      - '80:80'
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on: [user, order]

  user:
    build: ./services/user-service
    env_file: ./compose_env/user.env
    volumes:
      - ./services/user-service:/app
      - ./logs/user:/app/logs
    depends_on: [postgres, redis]

  order:
    build: ./services/order-service
    env_file: ./compose_env/order.env
    volumes:
      - ./services/order-service:/app
      - ./logs/order:/app/logs
    depends_on: [postgres, redis]

volumes:
  pgdata:
```

Notes:
- `logs` directory is mounted so Filebeat can read container log files.
- In production use remote logging (Filebeat on host or sidecar) and do not mount project sources.

---

## 4. services/*/Dockerfile (example)
```dockerfile
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# create logs dir and set permissions
RUN mkdir -p /app/logs && chown nobody:nogroup /app/logs
# use gunicorn for production
CMD ["/bin/sh", "-c", "gunicorn core.wsgi:application -w 3 -b 0.0.0.0:8000 --access-logfile /app/logs/gunicorn_access.log --error-logfile /app/logs/gunicorn_error.log"]
```

---

## 5. Django settings - logging (structured JSON)
Use structured JSON logs so Logstash can parse them easily. Example `settings.py` logging config:

```python
import os
import json

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', '/app/logs/django.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(asctime)s %(levelname)s %(name)s %(message)s',
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOG_FILE,
            'formatter': 'json'
        }
    },
    'root': {
        'handlers': ['file'],
        'level': LOG_LEVEL
    }
}
```

Install `python-json-logger` in requirements.

Log an example in code:
```python
import logging
logger = logging.getLogger('app')
logger.info('order_processed', extra={'order_id': 123, 'user_id': 45, 'duration_ms': 234})
```

The `extra` fields will be included in the JSON log output.

---

## 6. infra/logstash/pipeline/logstash.conf (simple pipeline)
```conf
input {
  beats { port => 5044 }
}

filter {
  json {
    source => "message"
    skip_on_invalid_json => true
  }

  if [message] and ![order_id] {
    # fallback grok parse if not JSON
    grok { match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] %{GREEDYDATA:msg}" } }
  }

  date { match => ["timestamp", "ISO8601"] }

  mutate { add_field => { "environment" => "staging" } }
}

output {
  elasticsearch { hosts => ["http://elasticsearch:9200"] index => "django-logs-%{+YYYY.MM.dd}" }
  stdout { codec => rubydebug }
}
```

Notes: We prefer JSON logs; the pipeline attempts to parse JSON and falls back to grok.

---

## 7. infra/filebeat/filebeat.yml
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/django/*.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      env: staging

output.logstash:
  hosts: ["logstash:5044"]
```

If running Filebeat as a host agent, point `paths` to host log directories or container volumes.

---

## 8. Minimal Django apps
### users app (users/views.py)
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from users.models import User
import logging
logger = logging.getLogger('users')

class UserDetail(APIView):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        logger.info('user_fetched', extra={'user_id': user.id})
        return Response({'id': user.id, 'email': user.email})
```

### orders app (orders/views.py)
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from orders.models import Order
import logging
logger = logging.getLogger('orders')

class CreateOrder(APIView):
    def post(self, request):
        # create order logic (simplified)
        order = Order.objects.create(user_id=request.data['user_id'], total=request.data['total'])
        logger.info('order_created', extra={'order_id': order.id, 'user_id': order.user_id})
        return Response({'id': order.id}, status=201)
```

Include healthcheck views and metrics endpoints (Prometheus) for real production use.

---

## 9. Nginx config (infra/nginx/nginx.conf)
```nginx
upstream user_upstream { server user:8000; }
upstream order_upstream { server order:8000; }

server {
  listen 80;
  location /users/ {
    proxy_pass http://user_upstream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  location /orders/ {
    proxy_pass http://order_upstream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

In production, terminate TLS at a load balancer (e.g., AWS ALB) or use Nginx with certbot and strong TLS settings.

---

## 10. Index lifecycle & ILM example (production Elasticsearch)
Create an ILM policy to rotate indices and keep 30 days:
```json
PUT _ilm/policy/django-logs-policy
{ "policy": { "phases": { "hot": { "actions": {} }, "delete": { "min_age": "30d", "actions": { "delete": {} } } } } }
```
Attach the policy to an index template for `django-logs-*`.

---

## 11. Deployment notes (production readiness)
1. **Secrets & env**: do not store secrets in compose files. Use a secret manager (AWS Secrets Manager, HashiCorp Vault, Kubernetes secrets).
2. **TLS & Auth**: enable transport TLS in Elasticsearch and secure Kibana. Use API keys for ingestion.
3. **Scaling**: run Elasticsearch cluster across multiple nodes, tune number_of_shards, replicas, and JVM heap (50% of RAM but <= 32GB).
4. **Backups**: use snapshot repository to S3 for index backups.
5. **Monitoring**: enable Metricbeat and APM for deeper tracing.
6. **Logging volume**: avoid logging PII; sample high-volume logs or use log level thresholds.

---

## 12. CI/CD pipeline (high-level)
- Build & test images for both services.
- Run `migrate` and smoke tests in a staging environment.
- Run contract tests between services.
- Deploy to production via blue/green or rolling updates.
- Run migrations with backward-compatible steps.

---

## 13. Troubleshooting checklist
- If no logs reach Kibana: confirm Filebeat is running and reading expected files; check Logstash logs; check Elasticsearch health.
- If indices are not found: check index naming and Kibana index pattern.
- High latency: check ES cluster health, slow queries, and reindex/shard counts.

---

## 14. Next steps & enhancements
- Add Metricbeat and APM to monitor performance and traces.
- Replace Filebeat with a sidecar or host-level agent in production for better performance.
- Use centralized config and secrets store.
- Add throttling and backpressure for log ingestion if your system produces heavy logs.

---

If you want, I can:
- provide complete runnable files (Dockerfiles, settings, requirements) in a ZIP layout you can download and run locally, or
- convert this to a Kubernetes manifest with Helm charts for production deployment.  Which do you prefer?

