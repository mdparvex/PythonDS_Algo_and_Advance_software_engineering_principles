# Saga Pattern — Technical Documentation

> A practical guide to understanding, designing, and implementing the Saga Pattern in a Django-based distributed system.

---

# Table of Contents

## Part I — Saga Pattern

1. [What Is the Saga Pattern?](#1-what-is-the-saga-pattern)
2. [Why Saga Is Needed](#2-why-saga-is-needed)
3. [When to Use Saga](#3-when-to-use-saga)
4. [When Not to Use Saga](#4-when-not-to-use-saga)
5. [Core Concepts](#5-core-concepts)
6. [Saga Execution Models](#6-saga-execution-models)
7. [Saga Architecture](#7-saga-architecture)
8. [Consistency Model](#8-consistency-model)
9. [Failure Scenarios](#9-failure-scenarios)
10. [Failure Handling](#10-failure-handling)
11. [Retries and Idempotency](#11-retries-and-idempotency)
12. [Compensation](#12-compensation)
13. [Transactional Outbox](#13-transactional-outbox)
14. [Timeouts and Recovery](#14-timeouts-and-recovery)
15. [Concurrency and Duplicate Execution](#15-concurrency-and-duplicate-execution)
16. [Observability](#16-observability)
17. [Saga vs Database Transaction](#17-saga-vs-database-transaction)
18. [Saga vs Two-Phase Commit](#18-saga-vs-two-phase-commit)
19. [Choreography vs Orchestration](#19-choreography-vs-orchestration)
20. [Production Checklist](#20-production-checklist)

## Part II — Real-Life Django Implementation

21. [Scenario: E-Commerce Order Processing](#21-scenario-e-commerce-order-processing)
22. [System Architecture](#22-system-architecture)
23. [Business Workflow](#23-business-workflow)
24. [Failure Example](#24-failure-example)
25. [Django Project Structure](#25-django-project-structure)
26. [Models](#26-models)
27. [Local Transactions](#27-local-transactions)
28. [Saga Orchestrator](#28-saga-orchestrator)
29. [Celery Tasks](#29-celery-tasks)
30. [Idempotent Operations](#30-idempotent-operations)
31. [Compensation](#31-compensation)
32. [Recovery Worker](#32-recovery-worker)
33. [API Endpoint](#33-api-endpoint)
34. [End-to-End Execution](#34-end-to-end-execution)
35. [Production Improvements](#35-production-improvements)

---

# Part I — Saga Pattern

## 1. What Is the Saga Pattern?

The **Saga Pattern** is a distributed transaction pattern used when one business operation spans multiple independent services or databases.

Instead of trying to execute one global ACID transaction, a Saga divides the workflow into a sequence of **local transactions**.

Each local transaction:

1. Updates its own database.
2. Commits independently.
3. Causes the next step to execute.
4. Has a corresponding **compensating action** when possible.

For example:

```text
Create Order
     |
     v
Reserve Inventory
     |
     v
Charge Payment
     |
     v
Create Delivery
     |
     v
Confirm Order
```

If delivery creation fails:

```text
Create Delivery
      X
      |
      v
Refund Payment
      |
      v
Release Inventory
      |
      v
Cancel Order
```

The important point is that the Saga does **not** perform a distributed database rollback.

It performs new business operations that compensate for previously completed operations.

---

# 2. Why Saga Is Needed

A normal database transaction works well when all operations use the same database:

```python
from django.db import transaction

with transaction.atomic():
    create_order()
    reserve_inventory()
    create_payment()
```

If something fails:

```text
ROLLBACK
```

Everything can be rolled back atomically.

This becomes difficult when the operations belong to different services:

```text
Order Service
    |
    +---- Order DB

Inventory Service
    |
    +---- Inventory DB

Payment Service
    |
    +---- Payment DB

Delivery Service
    |
    +---- Delivery DB
```

A Django `transaction.atomic()` block cannot make all those independent databases one atomic transaction.

A Saga provides a way to coordinate those independent local transactions.

---

# 3. When to Use Saga

Saga is useful when:

- A business workflow spans multiple services.
- Each service owns its own database.
- A global database transaction is impractical or undesirable.
- Temporary inconsistency is acceptable.
- Business operations have meaningful compensating actions.
- The workflow may take seconds or minutes.
- External APIs are involved.
- Long-running workflows need durable state and recovery.

Typical examples:

### E-commerce

```text
Order
  -> Inventory
  -> Payment
  -> Shipping
```

### Travel booking

```text
Flight
  -> Hotel
  -> Car Rental
  -> Payment
```

### Financial/business workflows

```text
Create Transaction
  -> Fraud Check
  -> Reserve Funds
  -> Settlement
  -> Notification
```

### Subscription provisioning

```text
Create Subscription
  -> Charge Customer
  -> Provision Account
  -> Enable Features
```

### Logistics

```text
Create Shipment
  -> Reserve Vehicle
  -> Assign Driver
  -> Generate Delivery
```

---

# 4. When Not to Use Saga

Do not introduce Saga simply because the application has multiple operations.

If everything belongs to one database and one local transaction is sufficient:

```python
with transaction.atomic():
    ...
```

is usually simpler.

Saga also may not be appropriate when:

- Strong immediate consistency is mandatory.
- There is no meaningful compensation.
- The workflow is extremely simple.
- A single transactional database can safely handle the operation.
- The additional operational complexity is not justified.

For example, this does not need Saga:

```text
Create Customer
  -> Create Address
  -> Create Profile
```

if all three are in the same PostgreSQL database and can be handled with one local transaction.

---

# 5. Core Concepts

A Saga consists of several important concepts.

## 5.1 Local Transaction

Each service performs its own atomic operation.

Example:

```text
Inventory Service

BEGIN
    decrease available stock
    increase reserved stock
COMMIT
```

That transaction is local to the Inventory Service.

---

## 5.2 Forward Action

The normal business operation.

Examples:

```text
reserve_inventory
charge_payment
create_delivery
```

---

## 5.3 Compensation

A business operation that reverses the effect of a previous successful step.

Examples:

```text
reserve_inventory
        |
        +--> release_inventory

charge_payment
        |
        +--> refund_payment

create_delivery
        |
        +--> cancel_delivery
```

Compensation is **not** necessarily a technical rollback.

For example:

```text
Charge ৳1,000
```

cannot necessarily be rolled back at the database level after the payment provider accepted it.

The compensation is:

```text
Refund ৳1,000
```

---

## 5.4 Saga State

The Saga itself needs durable state.

For example:

```text
Saga ID: 8b3...
Order ID: 1001

Status: IN_PROGRESS
Current Step: CHARGE_PAYMENT
```

Without persistent state, recovery after a crash becomes difficult.

---

## 5.5 Step State

Each step should have its own state:

```text
RESERVE_INVENTORY
    SUCCESS

CHARGE_PAYMENT
    SUCCESS

CREATE_DELIVERY
    FAILED
```

This makes the workflow observable and recoverable.

---

# 6. Saga Execution Models

There are two major execution models.

## 6.1 Choreography

Services communicate through events.

```text
Order Service
     |
     | OrderCreated
     v
Inventory Service
     |
     | InventoryReserved
     v
Payment Service
     |
     | PaymentCompleted
     v
Delivery Service
```

There is no central coordinator.

### Advantages

- Loosely coupled.
- Services are autonomous.
- No dedicated orchestrator.

### Disadvantages

- Workflow logic becomes distributed.
- Harder to visualize complex flows.
- Event chains can become difficult to debug.
- Circular dependencies can appear.
- Compensation logic may become scattered.

Choreography works well for relatively simple event-driven workflows.

---

## 6.2 Orchestration

A central Saga Orchestrator controls the workflow.

```text
                    Saga Orchestrator
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
        Inventory       Payment       Delivery
         Service        Service        Service
```

The orchestrator knows:

```text
1. Reserve Inventory
2. Charge Payment
3. Create Delivery
4. Confirm Order
```

And on failure:

```text
3. Cancel Delivery
2. Refund Payment
1. Release Inventory
```

### Advantages

- Workflow is explicit.
- Easier to monitor.
- Easier to implement compensation.
- Easier to reason about complex business processes.
- Central place for state transitions.

### Disadvantages

- Orchestrator becomes an important component.
- The orchestrator needs high availability.
- Workflow logic is centralized.

For complex business workflows, orchestration is often easier to maintain.

---

# 7. Saga Architecture

A typical production architecture looks like this:

```text
                         API
                          |
                          v
                 +------------------+
                 | Saga Orchestrator|
                 +--------+---------+
                          |
               +----------+----------+
               |                     |
               v                     v
          Saga State DB        Message Broker
                                    |
                  +-----------------+----------------+
                  |                 |                |
                  v                 v                v
             Inventory          Payment          Delivery
              Service           Service           Service
                  |                 |                |
                  v                 v                v
             Inventory DB      Payment DB       Delivery DB
```

For asynchronous implementations:

```text
API
 |
 v
Create Saga
 |
 v
Persist Saga State
 |
 v
Publish Command
 |
 v
Worker
 |
 v
Local Transaction
 |
 v
Persist Result/Event
 |
 v
Next Saga Step
```

---

# 8. Consistency Model

Saga provides **eventual consistency**, not global ACID atomicity.

During execution, temporary inconsistency can exist.

For example:

```text
Order       = PENDING
Inventory   = RESERVED
Payment     = CHARGED
Delivery    = FAILED
```

The Saga then compensates:

```text
Refund Payment
      |
      v
Release Inventory
      |
      v
Cancel Order
```

Final state:

```text
Order       = CANCELLED
Inventory   = AVAILABLE
Payment     = REFUNDED
Delivery    = NOT_CREATED
```

Therefore, Saga is suitable when the business can tolerate a workflow that is temporarily inconsistent while recovery or compensation is occurring.

---

# 9. Failure Scenarios

A production Saga must assume that almost anything can fail.

## 9.1 Service Failure

```text
Payment Service
       |
       X
```

The Saga should retry or compensate.

---

## 9.2 Network Timeout

The request may succeed even though the caller receives a timeout.

```text
Application
    |
    | charge payment
    v
Payment Provider
    |
    | SUCCESS
    X
Network timeout
```

The application may incorrectly assume:

```text
payment = FAILED
```

and retry.

This can cause duplicate payment unless the operation is idempotent.

---

## 9.3 Worker Crash

```text
Charge Payment
     |
     | SUCCESS
     |
     X
Worker crashes
```

The database may contain the successful operation, while the worker never advances the Saga.

Persistent state and recovery logic are required.

---

## 9.4 Duplicate Message

A broker may deliver a message more than once:

```text
ChargePaymentCommand
       |
       +---- Worker A
       |
       +---- Worker B
```

Both workers could attempt the same payment.

Idempotency is required.

---

## 9.5 Compensation Failure

This is one of the most important cases.

```text
Delivery creation FAILED

Refund payment
       |
       X
```

Now:

```text
Order       = needs cancellation
Payment     = still charged
Inventory   = still reserved
```

The Saga must remain in a recoverable state.

It must not simply mark the Saga as permanently failed and forget about it.

---

# 10. Failure Handling

A robust Saga normally combines:

```text
Saga State
    +
Retries
    +
Idempotency
    +
Compensation
    +
Timeout Detection
    +
Dead-Letter / Manual Recovery
    +
Observability
```

A typical failure flow:

```text
Step Failed
    |
    v
Is failure transient?
    |
   Yes
    |
    v
Retry
    |
    +---- Success ---> Continue Saga
    |
    +---- Exhausted
              |
              v
        Start Compensation
              |
              v
        Compensation Retry
              |
              +---- Success ---> Final Failed/Cancelled State
              |
              +---- Exhausted ---> Manual Recovery / DLQ
```

---

# 11. Retries and Idempotency

Retries are necessary for transient failures.

For example:

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def charge_payment_task(self, saga_id, order_id):
    ...
```

But retries create another problem.

Suppose:

```text
Attempt 1
    |
    v
Payment Provider
    |
    v
SUCCESS
    |
    X
Response lost
```

Celery sees the task as failed and retries:

```text
Attempt 2
    |
    v
Charge again
```

The customer may be charged twice.

Therefore, external side effects should be idempotent.

---

## 11.1 Idempotency Key

Use a stable key:

```text
{saga_id}:{step_name}
```

Example:

```text
8b2e...:charge_payment
```

The payment service stores the result for that key.

If the same command arrives again:

```text
8b2e...:charge_payment
```

the service returns the existing result rather than creating another charge.

---

# 12. Compensation

A compensation should be designed for every forward action where business reversal is possible.

Example:

| Forward Step | Compensation |
|---|---|
| Create Order | Cancel Order |
| Reserve Inventory | Release Inventory |
| Charge Payment | Refund Payment |
| Create Delivery | Cancel Delivery |
| Allocate Vehicle | Release Vehicle |
| Provision Account | Deprovision Account |

However, compensation may not always be a perfect inverse.

For example:

```text
Send SMS
```

cannot truly be undone.

The design must therefore distinguish between:

- reversible operations
- irreversible operations
- operations whose failure requires manual handling
- operations that can be made logically compensatable

---

# 13. Transactional Outbox

Saga and messaging commonly need a **Transactional Outbox**.

Consider:

```python
order.status = "CONFIRMED"
order.save()

publish_event("OrderConfirmed")
```

Two things can fail independently:

```text
Database update  -> SUCCESS
Message publish  -> FAILURE
```

Now the database says:

```text
Order = CONFIRMED
```

but the event was never published.

The Outbox Pattern solves this by writing the business update and outgoing event in the same local transaction:

```text
BEGIN TRANSACTION

Update Order
Create Outbox Event

COMMIT
```

Then a separate publisher sends the outbox event:

```text
Outbox Table
      |
      v
Publisher
      |
      v
Message Broker
```

This gives a reliable bridge between a local database transaction and asynchronous messaging.

---

# 14. Timeouts and Recovery

A Saga can become stuck:

```text
Status = IN_PROGRESS
Current Step = CREATE_DELIVERY
```

The worker might have crashed.

A recovery process should periodically find stale Sagas:

```text
IN_PROGRESS
AND updated_at < now - timeout
```

Then:

```text
Check step
   |
   +--> Safe to retry?
   |
   +--> Already completed?
   |
   +--> Needs compensation?
   |
   +--> Needs manual intervention?
```

This is especially important for long-running workflows.

---

# 15. Concurrency and Duplicate Execution

The same Saga should not be executed concurrently by multiple workers.

Possible situation:

```text
Worker A
   |
   +---- Saga #123

Worker B
   |
   +---- Saga #123
```

Both may execute:

```text
charge_payment()
```

Use mechanisms such as:

- database row locking
- optimistic concurrency
- unique constraints
- idempotency keys
- explicit state transitions

For example:

```python
Saga.objects.select_for_update().get(id=saga_id)
```

can protect a state transition inside a local database transaction.

---

# 16. Observability

Every Saga execution should have a correlation identifier.

Recommended fields:

```text
saga_id
aggregate_id / order_id
saga_type
step
status
attempt_count
created_at
started_at
completed_at
error_message
```

Logs should include:

```text
saga_id=8b2...
order_id=1001
step=charge_payment
attempt=2
status=FAILED
```

This allows an operator to trace a business transaction across multiple services.

---

# 17. Saga vs Database Transaction

### Database transaction

```text
BEGIN
    Operation A
    Operation B
    Operation C
COMMIT
```

Failure:

```text
ROLLBACK
```

Characteristics:

- Strong atomicity.
- Same transactional boundary.
- Simple when all operations share a database.

---

### Saga

```text
Transaction A
    |
    v
Transaction B
    |
    v
Transaction C
```

Failure:

```text
Compensation C
    |
    v
Compensation B
    |
    v
Compensation A
```

Characteristics:

- Distributed.
- Eventually consistent.
- Requires compensation.
- Requires retry/recovery logic.

---

# 18. Saga vs Two-Phase Commit

Two-Phase Commit (2PC) tries to coordinate distributed resources:

```text
Coordinator
    |
    +--> Prepare DB A
    +--> Prepare DB B
    +--> Prepare DB C
    |
    v
Commit
```

Saga uses a different model:

```text
Local Commit A
       |
       v
Local Commit B
       |
       v
Local Commit C

If C fails:
       |
       v
Compensate B
       |
       v
Compensate A
```

Saga generally trades global atomicity for greater independence and asynchronous execution.

---

# 19. Choreography vs Orchestration

| Characteristic | Choreography | Orchestration |
|---|---|---|
| Central coordinator | No | Yes |
| Workflow visibility | Distributed | Centralized |
| Simple workflows | Good | Good |
| Complex workflows | Can become difficult | Usually easier |
| Compensation logic | Distributed | Centralized |
| Service autonomy | High | Moderate |
| Debugging | Can be harder | Usually easier |
| Main risk | Event-chain complexity | Orchestrator complexity |

There is no universal choice.

Use the model that matches the complexity and ownership boundaries of the workflow.

---

# 20. Production Checklist

Before introducing Saga into production:

### Workflow

- [ ] Define every business step.
- [ ] Define forward action for every step.
- [ ] Define compensation where possible.
- [ ] Identify irreversible operations.
- [ ] Define Saga states.
- [ ] Define step states.

### Reliability

- [ ] Persist Saga state.
- [ ] Use idempotency keys.
- [ ] Implement retries.
- [ ] Implement compensation retries.
- [ ] Detect stale/stuck Sagas.
- [ ] Prevent concurrent execution.
- [ ] Define manual recovery.

### Messaging

- [ ] Use durable messaging where appropriate.
- [ ] Consider Transactional Outbox.
- [ ] Make consumers idempotent.
- [ ] Handle duplicate messages.
- [ ] Define dead-letter handling.

### Observability

- [ ] Saga ID.
- [ ] Correlation ID.
- [ ] Business entity ID.
- [ ] Step status.
- [ ] Attempt count.
- [ ] Error details.
- [ ] Execution timestamps.
- [ ] Alerts for stuck/failed Sagas.

---

# Part II — Real-Life Django Implementation

# 21. Scenario: E-Commerce Order Processing

Consider an e-commerce platform where placing an order requires several independent operations:

```text
1. Create Order
2. Reserve Inventory
3. Charge Payment
4. Create Delivery
5. Confirm Order
```

Assume the platform has separate services:

```text
Order Service
Inventory Service
Payment Service
Delivery Service
```

Each service owns its own database.

Therefore:

```text
Order DB
Inventory DB
Payment DB
Delivery DB
```

cannot be wrapped in one Django `transaction.atomic()` call.

This is an ideal Saga use case.

---

# 22. System Architecture

For the example, use an orchestration-based Saga.

```text
                         Client
                           |
                           v
                     Django API
                           |
                           v
                  +------------------+
                  | Saga Orchestrator|
                  +--------+---------+
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
       Inventory        Payment        Delivery
        Service         Service         Service
            |              |              |
            v              v              v
      Inventory DB     Payment DB     Delivery DB
```

Celery can execute the asynchronous steps:

```text
Django API
    |
    v
Create Saga
    |
    v
Celery
    |
    +--> Reserve Inventory
    |
    +--> Charge Payment
    |
    +--> Create Delivery
```

For this documentation, the service operations are represented by Django functions/classes. In a real microservice environment, those calls could instead be HTTP/gRPC commands or message-broker messages.

---

# 23. Business Workflow

The happy path:

```text
START
  |
  v
Create Order
  |
  v
Reserve Inventory
  |
  v
Charge Payment
  |
  v
Create Delivery
  |
  v
Confirm Order
  |
  v
COMPLETED
```

The failure path:

```text
Create Order
  |
  v
Reserve Inventory
  |
  v
Charge Payment
  |
  v
Create Delivery
  |
  X
FAILED
  |
  v
Refund Payment
  |
  v
Release Inventory
  |
  v
Cancel Order
  |
  v
COMPENSATED
```

---

# 24. Failure Example

Suppose customer `1001` buys:

```text
Product: Napa
Quantity: 10
Price: ৳100
Total: ৳1,000
```

Initial state:

```text
Order:
    PENDING

Inventory:
    available = 50
    reserved = 0

Payment:
    NOT_CHARGED

Delivery:
    NOT_CREATED
```

After inventory reservation:

```text
available = 40
reserved = 10
```

After payment:

```text
payment = CHARGED
amount = ৳1,000
```

Now delivery service fails:

```text
CREATE_DELIVERY = FAILED
```

The Saga compensates:

```text
Refund ৳1,000
        |
        v
Release 10 items
        |
        v
Cancel order
```

Final state:

```text
Order:
    CANCELLED

Inventory:
    available = 50
    reserved = 0

Payment:
    REFUNDED

Delivery:
    NOT_CREATED
```

---

# 25. Django Project Structure

A possible implementation:

```text
project/
│
├── apps/
│   ├── orders/
│   │   ├── models.py
│   │   ├── services.py
│   │   └── ...
│   │
│   ├── inventory/
│   │   ├── models.py
│   │   ├── services.py
│   │   └── ...
│   │
│   ├── payments/
│   │   ├── models.py
│   │   ├── services.py
│   │   └── ...
│   │
│   ├── delivery/
│   │   ├── models.py
│   │   ├── services.py
│   │   └── ...
│   │
│   └── saga/
│       ├── models.py
│       ├── orchestrator.py
│       ├── tasks.py
│       └── services.py
│
└── config/
    ├── celery.py
    └── settings.py
```

The Saga-specific code should not be mixed unnecessarily with model definitions.

---

# 26. Models

## 26.1 Order

```python
# apps/orders/models.py

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"
        CANCELLED = "CANCELLED"

    customer_id = models.PositiveBigIntegerField()
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
```

---

## 26.2 Saga

```python
# apps/saga/models.py

import uuid

from django.db import models


class Saga(models.Model):
    class Status(models.TextChoices):
        STARTED = "STARTED"
        IN_PROGRESS = "IN_PROGRESS"
        COMPENSATING = "COMPENSATING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    saga_type = models.CharField(
        max_length=100,
    )

    aggregate_id = models.CharField(
        max_length=100,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.STARTED,
    )

    current_step = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
```

---

## 26.3 Saga Step

```python
class SagaStep(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        COMPENSATED = "COMPENSATED"

    saga = models.ForeignKey(
        Saga,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    step_name = models.CharField(
        max_length=100,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    attempt_count = models.PositiveIntegerField(
        default=0,
    )

    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    error_message = models.TextField(
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
```

The unique `idempotency_key` provides an important database-level protection against duplicate execution records.

---

# 27. Local Transactions

The key principle is:

> Each service protects its own local state with a normal database transaction.

For example, inventory reservation:

```python
# apps/inventory/services.py

from django.db import transaction


def reserve_inventory(
    *,
    product_id: int,
    quantity: int,
    idempotency_key: str,
):
    with transaction.atomic():
        # Check whether this command was already processed.
        existing = find_existing_reservation(
            idempotency_key=idempotency_key,
        )

        if existing:
            return existing

        inventory = (
            Inventory.objects
            .select_for_update()
            .get(product_id=product_id)
        )

        if inventory.available_quantity < quantity:
            raise InsufficientInventoryError()

        inventory.available_quantity -= quantity
        inventory.reserved_quantity += quantity
        inventory.save(
            update_fields=[
                "available_quantity",
                "reserved_quantity",
            ]
        )

        return create_reservation(
            product_id=product_id,
            quantity=quantity,
            idempotency_key=idempotency_key,
        )
```

This transaction protects only the Inventory Service's database.

It does **not** include Payment or Order.

---

# 28. Saga Orchestrator

The orchestrator controls the business workflow.

```python
# apps/saga/orchestrator.py

from apps.orders.models import Order
from apps.saga.models import Saga


class OrderSagaOrchestrator:

    def __init__(self, saga: Saga):
        self.saga = saga

    def execute(self):
        self.create_order()

        self.reserve_inventory()

        self.charge_payment()

        self.create_delivery()

        self.confirm_order()
```

Each operation updates the Saga state before/after execution.

---

## 28.1 Create Order

```python
def create_order(self):
    self.saga.current_step = "CREATE_ORDER"
    self.saga.status = Saga.Status.IN_PROGRESS
    self.saga.save(
        update_fields=[
            "current_step",
            "status",
            "updated_at",
        ]
    )

    # Order creation itself is a local transaction.
    order = Order.objects.create(
        customer_id=1001,
        total_amount="1000.00",
        status=Order.Status.PENDING,
    )

    return order
```

In a real implementation, the order ID should be associated with the Saga from the beginning.

---

# 29. Celery Tasks

The Saga can use Celery to execute asynchronous work.

```python
# apps/saga/tasks.py

from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def reserve_inventory_task(
    self,
    saga_id,
    order_id,
):
    ...
```

Then payment:

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def charge_payment_task(
    self,
    saga_id,
    order_id,
):
    ...
```

And delivery:

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def create_delivery_task(
    self,
    saga_id,
    order_id,
):
    ...
```

The retry configuration handles transient failures, but it does **not** solve duplicate side effects by itself. Each task must still be idempotent.

---

# 30. Idempotent Operations

A payment operation should use a deterministic idempotency key.

```python
def get_idempotency_key(
    saga_id,
    step_name,
):
    return f"{saga_id}:{step_name}"
```

For payment:

```python
idempotency_key = get_idempotency_key(
    saga_id,
    "CHARGE_PAYMENT",
)
```

The payment service should store the result.

Example:

```python
class PaymentOperation(models.Model):
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    order_id = models.PositiveBigIntegerField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
    )

    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
```

If Celery retries:

```text
Attempt 1:
    saga-123:CHARGE_PAYMENT

Attempt 2:
    saga-123:CHARGE_PAYMENT
```

the second attempt finds the existing operation and returns its result.

---

# 31. Compensation

The orchestrator should compensate successful steps in reverse order.

```python
def compensate(self, completed_steps):
    for step in reversed(completed_steps):

        if step == "CREATE_DELIVERY":
            self.cancel_delivery()

        elif step == "CHARGE_PAYMENT":
            self.refund_payment()

        elif step == "RESERVE_INVENTORY":
            self.release_inventory()

        elif step == "CREATE_ORDER":
            self.cancel_order()
```

For the example:

```text
Successful steps:

CREATE_ORDER
RESERVE_INVENTORY
CHARGE_PAYMENT

Failed step:

CREATE_DELIVERY
```

Compensation:

```text
REFUND_PAYMENT
      |
      v
RELEASE_INVENTORY
      |
      v
CANCEL_ORDER
```

The failed delivery step itself does not need compensation because the delivery was never successfully created.

---

# 32. A More Complete Orchestrator

A simplified but clearer version:

```python
class OrderSagaOrchestrator:

    def __init__(self, saga_id):
        self.saga_id = saga_id

    def execute(self):
        completed_steps = []

        try:
            self.reserve_inventory()
            completed_steps.append("RESERVE_INVENTORY")

            self.charge_payment()
            completed_steps.append("CHARGE_PAYMENT")

            self.create_delivery()
            completed_steps.append("CREATE_DELIVERY")

            self.confirm_order()

            self.mark_completed()

        except Exception as exc:
            self.mark_compensating(str(exc))

            self.compensate(completed_steps)

            self.mark_failed(str(exc))

            raise
```

This is intentionally simplified.

A production orchestrator should persist each transition rather than relying only on the in-memory `completed_steps` list.

---

# 33. Persisting Step State

Instead of:

```python
completed_steps = []
```

use the database.

For example:

```python
def mark_step_success(
    saga,
    step_name,
):
    SagaStep.objects.filter(
        saga=saga,
        step_name=step_name,
    ).update(
        status=SagaStep.Status.SUCCESS,
        completed_at=timezone.now(),
    )
```

Then after a crash:

```text
Saga #123

RESERVE_INVENTORY   SUCCESS
CHARGE_PAYMENT      SUCCESS
CREATE_DELIVERY     RUNNING
```

The system can determine exactly what has already happened.

---

# 34. Recovery Worker

A periodic Celery task can recover stuck Sagas:

```python
@shared_task
def recover_stuck_sagas():
    cutoff = timezone.now() - timedelta(minutes=10)

    sagas = Saga.objects.filter(
        status=Saga.Status.IN_PROGRESS,
        updated_at__lt=cutoff,
    )

    for saga in sagas:
        recover_saga(saga)
```

Recovery logic should determine whether the current step:

1. Never started.
2. Started and failed.
3. Completed but the response was lost.
4. Needs retry.
5. Needs compensation.
6. Requires manual intervention.

Do not blindly execute the step again.

---

# 35. API Endpoint

A simplified API could start the Saga:

```python
from django.http import JsonResponse
from django.db import transaction


def create_order(request):
    with transaction.atomic():
        order = Order.objects.create(
            customer_id=request.user.id,
            total_amount="1000.00",
            status=Order.Status.PENDING,
        )

        saga = Saga.objects.create(
            saga_type="ORDER_CREATION",
            aggregate_id=str(order.id),
            status=Saga.Status.STARTED,
        )

    start_order_saga.delay(
        saga_id=str(saga.id),
        order_id=order.id,
    )

    return JsonResponse(
        {
            "order_id": order.id,
            "saga_id": str(saga.id),
            "status": "PROCESSING",
        },
        status=202,
    )
```

The API returns `202 Accepted` because the complete business workflow is asynchronous.

---

# 36. Starting the Saga

```python
@shared_task
def start_order_saga(
    saga_id,
    order_id,
):
    saga = Saga.objects.get(id=saga_id)

    saga.status = Saga.Status.IN_PROGRESS
    saga.current_step = "RESERVE_INVENTORY"
    saga.save(
        update_fields=[
            "status",
            "current_step",
            "updated_at",
        ]
    )

    reserve_inventory_task.delay(
        saga_id=saga_id,
        order_id=order_id,
    )
```

After inventory succeeds, the orchestrator schedules payment:

```python
charge_payment_task.delay(
    saga_id=saga_id,
    order_id=order_id,
)
```

After payment:

```python
create_delivery_task.delay(
    saga_id=saga_id,
    order_id=order_id,
)
```

After delivery:

```python
confirm_order_task.delay(
    saga_id=saga_id,
    order_id=order_id,
)
```

---

# 37. Important Transaction Boundary

Do not do this:

```python
with transaction.atomic():
    reserve_inventory()
    charge_payment()
    create_delivery()
```

if these are independent services.

Instead:

```text
Inventory Service
    |
    +-- Local transaction
    |
    +-- COMMIT

Payment Service
    |
    +-- Local transaction
    |
    +-- COMMIT

Delivery Service
    |
    +-- Local transaction
    |
    +-- COMMIT
```

The Saga coordinates those transactions.

---

# 38. End-to-End Successful Execution

Customer creates an order.

### Step 1

```text
POST /orders
```

Django creates:

```text
Order #1001
Saga #abc
```

State:

```text
Order = PENDING
Saga  = STARTED
```

---

### Step 2

Inventory:

```text
Reserve 10 Napa
```

State:

```text
Inventory:
available = 40
reserved = 10

Saga:
current_step = CHARGE_PAYMENT
```

---

### Step 3

Payment:

```text
Charge ৳1,000
```

State:

```text
Payment = CHARGED

Saga:
current_step = CREATE_DELIVERY
```

---

### Step 4

Delivery:

```text
Create delivery
```

Success.

---

### Step 5

Order:

```text
PENDING -> CONFIRMED
```

Saga:

```text
IN_PROGRESS -> COMPLETED
```

Final state:

```text
Order      = CONFIRMED
Inventory  = RESERVED
Payment    = CHARGED
Delivery   = CREATED
Saga       = COMPLETED
```

---

# 39. End-to-End Failed Execution

Suppose delivery fails.

```text
Order       = PENDING
Inventory   = RESERVED
Payment     = CHARGED
Delivery    = FAILED
```

The Saga changes:

```text
IN_PROGRESS
      |
      v
COMPENSATING
```

Then:

```text
Refund Payment
      |
      v
Release Inventory
      |
      v
Cancel Order
```

Final state:

```text
Order      = CANCELLED
Inventory  = AVAILABLE
Payment    = REFUNDED
Delivery   = NOT_CREATED
Saga       = FAILED
```

The Saga is considered `FAILED` only after its required compensation has completed or the system has explicitly moved the case into a manual-recovery state.

---

# 40. Compensation Failure

Suppose:

```text
Delivery = FAILED
Refund   = FAILED
```

Do **not** immediately do:

```python
saga.status = "FAILED"
```

and forget it.

Instead:

```text
Saga:
    status = COMPENSATING

Step:
    REFUND_PAYMENT
    status = FAILED
    attempts = 3
```

A retry worker can attempt:

```text
Refund Payment
    |
    +--> SUCCESS
```

Then:

```text
Release Inventory
    |
    v
Cancel Order
```

If refund continues to fail after the configured retry policy, the Saga can enter:

```text
MANUAL_INTERVENTION
```

or an equivalent operational state.

---

# 41. Recommended State Machine

A practical state model:

```text
STARTED
   |
   v
IN_PROGRESS
   |
   +----------------------+
   |                      |
   v                      v
COMPLETED             COMPENSATING
                           |
                    +------+------+
                    |             |
                    v             v
                FAILED     MANUAL_INTERVENTION
```

For individual steps:

```text
PENDING
   |
   v
RUNNING
   |
   +----------+
   |          |
   v          v
SUCCESS     FAILED
   |          |
   |          v
   |       RETRY
   |          |
   |          v
   |       SUCCESS
   |
   v
COMPENSATED
```

---

# 42. Production Improvements

The example above intentionally keeps the implementation understandable.

A production system should add the following.

## 42.1 Transactional Outbox

When a local transaction changes state and needs to publish an event:

```text
BEGIN
    Update business data
    Insert OutboxEvent
COMMIT
```

Then publish asynchronously.

---

## 42.2 Strong Idempotency

Every externally visible side effect should have a stable idempotency key:

```text
saga_id + step_name
```

Use a database unique constraint.

---

## 42.3 State Transition Validation

Do not allow arbitrary transitions.

For example:

```text
COMPLETED -> IN_PROGRESS
```

should be rejected.

Use explicit allowed transitions.

---

## 42.4 Distributed Correlation ID

Propagate:

```text
correlation_id
saga_id
order_id
```

through:

- API
- Celery task
- HTTP request
- message
- logs

---

## 42.5 Dead-Letter / Manual Recovery

After repeated failures:

```text
Retry 1
Retry 2
Retry 3
    |
    v
Dead Letter / Manual Recovery
```

An operations dashboard should expose:

```text
Saga ID
Order ID
Current Step
Failure
Attempts
Last Error
Last Updated
```

---

## 42.6 Timeouts

Every Saga should have reasonable timeouts.

For example:

```text
Payment timeout = 5 minutes
Delivery timeout = 10 minutes
Entire Saga timeout = 30 minutes
```

The exact values depend on the business.

---

## 42.7 Monitoring

Useful metrics include:

```text
saga_started_total
saga_completed_total
saga_failed_total
saga_compensation_total
saga_manual_intervention_total
saga_step_retry_total
saga_duration_seconds
```

Alert on:

```text
Large number of failed Sagas
Long-running Sagas
Repeated compensation failures
Payment charged but order not confirmed
Inventory reserved for cancelled orders
```

---

# 43. Final Mental Model

The easiest way to remember Saga is:

```text
             BUSINESS TRANSACTION
                      |
          +-----------+-----------+
          |                       |
      Forward path           Compensation
          |                       |
          v                       v
    Reserve Stock           Release Stock
          |                       |
          v                       v
    Charge Payment           Refund Payment
          |                       |
          v                       v
    Create Delivery          Cancel Delivery
          |
          v
      Confirm Order
```

Saga does not make multiple databases behave like one transactional database.

Instead:

> **Saga breaks a distributed business transaction into local transactions and uses orchestration/events, retries, idempotency, and compensating actions to bring the system to a valid business state when failures occur.**

For a Django + Celery implementation, the core production architecture is:

```text
Django
  |
  +-- Local DB Transaction
  |
  +-- Saga State
  |
  +-- Celery
  |
  +-- Message Broker
  |
  +-- Idempotent Service Operations
  |
  +-- Compensation
  |
  +-- Recovery Worker
  |
  +-- Transactional Outbox
  |
  +-- Monitoring
```

The most important design principle is:

```text
Saga
=
Durable Workflow State
+
Local Transactions
+
Idempotency
+
Retries
+
Compensation
+
Recovery
```
