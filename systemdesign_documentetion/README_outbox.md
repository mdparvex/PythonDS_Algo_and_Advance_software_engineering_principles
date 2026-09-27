# The Transactional Outbox Pattern

> A practical, production-oriented guide to the Transactional Outbox Pattern, with all examples in
> **Python + Django**, publishing to **Celery** via a **Redis** broker.
>
> **Core idea:** never let "update the database" and "notify the outside world" be two separate,
> independently-failing operations. Make the notification part of the same database transaction as
> the update, then deliver it out-of-band.

---

## Table of Contents

1. [The Problem This Pattern Solves](#1-the-problem-this-pattern-solves)
2. [Why the Obvious Fixes Don't Work](#2-why-the-obvious-fixes-dont-work)
3. [Core Idea](#3-core-idea)
4. [Architecture](#4-architecture)
5. [The Outbox Model](#5-the-outbox-model)
6. [Writing Events Transactionally](#6-writing-events-transactionally)
7. [The Relay / Publisher](#7-the-relay--publisher)
8. [Publisher Strategy: Polling vs. CDC](#8-publisher-strategy-polling-vs-cdc)
9. [Ordering Guarantees](#9-ordering-guarantees)
10. [Idempotency on the Consumer Side](#10-idempotency-on-the-consumer-side)
11. [At-Least-Once Delivery, Not Exactly-Once](#11-at-least-once-delivery-not-exactly-once)
12. [Retry and Dead-Lettering Failed Publishes](#12-retry-and-dead-lettering-failed-publishes)
13. [Outbox Table Growth and Cleanup](#13-outbox-table-growth-and-cleanup)
14. [Full Worked Example: Order Checkout](#14-full-worked-example-order-checkout)
15. [Testing the Outbox](#15-testing-the-outbox)
16. [Monitoring and Observability](#16-monitoring-and-observability)
17. [Outbox vs. Alternatives](#17-outbox-vs-alternatives)
18. [When *Not* to Use This Pattern](#18-when-not-to-use-this-pattern)
19. [Production Checklist](#19-production-checklist)
20. [Summary](#20-summary)

---

# 1. The Problem This Pattern Solves

A very common piece of application code looks like this:

```python
def create_order(data):
    order = Order.objects.create(**data)
    send_order_confirmation.delay(order.id)   # Celery task, published to Redis
    return order
```

This looks correct. It is not reliable, because it silently depends on **two independent systems
succeeding together**: the database write and the message broker write. They are not atomic with
respect to each other.

```text
                 Database                     Redis Broker
                     |                              |
   Order.objects.create()                           |
                     |  succeeds                     |
                     |------------------------------>|
                     |                     send_order_confirmation.delay()
                     |                                  |  FAILS (Redis down,
                     |                                  |   network blip, timeout)
                     v                                  v
              Order exists in DB          Task was NEVER enqueued
```

The result: the order is real, the customer was charged, but the confirmation email — or the
warehouse notification, or the analytics event, or whatever the task was supposed to do — simply
never happens. Nothing raised a loud, unambiguous exception during checkout, because from the
user's perspective the request "succeeded." The failure is silent, and it is discovered only when
someone complains that they never got their email.

This is the **dual-write problem**: writing to two systems (database + broker) that cannot be
committed together.

---

# 2. Why the Obvious Fixes Don't Work

## "Just retry the `.delay()` call"

```python
def create_order(data):
    order = Order.objects.create(**data)
    for attempt in range(3):
        try:
            send_order_confirmation.delay(order.id)
            break
        except Exception:
            continue
    return order
```

This narrows the failure window but does not close it. It blocks the HTTP request on Redis being
reachable, and if Redis is down for longer than your retry budget, you're back to a silent failure
— now with added latency for every request.

## "Just use `transaction.on_commit()`"

```python
from django.db import transaction

def create_order(data):
    with transaction.atomic():
        order = Order.objects.create(**data)
        transaction.on_commit(lambda: send_order_confirmation.delay(order.id))
    return order
```

This is a genuine improvement — it guarantees the task is only enqueued if the transaction actually
committed, which prevents publishing a task for an order that got rolled back. **Use it as your
default.** But it does not solve the dual-write problem: the `on_commit()` callback still calls
Redis directly, from inside the request/response cycle, after the point of no return. If Redis is
unreachable at that instant, the callback raises, and — because the database transaction has
*already committed* — the order now exists with no task ever created for it. There's also no
retry: `on_commit()` fires once.

## Why this matters more than it looks like

Both of the above assume the broker is "usually available," and handle the failure by hoping it
resolves quickly. For most events, that's a fine bet. For events that must not be lost —
`order.created`, `payment.captured`, `refund.issued` — you need a guarantee stronger than "usually
works," and that guarantee has to come from something as durable as the database itself.

---

# 3. Core Idea

The Transactional Outbox Pattern removes the direct dependency on the broker from the business
transaction entirely. Instead of calling Redis, you write a row describing "what should be
published" into a normal database table, **in the same atomic transaction as the business
change**.

```text
BEFORE (dual-write, not atomic):

    DB transaction  ---------------------------->  COMMIT
    Redis call      -----(separate, can fail)---->  ???


AFTER (single atomic write):

    DB transaction {
        business row
        outbox row
    } ---------------------------------------->  COMMIT   (all-or-nothing)

    A separate, independent process later reads the outbox row
    and publishes it to Redis — retrying on its own schedule.
```

Because the business row and the outbox row are written in the same database transaction, they are
atomic with respect to each other by construction — this is a guarantee the database already gives
you for free, not something you have to build. There is no code path where the order exists but
the outbox row doesn't, or vice versa.

The trade-off: publishing is no longer instantaneous. There's a small, bounded delay between
"transaction committed" and "task actually enqueued," while a separate publisher process picks up
the new row. In exchange, you get a durability guarantee that no amount of retry-wrapping the
direct call can provide: **once the transaction commits, the event will eventually be published,
regardless of what Redis is doing at that exact moment.**

---

# 4. Architecture

```text
                         Django view / service
                                  |
                                  v
                +----------------------------------+
                |         DB Transaction            |
                |                                    |
                |  1. Write business row(s)          |   e.g. Order.objects.create(...)
                |  2. Write OutboxEvent row           |   e.g. "order.created", {order_id: 42}
                |                                    |
                +-----------------+------------------+
                                  |
                                COMMIT      (atomic — both rows land, or neither does)
                                  |
                                  v
                       +---------------------+
                       |   Outbox Relay /    |     runs independently:
                       |     Publisher       |     Celery Beat task, cron job,
                       +----------+----------+     or a small standalone daemon
                                  |
                         reads unpublished rows
                         (ordered, in batches)
                                  |
                                  v
                       +---------------------+
                       |    Redis Broker     |
                       +----------+----------+
                                  |
                                  v
                       +---------------------+
                       |   Celery Worker     |  --->  side effects: email, webhook,
                       +---------------------+        analytics, warehouse sync, ...
                                  |
                                  v
                     mark OutboxEvent.published_at
```

**Three independent components**, each of which can fail without corrupting the others:

| Component | Responsibility | Failure mode if this breaks |
|---|---|---|
| Business transaction | Write business state + outbox row atomically | Whole transaction rolls back — nothing is half-done |
| Relay / Publisher | Read unpublished outbox rows, push to broker | Rows simply stay unpublished until it recovers — nothing is lost |
| Celery worker | Execute the actual side effect | Ordinary Celery retry/idempotency rules apply (see other sections) |

---

# 5. The Outbox Model

```python
import uuid
from django.db import models


class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # What happened, and to what — keep this generic and stable.
    event_type = models.CharField(max_length=255, db_index=True)   # e.g. "order.created"
    aggregate_type = models.CharField(max_length=100)              # e.g. "Order"
    aggregate_id = models.CharField(max_length=100)                # e.g. str(order.id)

    payload = models.JSONField()                                   # everything a consumer needs

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # Publish attempt bookkeeping (Section 12)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            # The publisher's core query is "unpublished, oldest first" — index for exactly that.
            models.Index(fields=["published_at", "created_at"], name="outbox_unpublished_idx"),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.event_type} ({self.aggregate_type}:{self.aggregate_id})"
```

Design notes:

- **`payload` should be self-contained.** Don't make the publisher or consumer re-query the
  database for details — by the time an event is published, the row it describes may have changed
  further. Put everything a consumer needs directly in the payload.
- **`event_type` should be a stable, versioned string**, not a Python class name or table name that
  might get refactored. Treat it like a public API — because for downstream consumers, it is one.
- **`aggregate_type` / `aggregate_id`** make it easy to query "everything that happened to order
  42," which is invaluable for debugging and for the dead-letter workflow in Section 12.

---

# 6. Writing Events Transactionally

This is the only step that happens inside the request/response cycle, and it never talks to Redis.

```python
from django.db import transaction


def create_order(data):
    with transaction.atomic():
        order = Order.objects.create(**data)

        OutboxEvent.objects.create(
            event_type="order.created",
            aggregate_type="Order",
            aggregate_id=str(order.id),
            payload={
                "order_id": order.id,
                "customer_email": order.customer_email,
                "total_amount": str(order.total_amount),
            },
        )

    return order
```

A few things are true of this code that were not true of the direct-`.delay()` version:

- If `Order.objects.create()` raises, the transaction rolls back and **no outbox row is written** —
  there is no dangling event for an order that doesn't exist.
- If writing the `OutboxEvent` itself somehow raised, the `Order` creation would roll back too —
  you can never have one without the other.
- **No network call happens here at all.** The only thing this code depends on being available is
  the database you were already writing to. Redis being down has zero effect on checkout.

You can write multiple outbox events in the same transaction for multi-step business operations
(e.g. `order.created` and `inventory.reserved`) — they'll be published independently but will
always exist together or not at all.

---

# 7. The Relay / Publisher

The publisher is a separate process. It has one job: move rows from "committed in the database" to
"delivered to the broker," and never lose a row in between.

```python
from celery import shared_task
from django.db import transaction
from django.utils import timezone

BATCH_SIZE = 100

# Map event_type -> the Celery task that should handle it.
EVENT_HANDLERS = {
    "order.created": lambda payload: send_order_confirmation.delay(payload["order_id"]),
    "order.created:analytics": lambda payload: track_order_created.delay(payload["order_id"]),
}


@shared_task
def publish_outbox_events():
    events = list(
        OutboxEvent.objects
        .filter(published_at__isnull=True)
        .order_by("created_at")[:BATCH_SIZE]
    )

    for event in events:
        handler = EVENT_HANDLERS.get(event.event_type)

        try:
            if handler is None:
                raise ValueError(f"No handler registered for {event.event_type}")

            handler(event.payload)

        except Exception as exc:
            event.attempts += 1
            event.last_error = str(exc)[:2000]
            event.save(update_fields=["attempts", "last_error"])
            continue  # leave published_at NULL — it will be retried next run

        event.published_at = timezone.now()
        event.save(update_fields=["published_at"])
```

Schedule it frequently with `django-celery-beat` so the gap between "committed" and "enqueued"
stays small:

```python
CELERY_BEAT_SCHEDULE = {
    "publish-outbox-events": {
        "task": "myapp.tasks.publish_outbox_events",
        "schedule": 2.0,  # every 2 seconds
    },
}
```

Note the failure handling: if `handler(event.payload)` raises — for instance, because Redis itself
is down — the row is **not** marked published, so the very next run of `publish_outbox_events`
picks it up again. The event cannot be silently dropped by a broker outage, because the publisher's
retry loop lives entirely in the database, independent of the broker's health.

---

# 8. Publisher Strategy: Polling vs. CDC

There are two common ways to implement the relay. Polling (shown above) is simpler to build and
sufficient for the vast majority of systems; Change Data Capture (CDC) is a heavier tool for a
narrower set of requirements.

| | Polling (Beat task / cron) | CDC (e.g. Debezium reading the DB replication log) |
|---|---|---|
| How it detects new rows | Periodic `SELECT ... WHERE published_at IS NULL` | Tails the database's write-ahead / binlog in real time |
| Latency | Bounded by poll interval (typically 1–5s) | Sub-second, event-driven |
| Infrastructure | None beyond what you already run (Celery Beat) | A CDC connector + Kafka (or similar) pipeline |
| Load on the database | Small, regular polling queries | None from polling — but requires binlog/WAL access |
| Operational complexity | Low | Higher — new infrastructure, new failure modes |
| Good fit | The vast majority of Django + Celery + Redis systems | High-throughput, low-latency, or already-Kafka-based systems |

**Default to polling.** Reach for CDC only once polling's latency or database load genuinely
becomes a measured problem — it is a significant infrastructure investment that most teams building
on Django + Celery + Redis do not need.

---

# 9. Ordering Guarantees

Polling with `order_by("created_at")` delivers events in the order they were **committed**, which
is usually — but not always — what you want.

```text
Two concurrent requests commit at nearly the same time:

Request A: creates OutboxEvent(created_at=10:00:00.001)
Request B: creates OutboxEvent(created_at=10:00:00.002)

If A's transaction commits AFTER B's (e.g. A was slower to commit even though it started first),
the publisher will see B's row before A's row — because "created_at" reflects when the row was
written, and the publisher only sees committed rows.
```

For most event types (independent orders, independent users) this doesn't matter — there's no
ordering relationship between them to begin with. It **does** matter when multiple events describe
the *same* aggregate:

```python
# If these three events must be applied in this order by a downstream consumer...
OutboxEvent(event_type="order.created", aggregate_id="42")
OutboxEvent(event_type="order.paid", aggregate_id="42")
OutboxEvent(event_type="order.shipped", aggregate_id="42")
```

...guarantee it explicitly rather than relying on timestamp ordering alone:

- Add a per-aggregate monotonic **sequence number** (`OutboxEvent.aggregate_seq`, incremented per
  `aggregate_id` inside the same transaction) and have consumers check it, rejecting or buffering
  out-of-order events.
- Or route all events for the same `aggregate_id` to the same Celery queue and rely on the fact
  that a single worker processes one queue's tasks serially — this only holds with `concurrency=1`
  on that queue, so it trades throughput for ordering.

If you don't need cross-aggregate ordering (most systems don't), skip this complexity entirely.

---

# 10. Idempotency on the Consumer Side

The outbox pattern guarantees **at-least-once** publication, not exactly-once (Section 11). If the
publisher crashes after calling `handler(event.payload)` but before saving `published_at`, the
event will be published again on the next run.

```text
Publisher calls handler() -> Celery task enqueued -> Redis has it
        |
        X  publisher crashes before event.save(published_at=...)
        |
        v
Next publisher run sees published_at IS NULL -> re-publishes -> DUPLICATE task
```

This is not a flaw in the pattern — it is the same at-least-once guarantee every reliable messaging
system provides, and it is a much easier problem than *losing* events. The fix is the same one used
throughout Celery task design: make the consuming task idempotent.

```python
@shared_task
def send_order_confirmation(order_id):
    order = Order.objects.get(pk=order_id)

    if order.confirmation_sent_at is not None:
        return "already-sent"  # duplicate delivery is a safe no-op

    email_service.send(order.customer_email, template="order_confirmation", order=order)

    order.confirmation_sent_at = timezone.now()
    order.save(update_fields=["confirmation_sent_at"])
```

For events with side effects on external systems (payment providers, webhooks to partners), pass
the `OutboxEvent.id` through as an idempotency key so the receiving system can also deduplicate:

```python
payment_gateway.charge(
    amount=payload["total_amount"],
    idempotency_key=str(event.id),   # stable across redeliveries of the same event
)
```

---

# 11. At-Least-Once Delivery, Not Exactly-Once

It's worth being explicit about the guarantee this pattern actually provides, since it's easy to
overstate:

```text
Transactional Outbox guarantees:

  "If the database transaction commits, the event WILL eventually be published
   at least once."

It does NOT guarantee:

  "The event will be published exactly once."
```

Exactly-once delivery across two independent systems (a database and a message broker) is not
achievable without a distributed transaction coordinator, which neither Django nor Celery nor Redis
provide, and which most teams should not attempt to build. The outbox pattern deliberately trades
"exactly-once" for "durable at-least-once + consumer-side idempotency" — a combination that is far
easier to build correctly and reason about.

---

# 12. Retry and Dead-Lettering Failed Publishes

`attempts` and `last_error` on the model (Section 5) exist so a row that keeps failing to publish
doesn't retry silently forever, unnoticed, next to healthy events.

```python
DEAD_LETTER_THRESHOLD = 10


@shared_task
def publish_outbox_events():
    events = list(
        OutboxEvent.objects
        .filter(published_at__isnull=True, attempts__lt=DEAD_LETTER_THRESHOLD)
        .order_by("created_at")[:BATCH_SIZE]
    )
    # ... same publish loop as Section 7 ...


@shared_task
def alert_on_stuck_outbox_events():
    stuck = OutboxEvent.objects.filter(
        published_at__isnull=True,
        attempts__gte=DEAD_LETTER_THRESHOLD,
    )
    if stuck.exists():
        notify_ops_channel(
            f"{stuck.count()} outbox events have failed to publish "
            f"{DEAD_LETTER_THRESHOLD}+ times and need manual review."
        )
```

This keeps a single poison event (say, one with a malformed payload that always raises inside its
handler) from being invisible, while still letting it retry automatically for genuinely transient
broker outages. Schedule `alert_on_stuck_outbox_events` on its own, less-frequent Beat schedule
(e.g. every 15 minutes) — it should page a human, not run every few seconds like the publisher
itself.

Provide a way to manually replay a dead-lettered event once the underlying issue (bad payload,
missing handler, external API outage) is fixed:

```python
def replay_outbox_event(event_id):
    OutboxEvent.objects.filter(pk=event_id).update(attempts=0, last_error="")
```

---

# 13. Outbox Table Growth and Cleanup

Published events accumulate. Keep the table small enough that the publisher's core query — "the
oldest unpublished rows" — stays fast, by periodically archiving or deleting old, successfully
published rows.

```python
from datetime import timedelta
from django.utils import timezone


@shared_task
def cleanup_published_outbox_events():
    cutoff = timezone.now() - timedelta(days=7)
    OutboxEvent.objects.filter(
        published_at__isnull=False,
        published_at__lt=cutoff,
    ).delete()
```

Run this daily, well below traffic peaks. If you need an audit trail longer than your operational
retention window, archive rows to cold storage (a data warehouse, an S3 export) before deleting
them from the primary table, rather than keeping them there indefinitely — the `outbox_unpublished_idx`
index only needs to stay small relative to *unpublished* rows, so a growing table of old published
rows is pure overhead on every publisher poll.

---

# 14. Full Worked Example: Order Checkout

Putting every piece together — model, transactional write, relay, idempotent consumer:

```python
# models.py
import uuid
from django.db import models


class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=255, db_index=True)
    aggregate_type = models.CharField(max_length=100)
    aggregate_id = models.CharField(max_length=100)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["published_at", "created_at"], name="outbox_unpublished_idx")]
        ordering = ["created_at"]


class Order(models.Model):
    customer_email = models.EmailField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
```

```python
# services.py — the only code that runs inside the request/response cycle
from django.db import transaction
from .models import Order, OutboxEvent


def checkout(data):
    with transaction.atomic():
        order = Order.objects.create(
            customer_email=data["customer_email"],
            total_amount=data["total_amount"],
        )

        OutboxEvent.objects.create(
            event_type="order.created",
            aggregate_type="Order",
            aggregate_id=str(order.id),
            payload={
                "order_id": order.id,
                "customer_email": order.customer_email,
                "total_amount": str(order.total_amount),
            },
        )

    return order
```

```python
# tasks.py — everything below runs OUTSIDE the request/response cycle
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from .models import Order, OutboxEvent

BATCH_SIZE = 100
DEAD_LETTER_THRESHOLD = 10

EVENT_HANDLERS = {
    "order.created": lambda payload: send_order_confirmation.delay(payload["order_id"]),
}


@shared_task
def publish_outbox_events():
    events = list(
        OutboxEvent.objects
        .filter(published_at__isnull=True, attempts__lt=DEAD_LETTER_THRESHOLD)
        .order_by("created_at")[:BATCH_SIZE]
    )

    for event in events:
        try:
            handler = EVENT_HANDLERS[event.event_type]
            handler(event.payload)
        except Exception as exc:
            event.attempts += 1
            event.last_error = str(exc)[:2000]
            event.save(update_fields=["attempts", "last_error"])
            continue

        event.published_at = timezone.now()
        event.save(update_fields=["published_at"])


@shared_task
def send_order_confirmation(order_id):
    order = Order.objects.get(pk=order_id)

    if order.confirmation_sent_at is not None:
        return "already-sent"

    send_mail(
        subject="Your order is confirmed",
        message=f"Thanks for your order #{order.id}!",
        from_email="orders@example.com",
        recipient_list=[order.customer_email],
    )

    order.confirmation_sent_at = timezone.now()
    order.save(update_fields=["confirmation_sent_at"])
```

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    "publish-outbox-events": {
        "task": "myapp.tasks.publish_outbox_events",
        "schedule": 2.0,
    },
    "cleanup-published-outbox-events": {
        "task": "myapp.tasks.cleanup_published_outbox_events",
        "schedule": 86400.0,  # daily
    },
}
```

---

# 15. Testing the Outbox

Test the two halves independently — they should never need to be tested together, since that's the
whole point of decoupling them.

## Testing the write path (no Celery, no Redis involved)

```python
from django.test import TestCase
from .models import Order, OutboxEvent
from .services import checkout


class CheckoutOutboxTests(TestCase):
    def test_checkout_writes_outbox_event_atomically(self):
        order = checkout({"customer_email": "a@example.com", "total_amount": "19.99"})

        event = OutboxEvent.objects.get(aggregate_id=str(order.id))
        self.assertEqual(event.event_type, "order.created")
        self.assertIsNone(event.published_at)
        self.assertEqual(event.payload["customer_email"], "a@example.com")

    def test_failed_order_creation_leaves_no_outbox_event(self):
        with self.assertRaises(Exception):
            checkout({"customer_email": "not-an-email", "total_amount": "bad-value"})

        self.assertEqual(OutboxEvent.objects.count(), 0)
```

## Testing the publisher (no real Redis needed — mock the handler)

```python
from unittest.mock import patch
from django.test import TestCase
from .models import OutboxEvent
from .tasks import publish_outbox_events


class OutboxPublisherTests(TestCase):
    def test_publishes_pending_events_and_marks_them(self):
        event = OutboxEvent.objects.create(
            event_type="order.created",
            aggregate_type="Order",
            aggregate_id="1",
            payload={"order_id": 1},
        )

        with patch("myapp.tasks.send_order_confirmation.delay") as mock_delay:
            publish_outbox_events()

        mock_delay.assert_called_once_with(1)
        event.refresh_from_db()
        self.assertIsNotNone(event.published_at)

    def test_failed_publish_leaves_event_unpublished_and_records_error(self):
        event = OutboxEvent.objects.create(
            event_type="order.created",
            aggregate_type="Order",
            aggregate_id="1",
            payload={"order_id": 1},
        )

        with patch("myapp.tasks.send_order_confirmation.delay", side_effect=ConnectionError("down")):
            publish_outbox_events()

        event.refresh_from_db()
        self.assertIsNone(event.published_at)
        self.assertEqual(event.attempts, 1)
        self.assertIn("down", event.last_error)
```

## Testing consumer idempotency

```python
class SendConfirmationIdempotencyTests(TestCase):
    def test_running_twice_sends_only_one_email(self):
        order = Order.objects.create(customer_email="a@example.com", total_amount="9.99")

        with patch("myapp.tasks.send_mail") as mock_send:
            send_order_confirmation(order.id)
            send_order_confirmation(order.id)  # simulates a duplicate delivery

        mock_send.assert_called_once()
```

---

# 16. Monitoring and Observability

Track these as first-class metrics, not just "check the table when something seems wrong":

| Metric | Why it matters | How to compute it |
|---|---|---|
| **Outbox lag** | How far behind is publishing? | `now() - oldest unpublished created_at` |
| **Unpublished backlog size** | Is the publisher keeping up? | `count(published_at IS NULL)` |
| **Dead-lettered count** | Events stuck past the retry threshold | `count(attempts >= DEAD_LETTER_THRESHOLD)` |
| **Publish success rate** | Is a downstream dependency degraded? | successful vs. failed publish attempts per run |
| **Table size / row count** | Is cleanup running? | `count(*)` on the outbox table over time |

```python
@shared_task
def report_outbox_health():
    oldest_unpublished = (
        OutboxEvent.objects.filter(published_at__isnull=True)
        .order_by("created_at")
        .first()
    )
    lag_seconds = (
        (timezone.now() - oldest_unpublished.created_at).total_seconds()
        if oldest_unpublished else 0
    )

    metrics.gauge("outbox.lag_seconds", lag_seconds)
    metrics.gauge("outbox.backlog_size", OutboxEvent.objects.filter(published_at__isnull=True).count())
    metrics.gauge("outbox.dead_letter_count", OutboxEvent.objects.filter(attempts__gte=DEAD_LETTER_THRESHOLD).count())
```

Alert on **lag**, not just backlog size — a backlog of 10,000 rows that are all one second old is
healthy (high throughput, keeping up); a backlog of 5 rows that are 20 minutes old means the
publisher itself has stopped running.

---

# 17. Outbox vs. Alternatives

| Approach | Atomicity with DB write | Added infrastructure | Complexity | Best for |
|---|---|---|---|---|
| Direct `.delay()` call | None | None | Lowest | Non-critical, best-effort events (a log line, a cache bust) |
| `transaction.on_commit()` | Enqueue only after commit, but call can still fail with no retry | None | Low | Most events — good default |
| **Transactional Outbox** | Full — event write is part of the DB transaction | One table + a relay process | Moderate | Events that must never be silently lost (payments, orders, anything downstream systems depend on) |
| CDC (Debezium + Kafka) | Full, at the storage-engine level | A CDC pipeline + Kafka | High | High-throughput, low-latency, or already-Kafka-based platforms |
| Two-phase commit (XA) | Full, in theory | A distributed transaction coordinator | Very high, rarely justified | Rarely — most brokers and ORMs don't support it well in practice |

---

# 18. When *Not* to Use This Pattern

The outbox pattern is not free, and reaching for it everywhere adds an extra table, an extra
process, and a small publish delay to events that didn't need any of it. Skip it when:

- **The event is best-effort by nature** — a cache invalidation, a "user viewed page" analytics
  ping, a Slack notification for internal visibility. Losing one occasionally is a non-issue; use
  `transaction.on_commit()` or even a direct call.
- **A small publish delay is unacceptable** and the event doesn't carry the same "must not be
  lost" requirement — the outbox trades a little latency for durability, so if you need
  sub-100ms delivery and can tolerate occasional loss, this pattern is working against you.
- **You already have a durable event log** — if you're running Kafka with `exactly_once` semantics
  end-to-end and your database already participates in that pipeline via CDC, a hand-rolled polling
  outbox on top is redundant.
- **The system's write volume is low enough that dual-write failures are rare AND cheap to fix
  manually** — for a low-traffic internal tool, the operational cost of building and maintaining an
  outbox relay may exceed the cost of occasionally re-sending a missed notification by hand.

---

# 19. Production Checklist

## Schema & writes

- [ ] `OutboxEvent` is written inside the same `transaction.atomic()` block as the business change.
- [ ] No code path calls Celery/Redis directly for events that go through the outbox.
- [ ] `payload` is self-contained — consumers don't need to re-query the source row.
- [ ] `event_type` is a stable, documented, versioned string.

## Publisher

- [ ] Publisher runs on a tight schedule (seconds, not minutes) via Celery Beat or equivalent.
- [ ] A failed publish attempt leaves `published_at` unset and increments `attempts`.
- [ ] A dead-letter threshold exists, with alerting separate from the publish loop itself.
- [ ] Manual replay path exists for dead-lettered events.

## Consumers

- [ ] Every task triggered by an outbox event is idempotent (Section 10).
- [ ] External side effects pass an idempotency key derived from `OutboxEvent.id`.

## Operations

- [ ] Old, published rows are cleaned up or archived on a schedule (Section 13).
- [ ] Outbox lag, backlog size, and dead-letter count are monitored and alerted on.
- [ ] The `outbox_unpublished_idx` index (or equivalent) exists and is confirmed used by the
      publisher's query (check with `EXPLAIN`).

---

# 20. Summary

The dual-write problem — a database write and a broker write that can succeed or fail
independently — is the root cause of a whole class of "it worked, but nothing happened" bugs. The
Transactional Outbox Pattern removes the problem at its source by never letting the two become
independent in the first place: the event is written in the same transaction as the business
change it describes, and a separate, independently-retrying process takes over from there.

```text
Business transaction  ---writes--->  Business row + Outbox row   (atomic, one commit)
                                              |
                                    Relay (independent process)
                                              |
                                              v
                                    Broker  --->  Worker  --->  Side effect
```

The guarantee this buys you is specific and worth remembering exactly as it's stated:

> **If the database transaction commits, the event will eventually be published — at least once —
> regardless of the broker's availability at that instant.**

Not exactly-once. Not zero-latency. Durable, at-least-once delivery, paired with idempotent
consumers — the same combination that underlies every reliable distributed system, applied to the
one gap that a plain `Celery.delay()` call leaves open.
