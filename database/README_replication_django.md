
# 🧬 Data Replication in Django with PostgreSQL

## 📖 What is Data Replication?

**Data replication** is the process of copying and maintaining data across multiple database servers to:
- Improve availability
- Distribute read load
- Support failover mechanisms
- Enable geo-distribution

---

## 🔁 Types of Replication

| Type | Description |
|------|-------------|
| **Master-Slave (Primary-Replica)** | Writes go to the master, and reads are handled by replicas |
| **Master-Master** | Both databases can read/write (synchronization is complex) |
| **Synchronous** | Safer: changes are committed after replication |
| **Asynchronous** | Faster: changes are replicated after commit (risk of data loss) |

---

## ⚙️ PostgreSQL Replication with Django

### How it Works
1. PostgreSQL enables **Write-Ahead Logging (WAL)**.
2. Changes are streamed to **replica servers**.
3. Replicas are set to **hot standby** for read-only queries.

---

## 🔧 Setting Up Replication in Django

### Step 1: Define Databases in `settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'main_db',
        'USER': 'admin',
        'HOST': 'master-db.host',
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'main_db',
        'USER': 'admin',
        'HOST': 'replica-db.host',
    },
}
```

---

### Step 2: Create a Database Router

Create a file `db_router.py`:

```python
class ReadReplicaRouter:
    def db_for_read(self, model, **hints):
        return 'replica'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
```

Then add to your `settings.py`:

```python
DATABASE_ROUTERS = ['your_project.db_router.ReadReplicaRouter']
```

---

### Step 3: How Django Handles Queries

```python
# Read from replica
books = Book.objects.filter(author="Mamun")

# Write to master
Book.objects.create(title="Replica Test", author="Mamun")
```

---

## ✅ Benefits

| Use Case | Benefit |
|----------|---------|
| High read traffic | Load balancing through replicas |
| Analytics | Avoids overloading the main DB |
| Disaster recovery | Failover support |
| Global scale | Replicas close to users reduce latency |

---

## 📌 Summary

| Feature | Replication Support |
|---------|----------------------|
| Read Scaling | ✅ |
| Write Scaling | ❌ |
| Native Django Support | ✅ via database routers |
| Setup Complexity | Moderate |
| Recommended When | Read-heavy apps or failover is critical |

---

## 🧪 Final Notes

- Use asynchronous replication for performance.
- Monitor replication lag to avoid serving stale data.
- Use Django routers wisely to separate read and write operations.

