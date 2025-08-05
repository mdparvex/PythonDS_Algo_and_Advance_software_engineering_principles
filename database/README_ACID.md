Here's the **enhanced version** of the ACID documentation with **Django-based examples** added to each section. These examples show how ACID principles apply when using Django with a relational database like PostgreSQL or MySQL.

# 📘 ACID Properties in Databases with Django Examples

## 📌 Introduction

In the world of **relational databases**, **ACID** properties (Atomicity, Consistency, Isolation, Durability) are the cornerstone of transaction management. When using **Django**, a high-level Python web framework, ACID properties are managed by Django's **ORM** and its integration with the underlying database.

This guide explains each ACID property and includes **real Django examples** to demonstrate how they apply in practice.

## 🔹 1. Atomicity

**Definition:**  
A transaction is either **fully completed** or **fully rolled back** — no partial changes are saved to the database.

**Django Example:**

```python
from django.db import transaction
from myapp.models import Account

def transfer_funds(from_id, to_id, amount):
    with transaction.atomic():
        from_account = Account.objects.select_for_update().get(pk=from_id)
        to_account = Account.objects.select_for_update().get(pk=to_id)

        if from_account.balance < amount:
            raise ValueError("Insufficient funds")

        from_account.balance -= amount
        to_account.balance += amount

        from_account.save()
        to_account.save()

```

**Explanation:**

- transaction.atomic() creates an atomic block.
- If any exception occurs inside the block (e.g., insufficient funds), all changes are **rolled back**.
- Without this, partial changes could corrupt data.

## 🔹 2. Consistency

**Definition:**  
A transaction must ensure the database goes from one **valid state** to another, preserving all constraints.

**Django Example with Constraints:**

```python
from django.db import models

class Account(models.Model):
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.balance < 0:
            raise ValidationError("Balance cannot be negative")

```

```python
from django.core.exceptions import ValidationError

def debit_account(account_id, amount):
    account = Account.objects.get(pk=account_id)
    account.balance -= amount
    account.full_clean()  # Enforces model-level constraints
    account.save()

```

**Explanation:**

- full_clean() ensures that any **custom or built-in model constraints** are enforced before saving.
- **Consistency** can also be enforced by **database-level constraints** (e.g., CHECK, UNIQUE, NOT NULL).

## 🔹 3. Isolation

**Definition:**  
Isolation ensures that concurrent transactions **don’t interfere** with each other, preventing issues like **dirty reads** or **phantom reads**.

**Django Example using select_for_update:**

```python
from django.db import transaction
from myapp.models import Inventory

def reserve_product(product_id):
    with transaction.atomic():
        product = Inventory.objects.select_for_update().get(pk=product_id)
        if product.stock <= 0:
            raise Exception("Out of stock")
        product.stock -= 1
        product.save()

```

**Explanation:**

- select_for_update() locks the row for update until the transaction is committed.
- Prevents race conditions during concurrent access (e.g., overselling).

**Isolation levels** can be set at the database level via:

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;')

```

## 🔹 4. Durability

**Definition:**  
Once a transaction commits, its changes are **persisted**, even if the system crashes immediately afterward.

**Django Perspective:**

```python
from django.db import transaction

@transaction.atomic
def create_order(user, items):
    # Create order and deduct stock
    ...
    # Committing this transaction makes it durable

```

**Durability is handled by:**

- Django's ORM committing the transaction only when no errors occur.
- The underlying RDBMS (e.g., PostgreSQL) ensures durability using:
  - **Write-ahead logs (WAL)**
  - **Disk syncing (fsync)**
  - **Transaction logs**

## ⚖️ Why ACID Matters in Django Projects

| **Feature** | **Django Implementation** | **ACID Role** |
| --- | --- | --- |
| Atomic fund transfer | transaction.atomic() | Atomicity |
| Data validation | model.full_clean(), constraints | Consistency |
| Concurrent stock update | select_for_update() | Isolation |
| Persistent order entry | Committed transaction | Durability |

## ⚠️ Performance Trade-offs in Django

| **ACID Property** | **Django Usage Example** | **Performance Impact** |
| --- | --- | --- |
| Atomicity | Large transaction.atomic() block | Higher memory/log usage |
| Consistency | Complex validation/constraint checks | Slower inserts/updates |
| Isolation | Serializable isolation with row locks | May block concurrent users |
| Durability | Relying on commit() & disk writes | Slower transactions (I/O cost) |

To optimize:

- Use smaller transaction blocks.
- Use bulk_create to reduce queries.
- Use lower isolation levels if your use case allows.

## 🧠 ACID vs BASE (with Django Context)

| **Feature** | **ACID (Django ORM + RDBMS)** | **BASE (Eventual Consistency / NoSQL)** |
| --- | --- | --- |
| Framework use | Django ORM with PostgreSQL/MySQL | Django with MongoDB (via Djongo or PyMongo) |
| Consistency | Strong, enforced by models/db | Eventual, must be handled manually |
| Use case | Financial, educational platforms | Realtime feeds, analytics |

## ✅ Summary Table

| **Property** | **Django Tools / Approach** |
| --- | --- |
| Atomicity | transaction.atomic() |
| Consistency | model.full_clean(), constraints |
| Isolation | select_for_update(), isolation levels |
| Durability | Automatic on commit by DB engine |

## 📎 Final Notes

- Django provides first-class support for **ACID-compliant** development through its **transaction framework** and **model system**.
- Understanding when to **enforce** and when to **relax** these guarantees is essential for building scalable Django applications.