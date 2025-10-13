# Production-grade Notification System — Design & Implementation

> End-to-end system design, architectural decisions, Django implementation patterns, scalability from small to large user volumes, production operational concerns, and code snippets you can drop into a repository.

---

## Table of contents
1. Goals & Requirements
2. High-level architecture
3. Data model and schema
4. Django project structure (apps)
5. Implementation details
   - Models
   - Serializers & APIs
   - Async worker (Celery) & broker
   - Notification delivery adapters
   - WebSocket / Push (real-time) with Channels
   - Scheduling & batching
   - Retries, backoff, DLT
   - Idempotency
6. Scaling & capacity planning
7. Monitoring, observability & SLOs
8. Security & compliance
9. Testing strategy
10. Deployment & Ops (Docker, K8s, CI/CD)
11. Example code snippets (models, tasks, views, Docker Compose)
12. Next steps & roadmap

---

## 1. Goals & Requirements
**Functional:**
- Deliver notifications to users via channels: in-app (WebSocket), email, SMS, push (APNs/FCM), and optionally third-party integrations (Slack, Teams).
- Support immediate, delayed (schedule), and recurring notifications.
- Allow templates with personalization (placeholders).
- Allow grouping (digest) and per-user preferences (opt-outs, channel preferences, quiet hours).

**Non-functional / production:**
- High throughput: support from hundreds to millions of notifications/day.
- Reliability: retry failed deliveries with exponential backoff, dead-letter for manual inspection.
- Scalability: horizontally scale workers and WebSocket layers.
- Observability: metrics, logs, tracing, alerting.
- Cost-conscious: batched sending, provider fallbacks.

**Constraints / design choices:**
- Use Django for the API and admin.
- Use Postgres as the primary relational store.
- Use Redis for caching, rate-limiting tokens, and as Celery broker (or RabbitMQ for larger scale).
- Use Celery for background jobs and scheduled tasks.
- Use Channels + Daphne for WebSockets (scale with multiple consumers behind a channel layer like Redis and run behind load balancer with sticky sessions or use token-based routing).

---

## 2. High-level architecture

```
Clients (web/mobile)
   |
   |--> REST API (Django/DRF) + Admin
   |      - create notifications, manage templates & preferences
   |
   |--> WebSocket (Django Channels / Daphne) for real-time in-app

DB: Postgres (notifications, templates, preferences, delivery logs)
Cache/Broker: Redis (celery broker + channel layer + caches)
Async Workers: Celery workers (delivery tasks)
Delivery Adapters: email (SES/Sendgrid), SMS (Twilio), push (FCM/APNs), Slack

Monitoring: Prometheus + Grafana, ELK/EFK stack for logs
Deployment: Docker -> Kubernetes (or ECS) with Horizontal Pod Autoscaler
```

Key flows:
1. API receives notification create request -> store Notification record -> enqueue delivery tasks (Celery) per channel respecting user preferences.
2. Celery worker performs adapter send -> updates DeliveryLog -> on success update Notification status or create DeliveryAudit.
3. Real-time: for users connected via WebSocket, publish an event on channel layer so the corresponding Channels consumer pushes it instantly.
4. For scheduled/digest, scheduler (Celery beat or external scheduler) enqueues tasks at given time.

---

## 3. Data model and schema

Core entities:
- `Notification` (logical notification intent)
- `NotificationTemplate` (templates with placeholders)
- `NotificationChannel` (ENUM: IN_APP, EMAIL, SMS, PUSH, SLACK)
- `DeliveryAttempt` / `DeliveryLog` (audit per-channel per-attempt)
- `UserPreference` (per-user channel opt-in and quiet hours)
- `Device` (for push: token, platform, last_seen)

Example simplified SQL-ish model:

```
Notification(id PK, sender_id, title, body, template_id FK, payload JSONB, priority, created_at, scheduled_at, expires_at, status)
NotificationTarget(id PK, notification_id FK, user_id FK, channel ENUM, status ENUM, attempted_count INT, last_attempt_at TIMESTAMP)
DeliveryLog(id PK, notification_target_id FK, provider VARCHAR, provider_resp JSONB, status ENUM, attempt INT, timestamp)
NotificationTemplate(id PK, name, subject_template, body_template, json_schema)
UserPreference(id PK, user_id FK, channel ENUM, enabled BOOL, quiet_hours JSON)
Device(id PK, user_id FK, platform ENUM, token, last_seen)
```

Notes:
- Use JSONB for `payload` to store arbitrary personalization data.
- Index `scheduled_at`, `status`, `user_id` for fast selection.
- Partition `DeliveryLog` by month if extremely high volume.

---

## 4. Django project structure (apps)

```
project/
  apps/
    notifications/  # core logic, models, APIs, admin
    users/          # user model + preferences
    integrations/   # provider adapters (email/sms/push)
    websocket/      # channels consumers
  workers/
    tasks.py        # Celery tasks
  config/
    settings/
```

Use separate apps to keep concerns isolated. `notifications` contains orchestration; `integrations` contains provider-specific code behind a common interface.

---

## 5. Implementation details

### Models (Django)
- `Notification` — represents a notification request. Fields: `id`, `created_by`, `title`, `body`, `template`, `payload`, `priority`, `status`, `scheduled_at`.
- `NotificationTarget` — per-user per-channel target. Holds status and attempt count.
- `DeliveryAttempt` — records provider responses.
- `UserPreference` — boolean per channel and optional quiet hours.
- `Device` — for push tokens.

Use `choices` for enums, and PostgreSQL JSONBField for payload.

### Serializers & APIs
- Public API to create notification (POST) where clients pass: `template_name` or `title/body`, `targets` (list of user_ids or filters), `channels` (or 'all'), `schedule`.
- Admin API to manage templates, view delivery logs, retry failed deliveries.

Important: perform input validation and rate-limit creation per-app or per-user to avoid floods.

### Async worker (Celery)
- Use Celery with Redis broker for simplicity; RabbitMQ scales better for huge volumes.
- Define tasks:
  - `enqueue_notification_targets(notification_id)` — creates NotificationTarget rows and enqueues per-target delivery tasks.
  - `deliver_notification_target(target_id)` — does actual send via provider adapter.
  - `send_digest(user_id, window)` — aggregates messages and sends digest.

- Configure concurrency, worker autoscaling, and worker queues (e.g., high-priority queue, low-priority, retry queue).

### Delivery adapters (provider abstraction)
- Provide an adapter interface with method `send(to, subject, body, payload)` returning `(status, provider_resp)`.
- Implement adapters for SendGrid/SES (email), Twilio (SMS), Firebase (FCM) and APNs (push).
- Implement provider fallbacks: e.g., if SendGrid fails, use SES if available.

### WebSocket / Push (Django Channels)
- Use Django Channels with Redis channel layer.
- When NotificationTarget is created, publish on channel layer `channel_layer.group_send(f'user_{user_id}', {...})` so connected consumers will push instantly.
- For mobile push, workers call FCM/APNs.

### Scheduling & batching
- For scheduled notifications, create `scheduled_at` and rely on Celery Beat to run a periodic job that selects due notifications and enqueues their targets.
- For digests, aggregate by user/time window. Batching reduces provider costs (e.g., single email with multiple items).

### Retries, backoff, dead-letter
- On transient failure, retry with exponential backoff; use Celery's retry mechanisms. Track attempt count on `NotificationTarget`.
- After N attempts (configurable), mark as failed and emit an alert/dlq (move payload to a Dead Letter Queue — e.g., a special DB table or broker queue) for manual inspection.

### Idempotency
- Make `deliver_notification_target` idempotent by ensuring if provider already returned success for that `target_id` it won't send again. Use DB unique constraints and check `DeliveryAttempt` success state.

### Rate limiting & throttling
- Per-user rate limits to prevent sending too many notifications in short time (Redis token bucket or leaky bucket). Also provider rate limits: implement local throttling/batching before provider call.

---

## 6. Scaling & capacity planning

**Database:**
- Start with single Postgres; add read-replicas for heavy reads.
- Partition `delivery_logs` by time.
- Use connection pooling (PgBouncer) for many workers.

**Workers:**
- Autoscale Celery workers based on queue length / CPU. Use separate worker pools per queue.
- For millions/day, use many small workers distributed across nodes with RabbitMQ or Redis clusters.

**Channels / Real-time:**
- Run multiple Daphne instances behind LB. Use Redis channel layer to route messages. For mobile/web, prefer push notifications for offline devices.

**Storage / Backups:**
- Archive old logs to object storage (S3) and remove from DB.

**Throughput example:**
- Each worker can handle X sends/sec depending on provider latency. For email, high throughput requires provider bulk APIs (SendGrid batch endpoints). For SMS, provider often limits per account per second — plan accordingly.

---

## 7. Monitoring, observability & SLOs
- Metrics to collect: notifications created/sec, delivered/sec, failed/sec, avg delivery latency, queue length, worker CPU/mem, provider error rates.
- Logs: structured JSON logs including `notification_id`, `target_id`, `provider`, `attempt`. Centralize to ELK/EFK.
- Tracing: instrument with OpenTelemetry to track end-to-end.
- Alerts: high failure rate, queue growth, provider latency spikes.

Define SLOs: e.g., 99% of high-priority notifications delivered to at least one channel within 30s.

---

## 8. Security & compliance
- Auth: APIs protected with JWT/OAuth2; admin with role-based access.
- PII: encrypt sensitive payload fields at rest if storing personal data; redact logs.
- Opt-outs: honor unsubscribe and multi-jurisdictional rules (e.g., TCPA for SMS US).
- Secrets: store provider API keys in secret manager (AWS Secrets Manager / Vault).

---

## 9. Testing strategy
- Unit tests for adapters by mocking provider APIs.
- Integration tests using localstack (for S3) and a test SMTP server if needed.
- Load tests (k6, locust) to estimate throughput and resource usage.
- Chaos testing for provider failures and network partitions.

---

## 10. Deployment & Ops
- Dev: Docker Compose with Postgres + Redis + Celery + Django + Daphne.
- Prod: Kubernetes with Horizontal Pod Autoscaler; separate deployments for API, workers, and channel layer.
- Use readiness/liveness probes; configure resource requests/limits.
- CI/CD: run tests -> build images -> push -> deploy via ArgoCD/Flux or GitHub Actions -> Kubernetes.

---

## 11. Example code snippets
> The snippets below are intentionally concise to show structure — use them as a starter.

### `models.py` (notifications app)

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.postgres.fields import JSONField

User = get_user_model()

class Notification(models.Model):
    PRIORITY_CHOICES = [(0, 'low'), (1, 'normal'), (2, 'high')]
    STATUS = [("pending","pending"),("processing","processing"),("sent","sent"),("failed","failed")]

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    payload = JSONField(default=dict)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    status = models.CharField(max_length=32, choices=STATUS, default='pending')

class NotificationTarget(models.Model):
    CHANNEL = [("in_app","in_app"),("email","email"),("sms","sms"),("push","push")]
    STATUS = [("queued","queued"),("delivered","delivered"),("failed","failed")]

    notification = models.ForeignKey(Notification, related_name='targets', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.CharField(max_length=32, choices=CHANNEL)
    status = models.CharField(max_length=32, choices=STATUS, default='queued')
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

class DeliveryLog(models.Model):
    target = models.ForeignKey(NotificationTarget, related_name='logs', on_delete=models.CASCADE)
    provider = models.CharField(max_length=100)
    provider_response = JSONField(default=dict)
    status = models.CharField(max_length=32)
    attempt = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### `tasks.py` (Celery)

```python
from celery import shared_task, Task
from django.utils import timezone
from .models import Notification, NotificationTarget, DeliveryLog
from integrations import get_adapter_for_channel
from django.db import transaction

@shared_task(bind=True, max_retries=5)
def deliver_notification_target(self, target_id):
    try:
        target = NotificationTarget.objects.select_for_update().get(pk=target_id)
    except NotificationTarget.DoesNotExist:
        return

    # idempotency check
    if target.status == 'delivered':
        return

    adapter = get_adapter_for_channel(target.channel)
    provider = adapter.provider_name
    try:
        result = adapter.send(
            to=target.user,
            subject=target.notification.title,
            body=target.notification.body,
            payload=target.notification.payload,
        )
    except Exception as exc:
        target.attempts += 1
        target.last_attempt_at = timezone.now()
        target.save(update_fields=['attempts','last_attempt_at'])
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    # record the attempt
    DeliveryLog.objects.create(
        target=target,
        provider=provider,
        provider_response=result,
        status=result.get('status', 'unknown'),
        attempt=target.attempts + 1,
    )

    if result.get('status') == 'success':
        target.status = 'delivered'
        target.save(update_fields=['status'])
    else:
        target.attempts += 1
        target.last_attempt_at = timezone.now()
        if target.attempts >= 3:
            target.status = 'failed'
        target.save(update_fields=['attempts','last_attempt_at','status'])
        if target.status != 'failed':
            raise self.retry(countdown=2 ** self.request.retries)
```

### `integrations/__init__.py` (adapter factory)

```python
# simple factory
from .email_adapter import EmailAdapter
from .sms_adapter import SMSAdapter
from .push_adapter import PushAdapter

def get_adapter_for_channel(channel_name):
    if channel_name == 'email':
        return EmailAdapter()
    if channel_name == 'sms':
        return SMSAdapter()
    if channel_name == 'push':
        return PushAdapter()
    # in_app doesn't need adapter
    raise ValueError('unknown channel')
```

### WebSocket consumer snippet (channels)

```python
# consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return
        self.group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_event(self, event):
        # event contains 'notification' payload
        await self.send_json(event['notification'])
```

When a NotificationTarget is created and user is connected, call:

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(f'user_{user_id}', {
  'type': 'notification.event',
  'notification': { 'title': '...', 'body': '...', 'meta': {...} }
})
```

---

### Example `docker-compose.yml` (dev)

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: notifications
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - db_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  web:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 project.asgi:application
    depends_on: [db, redis]
    ports: ['8000:8000']

  worker:
    build: .
    command: celery -A project worker -Q default -c 4
    depends_on: [db, redis]

  beat:
    build: .
    command: celery -A project beat
    depends_on: [db, redis]

volumes:
  db_data:
```

---

## 12. Next steps & roadmap
1. Implement the minimal MVP: DB models, API to create notifications, Celery tasks, a basic SendGrid adapter, and in-app WebSocket push.
2. Add user preferences and quiet-hours handling.
3. Add retries, monitoring and rate-limiting.
4. Optimize for scale: partition logs, move to RabbitMQ if necessary, move dial-out jobs to dedicated worker clusters.
5. Run load-testing and prepare Kubernetes manifests + HPA.

---

## Appendix: Operational checklist (quick)
- Secret management for provider keys.
- Configure provider webhooks (eg. email bounces) to update DB.
- Implement provider throttling and bulk APIs.
- Document runbooks for failed delivery spikes and provider outages.
- Archive old logs to S3 and purge DB periodically.

---

If you'd like, I can:
- Generate a ready-to-run Django project scaffold (models, tasks, adapters, Dockerfiles, K8s manifests) as a zip.
- Expand adapters for SendGrid, Twilio, FCM with concrete code.
- Provide Grafana dashboards and Prometheus metrics endpoints.

Tell me which of the above you'd like me to produce as files or code next and I will generate them.   



# Production-grade Django Notification System — Full Code Scaffold

This document contains a runnable, production-oriented scaffold for the notification system described earlier. The repository is intentionally opinionated but modular so you can extend adapters, providers, and scale components.

> **How to use:** Clone or copy the files below into a project directory. Follow the `RUNNING.md` section at the end to bring up the dev environment using Docker Compose. For production see the `k8s/` directory and `deploy/` notes.

---

## Repo layout

```
notifications_project/
├── Dockerfile
├── docker-compose.yml
├── RUNNING.md
├── manage.py
├── requirements.txt
├── project/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── tasks.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── email_adapter.py
│   │   ├── sms_adapter.py
│   │   └── push_adapter.py
│   └── websocket/
│       ├── __init__.py
│       └── consumers.py
└── k8s/
    ├── deployment.yml
    └── celery-deployment.yml
```

---

## `requirements.txt`

```
django>=4.2,<5
djangorestframework
psycopg2-binary
celery[redis]
redis
channels==4.0.0
channels-redis
asgiref
requests
python-dotenv
pytz
django-environ
```

---

## `Dockerfile`

```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["daphne","-b","0.0.0.0","-p","8000","project.asgi:application"]
```

---

## `docker-compose.yml` (dev)

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: notifications
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - db_data:/var/lib/postgresql/data

  redis:
    image: redis:7

  web:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 project.asgi:application
    volumes:
      - ./:/app
    ports:
      - '8000:8000'
    depends_on: [db, redis]
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings

  worker:
    build: .
    command: celery -A project worker -l info -Q default
    volumes:
      - ./:/app
    depends_on: [db, redis]
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings

  beat:
    build: .
    command: celery -A project beat -l info
    volumes:
      - ./:/app
    depends_on: [db, redis]
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings

volumes:
  db_data:
```

---

## `project/__init__.py`

```python
from .celery import app as celery_app
__all__ = ('celery_app',)
```

---

## `project/celery.py`

```python
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
app = Celery('project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

---

## `project/asgi.py`

```python
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.websocket import consumers
from django.urls import path

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/notifications/', consumers.NotificationsConsumer.as_asgi()),
        ])
    )
})
```

---

## `project/settings.py` (trimmed for dev; adjust for prod)

```python
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
DEBUG = os.getenv('DEBUG', '1') == '1'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'channels',
    'apps.notifications',
    'apps.integrations',
    'apps.websocket',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': ['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']},
    },
]

WSGI_APPLICATION = 'project.wsgi.application'
ASGI_APPLICATION = 'project.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'notifications'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Channels
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, 6379)],
        },
    },
}

# Celery
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:6379/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:6379/1'
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Static
STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

---

## `project/urls.py`

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/notifications/', include('apps.notifications.urls')),
]
```

---

## `manage.py`

```python
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

---

# apps/notifications

## `apps/notifications/apps.py`

```python
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
```

## `apps/notifications/models.py`

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.utils import timezone

User = get_user_model()

class Notification(models.Model):
    PRIORITY_CHOICES = [(0,'low'),(1,'normal'),(2,'high')]
    STATUS_CHOICES = [('pending','pending'),('processing','processing'),('sent','sent'),('failed','failed')]

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    payload = JSONField(default=dict)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Notification {self.id} {self.title}"

class NotificationTarget(models.Model):
    CHANNEL_CHOICES = [('in_app','in_app'),('email','email'),('sms','sms'),('push','push')]
    STATUS_CHOICES = [('queued','queued'),('delivered','delivered'),('failed','failed')]

    notification = models.ForeignKey(Notification, related_name='targets', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.CharField(max_length=32, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='queued')
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user','status'])]

class DeliveryLog(models.Model):
    target = models.ForeignKey(NotificationTarget, related_name='logs', on_delete=models.CASCADE)
    provider = models.CharField(max_length=100)
    provider_response = JSONField(default=dict)
    status = models.CharField(max_length=32)
    attempt = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

## `apps/notifications/serializers.py`

```python
from rest_framework import serializers
from .models import Notification, NotificationTarget

class NotificationSerializer(serializers.ModelSerializer):
    targets = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    channels = serializers.ListField(child=serializers.ChoiceField(choices=["in_app","email","sms","push"]), required=False)

    class Meta:
        model = Notification
        fields = ['id','title','body','payload','scheduled_at','priority','targets','channels']
        read_only_fields = ['id']

    def create(self, validated_data):
        targets = validated_data.pop('targets', [])
        channels = validated_data.pop('channels', ['in_app'])
        notification = Notification.objects.create(**validated_data)
        # create targets
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=targets)
        to_create = []
        for user in users:
            for channel in channels:
                to_create.append(NotificationTarget(notification=notification, user=user, channel=channel))
        NotificationTarget.objects.bulk_create(to_create)
        # enqueue tasks to deliver
        from .tasks import enqueue_notification_targets
        enqueue_notification_targets.delay(notification.id)
        return notification
```

## `apps/notifications/views.py`

```python
from rest_framework import generics, permissions
from .models import Notification
from .serializers import NotificationSerializer

class CreateNotificationView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
```

## `apps/notifications/urls.py`

```python
from django.urls import path
from .views import CreateNotificationView

urlpatterns = [
    path('', CreateNotificationView.as_view(), name='create-notification'),
]
```

## `apps/notifications/tasks.py`

```python
from celery import shared_task
from django.utils import timezone
from .models import Notification, NotificationTarget, DeliveryLog
from apps.integrations import get_adapter_for_channel
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task
def enqueue_notification_targets(notification_id):
    # set processing
    try:
        notification = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        return
    notification.status = 'processing'
    notification.save(update_fields=['status'])

    targets = NotificationTarget.objects.filter(notification=notification, status='queued')
    for t in targets:
        deliver_notification_target.delay(t.id)

@shared_task(bind=True, max_retries=5)
def deliver_notification_target(self, target_id):
    try:
        target = NotificationTarget.objects.select_related('notification','user').get(pk=target_id)
    except NotificationTarget.DoesNotExist:
        return

    # idempotency
    if target.status == 'delivered':
        return

    # In-app real-time
    if target.channel == 'in_app':
        channel_layer = get_channel_layer()
        payload = {
            'type': 'notification.event',
            'notification': {
                'id': target.notification.id,
                'title': target.notification.title,
                'body': target.notification.body,
                'payload': target.notification.payload,
            }
        }
        async_to_sync(channel_layer.group_send)(f'user_{target.user.id}', payload)
        target.status = 'delivered'
        target.attempts += 1
        target.last_attempt_at = timezone.now()
        target.save(update_fields=['status','attempts','last_attempt_at'])
        DeliveryLog.objects.create(target=target, provider='in_app', provider_response={'sent': True}, status='success', attempt=target.attempts)
        return

    adapter = get_adapter_for_channel(target.channel)
    try:
        result = adapter.send(
            to=target.user,
            subject=target.notification.title,
            body=target.notification.body,
            payload=target.notification.payload,
        )
    except Exception as exc:
        target.attempts += 1
        target.last_attempt_at = timezone.now()
        target.save(update_fields=['attempts','last_attempt_at'])
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    DeliveryLog.objects.create(target=target, provider=adapter.provider_name, provider_response=result or {}, status=result.get('status','unknown'), attempt=target.attempts+1)

    if result.get('status') == 'success':
        target.status = 'delivered'
        target.attempts += 1
        target.last_attempt_at = timezone.now()
        target.save(update_fields=['status','attempts','last_attempt_at'])
    else:
        target.attempts += 1
        target.last_attempt_at = timezone.now()
        if target.attempts >= 3:
            target.status = 'failed'
        target.save(update_fields=['attempts','last_attempt_at','status'])
        if target.status != 'failed':
            raise self.retry(countdown=2 ** self.request.retries)
```

## `apps/notifications/admin.py`

```python
from django.contrib import admin
from .models import Notification, NotificationTarget, DeliveryLog

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id','title','created_at','status','scheduled_at')

@admin.register(NotificationTarget)
class NotificationTargetAdmin(admin.ModelAdmin):
    list_display = ('id','notification','user','channel','status','attempts')

@admin.register(DeliveryLog)
class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('id','target','provider','status','attempt')
```

---

# apps/integrations

## `apps/integrations/__init__.py`

```python
from .email_adapter import EmailAdapter
from .sms_adapter import SMSAdapter
from .push_adapter import PushAdapter

def get_adapter_for_channel(channel_name):
    if channel_name == 'email':
        return EmailAdapter()
    if channel_name == 'sms':
        return SMSAdapter()
    if channel_name == 'push':
        return PushAdapter()
    raise ValueError('unknown channel')
```

## `apps/integrations/email_adapter.py` (example SendGrid implementation)

```python
import os
import requests

class EmailAdapter:
    provider_name = 'sendgrid'

    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.base_url = 'https://api.sendgrid.com/v3'

    def send(self, to, subject, body, payload=None):
        # `to` is a Django User instance here - adapt accordingly
        email = getattr(to, 'email', None)
        if not email:
            return {'status': 'failed', 'error': 'no-email'}
        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
        data = {
            'personalizations': [{'to': [{'email': email}], 'subject': subject}],
            'from': {'email': os.getenv('DEFAULT_FROM_EMAIL','no-reply@example.com')},
            'content': [{'type': 'text/plain', 'value': body or ''}]
        }
        resp = requests.post(f'{self.base_url}/mail/send', json=data, headers=headers, timeout=10)
        if resp.status_code in (200,202):
            return {'status':'success','provider_response':resp.text}
        return {'status':'failed','provider_response':resp.text,'code':resp.status_code}
```

## `apps/integrations/sms_adapter.py`

```python
import os

class SMSAdapter:
    provider_name = 'twilio'

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_FROM')

    def send(self, to, subject, body, payload=None):
        # `to` should have a phone_number attribute - adapt to your user model
        phone = getattr(to, 'phone_number', None)
        if not phone:
            return {'status':'failed','error':'no-phone'}
        # For brevity we won't call Twilio here. In production use twilio SDK.
        # Simulate success
        return {'status':'success','provider_response':{'to': phone}}
```

## `apps/integrations/push_adapter.py`

```python
import os

class PushAdapter:
    provider_name = 'fcm'

    def __init__(self):
        self.server_key = os.getenv('FCM_SERVER_KEY')

    def send(self, to, subject, body, payload=None):
        # `to` should have devices registered - this is a stub
        # In production fetch device tokens and call FCM or APNs
        return {'status':'success','provider_response':{'sent':True}}
```

---

# apps/websocket

## `apps/websocket/consumers.py`

```python
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return
        self.group_name = f'user_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_event(self, event):
        # Forward notification payload to client
        await self.send_json(event.get('notification', {}))
```

---

## `k8s/deployment.yml` (example snippet)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: myrepo/notifications:latest
        ports:
        - containerPort: 8000
        env:
        - name: DJANGO_SETTINGS_MODULE
          value: project.settings
```

---

## RUNNING.md

```
# Run dev environment (Docker Compose)

1. Copy `.env.example` to `.env` and set SENDGRID_API_KEY etc if you want to test email.
2. Build and run:
   docker compose up --build
3. In another shell migrate and create superuser:
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
4. Open http://localhost:8000/admin and register users, then POST to /api/notifications/ to create notifications.

Requests example (create notification via curl):

curl -X POST http://localhost:8000/api/notifications/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"title":"Hello","body":"Test","targets":[1],"channels":["in_app","email"]}'
```

---

## Notes & Next steps
- This scaffold provides a **working base**: models, Celery tasks, Channels consumer, adapters, and a Docker Compose dev environment.
- **Production improvements** you should apply before real usage:
  - Use RabbitMQ for heavy Celery load, or a Redis cluster.
  - Add authentication for WebSocket (token-based) for mobile apps.
  - Replace adapter stubs with robust SDK-based integrations, add provider fallbacks and rate-limiting.
  - Add logging (structured), retries, and DLQ handling. Partition `DeliveryLog` if needed.
  - Add Helm charts / k8s manifests for scaling and secrets management.

If you want, I can now:
- Generate a downloadable zip with these files assembled.
- Expand the SendGrid adapter into a fully tested implementation and add tests.
- Add GitHub Actions CI pipeline and Kubernetes manifests for production.

Tell me which next step you prefer and I'll produce it immediately.

