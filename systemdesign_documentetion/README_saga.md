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
8. [Consistency Model and Trade-offs](#8-consistency-model-and-trade-offs)
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
24. [Failure Example (Narrative)](#24-failure-example-narrative)
25. [Django Project Structure](#25-django-project-structure)
26. [Error Classification: Transient vs Business](#26-error-classification-transient-vs-business)
27. [Models](#27-models)
28. [Local Transactions and Idempotent Service Functions](#28-local-transactions-and-idempotent-service-functions)
29. [Saga Orchestrator](#29-saga-orchestrator)
30. [Celery Tasks and Recovery Worker](#30-celery-tasks-and-recovery-worker)
31. [API Endpoint](#31-api-endpoint)
32. [Important Transaction Boundary](#32-important-transaction-boundary)
33. [End-to-End Success Example (All Steps)](#33-end-to-end-success-example-all-steps)
34. [End-to-End Failure Example: Delivery Fails at Step 3](#34-end-to-end-failure-example-delivery-fails-at-step-3)
35. [Failure at Any Step: What Gets Reversed](#35-failure-at-any-step-what-gets-reversed)
36. [Transient Failure: Retry and Resume Without Repeating Work](#36-transient-failure-retry-and-resume-without-repeating-work)
37. [Compensation Failure: Parking the Saga for a Human](#37-compensation-failure-parking-the-saga-for-a-human)
38. [Tests That Prove Each Scenario](#38-tests-that-prove-each-scenario)
39. [Recommended State Machine](#39-recommended-state-machine)
40. [Production Improvements](#40-production-improvements)
41. [Final Mental Model](#41-final-mental-model)

---

# Part I — Saga Pattern

# 1. What Is the Saga Pattern?

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

# 8. Consistency Model and Trade-offs

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

## 8.1 The Trade-offs in One Table

Choosing Saga is a trade, not a free upgrade. Be explicit about what is being given up.

| You give up | You get | What you must build to pay for it |
|---|---|---|
| Atomicity across services (one `ROLLBACK`) | Each service commits and scales independently | Compensating action for every step, and a plan for steps that cannot be compensated |
| Isolation (other transactions never see half-done work) | No distributed locks, no blocking across services | Semantic locks / pending states so readers know data is in flight (see 8.2) |
| Immediate consistency | Availability during partial outages, long-running workflows | Durable saga state, timeouts, a recovery worker, operator tooling |
| Simple error handling (an exception aborts everything) | Fine-grained retry policies per step | Transient-vs-permanent error classification, idempotency keys on every side effect |
| Easy local testing | Loose coupling between teams and services | Tests that inject failure at every step and assert the compensated end state |
| One place to look when debugging | Independent deployability | Correlation IDs across API, tasks, messages and logs |

If the right-hand column looks like more engineering than the problem deserves, the answer is usually a single database and `transaction.atomic()` (section 4).

---

## 8.2 Saga Has No Isolation

A database transaction gives isolation: other transactions do not see its uncommitted changes. A Saga is a sequence of **committed** local transactions, so every intermediate state is visible to everyone, immediately.

Concrete consequences in the order example:

```text
Saga A (order 1001)                  Another reader
---------------------------------    -----------------------------------------
Reserve 10 units  -> COMMIT
                                     Stock report reads available = 40
Charge ৳1,000     -> COMMIT
                                     Finance report counts ৳1,000 revenue
Create delivery   -> FAILS
Refund ৳1,000     -> COMMIT          (finance report is now wrong)
Release 10 units  -> COMMIT          (stock report is now wrong)
```

These are the classic anomalies: **dirty reads** (reading data another saga will undo), **lost updates** (two sagas update the same row without seeing each other), **non-repeatable reads** (the same query returns different results during one saga).

Known countermeasures, and which ones the implementation in Part II uses:

| Countermeasure | Idea | Used in Part II |
|---|---|---|
| Semantic lock | Mark the record as in-flight (`Order.status = PENDING`) so other code treats it as provisional | Yes: order stays `PENDING` until the last step |
| Commutative updates | Express changes as deltas (`available -= 10`) rather than absolute values, so interleaved sagas do not overwrite each other | Yes: inventory uses `-=` / `+=` under `select_for_update()` |
| Pessimistic view | Order the steps so the hardest-to-compensate step runs last | Partly: payment is after inventory; a business that finds refunds expensive would move payment after delivery scheduling |
| Reread value | Re-read and verify a value before overwriting it | Yes: `select_for_update()` then check before write |
| Version file | Record operations in order so out-of-order arrivals can be reconciled | No (not needed for this flow) |
| By value | Pick Saga for low-risk operations and a stricter mechanism for high-value ones | Business decision, not shown |

Reporting and read models should be designed knowing that `PENDING` rows and `RESERVED` stock are provisional.

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

## 11.2 Retry Only Transient Failures

The decorator shown at the start of this section, `autoretry_for=(Exception,)`, is a common mistake. It retries **every** failure, including ones that can never succeed:

```text
Card declined          -> retried 3 times with backoff, then compensation starts
Insufficient stock     -> retried 3 times with backoff, then compensation starts
Address not serviceable-> retried 3 times with backoff, then compensation starts
```

Each pointless retry keeps the customer's money charged and the stock reserved for longer, and it delays the refund.

Classify failures and retry only the transient class:

```python
@shared_task(
    bind=True,
    autoretry_for=(TransientError,),   # timeouts, 5xx, deadlocks
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def run_order_saga(self, saga_id):
    ...
```

Business failures (`BusinessError`) should skip retries entirely and go straight to compensation. Section 26 shows the exception hierarchy used in the implementation.

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
- [ ] Decide how readers are protected from the saga's intermediate state (semantic lock, pending status).

### Reliability

- [ ] Persist Saga state.
- [ ] Use idempotency keys.
- [ ] Classify each step's failures as transient (retry) or permanent (compensate now).
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

Everything in this part is one coherent, runnable example. The code was executed with Django 5.2 and Celery 5.6, and the walkthroughs in sections 33 to 37 are the real output of that code, not hand-written expectations. The tests in section 38 prove each scenario.

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

Celery executes the saga asynchronously:

```text
Django API
    |
    v
Create Order + Saga (one local transaction, Order DB)
    |
    v
Celery task: run_order_saga
    |
    +--> Reserve Inventory
    |
    +--> Charge Payment
    |
    +--> Create Delivery
    |
    +--> Confirm Order
```

For this documentation, the service operations are Django functions living in separate apps. In a real microservice environment, each call becomes an HTTP/gRPC command or a message-broker message, but the saga logic (state, idempotency keys, compensation order) does not change.

> **Simplification used here:** the example runs all apps against one database so it can be executed with `manage.py test`. Nothing in the saga code relies on that. No step is ever wrapped in a transaction together with another step, which is exactly the constraint that separate databases impose.

---

# 23. Business Workflow

The happy path:

```text
START
  |
  v
Create Order (PENDING)
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

The failure path (delivery fails):

```text
Create Order (PENDING)
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
Saga = FAILED (business state consistent)
```

Note that the order is created *before* the saga starts, so that the saga has an order ID to work with. Cancelling the order is therefore always the last compensating action.

---

# 24. Failure Example (Narrative)

Suppose customer `1001` buys:

```text
Product: Napa (product_id = 7)
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

Now the delivery service fails:

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

Sections 33 to 37 show this exact scenario, and the others, executed by code.

---

# 25. Django Project Structure

```text
project/
│
├── apps/
│   ├── orders/
│   │   ├── models.py        Order
│   │   ├── services.py      confirm_order, cancel_order
│   │   └── views.py         POST /orders  -> creates Order + Saga, enqueues task
│   │
│   ├── inventory/
│   │   ├── models.py        Inventory, Reservation
│   │   └── services.py      reserve_inventory, release_inventory
│   │
│   ├── payments/
│   │   ├── models.py        PaymentOperation
│   │   ├── gateway.py       thin wrapper around the payment provider SDK
│   │   └── services.py      charge_payment, refund_payment
│   │
│   ├── delivery/
│   │   ├── models.py        Delivery
│   │   └── services.py      create_delivery, cancel_delivery
│   │
│   └── saga/
│       ├── exceptions.py    TransientError, BusinessError
│       ├── models.py        Saga, SagaStep
│       ├── orchestrator.py  OrderSagaOrchestrator
│       ├── tasks.py         run_order_saga, recover_stuck_sagas
│       └── tests.py         success + failure-at-every-step tests
│
└── config/
    ├── celery.py
    └── settings.py
```

Each service app exposes a **forward action** and its **compensation** side by side in `services.py`. The saga app knows nothing about tables of other apps; it only calls those functions.

---

# 26. Error Classification: Transient vs Business

The single most common mistake in saga implementations is retrying everything. A declined card will not become accepted on the third attempt. Retrying it only delays the refund of whatever was already charged and keeps stock reserved for nothing.

So every step failure is classified before the orchestrator decides what to do:

```python
# apps/saga/exceptions.py


class SagaError(Exception):
    """Base class for errors raised by saga steps."""


class TransientError(SagaError):
    """
    The step might succeed if tried again.
    Examples: network timeout, provider returned 503, DB deadlock.
    The orchestrator retries these.
    """


class BusinessError(SagaError):
    """
    The step can never succeed with the same input.
    Examples: insufficient stock, card declined, address not serviceable.
    The orchestrator does NOT retry these; it compensates immediately.
    """
```

| Failure | Class | Orchestrator reaction |
|---|---|---|
| Payment provider returned 503 | `TransientError` | Retry with backoff, then compensate |
| Courier API timed out | `TransientError` | Retry with backoff, then compensate |
| Card declined | `BusinessError` | Compensate immediately |
| Insufficient stock | `BusinessError` | Compensate immediately |
| Address not serviceable | `BusinessError` | Compensate immediately |
| Unexpected `KeyError` (a bug) | plain `Exception` | Compensate immediately, alert |

---

# 27. Models

## 27.1 Order (Order Service)

```python
# apps/orders/models.py

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONFIRMED = "CONFIRMED"
        CANCELLED = "CANCELLED"

    customer_id = models.PositiveBigIntegerField()
    product_id = models.PositiveBigIntegerField()
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    cancel_reason = models.TextField(blank=True, default="")
```

## 27.2 Inventory and Reservation (Inventory Service)

```python
# apps/inventory/models.py

from django.db import models


class Inventory(models.Model):
    product_id = models.PositiveBigIntegerField(unique=True)
    available_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)


class Reservation(models.Model):
    """
    One row per processed reserve command.
    The unique idempotency_key is what makes a retried command harmless.
    """

    class Status(models.TextChoices):
        RESERVED = "RESERVED"
        RELEASED = "RELEASED"

    idempotency_key = models.CharField(max_length=255, unique=True)
    product_id = models.PositiveBigIntegerField()
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RESERVED,
    )
```

## 27.3 PaymentOperation (Payment Service)

```python
# apps/payments/models.py

from django.db import models


class PaymentOperation(models.Model):
    class Status(models.TextChoices):
        CHARGED = "CHARGED"
        REFUNDED = "REFUNDED"

    idempotency_key = models.CharField(max_length=255, unique=True)
    order_id = models.PositiveBigIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices)
    provider_reference = models.CharField(max_length=255)
```

## 27.4 Delivery (Delivery Service)

```python
# apps/delivery/models.py

from django.db import models


class Delivery(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED"
        CANCELLED = "CANCELLED"

    idempotency_key = models.CharField(max_length=255, unique=True)
    order_id = models.PositiveBigIntegerField()
    address = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
```

## 27.5 Saga and SagaStep (Saga state)

```python
# apps/saga/models.py

import uuid

from django.db import models


class Saga(models.Model):
    class Status(models.TextChoices):
        STARTED = "STARTED"                          # created, no step run yet
        IN_PROGRESS = "IN_PROGRESS"                  # forward steps running
        COMPLETED = "COMPLETED"                      # every forward step succeeded
        COMPENSATING = "COMPENSATING"                # a step failed, undoing earlier steps
        FAILED = "FAILED"                            # compensation finished, business state is consistent
        MANUAL_INTERVENTION = "MANUAL_INTERVENTION"  # compensation itself failed, a human must look

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    saga_type = models.CharField(max_length=100)
    order_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.STARTED)
    current_step = models.CharField(max_length=100, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def step_key(self, step_name: str) -> str:
        """Deterministic idempotency key: same saga + same step => same key, forever."""
        return f"{self.id}:{step_name}"


class SagaStep(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        COMPENSATING = "COMPENSATING"
        COMPENSATED = "COMPENSATED"
        COMPENSATION_FAILED = "COMPENSATION_FAILED"

    saga = models.ForeignKey(Saga, on_delete=models.CASCADE, related_name="steps")
    step_name = models.CharField(max_length=100)
    sequence = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["saga", "step_name"], name="uniq_saga_step"),
        ]
        ordering = ["sequence"]
```

Why these fields matter:

- `Saga.step_key()` produces the idempotency key `"{saga_id}:{step_name}"`. The same saga always sends the same key for the same step, so a retried command is recognised by the receiving service.
- `SagaStep.sequence` is what lets compensation run in **reverse** order. The orchestrator never relies on an in-memory list.
- `SagaStep` has `COMPENSATING`, `COMPENSATED` and `COMPENSATION_FAILED` states. Without them you cannot tell "refund never attempted" from "refund attempted and failed".
- `Saga.MANUAL_INTERVENTION` exists because a saga whose compensation failed is **not** finished. It is parked, visibly, for an operator.

---

# 28. Local Transactions and Idempotent Service Functions

Each service protects its own data with a normal Django transaction and makes both its forward action and its compensation idempotent.

## 28.1 Inventory

```python
# apps/inventory/services.py

from django.db import transaction

from apps.inventory.models import Inventory, Reservation
from apps.saga.exceptions import BusinessError


class InsufficientInventoryError(BusinessError):
    pass


def reserve_inventory(*, product_id: int, quantity: int, idempotency_key: str) -> Reservation:
    """Forward action. Local transaction on the Inventory DB only."""
    with transaction.atomic():
        existing = Reservation.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing  # duplicate command: return the earlier result

        inventory = Inventory.objects.select_for_update().get(product_id=product_id)
        if inventory.available_quantity < quantity:
            raise InsufficientInventoryError(
                f"product {product_id}: wanted {quantity}, available {inventory.available_quantity}"
            )

        inventory.available_quantity -= quantity
        inventory.reserved_quantity += quantity
        inventory.save(update_fields=["available_quantity", "reserved_quantity"])

        return Reservation.objects.create(
            idempotency_key=idempotency_key,
            product_id=product_id,
            quantity=quantity,
        )


def release_inventory(*, idempotency_key: str) -> None:
    """Compensation. Safe to call when nothing was reserved and safe to call twice."""
    with transaction.atomic():
        reservation = (
            Reservation.objects.select_for_update()
            .filter(idempotency_key=idempotency_key)
            .first()
        )
        if reservation is None or reservation.status == Reservation.Status.RELEASED:
            return  # nothing to undo (never reserved, or already released)

        inventory = Inventory.objects.select_for_update().get(product_id=reservation.product_id)
        inventory.available_quantity += reservation.quantity
        inventory.reserved_quantity -= reservation.quantity
        inventory.save(update_fields=["available_quantity", "reserved_quantity"])

        reservation.status = Reservation.Status.RELEASED
        reservation.save(update_fields=["status"])
```

The reservation row with a unique `idempotency_key` is the idempotency mechanism. A duplicate reserve command finds the row and returns it. A release for a reservation that never happened, or that was already released, is a no-op. That is what makes compensation safe to retry.

## 28.2 Payments

```python
# apps/payments/gateway.py
#
# Stand-in for a real payment provider SDK (Stripe, SSLCommerz, bKash, ...).
# Real providers accept an idempotency key too; always pass it through.

import uuid
from decimal import Decimal

from apps.saga.exceptions import BusinessError, TransientError


class PaymentDeclinedError(BusinessError):
    pass


class PaymentGatewayUnavailable(TransientError):
    pass


def charge(*, amount: Decimal, idempotency_key: str) -> str:
    """Returns the provider's charge reference."""
    return f"ch_{uuid.uuid4().hex[:12]}"


def refund(*, provider_reference: str, idempotency_key: str) -> str:
    """Returns the provider's refund reference."""
    return f"re_{uuid.uuid4().hex[:12]}"
```

```python
# apps/payments/services.py

from decimal import Decimal

from django.db import transaction

from apps.payments import gateway
from apps.payments.models import PaymentOperation


def charge_payment(*, order_id: int, amount: Decimal, idempotency_key: str) -> PaymentOperation:
    """Forward action. The external call happens OUTSIDE the DB transaction."""
    existing = PaymentOperation.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing  # retry after a lost response: do not charge again

    reference = gateway.charge(amount=amount, idempotency_key=idempotency_key)

    with transaction.atomic():
        return PaymentOperation.objects.create(
            idempotency_key=idempotency_key,
            order_id=order_id,
            amount=amount,
            status=PaymentOperation.Status.CHARGED,
            provider_reference=reference,
        )


def refund_payment(*, idempotency_key: str) -> None:
    """Compensation. No-op if the charge never happened or was already refunded."""
    operation = PaymentOperation.objects.filter(idempotency_key=idempotency_key).first()
    if operation is None or operation.status == PaymentOperation.Status.REFUNDED:
        return

    gateway.refund(
        provider_reference=operation.provider_reference,
        idempotency_key=f"{idempotency_key}:refund",
    )

    with transaction.atomic():
        PaymentOperation.objects.filter(id=operation.id).update(
            status=PaymentOperation.Status.REFUNDED,
        )
```

Two things to notice:

1. The external provider call is made **outside** `transaction.atomic()`. Holding a database row lock while waiting on a network call is a classic way to exhaust the connection pool.
2. The refund gets its own key, `"{key}:refund"`, so the provider can de-duplicate refunds too.

If the response to `gateway.charge()` is lost after the provider accepted it, the retry calls the provider with the same idempotency key and the provider returns the original charge instead of a new one. That is why the key must be passed through to the provider, not only stored locally.

## 28.3 Delivery

```python
# apps/delivery/services.py

from django.db import transaction

from apps.delivery.models import Delivery
from apps.saga.exceptions import BusinessError, TransientError


class AddressNotServiceableError(BusinessError):
    pass


class CourierApiTimeout(TransientError):
    pass


def create_delivery(*, order_id: int, address: str, idempotency_key: str) -> Delivery:
    """Forward action."""
    with transaction.atomic():
        existing = Delivery.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

        if not address.strip():
            raise AddressNotServiceableError(f"order {order_id}: empty shipping address")

        return Delivery.objects.create(
            idempotency_key=idempotency_key,
            order_id=order_id,
            address=address,
        )


def cancel_delivery(*, idempotency_key: str) -> None:
    """Compensation."""
    Delivery.objects.filter(idempotency_key=idempotency_key).exclude(
        status=Delivery.Status.CANCELLED
    ).update(status=Delivery.Status.CANCELLED)
```

## 28.4 Orders

```python
# apps/orders/services.py

from django.db import transaction

from apps.orders.models import Order


def confirm_order(*, order_id: int) -> Order:
    """Forward action for the last step. Idempotent: confirming twice is a no-op."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        if order.status == Order.Status.CONFIRMED:
            return order
        if order.status == Order.Status.CANCELLED:
            raise ValueError(f"Order {order_id} is cancelled and cannot be confirmed")
        order.status = Order.Status.CONFIRMED
        order.save(update_fields=["status"])
        return order


def cancel_order(*, order_id: int, reason: str) -> Order:
    """Compensation for order creation. Idempotent: cancelling twice is a no-op."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        if order.status == Order.Status.CANCELLED:
            return order
        order.status = Order.Status.CANCELLED
        order.cancel_reason = reason
        order.save(update_fields=["status", "cancel_reason"])
        return order
```

---

# 29. Saga Orchestrator

The orchestrator is a table of steps plus a loop. Each `Step` pairs a forward action with its compensation (or `None` when there is nothing to undo).

```python
# apps/saga/orchestrator.py

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from django.db import transaction
from django.utils import timezone

from apps.delivery.services import cancel_delivery, create_delivery
from apps.inventory.services import release_inventory, reserve_inventory
from apps.orders.models import Order
from apps.orders.services import cancel_order, confirm_order
from apps.payments.services import charge_payment, refund_payment
from apps.saga.exceptions import TransientError
from apps.saga.models import Saga, SagaStep

logger = logging.getLogger(__name__)

MAX_ATTEMPTS_PER_STEP = 3


@dataclass(frozen=True)
class Step:
    name: str
    action: Callable[["OrderSagaOrchestrator"], None]
    compensation: Optional[Callable[["OrderSagaOrchestrator"], None]]


class OrderSagaOrchestrator:
    """
    Drives one order saga from start to COMPLETED, or to FAILED via compensation.

    Rules this class follows:
      * every step's result is persisted in SagaStep before the next step starts
      * a step that already SUCCEEDED is skipped, so the saga can be re-run after a crash
      * BusinessError  -> compensate immediately (retrying cannot help)
      * TransientError -> retry up to MAX_ATTEMPTS_PER_STEP, then compensate
      * compensations run in reverse order of the steps that actually succeeded
      * a failed compensation parks the saga in MANUAL_INTERVENTION, it is never "forgotten"
    """

    # ---- forward actions ----------------------------------------------------

    def _reserve(self):
        reserve_inventory(
            product_id=self.order.product_id,
            quantity=self.order.quantity,
            idempotency_key=self.saga.step_key("RESERVE_INVENTORY"),
        )

    def _charge(self):
        charge_payment(
            order_id=self.order.id,
            amount=self.order.total_amount,
            idempotency_key=self.saga.step_key("CHARGE_PAYMENT"),
        )

    def _deliver(self):
        create_delivery(
            order_id=self.order.id,
            address=self.order.shipping_address,
            idempotency_key=self.saga.step_key("CREATE_DELIVERY"),
        )

    def _confirm(self):
        confirm_order(order_id=self.order.id)

    # ---- compensations ------------------------------------------------------

    def _release(self):
        release_inventory(idempotency_key=self.saga.step_key("RESERVE_INVENTORY"))

    def _refund(self):
        refund_payment(idempotency_key=self.saga.step_key("CHARGE_PAYMENT"))

    def _cancel_delivery(self):
        cancel_delivery(idempotency_key=self.saga.step_key("CREATE_DELIVERY"))

    # ---- the workflow definition -------------------------------------------

    STEPS = [
        Step("RESERVE_INVENTORY", _reserve, _release),
        Step("CHARGE_PAYMENT", _charge, _refund),
        Step("CREATE_DELIVERY", _deliver, _cancel_delivery),
        Step("CONFIRM_ORDER", _confirm, None),  # last step, nothing after it can fail
    ]

    def __init__(self, saga_id):
        self.saga = Saga.objects.get(id=saga_id)
        self.order = Order.objects.get(id=self.saga.order_id)

    # ---- public entry point -------------------------------------------------

    def run(self) -> Saga:
        if not self._claim():
            return self.saga  # finished already, or in a terminal state

        for sequence, step in enumerate(self.STEPS, start=1):
            record = self._get_or_create_record(step, sequence)
            if record.status == SagaStep.Status.SUCCESS:
                continue  # resumed after a crash or retry: this step is already done

            self._mark_step_running(record)
            try:
                step.action(self)
            except TransientError as exc:
                self._mark_step_failed(record, exc)
                if record.attempt_count < MAX_ATTEMPTS_PER_STEP:
                    logger.warning(
                        "saga=%s step=%s attempt=%s transient failure, will retry: %s",
                        self.saga.id, step.name, record.attempt_count, exc,
                    )
                    raise  # Celery re-queues the task; completed steps are skipped on re-run
                self._compensate(reason=f"{step.name} failed after {record.attempt_count} attempts: {exc}")
                return self.saga
            except Exception as exc:  # BusinessError or an unexpected bug: cannot proceed
                self._mark_step_failed(record, exc)
                self._compensate(reason=f"{step.name} failed: {exc}")
                return self.saga

            self._mark_step_success(record)

        self._set_saga_status(Saga.Status.COMPLETED, current_step="")
        return self.saga

    # ---- compensation -------------------------------------------------------

    def _compensate(self, *, reason: str) -> None:
        self._set_saga_status(Saga.Status.COMPENSATING, error=reason)

        succeeded = (
            SagaStep.objects.filter(saga=self.saga, status=SagaStep.Status.SUCCESS)
            .order_by("-sequence")  # reverse order: the last success is undone first
        )
        steps_by_name = {s.name: s for s in self.STEPS}

        for record in succeeded:
            step = steps_by_name[record.step_name]
            if step.compensation is None:
                continue

            self._set_step_status(record, SagaStep.Status.COMPENSATING)
            try:
                step.compensation(self)
            except Exception as exc:
                # Do NOT mark the saga FAILED here. Money or stock may still be held.
                self._set_step_status(record, SagaStep.Status.COMPENSATION_FAILED, error=str(exc))
                self._set_saga_status(
                    Saga.Status.MANUAL_INTERVENTION,
                    error=f"{reason}; then compensation of {record.step_name} failed: {exc}",
                )
                logger.error("saga=%s needs manual intervention: %s", self.saga.id, exc)
                return
            self._set_step_status(record, SagaStep.Status.COMPENSATED)

        # The order itself was created before the saga began; cancelling it is the final undo.
        cancel_order(order_id=self.order.id, reason=reason)
        self._set_saga_status(Saga.Status.FAILED, error=reason, current_step="")

    # ---- persistence helpers ------------------------------------------------

    def _claim(self) -> bool:
        """Lock the saga row and move it to IN_PROGRESS. Returns False if it must not run."""
        with transaction.atomic():
            saga = Saga.objects.select_for_update().get(id=self.saga.id)
            if saga.status not in (Saga.Status.STARTED, Saga.Status.IN_PROGRESS):
                return False
            saga.status = Saga.Status.IN_PROGRESS
            saga.save(update_fields=["status", "updated_at"])
            self.saga = saga
            return True

    def _get_or_create_record(self, step: Step, sequence: int) -> SagaStep:
        record, _ = SagaStep.objects.get_or_create(
            saga=self.saga,
            step_name=step.name,
            defaults={"sequence": sequence},
        )
        return record

    def _mark_step_running(self, record: SagaStep) -> None:
        record.status = SagaStep.Status.RUNNING
        record.attempt_count += 1
        record.started_at = record.started_at or timezone.now()
        record.save(update_fields=["status", "attempt_count", "started_at"])
        self._set_saga_status(Saga.Status.IN_PROGRESS, current_step=record.step_name)

    def _mark_step_success(self, record: SagaStep) -> None:
        self._set_step_status(record, SagaStep.Status.SUCCESS)

    def _mark_step_failed(self, record: SagaStep, exc: Exception) -> None:
        self._set_step_status(record, SagaStep.Status.FAILED, error=str(exc))

    def _set_step_status(self, record: SagaStep, status: str, *, error: str = "") -> None:
        record.status = status
        record.error_message = error
        if status in (SagaStep.Status.SUCCESS, SagaStep.Status.COMPENSATED):
            record.completed_at = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at"])

    def _set_saga_status(
        self,
        status: str,
        *,
        error: Optional[str] = None,
        current_step: Optional[str] = None,
    ) -> None:
        self.saga.status = status
        fields = ["status", "updated_at"]
        if error is not None:
            self.saga.error_message = error
            fields.append("error_message")
        if current_step is not None:
            self.saga.current_step = current_step
            fields.append("current_step")
        self.saga.save(update_fields=fields)
```

How it behaves, in order:

1. **Claim.** Lock the `Saga` row, verify it is `STARTED` or `IN_PROGRESS`, and set it to `IN_PROGRESS`. Any other status (completed, compensating, failed, manual) means this run must do nothing. This is the guard against the same saga being executed twice by two workers or by a duplicate message.
2. **Walk the steps.** For each step, get or create its `SagaStep` row. A row already in `SUCCESS` is skipped. That single `continue` is what makes crash recovery work: re-running the saga after a crash resumes at the first unfinished step.
3. **Classify failures.** `TransientError` is re-raised so Celery retries, but only until `MAX_ATTEMPTS_PER_STEP`. `BusinessError`, or any unexpected exception, goes straight to compensation.
4. **Compensate in reverse.** Query the `SUCCESS` steps from the database ordered by `-sequence` and run each compensation. A step whose compensation fails is marked `COMPENSATION_FAILED`, the saga is set to `MANUAL_INTERVENTION`, and the loop stops. Steps earlier in the sequence are deliberately left untouched so an operator sees exactly what is still held.
5. **Finish.** If all compensations succeed, cancel the order and mark the saga `FAILED`. `FAILED` here means "business outcome: order not placed, and the system is consistent". It is a clean terminal state.

### Why `CONFIRM_ORDER` has no compensation

It is the last step and it is a local write in the Order service. If it fails the order is still `PENDING` and the earlier steps are compensated as usual. There is never a situation where "confirmed" has to be undone by this saga.

---

# 30. Celery Tasks and Recovery Worker

```python
# apps/saga/tasks.py

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.saga.exceptions import TransientError
from apps.saga.models import Saga
from apps.saga.orchestrator import OrderSagaOrchestrator


@shared_task(
    bind=True,
    autoretry_for=(TransientError,),   # only transient failures are retried
    retry_backoff=True,                # 1s, 2s, 4s, ...
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def run_order_saga(self, saga_id: str):
    OrderSagaOrchestrator(saga_id).run()


@shared_task
def recover_stuck_sagas():
    """
    Celery beat job. A saga that stayed IN_PROGRESS too long probably lost its worker.
    Re-running it is safe: SUCCESS steps are skipped and every action is idempotent.
    """
    cutoff = timezone.now() - timedelta(minutes=10)
    stuck = Saga.objects.filter(status=Saga.Status.IN_PROGRESS, updated_at__lt=cutoff)
    for saga in stuck:
        run_order_saga.delay(str(saga.id))
```

Important detail: `autoretry_for` lists only `TransientError`. If it listed `Exception`, a declined card would be retried five times with backoff before compensation even began.

The recovery job re-enqueues the same task. It does not need special "resume" logic because the orchestrator already skips `SUCCESS` steps and every service function is idempotent.

---

# 31. API Endpoint

```python
# apps/orders/views.py

import json
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.orders.models import Order
from apps.saga.models import Saga
from apps.saga.tasks import run_order_saga


@require_POST
def create_order(request):
    payload = json.loads(request.body)

    # Order + Saga live in the same (Order service) DB, so one local transaction is correct here.
    with transaction.atomic():
        order = Order.objects.create(
            customer_id=request.user.id,
            product_id=payload["product_id"],
            quantity=payload["quantity"],
            total_amount=Decimal(payload["total_amount"]),
            shipping_address=payload["shipping_address"],
        )
        saga = Saga.objects.create(saga_type="ORDER_PLACEMENT", order_id=order.id)
        # Enqueue only after COMMIT, otherwise the worker may not see the rows yet.
        transaction.on_commit(lambda: run_order_saga.delay(str(saga.id)))

    return JsonResponse(
        {"order_id": order.id, "saga_id": str(saga.id), "status": "PROCESSING"},
        status=202,
    )
```

Two details that are easy to get wrong:

- `Order` and `Saga` are created in **one** `transaction.atomic()`. That is correct, because they live in the same database (the Order service owns the saga state).
- The Celery task is enqueued with `transaction.on_commit`. Without it, a fast worker can pick up the task before the API's transaction commits and fail with `Saga.DoesNotExist`.

The API returns `202 Accepted` because the business workflow completes asynchronously. The client polls `GET /orders/{id}` or receives a notification.

---

# 32. Important Transaction Boundary

Do not do this:

```python
with transaction.atomic():
    reserve_inventory()
    charge_payment()
    create_delivery()
```

if these are independent services. Even in the single-database demo, the orchestrator never does it. Each step commits on its own:

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

The Saga coordinates those transactions; it does not merge them.

---

# 33. End-to-End Success Example (All Steps)

Customer `1001` orders 10 units of product `7` for ৳1,000. Stock is 50.

```text
POST /orders
{"product_id": 7, "quantity": 10, "total_amount": "1000.00",
 "shipping_address": "House 12, Road 5, Dhanmondi, Dhaka"}

202 Accepted
{"order_id": 1, "saga_id": "4f9c...", "status": "PROCESSING"}
```

The worker runs `run_order_saga("4f9c...")`. State after every persisted transition:

| Transition | Order | Inventory (avail / reserved) | Payment | Delivery | Saga |
|---|---|---|---|---|---|
| start | PENDING | 50 / 0 | NOT_CHARGED | NOT_CREATED | STARTED |
| RESERVE_INVENTORY → SUCCESS | PENDING | 40 / 10 | NOT_CHARGED | NOT_CREATED | IN_PROGRESS |
| CHARGE_PAYMENT → SUCCESS | PENDING | 40 / 10 | CHARGED | NOT_CREATED | IN_PROGRESS |
| CREATE_DELIVERY → SUCCESS | PENDING | 40 / 10 | CHARGED | SCHEDULED | IN_PROGRESS |
| CONFIRM_ORDER → SUCCESS | CONFIRMED | 40 / 10 | CHARGED | SCHEDULED | IN_PROGRESS |
| end | CONFIRMED | 40 / 10 | CHARGED | SCHEDULED | COMPLETED |

`SagaStep` rows at the end:

```text
1. RESERVE_INVENTORY  SUCCESS   attempts=1
2. CHARGE_PAYMENT     SUCCESS   attempts=1
3. CREATE_DELIVERY    SUCCESS   attempts=1
4. CONFIRM_ORDER      SUCCESS   attempts=1
```

Every row in every service carries the same saga ID in its idempotency key:

```text
Reservation.idempotency_key      = 4f9c...:RESERVE_INVENTORY
PaymentOperation.idempotency_key = 4f9c...:CHARGE_PAYMENT
Delivery.idempotency_key         = 4f9c...:CREATE_DELIVERY
```

That is what lets an operator trace one business transaction across four services.

---

# 34. End-to-End Failure Example: Delivery Fails at Step 3

Same order. This time the courier rejects the address.

| Transition | Order | Inventory (avail / reserved) | Payment | Delivery | Saga |
|---|---|---|---|---|---|
| start | PENDING | 50 / 0 | NOT_CHARGED | NOT_CREATED | STARTED |
| RESERVE_INVENTORY → SUCCESS | PENDING | 40 / 10 | NOT_CHARGED | NOT_CREATED | IN_PROGRESS |
| CHARGE_PAYMENT → SUCCESS | PENDING | 40 / 10 | CHARGED | NOT_CREATED | IN_PROGRESS |
| **CREATE_DELIVERY → FAILED** | PENDING | 40 / 10 | CHARGED | NOT_CREATED | IN_PROGRESS |
| CHARGE_PAYMENT → COMPENSATING | PENDING | 40 / 10 | CHARGED | NOT_CREATED | COMPENSATING |
| CHARGE_PAYMENT → COMPENSATED | PENDING | 40 / 10 | **REFUNDED** | NOT_CREATED | COMPENSATING |
| RESERVE_INVENTORY → COMPENSATING | PENDING | 40 / 10 | REFUNDED | NOT_CREATED | COMPENSATING |
| RESERVE_INVENTORY → COMPENSATED | PENDING | **50 / 0** | REFUNDED | NOT_CREATED | COMPENSATING |
| cancel_order | **CANCELLED** | 50 / 0 | REFUNDED | NOT_CREATED | COMPENSATING |
| end | CANCELLED | 50 / 0 | REFUNDED | NOT_CREATED | **FAILED** |

Read the table top to bottom and you can see the saga "reverse the transaction": the steps were done in the order *inventory, payment* and are undone in the order *payment, inventory*. The failed step itself, `CREATE_DELIVERY`, is not compensated because it never produced anything.

`SagaStep` rows at the end:

```text
1. RESERVE_INVENTORY  COMPENSATED   attempts=1
2. CHARGE_PAYMENT     COMPENSATED   attempts=1
3. CREATE_DELIVERY    FAILED        attempts=1   error='courier does not serve this area'
```

And the saga row:

```text
status        = FAILED
current_step  = ''
error_message = 'CREATE_DELIVERY failed: courier does not serve this area'
```

The order row also keeps the reason:

```text
Order.status        = CANCELLED
Order.cancel_reason = 'CREATE_DELIVERY failed: courier does not serve this area'
```

Compare the two tables: for roughly 100 ms the customer was charged for an order that will never ship. That window is the "temporary inconsistency" the Saga pattern accepts. The business must be comfortable with it; see section 8.

---

# 35. Failure at Any Step: What Gets Reversed

Because compensation is driven by the persisted `SUCCESS` rows, the orchestrator does the right thing no matter where the failure happens. These are the actual results of running the code with the failure injected at each step.

| Fails at | Steps that had succeeded | Compensations that run (in order) | Final: Order | Inventory | Payment | Saga |
|---|---|---|---|---|---|---|
| 1. RESERVE_INVENTORY (only 3 in stock) | none | cancel_order | CANCELLED | 3 / 0 (untouched) | NOT_CHARGED | FAILED |
| 2. CHARGE_PAYMENT (card declined) | RESERVE_INVENTORY | release_inventory → cancel_order | CANCELLED | 50 / 0 | NOT_CHARGED | FAILED |
| 3. CREATE_DELIVERY (address rejected) | RESERVE_INVENTORY, CHARGE_PAYMENT | refund_payment → release_inventory → cancel_order | CANCELLED | 50 / 0 | REFUNDED | FAILED |
| 4. CONFIRM_ORDER (unexpected error) | RESERVE_INVENTORY, CHARGE_PAYMENT, CREATE_DELIVERY | cancel_delivery → refund_payment → release_inventory → cancel_order | CANCELLED | 50 / 0 | REFUNDED | FAILED |

Trace for the step 2 case, to show the shorter undo chain:

```text
(start)                                  order=PENDING   avail=50 reserved=0  payment=NOT_CHARGED saga=STARTED
RESERVE_INVENTORY  -> SUCCESS            order=PENDING   avail=40 reserved=10 payment=NOT_CHARGED saga=IN_PROGRESS
CHARGE_PAYMENT     -> FAILED             order=PENDING   avail=40 reserved=10 payment=NOT_CHARGED saga=IN_PROGRESS
RESERVE_INVENTORY  -> COMPENSATING       order=PENDING   avail=40 reserved=10 payment=NOT_CHARGED saga=COMPENSATING
RESERVE_INVENTORY  -> COMPENSATED        order=PENDING   avail=50 reserved=0  payment=NOT_CHARGED saga=COMPENSATING
(end)                                    order=CANCELLED avail=50 reserved=0  payment=NOT_CHARGED saga=FAILED
```

Nothing is refunded because nothing was charged. The orchestrator does not need a special case for that; `CHARGE_PAYMENT` simply has no `SUCCESS` row.

---

# 36. Transient Failure: Retry and Resume Without Repeating Work

The payment provider returns 503 on the first attempt and succeeds on the second.

```text
Attempt 1 (Celery delivery #1)
  RESERVE_INVENTORY  -> SUCCESS
  CHARGE_PAYMENT     -> RUNNING  (attempt_count = 1)
  CHARGE_PAYMENT     -> FAILED   '503 from provider'
  raise TransientError            <- Celery schedules a retry with backoff

Attempt 2 (Celery delivery #2, a few seconds later)
  claim saga (still IN_PROGRESS, allowed)
  RESERVE_INVENTORY  already SUCCESS -> skipped
  CHARGE_PAYMENT     -> RUNNING  (attempt_count = 2)
  CHARGE_PAYMENT     -> SUCCESS
  CREATE_DELIVERY    -> SUCCESS
  CONFIRM_ORDER      -> SUCCESS
  saga -> COMPLETED
```

What the test for this asserts:

- exactly one `Reservation` row exists (inventory was not reserved twice),
- the provider saw the **same** idempotency key on both attempts,
- `CHARGE_PAYMENT.attempt_count == 2`.

If the step keeps failing, the third attempt gives up and compensates:

```text
Attempt 3
  CREATE_DELIVERY    -> FAILED  (attempt_count = 3 = MAX_ATTEMPTS_PER_STEP)
  compensate: refund_payment -> release_inventory -> cancel_order
  saga -> FAILED  error='CREATE_DELIVERY failed after 3 attempts: timeout'
```

---

# 37. Compensation Failure: Parking the Saga for a Human

Delivery fails, so the saga starts refunding. The refund call itself fails with a 503.

| Transition | Order | Inventory | Payment | Saga |
|---|---|---|---|---|
| RESERVE_INVENTORY → SUCCESS | PENDING | 40 / 10 | NOT_CHARGED | IN_PROGRESS |
| CHARGE_PAYMENT → SUCCESS | PENDING | 40 / 10 | CHARGED | IN_PROGRESS |
| CREATE_DELIVERY → FAILED | PENDING | 40 / 10 | CHARGED | IN_PROGRESS |
| CHARGE_PAYMENT → COMPENSATING | PENDING | 40 / 10 | CHARGED | COMPENSATING |
| **CHARGE_PAYMENT → COMPENSATION_FAILED** | PENDING | 40 / 10 | CHARGED | COMPENSATING |
| end | **PENDING** | **40 / 10** | **CHARGED** | **MANUAL_INTERVENTION** |

`SagaStep` rows:

```text
1. RESERVE_INVENTORY  SUCCESS               <- release was never attempted, on purpose
2. CHARGE_PAYMENT     COMPENSATION_FAILED   error='provider returned 503'
3. CREATE_DELIVERY    FAILED                error='courier does not serve this area'
```

```text
saga.error_message =
  'CREATE_DELIVERY failed: courier does not serve this area;
   then compensation of CHARGE_PAYMENT failed: provider returned 503'
```

Three deliberate choices here:

1. The saga is **not** marked `FAILED`. `FAILED` promises a consistent state, and the customer's money is still held.
2. The order is **not** cancelled yet. Cancelling it would tell the customer "nothing happened" while ৳1,000 is still charged.
3. Earlier steps are **not** compensated. Inventory stays reserved so that, when the refund is eventually retried, the undo still happens in the right order.

An operator dashboard (or a scheduled job) queries `Saga.objects.filter(status=MANUAL_INTERVENTION)`. Resolving the case means retrying the compensation, which is safe because every compensation is idempotent, then letting the orchestrator finish.

---

# 38. Tests That Prove Each Scenario

Every behaviour above is asserted by a test: success, failure at each of the four steps, transient retry-and-resume, retry exhaustion, compensation failure, and duplicate execution. Each failure is injected with `unittest.mock`, which is also how you would test a real implementation without calling a real payment provider.

```python
# apps/saga/tests.py

from decimal import Decimal
from unittest import mock

from django.test import TestCase

from apps.delivery.models import Delivery
from apps.delivery.services import AddressNotServiceableError, CourierApiTimeout
from apps.inventory.models import Inventory, Reservation
from apps.orders.models import Order
from apps.payments import gateway
from apps.payments.gateway import PaymentDeclinedError, PaymentGatewayUnavailable
from apps.payments.models import PaymentOperation
from apps.saga.exceptions import TransientError
from apps.saga.models import Saga, SagaStep
from apps.saga.orchestrator import OrderSagaOrchestrator


class OrderSagaTests(TestCase):
    def setUp(self):
        Inventory.objects.create(product_id=7, available_quantity=50, reserved_quantity=0)
        self.order = Order.objects.create(
            customer_id=1001,
            product_id=7,
            quantity=10,
            total_amount=Decimal("1000.00"),
            shipping_address="House 12, Road 5, Dhanmondi, Dhaka",
        )
        self.saga = Saga.objects.create(saga_type="ORDER_PLACEMENT", order_id=self.order.id)

    def snapshot(self):
        inv = Inventory.objects.get(product_id=7)
        pay = PaymentOperation.objects.filter(order_id=self.order.id).first()
        dlv = Delivery.objects.filter(order_id=self.order.id).first()
        self.order.refresh_from_db()
        self.saga.refresh_from_db()
        return {
            "order": self.order.status,
            "available": inv.available_quantity,
            "reserved": inv.reserved_quantity,
            "payment": pay.status if pay else "NOT_CHARGED",
            "delivery": dlv.status if dlv else "NOT_CREATED",
            "saga": self.saga.status,
        }

    def steps(self):
        return list(SagaStep.objects.filter(saga=self.saga).values_list("step_name", "status"))

    # ---- success ------------------------------------------------------------

    def test_all_steps_succeed(self):
        OrderSagaOrchestrator(self.saga.id).run()

        self.assertEqual(self.snapshot(), {
            "order": "CONFIRMED",
            "available": 40,
            "reserved": 10,
            "payment": "CHARGED",
            "delivery": "SCHEDULED",
            "saga": "COMPLETED",
        })
        self.assertEqual(self.steps(), [
            ("RESERVE_INVENTORY", "SUCCESS"),
            ("CHARGE_PAYMENT", "SUCCESS"),
            ("CREATE_DELIVERY", "SUCCESS"),
            ("CONFIRM_ORDER", "SUCCESS"),
        ])

    # ---- failure at each step ------------------------------------------------

    def test_failure_at_step_1_insufficient_stock(self):
        Inventory.objects.filter(product_id=7).update(available_quantity=3)

        OrderSagaOrchestrator(self.saga.id).run()

        self.assertEqual(self.snapshot(), {
            "order": "CANCELLED",
            "available": 3,
            "reserved": 0,
            "payment": "NOT_CHARGED",
            "delivery": "NOT_CREATED",
            "saga": "FAILED",
        })
        self.assertEqual(self.steps(), [("RESERVE_INVENTORY", "FAILED")])

    def test_failure_at_step_2_card_declined(self):
        with mock.patch.object(gateway, "charge", side_effect=PaymentDeclinedError("card declined")):
            OrderSagaOrchestrator(self.saga.id).run()

        self.assertEqual(self.snapshot(), {
            "order": "CANCELLED",
            "available": 50,
            "reserved": 0,
            "payment": "NOT_CHARGED",
            "delivery": "NOT_CREATED",
            "saga": "FAILED",
        })
        self.assertEqual(self.steps(), [
            ("RESERVE_INVENTORY", "COMPENSATED"),
            ("CHARGE_PAYMENT", "FAILED"),
        ])
        self.assertEqual(Reservation.objects.get().status, "RELEASED")

    def test_failure_at_step_3_delivery_rejected(self):
        with mock.patch(
            "apps.saga.orchestrator.create_delivery",
            side_effect=AddressNotServiceableError("courier does not serve this area"),
        ):
            OrderSagaOrchestrator(self.saga.id).run()

        self.assertEqual(self.snapshot(), {
            "order": "CANCELLED",
            "available": 50,
            "reserved": 0,
            "payment": "REFUNDED",
            "delivery": "NOT_CREATED",
            "saga": "FAILED",
        })
        self.assertEqual(self.steps(), [
            ("RESERVE_INVENTORY", "COMPENSATED"),
            ("CHARGE_PAYMENT", "COMPENSATED"),
            ("CREATE_DELIVERY", "FAILED"),
        ])
        self.saga.refresh_from_db()
        self.assertIn("CREATE_DELIVERY failed", self.saga.error_message)

    def test_failure_at_step_4_unexpected_bug(self):
        with mock.patch("apps.saga.orchestrator.confirm_order", side_effect=KeyError("bug")):
            OrderSagaOrchestrator(self.saga.id).run()

        self.assertEqual(self.snapshot(), {
            "order": "CANCELLED",
            "available": 50,
            "reserved": 0,
            "payment": "REFUNDED",
            "delivery": "CANCELLED",
            "saga": "FAILED",
        })
        self.assertEqual(self.steps(), [
            ("RESERVE_INVENTORY", "COMPENSATED"),
            ("CHARGE_PAYMENT", "COMPENSATED"),
            ("CREATE_DELIVERY", "COMPENSATED"),
            ("CONFIRM_ORDER", "FAILED"),
        ])

    # ---- transient failure: retry, then resume without repeating work -------

    def test_transient_failure_is_retried_and_completed_steps_are_not_repeated(self):
        charge_calls = []
        real_charge = gateway.charge

        def flaky_charge(**kwargs):
            charge_calls.append(kwargs["idempotency_key"])
            if len(charge_calls) == 1:
                raise PaymentGatewayUnavailable("503 from provider")
            return real_charge(**kwargs)

        with mock.patch.object(gateway, "charge", side_effect=flaky_charge):
            with self.assertRaises(TransientError):
                OrderSagaOrchestrator(self.saga.id).run()   # attempt 1: Celery would re-queue here
            OrderSagaOrchestrator(self.saga.id).run()       # attempt 2: resumes at CHARGE_PAYMENT

        self.assertEqual(self.snapshot()["saga"], "COMPLETED")
        self.assertEqual(Reservation.objects.count(), 1)            # inventory step was NOT re-run
        self.assertEqual(len(set(charge_calls)), 1)                 # same idempotency key both times
        step = SagaStep.objects.get(saga=self.saga, step_name="CHARGE_PAYMENT")
        self.assertEqual((step.status, step.attempt_count), ("SUCCESS", 2))

    def test_transient_failure_exhausts_retries_then_compensates(self):
        with mock.patch("apps.saga.orchestrator.create_delivery", side_effect=CourierApiTimeout("timeout")):
            for _ in range(2):
                with self.assertRaises(TransientError):
                    OrderSagaOrchestrator(self.saga.id).run()
            OrderSagaOrchestrator(self.saga.id).run()  # 3rd attempt: give up and compensate

        snap = self.snapshot()
        self.assertEqual(
            (snap["saga"], snap["order"], snap["payment"], snap["available"]),
            ("FAILED", "CANCELLED", "REFUNDED", 50),
        )

    # ---- compensation failure ------------------------------------------------

    def test_refund_failure_parks_saga_for_manual_intervention(self):
        with mock.patch("apps.saga.orchestrator.create_delivery", side_effect=AddressNotServiceableError("no")), \
             mock.patch.object(gateway, "refund", side_effect=PaymentGatewayUnavailable("503")):
            OrderSagaOrchestrator(self.saga.id).run()

        snap = self.snapshot()
        self.assertEqual(snap["saga"], "MANUAL_INTERVENTION")
        self.assertEqual(snap["payment"], "CHARGED")       # money is still held: visible, not hidden
        self.assertEqual(snap["reserved"], 10)             # release never ran, order of undo is preserved
        self.assertEqual(snap["order"], "PENDING")         # not cancelled until compensation completes
        self.assertEqual(self.steps(), [
            ("RESERVE_INVENTORY", "SUCCESS"),
            ("CHARGE_PAYMENT", "COMPENSATION_FAILED"),
            ("CREATE_DELIVERY", "FAILED"),
        ])

    # ---- duplicate execution -------------------------------------------------

    def test_completed_saga_is_not_executed_twice(self):
        OrderSagaOrchestrator(self.saga.id).run()
        OrderSagaOrchestrator(self.saga.id).run()  # duplicate Celery delivery

        self.assertEqual(PaymentOperation.objects.count(), 1)
        self.assertEqual(Reservation.objects.count(), 1)
```

Run them with:

```bash
python manage.py test apps.saga -v 2
```

Output from the run used for this document:

```text
test_all_steps_succeed ... ok
test_completed_saga_is_not_executed_twice ... ok
test_failure_at_step_1_insufficient_stock ... ok
test_failure_at_step_2_card_declined ... ok
test_failure_at_step_3_delivery_rejected ... ok
test_failure_at_step_4_unexpected_bug ... ok
test_refund_failure_parks_saga_for_manual_intervention ... ok
test_transient_failure_exhausts_retries_then_compensates ... ok
test_transient_failure_is_retried_and_completed_steps_are_not_repeated ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.082s

OK
```

---

# 39. Recommended State Machine

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

For individual steps (this is exactly what `SagaStep.Status` in section 27.5 implements):

```text
PENDING
   |
   v
RUNNING <------------------+
   |                       |
   +-----------+           |
   |           |           |
   v           v           |
SUCCESS      FAILED        |
   |           |           |
   |           +-- transient, attempts left --+
   |           |
   |           +-- permanent / attempts exhausted --> (saga starts compensating)
   |
   v
COMPENSATING
   |
   +---------------+
   |               |
   v               v
COMPENSATED   COMPENSATION_FAILED --> saga = MANUAL_INTERVENTION
```

---

# 40. Production Improvements

The example above is complete enough to run and test, but it is deliberately kept small.

A production system should add the following.

## 40.1 Transactional Outbox

When a local transaction changes state and needs to publish an event:

```text
BEGIN
    Update business data
    Insert OutboxEvent
COMMIT
```

Then publish asynchronously.

---

## 40.2 Strong Idempotency

Every externally visible side effect should have a stable idempotency key:

```text
saga_id + step_name
```

Use a database unique constraint.

---

## 40.3 State Transition Validation

Do not allow arbitrary transitions.

For example:

```text
COMPLETED -> IN_PROGRESS
```

should be rejected.

Use explicit allowed transitions.

---

## 40.4 Distributed Correlation ID

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

## 40.5 Dead-Letter / Manual Recovery

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

## 40.6 Timeouts

Every Saga should have reasonable timeouts.

For example:

```text
Payment timeout = 5 minutes
Delivery timeout = 10 minutes
Entire Saga timeout = 30 minutes
```

The exact values depend on the business.

---

## 40.7 Monitoring

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

# 41. Final Mental Model

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
