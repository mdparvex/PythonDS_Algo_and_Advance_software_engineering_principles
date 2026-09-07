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



# Celery Task Failure Handling — Advanced Django + Redis

> **Scope:** Production-grade failure handling for Celery tasks running with Django and Redis.
>
> **Core principle:** Design every task assuming it can fail, retry, execute more than once, execute late, or be interrupted at any point.

---

## Table of Contents

1. [Reliability Architecture](#1-reliability-architecture)
2. [The Real Celery Failure Model](#2-the-real-celery-failure-model)
3. [Failure Classification](#3-failure-classification)
4. [At-Least-Once Execution](#4-at-least-once-execution)
5. [Basic Task Failure Handling](#5-basic-task-failure-handling)
6. [Transient Failures and Retries](#6-transient-failures-and-retries)
7. [Exponential Backoff and Jitter](#7-exponential-backoff-and-jitter)
8. [HTTP/API Failure Handling](#8-httpapi-failure-handling)
9. [Database Failure Handling](#9-database-failure-handling)
10. [Django Transactions and `delay_on_commit`](#10-django-transactions-and-delay_on_commit)
11. [Worker Crash and Late Acknowledgement](#11-worker-crash-and-late-acknowledgement)
12. [Idempotency](#12-idempotency)
13. [External Side Effects and Unknown Outcomes](#13-external-side-effects-and-unknown-outcomes)
14. [Task Timeouts](#14-task-timeouts)
15. [Task Expiration](#15-task-expiration)
16. [Retry Exhaustion](#16-retry-exhaustion)
17. [Poison Tasks](#17-poison-tasks)
18. [Serialization and Task Registration Failures](#18-serialization-and-task-registration-failures)
19. [Redis/Broker Failures](#19-redisbroker-failures)
20. [Result Backend Failures](#20-result-backend-failures)
21. [Celery Beat Failures](#21-celery-beat-failures)
22. [Periodic Task Overlap](#22-periodic-task-overlap)
23. [Concurrency, Prefetch, and Queue Starvation](#23-concurrency-prefetch-and-queue-starvation)
24. [Retry Storms](#24-retry-storms)
25. [Database Locks and Connection Exhaustion](#25-database-locks-and-connection-exhaustion)
26. [Batch and Partial Failure Handling](#26-batch-and-partial-failure-handling)
27. [Transactional Outbox Pattern](#27-transactional-outbox-pattern)
28. [Dead-Letter and Quarantine Strategy](#28-dead-letter-and-quarantine-strategy)
29. [Observability and Failure Signals](#29-observability-and-failure-signals)
30. [Production Task Template](#30-production-task-template)
31. [Failure Decision Tree](#31-failure-decision-tree)
32. [Failure Matrix](#32-failure-matrix)
33. [Production Checklist](#33-production-checklist)
34. [Final Production Architecture](#34-final-production-architecture)

---

# 1. Reliability Architecture

A production Django + Celery + Redis system should be understood as a distributed system rather than simply a background-job library.

```text
                         ┌──────────────────────┐
                         │       Django API     │
                         │       Producer       │
                         └──────────┬───────────┘
                                    │
                         publish task/message
                                    │
                                    ▼
                    ┌─────────────────────────────┐
                    │        Redis Broker         │
                    │                             │
                    │ Queue: default              │
                    │ Queue: notifications        │
                    │ Queue: reports              │
                    │ Queue: critical             │
                    └──────────────┬──────────────┘
                                   │
                         deliver/reserve task
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
             ▼                     ▼                     ▼
      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
      │ Worker 1     │      │ Worker 2     │      │ Worker 3     │
      │ notifications│      │ default      │      │ critical     │
      └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   Django Business   │
                        │       Logic         │
                        └──────┬──────┬───────┘
                               │      │
                  ┌────────────┘      └──────────────┐
                  ▼                                  ▼
           ┌──────────────┐                   ┌──────────────┐
           │ MySQL /      │                   │ External API │
           │ PostgreSQL   │                   │ Payment/SMS  │
           └──────────────┘                   └──────────────┘


                    ┌──────────────────────┐
                    │     Celery Beat      │
                    │      Scheduler       │
                    └──────────┬───────────┘
                               │
                               ▼
                         Redis Broker


                    ┌──────────────────────┐
                    │ Monitoring / Alerts  │
                    │ Metrics / Logs /     │
                    │ Error Tracking       │
                    └──────────────────────┘
```

The key reliability layers are:

```text
Django
  │
  ├── durable business state
  ├── transactions
  └── idempotency
          │
          ▼
       Redis
          │
          ├── queues
          └── delivery
          │
          ▼
      Celery Worker
          │
          ├── retry
          ├── timeout
          ├── acknowledgement
          └── execution
          │
          ▼
 External systems
          │
          └── reconciliation
```

---

# 2. The Real Celery Failure Model

A simplistic model is:

```text
Task sent → Worker executes → Task succeeds
```

The real distributed-system model is:

```text
Producer
   |
   | publish
   v
Broker
   |
   | deliver
   v
Worker
   |
   | execute
   v
Database / External systems
```

Every arrow can fail.

## 2.1 Producer failure

```text
Django → X → Redis
```

The application may fail to publish the task.

The business transaction may nevertheless succeed.

Example:

```text
Order created successfully
        |
        X
Redis unavailable
        |
        v
Task never published
```

This is one reason the **Transactional Outbox Pattern** is valuable.

## 2.2 Broker failure

Redis may be unavailable, overloaded, disconnected, or restarted.

Effects include:

- Task publication failure
- Worker disconnection
- Delayed task delivery
- Redelivery behavior
- Result backend failures if Redis is also used for results

## 2.3 Worker failure

The worker may:

- Raise a Python exception
- Be killed
- Crash
- Run out of memory
- Lose its network connection
- Hit a hard time limit
- Be terminated during deployment

## 2.4 Business-system failure

The worker may successfully start but encounter:

- Database deadlock
- Database outage
- External API outage
- HTTP timeout
- Rate limiting
- Invalid business data
- Authentication failure

## 2.5 Side-effect ambiguity

The most dangerous category is:

```text
Did the external operation actually happen?
```

Example:

```text
Worker → Payment API
           |
           | charge request
           v
       Payment API
           |
           | succeeds
           X
       network lost
           |
           v
Worker sees timeout
```

The worker thinks:

```text
FAILED
```

but the payment provider may have:

```text
SUCCEEDED
```

Blindly retrying can create a duplicate charge.

---

# 3. Failure Classification

The first step in handling failures is classifying them.

| Failure | Usually Retry? | Strategy |
|---|---:|---|
| Connection timeout | Yes | Exponential backoff |
| HTTP 503 | Yes | Retry |
| HTTP 429 | Yes | Respect `Retry-After` |
| Database deadlock | Yes | Retry transaction |
| Temporary database outage | Yes | Backoff |
| Redis connection loss | Usually | Reconnect/publish retry |
| `DoesNotExist` | Usually no | Business decision |
| Invalid input | No | Fix data |
| Programming error | No | Fix code |
| HTTP 400 | No | Fix request/data |
| HTTP 401 | Usually no | Refresh credentials/alert |
| HTTP 403 | Usually no | Fix permissions |
| HTTP 404 | Usually no | Business decision |
| Serialization error | No | Fix task payload |
| Wrong task name | No | Fix deployment |
| Worker crash | Potentially | Late ACK + idempotency |
| Task timeout | Depends | Retry only if safe |
| External side effect uncertain | Do not blindly retry | Reconcile |
| Retry exhaustion | No more automatic retry | Alert/quarantine |
| Poison task | No infinite retry | Quarantine |
| Beat stopped | Not a task retry problem | Restore scheduler |
| Duplicate execution | Not a retry problem | Idempotency |

The critical distinction is:

```text
Transient failure
    ≠
Permanent failure
    ≠
Unknown outcome
```

---

# 4. At-Least-Once Execution

For production design, treat Celery workloads as potentially **at-least-once**.

That means a logical operation can execute more than once.

```text
Task published
     |
     v
Worker starts
     |
     v
Business operation succeeds
     |
     X
Worker crashes before acknowledgement
     |
     v
Task may be delivered again
     |
     v
Business operation executes again
```

Therefore:

> **Idempotency is not optional for important side-effecting tasks.**

Do not design around an assumption of exactly-once execution.

A robust design is:

```text
At-least-once delivery
        +
Idempotent processing
        +
Durable business state
        +
Reconciliation
```

---

# 5. Basic Task Failure Handling

A normal Django task:

```python
from celery import shared_task

from orders.models import Order


@shared_task
def process_order(order_id):
    order = Order.objects.get(pk=order_id)

    process(order)

    return {
        "order_id": order.id,
        "status": "processed",
    }
```

If:

```python
process(order)
```

raises an exception and it escapes the task, Celery marks the task as failed.

## 5.1 Never silently swallow exceptions

Bad:

```python
@shared_task
def process_order(order_id):
    try:
        order = Order.objects.get(pk=order_id)
        process(order)
    except Exception:
        logger.exception("Failed")
```

Because no exception escapes, Celery can consider the task successful.

Better:

```python
@shared_task
def process_order(order_id):
    try:
        order = Order.objects.get(pk=order_id)
        process(order)

    except Exception:
        logger.exception(
            "Order processing failed",
            extra={"order_id": order_id},
        )
        raise
```

The `raise` preserves the failure state.

## 5.2 Do not catch everything unless you have a policy

Avoid:

```python
except Exception:
    retry()
```

because it treats:

```text
invalid input
programming bug
permission failure
database outage
network timeout
```

as if they were identical.

---

# 6. Transient Failures and Retries

A transient failure is one that may succeed later.

Examples:

```text
Network timeout
HTTP 503
Database deadlock
Temporary Redis disconnect
Temporary upstream outage
```

## 6.1 Manual retry

```python
from celery import shared_task


@shared_task(bind=True, max_retries=5)
def sync_customer(self, customer_id):
    try:
        perform_sync(customer_id)

    except TimeoutError as exc:
        raise self.retry(
            exc=exc,
            countdown=60,
        )
```

The task will retry later.

## 6.2 Automatic retry

```python
from celery import shared_task


@shared_task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def sync_customer(customer_id):
    perform_sync(customer_id)
```

This is convenient for well-defined transient exception classes.

---

# 7. Exponential Backoff and Jitter

Immediate retrying is dangerous.

Bad:

```text
failure
 ↓
retry immediately
 ↓
failure
 ↓
retry immediately
 ↓
failure
 ↓
...
```

If an external service is down, this creates more load.

## 7.1 Exponential backoff

Prefer:

```text
Failure
   ↓
2 seconds
   ↓
4 seconds
   ↓
8 seconds
   ↓
16 seconds
```

Example:

```python
@shared_task(
    autoretry_for=(TimeoutError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def call_service():
    ...
```

## 7.2 Jitter

Suppose 10,000 tasks fail at exactly the same time.

Without jitter:

```text
10,000 failures
       |
       v
all retry at T+10
       |
       v
10,000 requests
       |
       v
service overloaded
       |
       v
all fail again
```

With jitter:

```text
Task 1 → T+11
Task 2 → T+14
Task 3 → T+18
Task 4 → T+12
...
```

Traffic is spread over time.

For distributed systems, prefer:

```python
retry_jitter=True
```

unless there is a specific reason not to.

---

# 8. HTTP/API Failure Handling

Not every HTTP error should be retried.

## 8.1 Typical retryable statuses

Usually candidates:

```text
408 Request Timeout
429 Too Many Requests
500 Internal Server Error
502 Bad Gateway
503 Service Unavailable
504 Gateway Timeout
```

Usually permanent:

```text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
422 Unprocessable Entity
```

The exact policy depends on the API contract.

## 8.2 Example

```python
import requests

from celery import shared_task


RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}


@shared_task(bind=True, max_retries=5)
def sync_customer(self, customer_id):
    try:
        response = requests.get(
            f"https://api.example.com/customers/{customer_id}",
            timeout=10,
        )

        if response.status_code in RETRYABLE_STATUS_CODES:
            response.raise_for_status()

        response.raise_for_status()

    except requests.Timeout as exc:
        raise self.retry(
            exc=exc,
            countdown=60,
        )

    except requests.HTTPError as exc:
        status = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        if status in RETRYABLE_STATUS_CODES:
            raise self.retry(
                exc=exc,
                countdown=60,
            )

        raise
```

## 8.3 HTTP 429

If an API sends:

```text
429 Too Many Requests
Retry-After: 120
```

respect the provider's requested delay.

```python
if response.status_code == 429:
    retry_after = response.headers.get("Retry-After")

    countdown = int(retry_after or 60)

    raise self.retry(
        countdown=countdown,
    )
```

Do not hammer a rate-limited service.

---

# 9. Database Failure Handling

Database failures are not all equivalent.

## 9.1 Deadlock

Example:

```text
Transaction A locks Row 1
Transaction B locks Row 2

A waits for B
B waits for A

Database detects deadlock
```

A deadlock can be transient.

```python
from celery import shared_task
from django.db import OperationalError, transaction


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def update_order(order_id):
    with transaction.atomic():
        order = (
            Order.objects
            .select_for_update()
            .get(pk=order_id)
        )

        order.status = "processing"

        order.save(
            update_fields=["status"],
        )
```

### Important

Do not blindly retry every `OperationalError` in a critical system.

Some operational errors indicate persistent infrastructure problems.

For mature systems, classify database exceptions more precisely.

## 9.2 Missing object

```python
from orders.models import Order


@shared_task
def process_order(order_id):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning(
            "Order does not exist",
            extra={"order_id": order_id},
        )
        return "order-not-found"

    process(order)
```

Usually, retrying will not create a missing object.

However, if the task was published before the transaction committed, the correct solution is not repeated retries. Use `delay_on_commit()` or `transaction.on_commit()`.

---

# 10. Django Transactions and `delay_on_commit`

This is one of the most important Django + Celery failure cases.

## 10.1 The race condition

Bad:

```python
from django.db import transaction


@transaction.atomic
def create_order():
    order = Order.objects.create(
        status="pending",
    )

    process_order.delay(order.id)
```

Possible timeline:

```text
T0  Django inserts Order
T1  Django publishes Celery task
T2  Worker starts
T3  Worker queries Order
T4  Django transaction commits
```

At T3, the worker may not see the order.

## 10.2 Correct approach

Use:

```python
from django.db import transaction


def create_order():
    with transaction.atomic():
        order = Order.objects.create(
            status="pending",
        )

        transaction.on_commit(
            lambda: process_order.delay(order.id)
        )
```

If your Celery/Django versions support it, use:

```python
process_order.delay_on_commit(order.id)
```

The key guarantee is:

```text
DB COMMIT
   |
   v
publish task
```

instead of:

```text
publish task
   |
   v
DB COMMIT
```

## 10.3 Important limitation

`on_commit()` solves the:

```text
"task ran before DB commit"
```

race.

It does **not** provide atomicity between:

```text
database commit
```

and:

```text
Redis publish
```

That is where the Outbox Pattern becomes useful.

---

# 11. Worker Crash and Late Acknowledgement

One of the most important Celery reliability settings is late acknowledgement.

Conceptually:

```text
Early ACK:

Worker receives
      |
      v
ACK
      |
      v
Execute
      |
      X
Crash
```

If the task was already acknowledged, redelivery may not occur.

With late acknowledgement:

```text
Worker receives
      |
      v
Execute
      |
      X
Crash
      |
      v
No successful ACK
      |
      v
Redelivery may occur
```

A relevant configuration is:

```python
CELERY_TASK_ACKS_LATE = True
```

This improves resilience to worker crashes.

## 11.1 Late ACK is not enough

Suppose:

```text
1. Worker receives task
2. Payment API succeeds
3. Worker crashes
4. ACK is never sent
5. Task is redelivered
```

Now:

```text
Payment API called twice
```

Therefore:

```text
Late ACK
+
Side effects
=
Idempotency required
```

---

# 12. Idempotency

An idempotent task produces the same intended business outcome even if it executes multiple times.

## 12.1 Bad example

```python
@shared_task
def charge_order(order_id):
    payment_gateway.charge(order_id)
```

If the task runs twice:

```text
charge(order_id)
charge(order_id)
```

The customer could be charged twice.

## 12.2 Better external idempotency

Use an operation-specific key:

```python
@shared_task
def charge_order(order_id):
    order = Order.objects.get(pk=order_id)

    if order.payment_status == "paid":
        return "already-paid"

    payment_gateway.charge(
        order_id=order.id,
        idempotency_key=f"order:{order.id}:payment",
    )

    order.payment_status = "paid"

    order.save(
        update_fields=["payment_status"],
    )

    return "paid"
```

The external provider must actually support and enforce the idempotency key.

## 12.3 Database uniqueness

For local idempotency:

```python
class ProcessedOperation(models.Model):
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )
```

Then:

```python
from django.db import IntegrityError


@shared_task
def process_payment(payment_id):
    key = f"payment:{payment_id}"

    try:
        ProcessedOperation.objects.create(
            idempotency_key=key,
        )
    except IntegrityError:
        return "already-processed"

    payment = Payment.objects.get(pk=payment_id)

    perform_payment_operation(payment)

    return "success"
```

For complex workflows, put the idempotency record and relevant business-state transition in an appropriate database transaction.

## 12.4 Celery task ID is not business idempotency

Celery:

```text
task_id = UUID
```

Two logical duplicates can have:

```text
Task A → abc
Task B → xyz
```

while both represent:

```text
"send payment for order 123"
```

Therefore:

```text
Celery task ID
      !=
Business idempotency key
```

Use your own business identifier.

---

# 13. External Side Effects and Unknown Outcomes

This is the most subtle category.

Consider:

```text
Worker
  |
  | charge request
  v
Payment API
  |
  | payment succeeds
  X
network connection lost
  |
  v
Worker gets timeout
```

The worker cannot safely conclude:

```text
payment failed
```

The actual state is:

```text
UNKNOWN
```

## 13.1 Recommended state machine

```text
PENDING
   |
   v
PROCESSING
   |
   +------> SUCCESS
   |
   +------> FAILED
   |
   +------> UNKNOWN
```

`UNKNOWN` is essential when an external side effect may already have happened.

## 13.2 Reconciliation architecture

```text
Celery Task
     |
     v
External API
     |
     +---- success ------> SUCCESS
     |
     +---- clear failure -> FAILED
     |
     +---- timeout ------> UNKNOWN
                              |
                              v
                       Reconciliation Job
                              |
                     ┌────────┴────────┐
                     ▼                 ▼
                  SUCCESS           FAILED
```

The reconciliation task can query the provider using:

```text
transaction ID
merchant reference
idempotency key
operation ID
```

and resolve the state.

## 13.3 Do not blindly retry ambiguous operations

Bad:

```python
try:
    payment_gateway.charge(...)
except TimeoutError:
    raise self.retry(...)
```

This may create duplicate charges.

Better:

```text
timeout
  ↓
UNKNOWN
  ↓
reconcile
  ↓
retry only if it is proven safe
```

---

# 14. Task Timeouts

A task can hang because of:

- External HTTP request
- Database query
- Infinite loop
- Deadlock
- Resource exhaustion
- Unexpected library behavior

Use Celery time limits as an additional protection.

```python
@shared_task(
    soft_time_limit=300,
    time_limit=360,
)
def generate_report(report_id):
    generate(report_id)
```

Conceptually:

```text
Soft time limit
      |
      v
Task gets opportunity to handle timeout
      |
      v
Hard time limit
      |
      v
Worker terminates task
```

## 14.1 Soft timeout handling

```python
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded


@shared_task(soft_time_limit=300)
def generate_report(report_id):
    try:
        generate(report_id)

    except SoftTimeLimitExceeded:
        logger.warning(
            "Report generation timed out",
            extra={"report_id": report_id},
        )

        mark_report_as_failed(report_id)

        raise
```

Do not rely on cleanup code running after a hard kill.

## 14.2 Layer timeouts

A production integration can have:

```text
HTTP connect timeout:    5 sec
HTTP read timeout:      30 sec
Database timeout:       application-specific
Celery soft limit:      60 sec
Celery hard limit:      90 sec
```

Avoid indefinite network operations.

---

# 15. Task Expiration

Some tasks become useless after a certain point.

Example:

```python
send_notification.apply_async(
    args=[user_id],
    expires=300,
)
```

Useful for:

```text
OTP notifications
real-time alerts
time-sensitive reminders
short-lived synchronization
```

Expiration is not a replacement for retry handling.

A task that expires is generally a business decision:

```text
"Do this only while it is still relevant."
```

---

# 16. Retry Exhaustion

Suppose:

```python
max_retries=5
```

and all attempts fail:

```text
Attempt 1 → failure
Attempt 2 → failure
Attempt 3 → failure
Attempt 4 → failure
Attempt 5 → failure
              |
              v
        terminal failure
```

At this point the system should do more than simply log an exception.

Possible actions:

```text
1. Alert operations
2. Store failure reason
3. Record retry count
4. Mark business object as failed
5. Quarantine the task
6. Schedule reconciliation
7. Allow manual retry
```

For critical business workflows, terminal failure should be visible.

---

# 17. Poison Tasks

A poison task is a task that will fail repeatedly for the same permanent reason.

Example:

```python
@shared_task(
    autoretry_for=(Exception,),
    max_retries=None,
)
def broken_task():
    return undefined_variable
```

This can produce:

```text
FAIL
 ↓
RETRY
 ↓
FAIL
 ↓
RETRY
 ↓
...
```

Potential consequences:

- CPU waste
- Queue congestion
- Log flooding
- External API pressure
- Delayed healthy tasks

## 17.1 Protection

Use:

```python
max_retries=5
```

with:

```python
retry_backoff=True
retry_jitter=True
```

Then:

```text
retry limit reached
        |
        v
quarantine / alert
```

Never use unlimited retries casually.

---

# 18. Serialization and Task Registration Failures

## 18.1 Serialization failure

Do not pass complex runtime objects through Celery.

Bad:

```python
task.delay(
    open("/tmp/file.txt"),
)
```

Bad:

```python
task.delay(
    database_connection,
)
```

Better:

```python
task.delay(file_id)
```

Then load the resource inside the worker:

```python
@shared_task
def process_file(file_id):
    file_obj = UploadedFile.objects.get(pk=file_id)

    process_file_content(file_obj)
```

Prefer small, serializable payloads:

```text
ID
string
integer
boolean
simple JSON
```

## 18.2 Wrong task name

Suppose queued messages reference:

```text
orders.tasks.send_invoice
```

but the deployed worker only contains:

```text
orders.tasks.send_invoice_pdf
```

The worker cannot execute the old task.

Common causes:

- Task renamed
- Task deleted
- Wrong module
- Worker not loading Django app
- Deployment mismatch
- Different Celery application

Inspect registered tasks:

```bash
celery -A config inspect registered
```

## 18.3 Deployment compatibility

A safe deployment sequence is:

```text
Version 1
  |
  | old task exists
  v
Deploy Version 2
  |
  | keep old task as compatibility wrapper
  | add new task
  v
Wait for old messages to drain
  |
  v
Remove old task in later release
```

Do not rename/delete task names while old messages may still exist.

---

# 19. Redis/Broker Failures

Redis is a critical component when used as the Celery broker.

## 19.1 Producer cannot publish

Architecture:

```text
Django
  |
  X
Redis
```

Then:

```python
process_order.delay(order.id)
```

may fail.

If the task is business-critical, consider:

```text
database transaction
+
outbox event
+
reliable publisher
```

rather than depending on a best-effort publish.

## 19.2 Worker loses Redis connection

Architecture:

```text
Worker
   |
   X
Redis
```

The worker may no longer receive tasks or communicate normally with the broker.

Worker reconnection behavior and task redelivery depend on Celery/Redis configuration and the exact failure mode.

Test this in staging rather than assuming.

## 19.3 Redis restart

When Redis restarts, understand separately:

```text
broker durability
result durability
unacknowledged task behavior
producer retry behavior
worker reconnect behavior
```

Do not assume that:

```text
Redis = durable message queue
```

in the same sense as a purpose-built durable messaging architecture without validating your Redis deployment and persistence/HA configuration.

## 19.4 Redis memory exhaustion

If Redis reaches its memory limit, behavior depends on its configured eviction/persistence policy.

For Celery workloads, uncontrolled eviction can be dangerous.

Monitor:

```text
used_memory
maxmemory
evicted_keys
connected_clients
blocked_clients
memory fragmentation
queue depth
```

For critical workloads, choose Redis persistence, memory limits, HA, and eviction behavior deliberately.

---

# 20. Result Backend Failures

A common architecture is:

```text
Redis
 ├── broker
 └── result backend
```

A task can successfully execute while result storage fails.

Example:

```text
Task
 |
 v
Database update succeeds
 |
 v
Task returns SUCCESS
 |
 X
Result backend unavailable
```

Business state may still be correct.

Therefore:

> **Do not use Celery result state as the source of truth for business state.**

For example:

```text
Order.status
Payment.status
Notification.status
Inventory.status
```

should be stored in the application database.

Celery result state is operational metadata.

---

# 21. Celery Beat Failures

Beat is responsible for creating periodic task messages.

If Beat stops:

```text
Beat
  |
  X
Redis
```

No new periodic messages are generated.

Existing tasks already in the queue can continue running.

Architecture:

```text
                 Beat
                  |
                  | schedule
                  v
                Redis
                  |
                  v
                Worker
```

If Beat stops:

```text
Worker
  |
  +-- can process existing tasks
  |
  X-- no new periodic tasks
```

## 21.1 Monitor Beat independently

Monitor:

```text
Beat process alive
Last schedule publication
Expected task cadence
Queue activity
```

## 21.2 Multiple Beat instances

Bad:

```text
Beat 1 ─┐
        ├── Redis → Worker
Beat 2 ─┘
```

Both schedulers may publish the same periodic task.

Possible result:

```text
same periodic operation
        +
duplicate execution
```

Use one logical scheduler per schedule unless you have an explicit distributed scheduling/locking design.

---

# 22. Periodic Task Overlap

Suppose:

```text
Task runs every 1 minute
Task execution takes 5 minutes
```

Possible execution:

```text
12:00 → Task A starts
12:01 → Task B starts
12:02 → Task C starts
12:03 → Task D starts
12:04 → Task E starts
```

If the operation is not designed for concurrency, data corruption or duplicate processing may occur.

Solutions:

- Distributed lock
- Database uniqueness
- State machine
- `select_for_update()`
- Idempotency
- Queue isolation
- Increase schedule interval

## 22.1 Simple Redis lock example

```python
import redis

from django.conf import settings
from celery import shared_task


redis_client = redis.Redis.from_url(
    settings.CELERY_BROKER_URL,
)


@shared_task
def periodic_job():
    lock = redis_client.lock(
        "periodic-job-lock",
        timeout=300,
    )

    if not lock.acquire(blocking=False):
        return "already-running"

    try:
        perform_job()
    finally:
        lock.release()
```

A production distributed lock needs careful handling of:

- Expiration
- Worker crashes
- Lock ownership
- Long execution
- Lock renewal
- Failure between acquiring and releasing

For strict correctness, database constraints and transactions are often preferable to a simplistic Redis lock.

---

# 23. Concurrency, Prefetch, and Queue Starvation

Suppose:

```text
worker concurrency = 4
```

and all workers run long tasks:

```text
Worker 1 → 20 minutes
Worker 2 → 20 minutes
Worker 3 → 20 minutes
Worker 4 → 20 minutes
```

A new high-priority task waits.

This is:

```text
queue latency
```

rather than necessarily task failure.

Monitor:

```text
queue depth
queue wait time
task execution time
worker utilization
```

## 23.1 Prefetch

Workers may reserve multiple tasks before executing them.

For long-running tasks, a lower prefetch multiplier can improve fairness:

```python
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

Tune based on workload.

## 23.2 Queue isolation

Separate workloads:

```text
notifications
reports
critical
default
```

Example:

```python
send_notification.apply_async(
    args=[user_id],
    queue="notifications",
)
```

Run dedicated workers:

```bash
celery -A config worker -Q notifications
```

and:

```bash
celery -A config worker -Q reports
```

This prevents heavy reports from starving latency-sensitive notifications.

---

# 24. Retry Storms

A retry storm occurs when a shared dependency fails and many tasks retry simultaneously.

Example:

```text
External API outage
       |
       v
50,000 tasks fail
       |
       v
50,000 retries
       |
       v
API receives huge load
       |
       v
API remains unhealthy
```

Use:

```text
Exponential backoff
+
Jitter
+
Maximum retries
+
Rate limits
+
Queue isolation
+
Circuit breaker where appropriate
```

## 24.1 Circuit breaker concept

```text
              NORMAL
                 |
          too many failures
                 v
               OPEN
                 |
             cooldown
                 v
            HALF-OPEN
             /       \
        success      failure
           |            |
           v            v
         NORMAL        OPEN
```

Celery is not itself a complete circuit-breaker implementation. Implement circuit-breaking at the integration/service layer when needed.

---

# 25. Database Locks and Connection Exhaustion

## 25.1 Long transactions

Bad:

```python
@shared_task
def process_large_order():
    with transaction.atomic():
        for item in huge_queryset:
            process(item)
```

Potential problems:

- Locks held too long
- Deadlocks
- Connection occupation
- Large rollback
- Poor concurrency

Prefer smaller transaction boundaries where business semantics allow.

## 25.2 Connection exhaustion

Suppose:

```text
Web workers       = 30
Celery processes  = 40
Admin/monitoring  = 5
Other services    = 20
```

The database may see:

```text
95 possible connections
```

before considering connection pooling and actual usage.

Always calculate worker concurrency against database capacity.

---

# 26. Batch and Partial Failure Handling

Consider:

```python
@shared_task
def send_notifications(user_ids):
    for user_id in user_ids:
        send_notification(user_id)
```

Suppose:

```text
User 1 → SUCCESS
User 2 → SUCCESS
User 3 → FAILURE
User 4 → not executed
```

If the whole task is retried:

```text
User 1 → duplicate
User 2 → duplicate
User 3 → retry
User 4 → retry
```

This is dangerous.

## 26.1 Per-item task

Prefer:

```python
@shared_task
def send_notification(user_id):
    ...
```

Then enqueue individual tasks:

```python
for user_id in user_ids:
    send_notification.delay(user_id)
```

For very large workloads, use controlled chunking instead of blindly creating millions of tiny tasks.

## 26.2 Track item states

For chunk processing:

```text
PENDING
PROCESSING
SUCCESS
FAILED
```

On retry:

```text
SUCCESS → skip
FAILED  → retry
PENDING → process
```

This makes recovery deterministic.

---

# 27. Transactional Outbox Pattern

`transaction.on_commit()` prevents the task from running before the transaction commits, but it does not make database commit and message publication atomic.

Consider:

```text
DB transaction
      |
      v
COMMIT SUCCESS
      |
      X
Redis publish FAILS
```

Now:

```text
Order exists
Task does not
```

The **Transactional Outbox Pattern** solves this class of problem.

## 27.1 Architecture

```text
                Django
                   |
                   v
          ┌─────────────────┐
          │ DB Transaction  │
          │                 │
          │ Order           │
          │ OutboxEvent     │
          └────────┬────────┘
                   |
                 COMMIT
                   |
                   v
             Outbox Publisher
                   |
                   v
             Redis Broker
                   |
                   v
             Celery Worker
```

## 27.2 Outbox model

```python
class OutboxEvent(models.Model):
    event_type = models.CharField(
        max_length=100,
    )

    aggregate_id = models.CharField(
        max_length=100,
    )

    payload = models.JSONField()

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    attempts = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )
```

## 27.3 Create business object and event atomically

```python
from django.db import transaction


def create_order():
    with transaction.atomic():
        order = Order.objects.create(
            status="pending",
        )

        OutboxEvent.objects.create(
            event_type="order.created",
            aggregate_id=str(order.id),
            payload={
                "order_id": order.id,
            },
        )
```

Both records are committed together.

## 27.4 Publish outbox events

A publisher can periodically process unpublished events:

```python
@shared_task
def publish_outbox_events():
    events = (
        OutboxEvent.objects
        .filter(published_at__isnull=True)
        .order_by("id")[:100]
    )

    for event in events:
        process_order.delay(
            event.payload["order_id"],
        )

        event.attempts += 1

        event.published_at = timezone.now()

        event.save(
            update_fields=[
                "published_at",
                "attempts",
            ],
        )
```

### Important limitation

The simple publisher can still experience:

```text
1. Publish succeeds
2. Database update fails
3. Publisher retries
4. Same task is published again
```

That is not a reason to abandon the pattern.

It means the downstream task must also be idempotent.

The robust combination is:

```text
Transactional outbox
+
At-least-once publication
+
Idempotent consumer
```

---

# 28. Dead-Letter and Quarantine Strategy

After a task reaches terminal failure:

```text
Worker
  |
  | retries exhausted
  v
Failed / Quarantine
  |
  +----> alert
  |
  +----> manual retry
  |
  +----> automated reconciliation
```

Redis does not provide the same native dead-letter-queue model commonly associated with RabbitMQ.

For Redis-backed Celery systems, consider application-level failed-task/quarantine storage when critical workflows require durable inspection and replay.

## 28.1 Failed task model

```python
class FailedTask(models.Model):
    task_id = models.CharField(
        max_length=255,
        unique=True,
    )

    task_name = models.CharField(
        max_length=255,
    )

    arguments = models.JSONField(
        default=dict,
    )

    error_type = models.CharField(
        max_length=255,
    )

    error_message = models.TextField()

    retry_count = models.PositiveIntegerField(
        default=0,
    )

    failed_at = models.DateTimeField(
        auto_now_add=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )
```

Store enough information to answer:

```text
What failed?
Why?
When?
How many attempts?
Which business object?
Was an external side effect possible?
Can it be retried safely?
```

Avoid storing secrets or sensitive credentials in task arguments/logs.

---

# 29. Observability and Failure Signals

Failure handling without observability is incomplete.

Track at minimum:

```text
Task count
Task success rate
Task failure rate
Retry rate
Task duration
Queue depth
Queue latency
Worker availability
Worker memory
Worker CPU
Redis health
Database health
External API latency
External API error rate
```

## 29.1 Log task identity

```python
@shared_task(bind=True)
def process_order(self, order_id):
    logger.info(
        "Starting order processing",
        extra={
            "task_id": self.request.id,
            "order_id": order_id,
            "retry_count": self.request.retries,
        },
    )

    ...
```

Useful fields:

```text
task_id
task_name
queue
business ID
retry count
exception type
execution duration
```

## 29.2 Task failure signal

```python
from celery.signals import task_failure


@task_failure.connect
def handle_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    **extra,
):
    logger.error(
        "Celery task failed",
        extra={
            "task_id": task_id,
            "task_name": sender.name if sender else None,
            "exception": str(exception),
        },
    )
```

Use signals primarily for:

```text
logging
metrics
alerting
observability
```

Avoid putting complex business recovery logic into a global signal unless necessary.

---

# 30. Production Task Template

A production-oriented task can combine:

- Explicit retry policy
- Idempotent state checks
- Database transactions
- Timeouts
- Structured logging
- Terminal failure handling

Example:

```python
import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import OperationalError, transaction

from orders.models import Order

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(
        ConnectionError,
        TimeoutError,
    ),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=300,
    time_limit=360,
)
def process_order(self, order_id):
    task_id = self.request.id
    retry_count = self.request.retries

    logger.info(
        "Starting order processing",
        extra={
            "task_id": task_id,
            "order_id": order_id,
            "retry_count": retry_count,
        },
    )

    try:
        with transaction.atomic():
            order = (
                Order.objects
                .select_for_update()
                .get(pk=order_id)
            )

            if order.status == "completed":
                return "already-completed"

            if order.status not in {
                "pending",
                "retryable",
            }:
                return f"ignored:{order.status}"

            order.status = "processing"

            order.save(
                update_fields=["status"],
            )

        perform_order_processing(order_id)

        with transaction.atomic():
            Order.objects.filter(
                pk=order_id,
            ).update(
                status="completed",
            )

        return "completed"

    except SoftTimeLimitExceeded:
        logger.exception(
            "Order processing timed out",
            extra={
                "task_id": task_id,
                "order_id": order_id,
            },
        )

        Order.objects.filter(
            pk=order_id,
        ).update(
            status="retryable",
        )

        raise

    except OperationalError:
        logger.exception(
            "Database operational error",
            extra={
                "task_id": task_id,
                "order_id": order_id,
            },
        )

        raise

    except Exception:
        logger.exception(
            "Unclassified order processing failure",
            extra={
                "task_id": task_id,
                "order_id": order_id,
            },
        )

        Order.objects.filter(
            pk=order_id,
        ).update(
            status="failed",
        )

        raise
```

### Important

This is a template, not a universal copy/paste implementation.

For example, if:

```python
perform_order_processing()
```

contains an external payment or shipment side effect, the task needs explicit idempotency and possibly an `UNKNOWN` state plus reconciliation.

---

# 31. Failure Decision Tree

Use this decision tree whenever a task fails:

```text
                    TASK FAILED
                         |
                         v
              Is the failure transient?
                    /           \
                  YES            NO
                   |              |
                   v              v
              Can it be       Is it a
              safely retried? permanent /
                /      \       programming
              YES       NO       error?
               |         |          |
               v         v          v
             RETRY     UNKNOWN    FIX CODE /
               |                  DATA / CONFIG
               v
       Could a side effect
       already have happened?
            /          \
          NO            YES
          |              |
          v              v
       Retry        Idempotency /
                    reconciliation
                         |
                         v
                  Retry safely
                         |
                         v
                Max retries reached?
                    /          \
                  NO            YES
                  |              |
                  v              v
                retry       alert / quarantine /
                            manual intervention
```

The most important question is:

> **If I retry this operation, could I duplicate a side effect?**

If yes, do not blindly retry.

---

# 32. Failure Matrix

| Scenario | Recommended Action |
|---|---|
| Python programming bug | Fail + alert + fix code |
| Invalid input | Permanent failure |
| Object missing | Usually fail/ignore |
| Database deadlock | Retry with backoff |
| Database temporarily unavailable | Retry with backoff |
| Redis unavailable during publishing | Producer retry and/or outbox |
| Redis unavailable during consumption | Worker reconnect/recovery |
| HTTP 503 | Retry |
| HTTP 429 | Retry after provider delay |
| HTTP 400 | Do not retry |
| HTTP 401 | Refresh credentials or alert |
| HTTP 403 | Usually permanent |
| HTTP 404 | Usually permanent/business decision |
| External timeout | Retry only if safe |
| External timeout after possible side effect | Mark `UNKNOWN` + reconcile |
| Worker crash before ACK | Redelivery may occur |
| Worker crash after side effect | Idempotency required |
| Task timeout | Recover/retry if safe |
| Retry exhausted | Alert + quarantine/manual retry |
| Poison task | Stop automatic retries + quarantine |
| Beat stopped | Restore scheduler |
| Multiple Beat instances | Prevent duplicate scheduling |
| Wrong queue | Fix routing/worker |
| Wrong task name | Fix deployment/registration |
| Serialization failure | Fix task payload |
| Task published before DB commit | Use `delay_on_commit()` |
| Duplicate publication | Idempotency |
| Long-running task starvation | Tune queues/concurrency/prefetch |
| Result backend unavailable | Do not use result as business truth |
| DB connection exhaustion | Reduce concurrency/pool appropriately |
| Partial batch failure | Track item state/idempotency |

---

# 33. Production Checklist

## Task design

- [ ] Tasks accept IDs rather than ORM objects.
- [ ] Tasks are idempotent.
- [ ] Business operations have unique operation IDs.
- [ ] External side effects use provider idempotency keys where supported.
- [ ] Transient failures are retryable.
- [ ] Permanent failures are not blindly retried.
- [ ] Maximum retries are defined.
- [ ] Backoff is enabled.
- [ ] Jitter is considered.
- [ ] Network timeouts are configured.
- [ ] Long-running tasks have time limits.
- [ ] Business state is stored in the database.

## Django database

- [ ] `transaction.on_commit()` or `delay_on_commit()` is used.
- [ ] Transactions are short.
- [ ] `select_for_update()` is used intentionally.
- [ ] Database uniqueness enforces idempotency where appropriate.
- [ ] Database connection capacity is calculated.
- [ ] Deadlock handling is understood.
- [ ] Outbox is considered for critical event publication.

## Redis

- [ ] Redis is not publicly exposed.
- [ ] Authentication/security is configured.
- [ ] Persistence requirements are understood.
- [ ] HA/failover requirements are understood.
- [ ] Memory is monitored.
- [ ] Eviction behavior is understood.
- [ ] Connection failures are monitored.
- [ ] Broker and result-backend responsibilities are understood.

## Workers

- [ ] Worker concurrency is tuned.
- [ ] Prefetch is tuned.
- [ ] Queues are isolated where necessary.
- [ ] Worker health is monitored.
- [ ] Graceful shutdown is configured.
- [ ] Deployments are backward compatible.
- [ ] Worker memory growth is monitored.

## Beat

- [ ] Beat is monitored.
- [ ] Only one logical Beat scheduler runs per schedule.
- [ ] Periodic tasks cannot unexpectedly overlap.
- [ ] Timezone configuration is consistent.
- [ ] Missed schedule behavior is understood.

## Observability

- [ ] Task IDs are logged.
- [ ] Business IDs are logged.
- [ ] Retry counts are logged.
- [ ] Task duration is measured.
- [ ] Queue latency is measured.
- [ ] Failure rate is monitored.
- [ ] Retry rate is monitored.
- [ ] Terminal failures trigger alerts.
- [ ] External dependency failures trigger alerts.
- [ ] Redis and database health are monitored.

## Recovery

- [ ] Failed tasks can be inspected.
- [ ] Critical failures can be manually replayed.
- [ ] Poison tasks cannot retry forever.
- [ ] Ambiguous external operations can be reconciled.
- [ ] Business state can recover after worker crashes.
- [ ] Deployment rollback/replay procedures exist.
- [ ] Failure-injection tests exist for critical workflows.

---

# 34. Final Production Architecture

For a critical Django + Celery + Redis system, a strong architecture is:

```text
                         ┌───────────────────┐
                         │     Django API    │
                         └─────────┬─────────┘
                                   │
                                   ▼
                       ┌──────────────────────┐
                       │ DB Transaction        │
                       │                       │
                       │ Business State        │
                       │ Idempotency Record    │
                       │ Outbox Event          │
                       └──────────┬───────────┘
                                  │
                                COMMIT
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │  Outbox Publisher    │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │    Redis Broker      │
                       └──────────┬───────────┘
                                  │
                         task delivery
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   Celery Worker      │
                       │                      │
                       │ Retry + Backoff      │
                       │ Jitter               │
                       │ Idempotency          │
                       │ Timeouts             │
                       │ State Transitions    │
                       │ Structured Logging   │
                       └───────┬───────┬──────┘
                               │       │
                     ┌─────────┘       └─────────┐
                     ▼                           ▼
              ┌──────────────┐            ┌──────────────┐
              │   Database   │            │ External API │
              └──────┬───────┘            └──────┬───────┘
                     │                           │
                     └──────────┬────────────────┘
                                ▼
                         Reconciliation
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
                Recovered               Manual review
```

## The core reliability model

```text
              At-least-once delivery
                         +
                 Possible duplicates
                         +
                 Worker/broker failures
                         |
                         v
                   Idempotency
                         +
                 Durable DB state
                         +
               Retry + Backoff + Jitter
                         +
                Timeout protection
                         +
                Failed-task quarantine
                         +
                  Reconciliation
                         |
                         v
              Reliable business outcome
```

## The five rules to remember

### Rule 1 — Assume duplicate execution

```text
A Celery task can execute more than once.
```

Design accordingly.

### Rule 2 — Retry only transient failures

```text
Timeout      → retry
HTTP 503     → retry
DB deadlock  → retry

Programming bug → don't blindly retry
Invalid input   → don't retry
HTTP 400        → don't retry
```

### Rule 3 — An exception does not prove that a side effect failed

```text
Request sent
     |
     v
External service succeeds
     |
     X
Response lost
     |
     v
Worker sees exception
```

The external operation may already have succeeded.

### Rule 4 — Business state belongs in the database

Do not treat:

```text
Celery SUCCESS
```

as permanent business truth.

Use:

```text
Order.status
Payment.status
Shipment.status
Notification.status
```

as the source of truth.

### Rule 5 — Reliability requires recovery, not just retries

A mature Celery architecture combines:

```text
Retry
+
Exponential backoff
+
Jitter
+
Idempotency
+
Durable state
+
Timeouts
+
Quarantine
+
Monitoring
+
Reconciliation
```

---

# Summary

The question for a production Celery system should not be:

```text
"How do I retry a failed task?"
```

The correct question is:

```text
"What can fail before, during, and after this task,
and how do I guarantee a correct business outcome?"
```

That change in perspective is the difference between a basic background-task implementation and a resilient distributed task-processing architecture.
