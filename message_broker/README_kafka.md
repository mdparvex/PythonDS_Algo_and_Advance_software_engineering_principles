# 📖 Technical Documentation on Apache Kafka

## 1\. Introduction

**Apache Kafka** is an open-source **distributed event streaming platform** designed for high-throughput, fault-tolerant, and real-time data pipelines. It is widely used for **event-driven architectures, stream processing, and messaging systems** in modern applications.

Kafka enables:

- Publishing and subscribing to streams of records (like a messaging queue).
- Storing streams of data in a distributed, fault-tolerant way.
- Processing streams in real-time.

## 2\. Core Concepts

### 🔹 2.1 Topics

- A **topic** is a category or feed name where records are published.
- Producers write data to topics, consumers read from them.
- Topics are split into **partitions** for scalability.

### 🔹 2.2 Partitions

- Each topic is divided into **partitions**.
- Messages within a partition are ordered and immutable.
- Partitions are distributed across **brokers**.

### 🔹 2.3 Brokers

- A **broker** is a Kafka server that stores data and serves client requests.
- A Kafka cluster consists of multiple brokers.

### 🔹 2.4 Producers

- Applications that publish messages to Kafka topics.
- Can choose which partition to write to.

### 🔹 2.5 Consumers

- Applications that subscribe to topics and process messages.
- Organized into **consumer groups** for load balancing.

### 🔹 2.6 Zookeeper / KRaft (Kafka Raft)

- **Zookeeper** (legacy) was used for cluster coordination and metadata.
- **KRaft mode** (newer) replaces Zookeeper for simplified deployment.

## 3\. Kafka Architecture

**Flow:**  
Producer → Topic (partitioned across brokers) → Consumer

Key features:

- **Distributed**: Data is replicated across brokers.
- **Scalable**: Add partitions/brokers to scale horizontally.
- **Fault-tolerant**: Replication ensures high availability.

## 4\. Installation and Setup

### 🔹 Install Kafka (with Zookeeper)

```bash
# Download Kafka
wget https://downloads.apache.org/kafka/3.7.0/kafka_2.13-3.7.0.tgz
tar -xzf kafka_2.13-3.7.0.tgz
cd kafka_2.13-3.7.0

# Start Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties

# Start Kafka broker
bin/kafka-server-start.sh config/server.properties
```

## 5\. Kafka Operations

### 🔹 Create a Topic
```bash
bin/kafka-topics.sh --create --topic test-topic --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

```
### 🔹 List Topics
```bash
bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

### 🔹 Produce Messages

```bash
bin/kafka-console-producer.sh --topic test-topic --bootstrap-server localhost:9092
```

(Type some messages and press Enter.)

### 🔹 Consume Messages

```bash
bin/kafka-console-consumer.sh --topic test-topic --from-beginning --bootstrap-server localhost:9092
```

## 6\. Kafka in Django (Example)

Kafka can be integrated into Django using **confluent-kafka** or **kafka-python** libraries.

### 🔹 Install
```bash
pip install kafka-python
```
### 🔹 Producer Example (Django view)

```python
# Producer Example (Django view)
from django.http import JsonResponse
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_event(request):
    event_data = {"user_id": 1, "chapter_id": 5, "action": "read"}
    producer.send('reading-events', event_data)
    producer.flush()
    return JsonResponse({"status": "event sent"})

```

### 🔹 Consumer Example (background worker)

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'reading-events',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    print(f"Received: {message.value}")
```

## 7\. Kafka Use Cases

- **Real-time analytics** (e.g., fraud detection, log monitoring).
- **Event-driven microservices** (decouple producers/consumers).
- **Data pipelines** (moving data between databases and systems).
- **IoT** (collect and process sensor data).
- **Messaging system replacement** (better than RabbitMQ in scale).

## 8\. Pros & Cons

### ✅ Pros

- High throughput and scalability.
- Distributed and fault-tolerant.
- Real-time stream processing.
- Supports replay of messages.

### ❌ Cons

- Complex setup and management.
- Steeper learning curve compared to RabbitMQ.
- Requires external systems (e.g., schema registry, monitoring).

## 9\. Comparison with Other Systems

| **Feature** | **Kafka** | **RabbitMQ** | **ActiveMQ** |
| --- | --- | --- | --- |
| **Model** | Log-based, pub-sub | Message queue | Message queue |
| **Throughput** | Very high | Medium | Medium |
| **Use Case** | Streaming, big data | Task queues | Enterprise integration |
| **Persistence** | Long-term storage | Short-term | Short-term |
| **Scalability** | Excellent | Limited | Limited |

## 10\. Troubleshooting Common Issues

1. **Message Lag**
    - Cause: Consumers are slower than producers.
    - Fix: Scale consumers, increase partitions.
2. **Broker Not Starting**
    - Check logs in /logs/server.log.
    - Port conflicts or Zookeeper not running.
3. **Consumer Not Receiving Messages**
    - Ensure correct topic name.
    - Verify auto_offset_reset and consumer group.
4. **High Disk Usage**
    - Kafka stores logs by default.
    - Use retention policies (log.retention.hours).

## 11\. Conclusion

Apache Kafka is a **powerful distributed streaming platform** ideal for handling high-volume, real-time data. It is more than a messaging queue — it’s a backbone for **event-driven architectures and data pipelines**.

- Use Kafka when you need **real-time, scalable, durable messaging**.
- For smaller use cases, RabbitMQ might be simpler.
- With proper integration, Kafka can power both **microservices communication** and **big data streaming**.

✅ Now you have a **complete developer-friendly documentation** on Kafka: concepts, setup, Django examples, use cases, pros/cons, and troubleshooting.


here’s a practical, step-by-step, production-minded guide to using **Kafka in an Event-Driven Architecture (EDA) with Django microservices**. It’s opinionated toward reliability, observability, and maintainability.

# Kafka in EDA with Django Microservices — Step-by-Step

## 0) What we’re building (reference architecture)

We’ll model three services:

- **User Service** – owns User domain, emits user.created events
- **Order Service** – owns Order domain, consumes user.\* (for enrichment), emits order.created
- **Notification Service** – consumes order.created and sends emails/notifications

### Topics

- users.v1 (key=user_id, compacted)
- orders.v1 (key=order_id, log + retention policy)
- dlq.v1 (dead-letter)

### Contracts & schema

- JSON with a versioned envelope: { "schema": "users.v1", "event": "user.created", "id": "...", "ts": 1690000000, "key": {...}, "data": {...}, "headers": {...} }  
    (You can swap JSON for Avro/Protobuf + Schema Registry later.)

## 1) Plan the events and ownership

- Each service **owns** a set of entities and emits **facts** (immutable events).
- Consumers **react** and update their own stores (CQRS-ish).
- Never share DBs across services. Communicate **only** via events.

Deliverables:

- Event catalog (google doc / md file): name, owner, schema, retention, partition key.
- Service boundaries and team ownership.

## 2) Design topics, partitions, keys, and retention

- **Partitioning**: Choose a key that ensures ordering per entity.
  - users.v1: key = user_id (compacted)
  - orders.v1: key = order_id (delete after 7–30 days)
- **Replication**: replication.factor=3 in prod
- **Retention**:
  - users.v1: cleanup.policy=compact (retain latest user state)
  - orders.v1: retention.ms=604800000 (7 days)
- **DLQ**: single dlq.v1 or per-domain DLQ

## 3) Local infrastructure with Docker Compose (KRaft mode)

Create docker-compose.yml:

```yaml
version: "3.8"
services:
  kafka:
    image: bitnami/kafka:3.7
    environment:
      - KAFKA_ENABLE_KRAFT=yes
      - KAFKA_CFG_NODE_ID=1
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=1@kafka:9093
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      - KAFKA_CFG_AUTO_CREATE_TOPICS_ENABLE=false
    ports: ["9092:9092"]
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    environment:
      - KAFKA_CLUSTERS_0_NAME=local
      - KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS=kafka:9092
    ports: ["8080:8080"]
```

Create topics (one-time):

```bash
docker exec -it $(docker ps -qf name=kafka) \
kafka-topics.sh --bootstrap-server kafka:9092 --create --topic users.v1 --partitions 3 --replication-factor 1 --config cleanup.policy=compact

docker exec -it $(docker ps -qf name=kafka) \
kafka-topics.sh --bootstrap-server kafka:9092 --create --topic orders.v1 --partitions 6 --replication-factor 1

docker exec -it $(docker ps -qf name=kafka) \
kafka-topics.sh --bootstrap-server kafka:9092 --create --topic dlq.v1 --partitions 3 --replication-factor 1
```

## 4) Django project layout and shared utilities

Each microservice is its own repo/container. Create a **small shared package** (internal PyPI or Git submodule) for:

- Event envelope struct & validation
- Kafka producer/consumer wrappers
- Idempotency helpers (dedupe store)

Install client:
```bash
pip install confluent-kafka pydantic
```
events/base.py (shared):

```python
# shared/events/base.py
from pydantic import BaseModel, Field
from typing import Any, Dict
import json, time, uuid

class Event(BaseModel):
    schema: str
    event: str
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: int = Field(default_factory=lambda: int(time.time() * 1000))
    key: Dict[str, Any]
    data: Dict[str, Any]
    headers: Dict[str, str] = {}

    def to_bytes(self) -> bytes:
        return json.dumps(self.dict()).encode("utf-8")
```

kafka/client.py (shared):

```python
# shared/kafka/client.py
from confluent_kafka import Producer, Consumer, KafkaException
import json, logging, os

logger = logging.getLogger(__name__)

def new_producer():
    conf = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        "enable.idempotence": True,  # producer exactly-once on broker
        "retries": 5,
        "acks": "all",
        "compression.type": "snappy",
        "linger.ms": 5,
        "batch.num.messages": 10000,
    }
    return Producer(conf)

def new_consumer(group_id: str, topics: list[str]):
    conf = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,  # manual commit for at-least-once with correctness
        "max.poll.interval.ms": 300000,
    }
    c = Consumer(conf)
    c.subscribe(topics)
    return c

def delivery_report(err, msg):
    if err:
        logger.error(f"Delivery failed: {err}")
    else:
        logger.debug(f"Delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
```

## 5) Outbox pattern (reliable event publishing)

**Why**: avoid dual-write (DB + Kafka) inconsistencies.  
**How**: write domain change + outbox row in a single DB transaction; a relay publishes outbox rows to Kafka and marks them sent.

### Model (in the ****User Service****)

```python
# user_service/users/models.py
from django.db import models
from django.contrib.postgres.fields import JSONField

class User(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

class Outbox(models.Model):
    id = models.BigAutoField(primary_key=True)
    topic = models.CharField(max_length=100)
    key = JSONField()
    payload = JSONField()
    headers = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
```

### Write domain + outbox in one transaction

```python
# user_service/users/services.py
from django.db import transaction
from .models import User, Outbox

def create_user_and_enqueue(user_id, email, name):
    with transaction.atomic():
        user = User.objects.create(id=user_id, email=email, name=name)
        Outbox.objects.create(
            topic="users.v1",
            key={"user_id": str(user.id)},
            payload={
                "schema": "users.v1",
                "event": "user.created",
                "key": {"user_id": str(user.id)},
                "data": {"email": user.email, "name": user.name},
            },
            headers={"source": "user-service"},
        )
    return user
```

### Relay command (publisher)

Run as a separate process/container (e.g., python manage.py outbox_relay):

```python
# user_service/users/management/commands/outbox_relay.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import Outbox
from shared.kafka.client import new_producer, delivery_report
from confluent_kafka import Message
import json, time

class Command(BaseCommand):
    help = "Publish Outbox entries to Kafka"

    def handle(self, *args, **opts):
        producer = new_producer()
        while True:
            batch = list(Outbox.objects.filter(published_at__isnull=True).order_by("id")[:500])
            if not batch:
                time.sleep(0.5); continue
            for ob in batch:
                producer.produce(
                    topic=ob.topic,
                    key=json.dumps(ob.key).encode(),
                    value=json.dumps(ob.payload).encode(),
                    headers=list(ob.headers.items()),
                    on_delivery=delivery_report,
                )
            producer.flush()
            Outbox.objects.filter(id__in=[b.id for b in batch]).update(published_at=timezone.now())
```

## 6) Consuming with idempotency, retries, and DLQ

**At-least-once**: process, then commit. If processing fails, do a **bounded retry**; if still failing, publish to **DLQ** with diagnostic headers.

### Idempotency store

Create a small table to dedupe by event id.

```python
# notification_service/core/models.py
from django.db import models

class ProcessedMessage(models.Model):
    event_id = models.CharField(max_length=64, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)
```

### Consumer loop (Notification Service → orders.v1)

```python
# notification_service/notifications/management/commands/orders_consumer.py
from django.core.management.base import BaseCommand
from shared.kafka.client import new_consumer, new_producer
from django.db import transaction, IntegrityError
from core.models import ProcessedMessage
import json, logging, time

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Consume orders.v1 and send notifications"

    def handle(self, *args, **opts):
        consumer = new_consumer(group_id="notification-svc", topics=["orders.v1"])
        dlq_producer = new_producer()

        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None: 
                continue
            if msg.error():
                log.error(msg.error()); 
                continue

            try:
                payload = json.loads(msg.value())
                event_id = payload.get("id")
                with transaction.atomic():
                    # idempotency
                    ProcessedMessage.objects.create(event_id=event_id)

                    # domain logic (send email / push)
                    order = payload["data"]
                    self._send_email(order)

                consumer.commit(message=msg)  # commit after success

            except IntegrityError:
                # already processed -> just commit and move on
                consumer.commit(message=msg)

            except Exception as e:
                log.exception("Processing failed")
                # simple bounded retry using header counter (or use backoff + retry topic)
                retries = int(dict(msg.headers() or {}).get("x-retries", b"0"))
                if retries < 3:
                    headers = list(msg.headers() or []) + [("x-retries", str(retries + 1).encode())]
                    dlq_producer.produce("orders.v1", key=msg.key(), value=msg.value(), headers=headers)
                else:
                    # send to DLQ with reason
                    headers = list(msg.headers() or []) + [("x-error", str(e).encode())]
                    dlq_producer.produce("dlq.v1", key=msg.key(), value=msg.value(), headers=headers)
                dlq_producer.flush()
```

Alternative: **retry topics** (orders.retry.5s, orders.retry.1m) with a small scheduler/bridge to re-publish after delay, or use Kafka Streams/Kafka Connect + DeadLetterQueue.

## 7) Producing directly (Order Service)

When Order Service creates an order (if it **owns** orders), it should use the **outbox** too. If it reacts to user.created to enrich a read model, it consumes users.v1 and updates its local UserProjection.

```python
# order_service/orders/publishers.py
from shared.kafka.client import new_producer, delivery_report
from events.base import Event

producer = new_producer()

def publish_order_created(order):
    evt = Event(
        schema="orders.v1",
        event="order.created",
        key={"order_id": str(order.id)},
        data={
            "order_id": str(order.id),
            "user_id": str(order.user_id),
            "amount": str(order.amount),
            "status": order.status,
        },
        headers={"source": "order-service"},
    )
    producer.produce("orders.v1", key=str(order.id), value=evt.to_bytes(), on_delivery=delivery_report)
    producer.flush()
```

## 8) Configuration & settings (12-factor friendly)

Use env vars in each service:

```python
# settings.py
import os
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
SERVICE_NAME = os.getenv("SERVICE_NAME", "user-service")
```

Container processes:

- web: Django ASGI/WSGI
- outbox_relay: management command
- consumer: management command per topic group

Use **supervisord** or Docker Compose command: to run them.

## 9) Observability (logs, metrics, tracing)

- **Logs**: structured JSON logs (service, topic, partition, offset, event_id, duration, outcome).
- **Metrics**: export producer/consumer metrics (Prometheus JMX exporter for Kafka; app-level counters via Prometheus client).
- **Tracing**: add OpenTelemetry spans around produce/consume/DB.
- **Kafka UI**: inspect offsets, lag, DLQ payloads.

Python metrics example:

```python
# shared/metrics.py
from prometheus_client import Counter, Histogram
EVENTS_PROCESSED = Counter("events_processed_total", "Events processed", ["service","topic","status"])
EVENT_LATENCY = Histogram("event_latency_seconds", "Event processing latency", ["service","topic"])
```

## 10) Security & governance (prod)

- **ACLs**: per-service principals with least privilege
- **Auth**: SASL/SCRAM or mTLS
- **Encrypt**: TLS in transit, disk encryption
- **Schema management**: evolve with versioning (never break consumers); prefer Schema Registry in prod
- **PII**: keep PII minimal; tokenize/encrypt sensitive fields
- **Quotas**: limit rogue producers/consumers

## 11) CI/CD & migrations

- Run DB migrations before starting consumers to ensure idempotency tables/outbox exist.
- Smoke tests: produce test events to a \_test topic in staging; consumers must process & assert side effects.
- Contract tests: validate event JSON against schema on CI.

## 12) Local/dev testing recipes

- Produce a message quickly:

```bash
docker exec -it $(docker ps -qf name=kafka) \
kafka-console-producer.sh --bootstrap-server kafka:9092 --topic orders.v1
# paste a line of JSON and hit enter
```

- Consume from beginning:

```bash
docker exec -it $(docker ps -qf name=kafka) \
kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic orders.v1 --from-beginning
```

- Check consumer lag in Kafka UI (<http://localhost:8080>).

## 13) Common pitfalls & fixes

- **Duplicate processing**: always design consumers to be **idempotent** (dedupe table, natural keys, UPSERTs).
- **Lost events (dual write)**: use the **outbox pattern** or CDC (Debezium).
- **Hot partitions**: choose keys with good cardinality (avoid always-same key).
- **Unbounded DLQ**: set retention + alerts; build a reprocessor to fix & replay.
- **Commit too early**: commit **after** successful processing only.
- **Producer timeouts**: tune linger.ms, batch.num.messages, compression.
- **Schema drift**: version schemas (users.v1 → users.v2) and keep old fields optional for a while.

## 14) Minimal end-to-end demo flow (what to run)

1. docker compose up -d (Kafka + Kafka UI)
2. Start services:
    - User Service: web, python manage.py outbox_relay
    - Order Service: web (and maybe a consumer of users.v1 for projections)
    - Notification Service: python manage.py orders_consumer
3. Create a user via User Service API → outbox → Kafka users.v1
4. Create an order via Order Service API → outbox → Kafka orders.v1
5. Observe Notification Service printing “email sent” and committing offsets.

## 15) When to add advanced components

- **Schema Registry + Avro/Protobuf**: strict contracts at scale
- **Kafka Connect**: sink to warehouses (BigQuery/Snowflake), source from DBs (CDC)
- **Streams/Flink**: joins, aggregations, windowing
- **Multi-region**: MirrorMaker 2 or vendor-managed geo-replication

### Quick checklists

**Producer checklist**

- Outbox or transactional producer
- Key chosen for ordering
- Schema versioned
- Delivery callback logs errors
-  Retries + idempotence enabled

**Consumer checklist**

- Manual commit after success
- Idempotency (dedupe)
- Bounded retry or retry topics
- DLQ with reason headers
- Metrics: processed, errors, lag, latency
