# Celery + Redis with Django — Advanced Technical Documentation

> A practical, production-oriented guide to asynchronous task processing with **Celery**, **Redis**, and **Django**.  
> All application examples use **Python + Django**.

---

## Table of Contents

1. [What Celery and Redis Solve](#1-what-celery-and-redis-solve)
2. [Core Architecture](#2-core-architecture)
3. [How Celery Works Internally](#3-how-celery-works-internally)
4. [Redis as a Celery Broker](#4-redis-as-a-celery-broker)
5. [Django Project Setup](#5-django-project-setup)
6. [First Task](#6-first-task)
7. [Task Lifecycle](#7-task-lifecycle)
8. [Calling Tasks Correctly](#8-calling-tasks-correctly)
9. [Retries and Failure Handling](#9-retries-and-failure-handling)
10. [Acknowledgements and Message Loss](#10-acknowledgements-and-message-loss)
11. [Idempotency and Duplicate Execution](#11-idempotency-and-duplicate-execution)
12. [Task States and Result Backend](#12-task-states-and-result-backend)
13. [Periodic Tasks and Celery Beat](#13-periodic-tasks-and-celery-beat)
14. [django-celery-beat](#14-django-celery-beat)
15. [Scheduling Time Zones](#15-scheduling-time-zones)
16. [Concurrency and Worker Pools](#16-concurrency-and-worker-pools)
17. [Prefetching and Fair Task Distribution](#17-prefetching-and-fair-task-distribution)
18. [Routing and Multiple Queues](#18-routing-and-multiple-queues)
19. [Priority](#19-priority)
20. [Task Expiration and Time Limits](#20-task-expiration-and-time-limits)
21. [Database Transactions and Celery](#21-database-transactions-and-celery)
22. [Django ORM and Connection Management](#22-django-orm-and-connection-management)
23. [Serialization](#23-serialization)
24. [Redis Failure Modes](#24-redis-failure-modes)
25. [Celery Failure Modes](#25-celery-failure-modes)
26. [Common Production Bugs](#26-common-production-bugs)
27. [Monitoring and Observability](#27-monitoring-and-observability)
28. [Graceful Shutdown and Deployments](#28-graceful-shutdown-and-deployments)
29. [Security](#29-security)
30. [Performance Tuning](#30-performance-tuning)
31. [Testing](#31-testing)
32. [Production Configuration](#32-production-configuration)
33. [Reliable Design Patterns](#33-reliable-design-patterns)
34. [End-to-End Example](#34-end-to-end-example)
35. [Troubleshooting Checklist](#35-troubleshooting-checklist)
36. [Advanced Interview Questions](#36-advanced-interview-questions)
37. [Quick Reference](#37-quick-reference)

---

# 1. What Celery and Redis Solve

A normal Django request is synchronous:

```text
Browser
   |
   v
Django
   |
   v
Do expensive work
   |
   v
HTTP response
```

If the expensive work takes 20 seconds, the client waits approximately 20 seconds.

Examples of work that should often be asynchronous:

- Sending email
- Sending push notifications
- Generating reports
- Processing uploaded files
- Image/video processing
- Calling slow third-party APIs
- Bulk database operations
- Scheduled jobs
- Repeated background processing

With Celery:

```text
Client
  |
  v
Django
  |
  | enqueue task
  v
Redis Broker
  |
  | deliver message
  v
Celery Worker
  |
  v
Python Task
```

The Django request can return immediately while a worker performs the expensive operation.

## Important distinction

**Celery is not Redis.**

- **Celery** = distributed task-processing framework.
- **Redis** = in-memory data store that can act as a message broker and/or result backend.

Celery can work with several brokers and result backends. Redis is only one possible infrastructure component.

---

# 2. Core Architecture

A production Celery system commonly contains these components:

```text
                         +----------------+
                         |     Django     |
                         | Web/API Server |
                         +-------+--------+
                                 |
                          publish task
                                 |
                                 v
                    +-------------------------+
                    |      Redis Broker       |
                    |   Task message queues   |
                    +------------+------------+
                                 |
                         consume messages
                                 |
               +-----------------+-----------------+
               |                                   |
               v                                   v
      +------------------+                +------------------+
      | Celery Worker 1  |                | Celery Worker 2  |
      +------------------+                +------------------+
               |                                   |
               +-----------------+-----------------+
                                 |
                            execute tasks
                                 |
                                 v
                         +---------------+
                         |   Database    |
                         | External APIs |
                         +---------------+

Optional:

Celery Worker ----> Redis Result Backend
Celery Beat ------> Redis Broker
Monitoring -------> Worker events / metrics
```

## Components

### Django application

Creates task messages:

```python
send_email_task.delay(user.id)
```

Django does not execute the task itself.

### Redis broker

Stores/delivers task messages until workers consume them.

### Celery worker

A long-running process that:

1. Connects to the broker.
2. Receives task messages.
3. Imports the task code.
4. Executes the task.
5. Acknowledges the message according to configuration.
6. Optionally stores task state/result.

### Celery Beat

A scheduler.

It does **not** execute tasks.

Instead:

```text
Celery Beat
    |
    | "run task X now"
    v
Redis
    |
    v
Celery Worker
    |
    v
Task execution
```

### Result backend

Optional infrastructure used for task state/results.

For example:

```python
result = my_task.delay(10)
result.status
result.get()
```

---

# 3. How Celery Works Internally

Suppose Django executes:

```python
from .tasks import send_email

send_email.delay(123)
```

Conceptually:

```text
1. Django imports task
2. Celery creates a task message
3. Message receives:
   - task name
   - task ID
   - arguments
   - keyword arguments
   - metadata
4. Message is published to broker
5. Redis stores/routes the message
6. Worker consumes message
7. Worker resolves task name
8. Worker executes Python function
9. Worker acknowledges message
10. Result/state may be written to result backend
```

A task message is conceptually similar to:

```python
{
    "task": "orders.tasks.send_email",
    "id": "uuid",
    "args": [123],
    "kwargs": {},
    "retries": 0,
}
```

The exact wire representation depends on Celery/protocol configuration.

## Producer vs Consumer

Django is generally the **producer**.

Celery worker is the **consumer**.

Redis sits between them.

```text
Producer                    Broker                 Consumer

Django   --->   task   ---> Redis   ---> task ---> Worker
```

This decoupling is one of the main benefits of Celery.

---

# 4. Redis as a Celery Broker

Redis is commonly used because it is:

- Fast
- Simple to operate
- Easy to run locally
- Supported by Celery
- Useful for multiple application workloads

A typical URL:

```python
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
```

Format:

```text
redis://[:password]@host:port/db
```

Example:

```python
CELERY_BROKER_URL = "redis://:secret@redis:6379/0"
```

## Separate Redis databases

You may use different Redis logical databases:

```text
Redis DB 0 -> Celery broker
Redis DB 1 -> Celery results
Redis DB 2 -> Django cache
```

Example:

```python
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
```

This is a logical separation, not the same thing as completely separate Redis servers.

For strong isolation, use separate Redis instances/clusters.

---

# 5. Django Project Setup

## Install packages

```bash
pip install celery redis django-celery-beat
```

If you use a requirements file:

```text
Django
celery
redis
django-celery-beat
```

---

## Recommended project structure

```text
project/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
│
└── orders/
    ├── __init__.py
    ├── models.py
    ├── tasks.py
    ├── views.py
    └── ...
```

---

## `config/celery.py`

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

app.autodiscover_tasks()
```

---

## `config/__init__.py`

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

This makes the Celery application available when Django imports the project.

---

## `settings.py`

```python
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"

CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "Asia/Dhaka"
CELERY_ENABLE_UTC = True
```

Recommended for most Django applications:

```python
USE_TZ = True
TIME_ZONE = "Asia/Dhaka"
```

---

# 6. First Task

Create:

```text
orders/tasks.py
```

```python
from celery import shared_task


@shared_task
def add_numbers(a, b):
    return a + b
```

Call it:

```python
from orders.tasks import add_numbers

result = add_numbers.delay(10, 20)
```

`delay()` is shorthand for:

```python
add_numbers.apply_async(args=[10, 20])
```

The HTTP request does not execute:

```python
10 + 20
```

directly.

It publishes a message for a worker.

---

## Start Redis

Local Redis example:

```bash
redis-server
```

Check:

```bash
redis-cli ping
```

Expected:

```text
PONG
```

---

## Start worker

From the Django project root:

```bash
celery -A config worker -l INFO
```

Windows development:

```bash
celery -A config worker -l INFO --pool=solo
```

For Linux production, the prefork pool is generally a better default for CPU/process isolation.

---

# 7. Task Lifecycle

A useful mental model is:

```text
PENDING
   |
   v
QUEUED
   |
   v
RECEIVED
   |
   v
STARTED
   |
   +----------+
   |          |
   v          v
SUCCESS     FAILURE
              |
              v
           RETRY
              |
              v
           RECEIVED
```

The exact visible state depends on configuration and whether task events/result tracking are enabled.

Common Celery states:

- `PENDING`
- `RECEIVED`
- `STARTED`
- `RETRY`
- `SUCCESS`
- `FAILURE`
- `REVOKED`

Do not confuse:

```text
task state
```

with:

```text
business/database state
```

For example:

```text
Celery task SUCCESS
```

does not necessarily mean:

```text
Order successfully delivered
```

It only means the task function completed without raising an exception.

---

# 8. Calling Tasks Correctly

## `delay()`

Simple:

```python
send_email.delay(user_id)
```

Equivalent to:

```python
send_email.apply_async(args=[user_id])
```

---

## `apply_async()`

Use when you need options:

```python
send_email.apply_async(
    args=[user_id],
    countdown=60,
)
```

Execute after approximately 60 seconds.

---

## ETA

```python
from datetime import timedelta

send_email.apply_async(
    args=[user_id],
    countdown=timedelta(minutes=5).total_seconds(),
)
```

Or with an explicit ETA:

```python
from django.utils import timezone

send_email.apply_async(
    args=[user_id],
    eta=timezone.now() + timedelta(minutes=5),
)
```

### Important

ETA/countdown tasks can remain in worker memory depending on broker/pool behavior. They are not a replacement for a durable scheduling system for very large volumes of far-future jobs.

For recurring schedules, prefer Celery Beat.

---

## Do not pass Django model objects

Avoid:

```python
send_email.delay(user)
```

Prefer:

```python
send_email.delay(user.pk)
```

Then:

```python
@shared_task
def send_email(user_id):
    user = User.objects.get(pk=user_id)
```

Reasons:

- Serialization
- Stale data
- Large messages
- Database state may change before task execution
- ORM objects should not cross process boundaries

---

# 9. Retries and Failure Handling

A robust task should distinguish between:

- Temporary failure
- Permanent failure

Example temporary failure:

```text
Third-party API timeout
```

Permanent failure:

```text
User does not exist
```

---

## Automatic retries

```python
from celery import shared_task


@shared_task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def call_external_api():
    ...
```

---

## Explicit retry

```python
from celery import shared_task


@shared_task(bind=True, max_retries=5)
def process_order(self, order_id):
    try:
        ...
    except TimeoutError as exc:
        raise self.retry(exc=exc, countdown=60)
```

---

## Exponential backoff

Instead of:

```text
retry after 10 seconds
retry after 10 seconds
retry after 10 seconds
```

use:

```text
10s
20s
40s
80s
...
```

Celery supports:

```python
retry_backoff=True
```

and:

```python
retry_backoff=10
```

---

## Retry with jitter

Without jitter, thousands of tasks can retry simultaneously.

Use:

```python
retry_jitter=True
```

This helps avoid a retry storm.

---

## Never retry everything blindly

Bad:

```python
@shared_task(autoretry_for=(Exception,))
def task():
    ...
```

This can repeatedly retry programming errors.

Better:

```python
@shared_task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    max_retries=5,
)
def task():
    ...
```

---

# 10. Acknowledgements and Message Loss

This is one of the most important Celery concepts.

A worker receives a task.

There are two broad moments when the message can be acknowledged:

```text
A. Before execution
B. After execution
```

The important setting is:

```python
CELERY_TASK_ACKS_LATE = True
```

With late acknowledgement, the worker acknowledges after task execution.

---

## Why late acknowledgement matters

Suppose:

```text
Redis -> Worker
```

Worker receives:

```text
process_order(100)
```

Then worker crashes before finishing.

With early acknowledgement:

```text
Redis thinks:
"message completed"
```

Potentially:

```text
task lost
```

With late acknowledgement:

```text
Worker crashes
       |
       v
message can be redelivered
```

This is generally safer for important tasks.

---

## But late acknowledgement creates duplicates

Suppose:

```text
1. Worker receives task
2. Task completes successfully
3. External side effect happens
4. Worker crashes before ACK
5. Broker redelivers task
6. Task executes again
```

Now the task can execute twice.

Therefore:

> **At-least-once delivery requires idempotent task design.**

This is one of the most important production principles for Celery.

---

## Worker lost behavior

Depending on your Celery version/configuration, settings related to worker loss/requeue behavior can include:

```python
CELERY_TASK_REJECT_ON_WORKER_LOST = True
```

Use this carefully and understand the broker/worker semantics before enabling it globally.

---

# 11. Idempotency and Duplicate Execution

An idempotent task produces the same intended business outcome even if it runs more than once.

Bad example:

```python
@shared_task
def charge_customer(order_id):
    payment_gateway.charge(order_id)
```

If the task executes twice, the customer might be charged twice.

---

## Better: idempotency key

```python
@shared_task
def charge_customer(order_id):
    order = Order.objects.get(pk=order_id)

    if order.payment_status == "paid":
        return "already-paid"

    payment_gateway.charge(
        order_id=order.id,
        idempotency_key=f"order-{order.id}",
    )

    order.payment_status = "paid"
    order.save(update_fields=["payment_status"])

    return "paid"
```

The external payment system should also support idempotency.

---

## Database uniqueness

Another powerful pattern:

```python
class TaskExecution(models.Model):
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
```

Then:

```python
from django.db import IntegrityError


@shared_task
def process_once(order_id):
    key = f"order:{order_id}:payment"

    try:
        TaskExecution.objects.create(
            idempotency_key=key,
        )
    except IntegrityError:
        return "already-processed"

    # Business operation
    ...
```

The database unique constraint becomes the final guard.

---

# 12. Task States and Result Backend

Configure:

```python
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
```

Then:

```python
@shared_task
def add(a, b):
    return a + b
```

Call:

```python
result = add.delay(2, 3)
```

Check:

```python
result.id
result.status
result.ready()
result.successful()
```

Get result:

```python
value = result.get(timeout=10)
```

---

## Do not block Django requests unnecessarily

Avoid:

```python
result = add.delay(2, 3)

value = result.get()
```

inside a normal HTTP request unless there is a strong reason.

You have effectively turned asynchronous work back into synchronous work.

Instead:

```text
POST request
   |
   v
enqueue task
   |
   v
return 202 Accepted + task ID
```

Then expose a status endpoint if needed.

---

## Example status API

```python
from celery.result import AsyncResult
from rest_framework.response import Response
from rest_framework.views import APIView


class TaskStatusAPIView(APIView):
    def get(self, request, task_id):
        result = AsyncResult(task_id)

        return Response({
            "task_id": task_id,
            "status": result.status,
        })
```

---

# 13. Periodic Tasks and Celery Beat

Celery Beat is the scheduler.

Example:

```text
Beat
 |
 | every 5 minutes
 v
Redis
 |
 v
Worker
 |
 v
cleanup_task()
```

---

## Static schedule

In `settings.py`:

```python
from celery.schedules import crontab


CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-orders": {
        "task": "orders.tasks.cleanup_expired_orders",
        "schedule": crontab(minute="*/5"),
    },
}
```

Task:

```python
@shared_task
def cleanup_expired_orders():
    ...
```

Run:

```bash
celery -A config beat -l INFO
```

Worker separately:

```bash
celery -A config worker -l INFO
```

---

## Never confuse Beat with Worker

Beat:

```text
"When should the task be sent?"
```

Worker:

```text
"Execute the task."
```

You need both for periodic tasks.

---

# 14. django-celery-beat

`django-celery-beat` stores schedules in Django's database.

Install:

```bash
pip install django-celery-beat
```

Add:

```python
INSTALLED_APPS = [
    ...
    "django_celery_beat",
]
```

Migrate:

```bash
python manage.py migrate
```

Run:

```bash
celery -A config beat \
    -l INFO \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

This allows schedules to be managed dynamically through Django Admin.

---

## Interval schedule example

```python
from django_celery_beat.models import (
    IntervalSchedule,
    PeriodicTask,
)

schedule, _ = IntervalSchedule.objects.get_or_create(
    every=120,
    period=IntervalSchedule.SECONDS,
)

PeriodicTask.objects.update_or_create(
    name="dispatch scheduled notifications",
    defaults={
        "interval": schedule,
        "task": "notifications.tasks.dispatch_scheduled_notifications",
        "enabled": True,
    },
)
```

---

## Critical requirement

A periodic task requires:

```text
Redis
Celery Worker
Celery Beat
```

If Beat is down:

```text
No new periodic messages are published.
```

If Worker is down:

```text
Beat may publish tasks,
but nobody executes them.
```

---

# 15. Scheduling Time Zones

Django:

```python
USE_TZ = True
TIME_ZONE = "Asia/Dhaka"
```

Celery:

```python
CELERY_TIMEZONE = "Asia/Dhaka"
CELERY_ENABLE_UTC = True
```

Use Django's timezone utilities:

```python
from django.utils import timezone

now = timezone.now()
```

Do not manually assume:

```python
datetime.now()
```

is in your application timezone.

---

## Date range filtering

Correct pattern:

```python
from datetime import datetime, time, timedelta

from django.utils import timezone


def day_range(date):
    tz = timezone.get_current_timezone()

    start = timezone.make_aware(
        datetime.combine(date, time.min),
        timezone=tz,
    )

    end = start + timedelta(days=1)

    return start, end
```

Then:

```python
Order.objects.filter(
    created_at__gte=start,
    created_at__lt=end,
)
```

Prefer:

```text
[start, end)
```

instead of:

```text
[start, 23:59:59.999999]
```

because half-open intervals avoid precision problems.

---

# 16. Concurrency and Worker Pools

A Celery worker can execute multiple tasks concurrently.

For example:

```bash
celery -A config worker --concurrency=4
```

The concurrency model depends on the worker pool.

---

## Prefork

Typical Linux production choice:

```bash
celery -A config worker --pool=prefork --concurrency=4
```

Uses multiple processes.

Good for:

- CPU-bound Python work
- Process isolation
- Django workloads

---

## Solo

```bash
celery -A config worker --pool=solo
```

One process, one task at a time.

Useful for:

- Windows development
- Debugging

Not normally the production choice.

---

## Threads

```bash
celery -A config worker --pool=threads --concurrency=10
```

Can be useful for I/O-heavy work, but understand Python's execution model and your workload before choosing it.

---

## CPU-bound vs I/O-bound

CPU-bound:

```text
Image processing
Large calculations
ML inference
```

More worker processes may help.

I/O-bound:

```text
HTTP requests
Network calls
Waiting on external services
```

Concurrency can often be higher, but the correct value depends on external limits and system resources.

---

# 17. Prefetching and Fair Task Distribution

Celery workers may reserve tasks before executing them.

This is controlled by:

```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
```

With concurrency 4, a worker may reserve approximately:

```text
4 × 4 = 16 tasks
```

depending on broker/pool semantics.

---

## Why prefetch can be a problem

Suppose:

```text
Task A = 5 minutes
Task B = 1 second
Task C = 1 second
...
```

One worker may reserve many tasks while another worker becomes idle.

For long-running tasks, consider:

```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

This often improves fairness.

---

## Late acknowledgement + prefetch

These settings interact.

A production configuration should be chosen based on:

- Task duration
- Duplicate tolerance
- Broker behavior
- Worker count
- Failure recovery requirements

Do not copy a configuration blindly.

---

# 18. Routing and Multiple Queues

Large systems should not necessarily put every task into one queue.

Example:

```text
default
notifications
reports
payments
```

---

## Task routing

```python
CELERY_TASK_ROUTES = {
    "notifications.tasks.send_push": {
        "queue": "notifications",
    },
    "reports.tasks.generate_report": {
        "queue": "reports",
    },
}
```

Run workers separately:

```bash
celery -A config worker \
    -Q notifications \
    -n notifications@%h \
    -l INFO
```

And:

```bash
celery -A config worker \
    -Q reports \
    -n reports@%h \
    -l INFO
```

---

## Why multiple queues help

Suppose report generation is CPU-heavy.

Without queues:

```text
report task
report task
report task
report task
notification task <- delayed
```

With queues:

```text
reports queue       -> report workers
notifications queue -> notification workers
```

This provides workload isolation.

---

# 19. Priority

Celery supports task priorities depending on the broker/transport and configuration.

Example:

```python
send_sms.apply_async(
    args=[user_id],
    priority=9,
)
```

Lower-priority background work:

```python
generate_report.apply_async(
    args=[report_id],
    priority=1,
)
```

Priority behavior is broker-specific, so verify the exact semantics for your production broker.

Do not assume Redis priority behaves exactly like RabbitMQ priority queues.

---

# 20. Task Expiration and Time Limits

## Task expiration

```python
send_email.apply_async(
    args=[user_id],
    expires=60,
)
```

If the task is not accepted within its expiration window, it may be discarded/revoked according to Celery semantics.

Useful for:

```text
"Send this notification only if it is still relevant."
```

---

## Soft time limit

```python
@shared_task(soft_time_limit=300)
def process_file(file_id):
    ...
```

A soft limit raises an exception inside the task, allowing cleanup.

---

## Hard time limit

```python
@shared_task(time_limit=360)
def process_file(file_id):
    ...
```

The worker terminates the task after the limit.

Use time limits carefully because abrupt termination can leave partial side effects.

---

# 21. Database Transactions and Celery

This is a major Django/Celery issue.

Consider:

```python
from django.db import transaction


@transaction.atomic
def create_order():
    order = Order.objects.create(...)

    send_order_notification.delay(order.id)
```

Potential race:

```text
Database transaction not committed
           |
           v
Celery task starts
           |
           v
Task queries order
           |
           v
Order does not exist yet
```

---

## Correct: `transaction.on_commit`

```python
from django.db import transaction


def create_order():
    with transaction.atomic():
        order = Order.objects.create(...)

        transaction.on_commit(
            lambda: send_order_notification.delay(order.id)
        )
```

Now:

```text
DB COMMIT
   |
   v
enqueue Celery task
```

This is extremely important.

---

## Celery 5.4+ shortcut

Celery provides Django integration for deferring task publication until transaction commit via `delay_on_commit()` on tasks in supported configurations.

Example:

```python
send_order_notification.delay_on_commit(order.id)
```

When available, this is often cleaner than manually wrapping `transaction.on_commit()`.

---

# 22. Django ORM and Connection Management

Workers are long-lived processes.

Unlike Django's normal request lifecycle, a Celery worker can execute many tasks in the same process.

Be aware of:

- Stale database connections
- Connection limits
- Long-running transactions
- Database locks
- Connection pool configuration

Use Django's database connection management appropriately.

For example:

```python
from django.db import close_old_connections


@shared_task
def process_large_job(job_id):
    close_old_connections()

    ...
```

Do not randomly call:

```python
connection.close()
```

everywhere. Understand Django's connection lifecycle first.

---

## Avoid huge ORM operations

Bad:

```python
users = list(User.objects.all())

for user in users:
    ...
```

Better:

```python
for user in User.objects.iterator(chunk_size=1000):
    ...
```

For bulk updates:

```python
User.objects.filter(...).update(...)
```

For bulk inserts:

```python
Model.objects.bulk_create(
    objects,
    batch_size=500,
)
```

---

# 23. Serialization

Celery needs to serialize task arguments.

Recommended:

```python
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
```

Good arguments:

```python
task.delay(
    order_id=123,
    customer_id=456,
)
```

Avoid:

```python
task.delay(
    django_model_instance,
    open_file,
    database_connection,
)
```

JSON-compatible types are safest:

```text
string
integer
float
boolean
null
list
dictionary
```

Dates/times should be converted into a deliberate serialized representation.

---

# 24. Redis Failure Modes

Redis is infrastructure, so it can fail.

Important scenarios:

### Redis unavailable

Django:

```text
Cannot publish task
```

Worker:

```text
Cannot consume tasks
```

Possible errors include connection errors/timeouts.

---

## Redis restart

Depending on Redis persistence/configuration and broker state, messages may be lost.

Do not treat Redis as magically durable just because it is a broker.

For critical workloads, evaluate:

- Redis persistence
- High availability
- Replication
- Sentinel/managed Redis
- Cluster architecture
- Broker suitability

---

## Redis memory pressure

Redis is memory-oriented.

If Redis reaches its configured memory limit, eviction policy can become critical.

A careless eviction policy can cause unexpected removal of keys.

Monitor:

```text
used_memory
maxmemory
evicted_keys
connected_clients
blocked_clients
```

---

## Redis latency

High Redis latency can cause:

- Slow task publication
- Slow consumption
- Delayed scheduling
- Connection timeouts

Monitor Redis separately from Celery.

---

## Redis network partition

Possible result:

```text
Django       X       Redis       X       Worker
```

Both producers and consumers may experience connection failures.

Your task design should tolerate temporary infrastructure failures.

---

# 25. Celery Failure Modes

## 25.1 Worker crashes

Task may be:

```text
lost
```

or:

```text
redelivered
```

depending on acknowledgement/requeue settings.

Design tasks assuming duplicate execution can happen.

---

## 25.2 Task raises exception

Example:

```python
@shared_task
def divide(a, b):
    return a / b
```

Calling:

```python
divide.delay(10, 0)
```

results in failure.

With a result backend:

```python
result.status
```

can become:

```text
FAILURE
```

---

## 25.3 Worker is running but task is not executed

Check:

```text
Is the task registered?
Is the worker listening to the correct queue?
Is the worker connected to the correct Redis?
Is the task routed elsewhere?
Is the task expired?
Is concurrency exhausted?
```

---

## 25.4 Beat is running but no task arrives

Check:

```text
Beat logs
Scheduler configuration
PeriodicTask.enabled
Schedule timezone
Redis connection
Task name
Worker queue
```

---

## 25.5 Beat starts but schedule does not change

With `django-celery-beat`, verify:

```python
PeriodicTask.objects.filter(enabled=True)
```

and:

```python
PeriodicTask.objects.all()
```

Also check the scheduler process is actually using:

```text
DatabaseScheduler
```

---

## 25.6 Multiple Beat instances

Do not run multiple Beat instances for the same schedule unless you deliberately understand the consequences.

You can accidentally publish duplicate periodic tasks.

Recommended:

```text
1 logical scheduler
+
many workers
```

---

# 26. Common Production Bugs

## Bug 1: Running worker but not Beat

Symptom:

```text
Normal .delay() tasks work.
Periodic tasks never run.
```

Cause:

```text
Beat is not running.
```

---

## Bug 2: Running Beat but not Worker

Symptom:

```text
Beat says it sent task.
Nothing happens.
```

Cause:

```text
No worker consuming the queue.
```

---

## Bug 3: Wrong Celery app

Command:

```bash
celery -A wrong_project worker
```

can load a different Celery application.

Verify:

```bash
celery -A config inspect registered
```

---

## Bug 4: Task not discovered

If:

```python
app.autodiscover_tasks()
```

is used, tasks should generally be in:

```text
<django_app>/tasks.py
```

Check:

```bash
celery -A config inspect registered
```

---

## Bug 5: Wrong task name

Configured:

```python
"task": "notifications.tasks.dispatch_notifications"
```

But actual function is:

```python
notifications.tasks.dispatch_scheduled_notifications
```

Beat may publish a task name that workers do not recognize.

---

## Bug 6: Queue mismatch

Beat publishes to:

```text
notifications
```

Worker consumes:

```text
default
```

Result:

```text
Task appears stuck.
```

---

## Bug 7: Time zone mismatch

Django:

```python
TIME_ZONE = "Asia/Dhaka"
```

Celery:

```python
CELERY_TIMEZONE = "UTC"
```

Can cause surprising scheduling behavior.

Use one deliberate timezone strategy.

---

## Bug 8: Naive datetime

Bad:

```python
datetime.now()
```

Better:

```python
timezone.now()
```

when `USE_TZ = True`.

---

## Bug 9: Task sent before transaction commits

Bad:

```python
Order.objects.create(...)
send_notification.delay(order.id)
```

inside a transaction.

Better:

```python
transaction.on_commit(
    lambda: send_notification.delay(order.id)
)
```

or:

```python
send_notification.delay_on_commit(order.id)
```

when supported.

---

## Bug 10: Counting "currently delivering" incorrectly

Do not derive a historical operational state from:

```python
total_orders - total_delivered
```

unless the business definition explicitly guarantees that relationship.

Example:

```text
Aug 1 -> assigned -> delivering
Aug 1 -> returned undelivered

Aug 2 -> assigned -> delivering
Aug 2 -> returned undelivered

Aug 3 -> assigned -> delivered
```

If you need:

```text
"orders that entered delivering on Aug 1"
```

you need the relevant historical timestamp/event.

If you need:

```text
"orders currently delivering"
```

you need the current business state.

If you need:

```text
"orders delivered after being assigned on Aug 1"
```

you need both assignment history and delivery history.

The important principle is:

> **Current state and historical events are different datasets.**

---

# 27. Monitoring and Observability

Production Celery should not be operated using logs alone.

Monitor:

```text
Queue length
Task latency
Task execution duration
Task failure rate
Retry rate
Worker count
Worker health
Redis memory
Redis latency
Beat health
Database connections
External API latency
```

---

## Celery inspect

Registered tasks:

```bash
celery -A config inspect registered
```

Active tasks:

```bash
celery -A config inspect active
```

Reserved tasks:

```bash
celery -A config inspect reserved
```

Scheduled tasks:

```bash
celery -A config inspect scheduled
```

Worker stats:

```bash
celery -A config inspect stats
```

---

## Flower

Flower is a web-based monitoring tool for Celery.

Install:

```bash
pip install flower
```

Run:

```bash
celery -A config flower
```

It can provide visibility into:

- Workers
- Tasks
- Queues
- Failures
- Runtime
- Task states

For serious production environments, also consider centralized metrics/logging platforms.

---

## Structured logging

Example:

```python
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_order(self, order_id):
    logger.info(
        "Processing order",
        extra={
            "task_id": self.request.id,
            "order_id": order_id,
        },
    )

    ...
```

Useful fields:

```text
task_id
task_name
order_id
user_id
queue
retry_count
duration
error
```

---

# 28. Graceful Shutdown and Deployments

A Celery worker is a long-running process.

During deployment:

```text
Old worker
   |
   | stop accepting new work
   |
   v
finish/recover tasks
   |
   v
exit
```

Then:

```text
New worker
   |
   v
start consuming
```

Avoid killing workers abruptly unless necessary.

---

## Important deployment principle

Do not deploy code that removes/renames a task while old workers may still receive the old task name.

For example:

```text
Version A:
orders.tasks.send_invoice
```

Then deploy Version B:

```text
orders.tasks.send_invoice_pdf
```

There may still be queued messages referring to:

```text
orders.tasks.send_invoice
```

Use backward-compatible deployment strategies.

---

# 29. Security

## Never trust task arguments blindly

A task can receive data from a queue.

Validate business inputs.

---

## Prefer JSON

```python
CELERY_ACCEPT_CONTENT = ["json"]
```

Avoid enabling unsafe serializers unnecessarily.

Pickle-based serialization can execute arbitrary Python objects and should not be enabled for untrusted message sources.

---

## Protect Redis

Do not expose Redis publicly.

Prefer:

```text
Django ---- private network ---- Redis
Worker ---- private network ---- Redis
```

Use:

- Authentication/ACLs
- TLS where appropriate
- Firewall/security groups
- Private networking
- Secret management

---

## Store secrets outside source code

Bad:

```python
CELERY_BROKER_URL = (
    "redis://:my-super-secret-password@redis:6379/0"
)
```

Better:

```python
import os

CELERY_BROKER_URL = os.environ["CELERY_BROKER_URL"]
```

Use environment variables or a proper secret manager.

---

# 30. Performance Tuning

There is no universal "best Celery configuration."

Tune according to workload.

---

## Worker concurrency

Example:

```bash
celery -A config worker \
    --concurrency=8 \
    -l INFO
```

Too high:

```text
CPU contention
Memory pressure
Database connection exhaustion
External API overload
```

Too low:

```text
Queue grows
Latency increases
```

---

## Prefetch

For short tasks:

```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
```

may be reasonable.

For long tasks:

```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

may provide better fairness.

Benchmark instead of guessing.

---

## Task granularity

Bad:

```text
One task processes 10 million records
```

Potential problems:

- Huge runtime
- Difficult retries
- Large transaction
- Hard failure recovery

Better:

```text
10,000 tasks × 1,000 records
```

when appropriate.

---

## But avoid over-fragmentation

Do not create:

```text
1 million tiny tasks
```

without considering broker overhead.

A good task is generally:

```text
large enough to amortize queue overhead
small enough to retry safely
```

---

# 31. Testing

## Unit testing task logic

Keep business logic testable independently.

```python
def calculate_total(price, quantity):
    return price * quantity


@shared_task
def calculate_order_total(order_id):
    ...
```

Then test:

```python
def test_calculate_total():
    assert calculate_total(100, 3) == 300
```

---

## Celery eager mode

For some tests:

```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

This executes tasks locally rather than through a real worker.

Useful for simple tests, but it does **not** reproduce real broker/worker behavior.

You should still run integration tests with actual Redis and a worker for important workflows.

---

## Testing retries

Example:

```python
@shared_task(bind=True, max_retries=3)
def unreliable_task(self):
    try:
        call_service()
    except TimeoutError as exc:
        raise self.retry(exc=exc, countdown=5)
```

Test:

```python
result = unreliable_task.apply()

assert result.state in {
    "SUCCESS",
    "RETRY",
    "FAILURE",
}
```

For robust tests, mock the external service and verify retry behavior explicitly.

---

# 32. Production Configuration

A reasonable baseline:

```python
CELERY_BROKER_URL = os.environ["CELERY_BROKER_URL"]

CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND"
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "Asia/Dhaka"
CELERY_ENABLE_UTC = True

CELERY_TASK_ACKS_LATE = True

CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_TASK_TRACK_STARTED = True

CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60

CELERY_TASK_SEND_SENT_EVENT = True

CELERY_WORKER_SEND_TASK_EVENTS = True
```

Do not copy every option into production blindly.

Especially validate:

```text
ACK behavior
Retry behavior
Time limits
Prefetch
Result retention
Redis persistence
```

against your workload.

---

# 33. Reliable Design Patterns

## Pattern 1: Transaction + task

```python
from django.db import transaction


def create_order(data):
    with transaction.atomic():
        order = Order.objects.create(**data)

        transaction.on_commit(
            lambda: process_order.delay(order.id)
        )

    return order
```

---

## Pattern 2: Idempotent task

```python
@shared_task
def process_order(order_id):
    order = Order.objects.get(pk=order_id)

    if order.processed:
        return

    # Business operation

    order.processed = True
    order.save(update_fields=["processed"])
```

For high-concurrency workflows, use database locking/constraints where necessary.

---

## Pattern 3: Retry only transient failures

```python
@shared_task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def sync_external_service(object_id):
    ...
```

---

## Pattern 4: Queue isolation

```text
payments
notifications
reports
default
```

Use separate workers when workloads need isolation.

---

## Pattern 5: Thin task, reusable service

Instead of putting everything into the Celery task:

```python
@shared_task
def process_order(order_id):
    ...
    ...
    ...
    ...
```

Prefer:

```python
def process_order_service(order_id):
    ...


@shared_task
def process_order(order_id):
    return process_order_service(order_id)
```

Benefits:

- Easier unit testing
- Reusable business logic
- Smaller task code
- Easier transaction management

---

# 34. End-to-End Example

Let's build an order notification workflow.

## Model

```python
from django.db import models


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    notification_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
```

---

## Service

```python
from django.db import transaction

from .models import Order


def complete_order(order_id):
    with transaction.atomic():
        order = (
            Order.objects
            .select_for_update()
            .get(pk=order_id)
        )

        if order.status == "completed":
            return False

        order.status = "completed"
        order.save(update_fields=["status"])

        return True
```

---

## Task

```python
from celery import shared_task

from .models import Order


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_order_notification(self, order_id):
    order = Order.objects.get(pk=order_id)

    if order.notification_sent:
        return "already-sent"

    notification_service.send(
        order_id=order.id,
    )

    order.notification_sent = True
    order.save(update_fields=["notification_sent"])

    return "sent"
```

---

## Create order and enqueue after commit

```python
from django.db import transaction

from .models import Order
from .tasks import send_order_notification


def create_order():
    with transaction.atomic():
        order = Order.objects.create()

        transaction.on_commit(
            lambda: send_order_notification.delay(order.id)
        )

    return order
```

Or, when supported:

```python
send_order_notification.delay_on_commit(order.id)
```

---

## API

```python
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .tasks import send_order_notification


class SendOrderNotificationAPIView(APIView):
    def post(self, request, order_id):
        task = send_order_notification.delay(order_id)

        return Response(
            {
                "task_id": task.id,
                "status": "queued",
            },
            status=status.HTTP_202_ACCEPTED,
        )
```

---

## Production architecture

```text
                 +----------------+
                 | Django / DRF   |
                 +-------+--------+
                         |
                         | delay()
                         v
                 +---------------+
                 | Redis Broker  |
                 +-------+-------+
                         |
                         v
                 +---------------+
                 | Celery Worker |
                 +-------+-------+
                         |
                         v
                 +---------------+
                 | MySQL/Postgres|
                 +---------------+

                 +---------------+
                 | Celery Beat   |
                 +-------+-------+
                         |
                         v
                      Redis
```

---

# 35. Troubleshooting Checklist

When a Celery task does not run, check in this order.

## Step 1 — Is Redis alive?

```bash
redis-cli ping
```

Expected:

```text
PONG
```

---

## Step 2 — Is the worker alive?

```bash
celery -A config inspect ping
```

Expected something similar to:

```text
pong
```

---

## Step 3 — Is the task registered?

```bash
celery -A config inspect registered
```

Find:

```text
orders.tasks.process_order
```

---

## Step 4 — Is the worker consuming the correct queue?

```bash
celery -A config inspect active_queues
```

---

## Step 5 — Is the task actually being published?

Look at Django logs.

For deeper debugging, inspect Redis/worker behavior and Celery events.

---

## Step 6 — Is the task reserved?

```bash
celery -A config inspect reserved
```

---

## Step 7 — Is the task executing?

```bash
celery -A config inspect active
```

---

## Step 8 — Is the task scheduled for later?

```bash
celery -A config inspect scheduled
```

---

## Step 9 — If periodic, is Beat running?

```bash
celery -A config beat -l INFO
```

For database scheduling:

```bash
celery -A config beat \
    -l INFO \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## Step 10 — Check timezone

Django:

```python
USE_TZ = True
TIME_ZONE = "Asia/Dhaka"
```

Celery:

```python
CELERY_TIMEZONE = "Asia/Dhaka"
```

---

## Step 11 — Check task name

Beat:

```python
"task": "app.tasks.my_task"
```

Actual:

```python
@app.task
def my_task():
    ...
```

---

## Step 12 — Check queue routing

```text
Beat -> notifications
Worker -> default
```

means the worker will not consume that notification task.

---

# 36. Advanced Interview Questions

## Q1. What is Celery?

**Answer:**

Celery is a distributed task queue/framework for executing Python functions asynchronously or on a schedule. It separates task producers from workers through a broker such as Redis or RabbitMQ.

---

## Q2. Is Redis Celery?

No.

```text
Celery = task processing framework
Redis = broker/result backend option
```

---

## Q3. What does Celery Beat do?

Beat schedules task messages. It does not execute tasks.

```text
Beat -> Broker -> Worker
```

---

## Q4. What happens if a worker crashes?

It depends on acknowledgement configuration.

With late acknowledgement:

```python
CELERY_TASK_ACKS_LATE = True
```

an unacknowledged message can be redelivered, depending on broker/worker behavior.

This improves reliability but can cause duplicate execution.

---

## Q5. Why must Celery tasks be idempotent?

Because distributed task processing commonly provides at-least-once execution semantics in failure scenarios.

A task can execute more than once.

---

## Q6. Why use `transaction.on_commit()`?

To prevent a task from querying database data that has not yet been committed.

---

## Q7. Why not pass Django models to Celery?

Because task arguments must be serialized and processes are independent.

Pass:

```python
order.id
```

instead of:

```python
order
```

---

## Q8. What is prefetch?

Workers can reserve multiple messages before executing them.

Too much prefetch can cause unfair distribution for long-running tasks.

---

## Q9. What is the difference between retry and duplicate execution?

Retry is intentional re-execution caused by task failure/retry logic.

Duplicate execution can happen even when the task originally succeeded, for example if the worker crashes before acknowledging the message.

---

## Q10. Why can Beat cause duplicate tasks?

If multiple Beat instances schedule the same periodic task without appropriate coordination, more than one copy may be published.

---

## Q11. Why use multiple queues?

To isolate workloads.

For example:

```text
payments -> payment workers
reports -> report workers
notifications -> notification workers
```

---

## Q12. Why is `result.get()` dangerous in a Django request?

It blocks the HTTP request while waiting for a background task, defeating much of the purpose of asynchronous execution and potentially causing worker/request deadlocks or resource exhaustion.

---

## Q13. Redis vs RabbitMQ?

High-level:

| Concern | Redis | RabbitMQ |
|---|---|---|
| Simplicity | Excellent | Moderate |
| General-purpose data store | Yes | No |
| Message broker specialization | Moderate | Excellent |
| Celery support | Yes | Yes |
| Complex routing | More limited | Strong |
| Operational simplicity | Often easier | More specialized |
| Existing Redis infrastructure | Convenient | Separate system |

The correct choice depends on workload, reliability requirements, routing requirements, and operational expertise.

---

# 37. Quick Reference

## Start services

```bash
redis-server
```

```bash
celery -A config worker -l INFO
```

```bash
celery -A config beat -l INFO
```

Database scheduler:

```bash
celery -A config beat \
    -l INFO \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## Send task

```python
my_task.delay(123)
```

---

## Send with options

```python
my_task.apply_async(
    args=[123],
    countdown=60,
)
```

---

## Retry

```python
@shared_task(bind=True, max_retries=5)
def my_task(self):
    try:
        ...
    except TimeoutError as exc:
        raise self.retry(
            exc=exc,
            countdown=60,
        )
```

---

## Auto retry

```python
@shared_task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def my_task():
    ...
```

---

## Idempotency

```python
@shared_task
def my_task(order_id):
    order = Order.objects.get(pk=order_id)

    if order.processed:
        return

    # Perform operation

    order.processed = True
    order.save(update_fields=["processed"])
```

---

## Transaction safety

```python
from django.db import transaction

transaction.on_commit(
    lambda: my_task.delay(object_id)
)
```

or:

```python
my_task.delay_on_commit(object_id)
```

when supported.

---

## Timezone

```python
USE_TZ = True
TIME_ZONE = "Asia/Dhaka"

CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "Asia/Dhaka"
```

---

## Production principles

Remember these:

```text
1. Celery != Redis
2. Beat schedules; workers execute
3. Pass IDs, not ORM objects
4. Use JSON serialization
5. Use on_commit for transaction-dependent tasks
6. Design tasks to be idempotent
7. Expect duplicate execution
8. Retry transient failures, not every exception
9. Tune prefetch for workload
10. Isolate heavy workloads with queues
11. Monitor workers, queues, Redis, DB, and failures
12. Do not block HTTP requests with result.get()
13. Run only one logical Beat scheduler per schedule
14. Treat Redis as infrastructure that can fail
15. Make deployments backward-compatible with queued task messages
```

---

# Final Mental Model

If you remember only one architecture, remember this:

```text
                         SCHEDULING
                            |
                            v
                     +-------------+
                     | Celery Beat |
                     +------+------+
                            |
                            | publish
                            v
+-------------+       +-----------+       +----------------+
|    Django   | ----> |   Redis   | ----> | Celery Worker  |
|   Producer  |       |   Broker  |       |    Consumer    |
+-------------+       +-----------+       +-------+--------+
                                                   |
                                                   v
                                          +----------------+
                                          | Business Logic |
                                          | Django ORM     |
                                          | External APIs  |
                                          +----------------+
                                                   |
                                                   v
                                          +----------------+
                                          | Result Backend |
                                          |    (optional)  |
                                          +----------------+
```

The most important production concept is:

```text
At-least-once execution
        +
possible worker/broker failure
        +
late acknowledgement
        |
        v
duplicate execution is possible
        |
        v
IDEMPOTENCY IS REQUIRED
```

That single principle explains many of the most difficult Celery production bugs.

