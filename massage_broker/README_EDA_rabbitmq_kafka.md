Here’s a practical, engineer-friendly guide to how **RabbitMQ** and **Kafka** fit into an **Event-Driven Architecture (EDA)**—with clear terminology, mental models, and Django examples you can paste into real projects.

# 1) What “Event-Driven” actually means

**Event**: an immutable fact that something happened (e.g., UserRegistered, OrderPlaced).  
**Producer**: code that publishes events.  
**Broker**: infrastructure that transports/keeps events (RabbitMQ/Kafka).  
**Consumer**: code that reacts to events.  
**Stream**: an append-only sequence of events (Kafka topics).  
**Message**: the unit transmitted (event payload + headers/metadata).  
**Schema**: the shape of the event (JSON/Avro/Protobuf).  
**Contract**: a stable promise between producers and consumers about schema & semantics.  
**DLQ** (Dead-Letter Queue/Topic): where poison messages go after repeated failures.  
**At-least-once** vs **At-most-once** vs **Exactly-once**: delivery guarantees (see §7).  
**Idempotency**: processing the same event multiple times yields the same final state.

# 2) RabbitMQ vs Kafka: mental model

| **Dimension** | **RabbitMQ** | **Kafka** |
| --- | --- | --- |
| Primary model | **Message broker** (queues, routing) | **Distributed log** (topics, partitions) |
| Use cases | Task queues, RPC, request/response, fanout, per-message routing | Event streaming, analytics, replay, durable event sourcing |
| Storage | Messages typically flow through queues; can be persisted but optimized for delivery | Persisted logs by default; retention by time/size; replay any time |
| Ordering | Per-queue (not strong if multiple consumers in parallel) | Strong ordering within a **partition** |
| Scale | Horizontal via sharding/queues | Horizontal via partitions/consumer groups |
| Delivery | At-least-once by default (ack/nack); per consumer | At-least-once by default (commit offsets); per group |
| Routing | Exchanges (direct/topic/fanout/headers) bind to queues | No routing; producers choose topic & optional key → partition |
| Schema | Bring your own (JSON/Proto) | Often used with Schema Registry (Avro/JSON Schema/Protobuf) |
| Admin UX | Excellent management UI | CLI + tools; newer KRaft (no ZooKeeper) |

**Rule of thumb**

- Use **RabbitMQ** when you need **work queues**, precise **routing**, or **RPC-ish** patterns.
- Use **Kafka** when you need **durable streams**, **replay**, **high throughput**, **analytics**, or **event sourcing/CQRS**.

# 3) Core RabbitMQ concepts (quick)

- **Exchange**: receives messages; routes to queues using **bindings**.
  - **direct** (exact routing key), **topic** (orders.\*), **fanout** (broadcast), **headers**.
- **Queue**: buffers messages until consumed.
- **Binding**: exchange → queue rule.
- **Ack/Nack/Requeue**: confirms success or failure.
- **Prefetch** (QoS): how many messages a consumer can process concurrently.
- **DLX** (Dead-Letter Exchange): where messages go after TTL/negative ack/max retries.

# 4) Core Kafka concepts (quick)

- **Topic**: named event stream.
- **Partition**: ordered shard of a topic; events with same key go to same partition.
- **Offset**: sequential position in a partition.
- **Consumer group**: consumers share partitions; each partition is consumed by exactly one consumer in the group for parallelism + ordering.
- **Retention**: time/size/policy; enables replay.
- **KRaft**: Kafka’s built-in consensus replacing ZooKeeper.

# 5) Django + RabbitMQ: two ways

## 5.1 Celery (recommended for task queues)

**Install**
```bash
pip install celery\[redis,rabbitmq\] # amqp is included via kombu
```
**project/init.py**
```python
from .celery import app as celery_app
__all__ = ("celery_app",)

```
**project/celery.py**

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
app = Celery("project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

```

**settings.py**

```python
CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672//"  # RabbitMQ
CELERY_RESULT_BACKEND = "rpc://"  # or Redis/db
CELERY_TASK_ACKS_LATE = True      # at-least-once; retry-safe tasks
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 60

```

**app/tasks.py**

```python
from celery import shared_task
import time

@shared_task(bind=True, max_retries=5, default_retry_delay=10)
def send_welcome_email(self, user_id):
    # idempotency: check if already sent in DB before sending again
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    # ... send email (idempotent) ...
    return f"sent to {user.email}"

```

**app/views.py**

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from .tasks import send_welcome_email

class RegisterView(APIView):
    def post(self, request):
        # ... create user ...
        user_id = 123
        send_welcome_email.delay(user_id)  # publish task to RabbitMQ
        return Response({"status": "queued"})

```

This gives you reliable queuing, retries, and visibility via **RabbitMQ Management UI** and celery -A project worker -l info.

## 5.2 Raw AMQP (pika) when you need exchanges/routing

**Install**
```bash
pip install pika
```
**publisher.py** (Django service publishes a domain event)

```python
import json, pika, uuid

def publish_user_registered(event: dict):
    # event contains idempotency_key (e.g., event_id)
    connection = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@localhost:5672/"))
    channel = connection.channel()

    channel.exchange_declare(exchange="users", exchange_type="topic", durable=True)

    message = json.dumps(event).encode()
    props = pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,  # persistent
        message_id=event["event_id"],
    )

    channel.basic_publish(
        exchange="users",
        routing_key="user.registered",
        body=message,
        properties=props,
        mandatory=True,
    )
    connection.close()

```

**consumer.py** (bound queue with DLX and retry)

```python
import json, pika, time

conn = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@localhost:5672/"))
ch = conn.channel()

# DLX setup
ch.exchange_declare("dlx.users", "topic", durable=True)
ch.queue_declare("q.users.dlq", durable=True)
ch.queue_bind("q.users.dlq", "dlx.users", routing_key="#")

# Main exchange/queue with dead-lettering & retry TTL
args = {
    "x-dead-letter-exchange": "dlx.users",
    "x-message-ttl": 300000,  # 5 minutes optional
}
ch.exchange_declare("users", "topic", durable=True)
ch.queue_declare("q.users.registered", durable=True, arguments=args)
ch.queue_bind("q.users.registered", "users", routing_key="user.registered")

def handle_message(ch_, method, props, body):
    evt = json.loads(body)
    try:
        # idempotent processing (check event_id in DB)
        print("Processing", evt)
        ch_.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        # Nack with requeue=False to dead-letter after retries handled externally
        ch_.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

ch.basic_qos(prefetch_count=1)
ch.basic_consume(queue="q.users.registered", on_message_callback=handle_message)
ch.start_consuming()

```

# 6) Django + Kafka: producer/consumer pattern

**Install**
```bash
pip install confluent-kafka pydantic
```
**settings.py**

```python
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_SECURITY = {
    # Example for SASL/TLS if needed
    # "security.protocol": "SASL_SSL",
    # "sasl.mechanisms": "PLAIN",
    # "sasl.username": "...",
    # "sasl.password": "...",
}

```

**events/schemas.py** (define a stable schema; Pydantic for JSON)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class UserRegistered(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime
    user_id: int
    email: str
    source: str = "auth-service"
    version: int = 1

```

**events/producer.py**

```python
import json
from confluent_kafka import Producer
from django.conf import settings

def get_producer():
    conf = {"bootstrap.servers": settings.KAFKA_BOOTSTRAP, **settings.KAFKA_SECURITY}
    return Producer(conf)

def publish_user_registered(event_model):
    p = get_producer()
    topic = "users.events"
    key = str(event_model.user_id).encode()  # ensures same partition per user

    p.produce(topic, key=key, value=event_model.json().encode())
    p.flush()  # in hot paths, avoid flush per message; batch instead

```

**views.py**

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from .events.schemas import UserRegistered
from .events.producer import publish_user_registered
from django.utils.timezone import now

class RegisterView(APIView):
    def post(self, request):
        # ... create user ...
        evt = UserRegistered(occurred_at=now(), user_id=123, email="u@example.com")
        publish_user_registered(evt)
        return Response({"status": "published", "event_id": str(evt.event_id)})

```

**Management command: Kafka consumer (idempotent + DLQ)**  
Create app/management/commands/run_user_consumer.py
```python
from django.core.management.base import BaseCommand
from confluent_kafka import Consumer, Producer
from django.conf import settings
import json, logging

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Consume user events from Kafka"

    def handle(self, *args, **opts):
        consumer = Consumer({
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP,
            "group.id": "users-processor",     # consumer group
            "enable.auto.commit": False,       # commit only after success
            "auto.offset.reset": "earliest",
            **settings.KAFKA_SECURITY
        })
        dlq = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP, **settings.KAFKA_SECURITY})

        consumer.subscribe(["users.events"])

        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None: 
                    continue
                if msg.error():
                    log.error("Kafka error: %s", msg.error())
                    continue

                try:
                    evt = json.loads(msg.value())
                    event_id = evt["event_id"]

                    # Idempotency example:
                    # if ProcessedEvent.objects.filter(event_id=event_id).exists(): 
                    #     consumer.commit(message=msg, asynchronous=False)
                    #     continue
                    # ... do work ...
                    # ProcessedEvent.objects.create(event_id=event_id)

                    consumer.commit(message=msg, asynchronous=False)
                except Exception as e:
                    dlq.produce("users.events.dlq", key=msg.key(), value=msg.value())
                    dlq.flush()
                    # Do NOT commit; keep offset for observability or move forward based on your policy
        finally:
            consumer.close()
```

**Notes**

- **At-least-once** is achieved by committing offsets only after successful processing.
- **Ordering**: guaranteed per **partition**; keep a consumer concurrency ≤ number of partitions to respect per-key order.

# 7) Delivery semantics & idempotency (the part that saves you)

- **At-least-once** (default in both): you may process duplicates. **Make handlers idempotent**:
  - Store a ProcessedEvent(event_id) row; ignore if seen.
  - Use **idempotency keys** in writes (e.g., unique constraints).
- **At-most-once**: commit/ack before processing—fast but can drop messages on crash (usually not recommended).
- **Exactly-once**:
  - Kafka: **EOS** (transactional.id, idempotent producer, read-process-write within a transaction) mainly for Kafka→Kafka processing with stream processors (Kafka Streams, ksqlDB). Cross-system exactly-once is hard—in practice, do **outbox + idempotent consumers**.
  - RabbitMQ: not natively; model as at-least-once + idempotent consumers.

# 8) Outbox pattern (Django-ready)

Guarantees you **never lose events** emitted from your app even if the broker is down, and avoids dual-write races.

**models.py**

```python
from django.db import models
from django.utils.timezone import now
import uuid

class EventOutbox(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=200)        # or exchange + routing_key for RabbitMQ
    key = models.CharField(max_length=200, null=True, blank=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(default=now)
    published_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)

```

**writing the event atomically**

```python
from django.db import transaction
from .models import EventOutbox

def create_user_and_record_event(user_data):
    with transaction.atomic():
        user = User.objects.create(**user_data)
        EventOutbox.objects.create(
            topic="users.events",
            key=str(user.id),
            payload={"type":"UserRegistered","user_id":user.id,"email":user.email},
        )
    return user

```

**publisher job (Celery beat or management command)**

```python
from django.utils.timezone import now
from .models import EventOutbox
from .events.producer import get_producer

def publish_outbox_batch(batch_size=500):
    p = get_producer()
    rows = (EventOutbox.objects
            .filter(published_at__isnull=True)
            .order_by("created_at")[:batch_size])
    for row in rows:
        try:
            p.produce(row.topic, key=(row.key or "").encode(), value=json.dumps(row.payload).encode())
            p.poll(0)
            row.published_at = now()
            row.attempts += 1
            row.save(update_fields=["published_at","attempts"])
        except Exception:
            row.attempts += 1
            row.save(update_fields=["attempts"])
    p.flush()
```

Same idea works with RabbitMQ (swap the producer).

# 9) Retries, backoff, and DLQ

## RabbitMQ

- **Per-message retry**: nack + requeue (beware hot loops).
- **Dedicated retry queue(s)** with TTL + DLX:
  - Publish failures to q.retry.5s (TTL 5000ms) that dead-letters back to main.
  - After N attempts, route to q.dlq.

## Kafka

- **Retry topic(s)** with increasing delays (e.g., users.events.retry.1m, …5m) using a scheduler (Kafka doesn’t delay natively).
- **DLQ topic** after max attempts; keep headers with attempt count and error.

# 10) Schema & compatibility

- Prefer **JSON** for simplicity or **Avro/Protobuf** with a **Schema Registry** for evolution.
- Rules:
  - **Backward compatible** changes only (add optional fields; don’t break consumers).
  - Include type, version, occurred_at, event_id, and **producer name**.
  - Validate at the producer boundary (Pydantic/DRF serializers); validate again on the consumer if the topic isn’t trusted.

# 11) Observability & ops

- **RabbitMQ**: enable the Management Plugin; watch queue depth, unacked, publish/ack rates; use Prometheus RabbitMQ exporter.
- **Kafka**: monitor broker/controller health, under-replicated partitions, consumer lag (Burrow, Kafka Lag Exporter), throughput.
- **Tracing**: propagate **trace/Span IDs** (W3C Trace Context) in message headers; integrate with OpenTelemetry.
- **Dashboards**: message rates, error rates, retry/DLQ volume, consumer lag, processing latency.

# 12) Security & hardening

- Use **TLS** for both brokers.
- RabbitMQ: **virtual hosts**, per-user permissions, quorum queues for HA.
- Kafka: **SASL** (PLAIN/OAUTH/GSSAPI), **ACLs**; prefer **KRaft**\-based clusters; set appropriate retention and quotas.
- Keep **message sizes** small; prefer storing large blobs externally and passing references.

# 13) Patterns you’ll likely use

- **Fan-out**: one event → many services (RabbitMQ fanout or Kafka multiple consumer groups).
- **CQRS**: command model emits events; read models subscribe to build projections.
- **Saga/Process manager**: orchestrate multi-step workflows with compensations.
- **Request/Reply**:
  - RabbitMQ: reply queue + correlation ID.
  - Kafka: doable with “reply topics” + correlation IDs, but not its sweet spot.
- **Filtering**:
  - RabbitMQ exchanges + routing keys.
  - Kafka: consumers filter in code, or use streams/ksqlDB for server-side filtering.

# 14) Minimal docker-compose (sketch)

```yaml
version: "3.8"
services:
  rabbitmq:
    image: rabbitmq:3.13-management
    ports: ["5672:5672", "15672:15672"]

  kafka:
    image: bitnami/kafka:latest
    environment:
      - KAFKA_ENABLE_KRAFT=yes
      - KAFKA_CFG_NODE_ID=1
      - KAFKA_CFG_PROCESS_ROLES=broker,controller
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=1@kafka:9093
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092
    ports: ["9092:9092"]
```

# 15) Checklists

## Designing a new event

1. Name: OrderPlaced (present/past tense is fine; pick one convention).
2. Include: event_id, occurred_at, version, producer, payload.
3. Define schema & add tests for backward compatibility.
4. Publish within **outbox** transaction.
5. Consumer is **idempotent** and observable.
6. Decide retry policy + DLQ routing/topic.

## Launching consumers safely

- Start consumers after topic/queue exists and producer deployed.
- Set prefetch (RabbitMQ) or group.id + offset policy (Kafka).
- Roll out with canary consumers; watch lag/queue depth & errors.

# 16) Common pitfalls & fixes

- **Duplicate processing**: always implement idempotency.
- **Poison messages**: route to DLQ after bounded retries.
- **Hot requeue loops** (RabbitMQ): use delayed retry queues (TTL) instead of immediate requeue.
- **Kafka rebalancing storms**: set cooperative rebalancing, keep sessions healthy, avoid very slow handlers.
- **Losing order**: in Kafka, use keys; in RabbitMQ, avoid >1 consumer for strict per-queue order.
- **Dual write bug** (DB + broker): use **Outbox**.

## TL;DR recommendations

- **Work queues, per-message routing, RPC-ish patterns** → **RabbitMQ + Celery**.
- **High-throughput, durable streams, replay, event sourcing** → **Kafka + Outbox + Idempotent consumers**.
- In both: **outbox, retries + DLQ, idempotency, observability** are non-negotiables.