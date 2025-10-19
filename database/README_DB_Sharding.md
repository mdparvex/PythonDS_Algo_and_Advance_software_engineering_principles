# Technical Documentation: **Database Sharding**

## ****1\. Introduction****

**Database sharding** is a technique used to **horizontally partition data across multiple database instances** (called **shards**) to improve **scalability, performance, and availability**.

Instead of storing all data in a single monolithic database, data is **split (sharded)** based on a **sharding key**-such as user ID, region, or tenant-so that **each shard holds only a portion of the dataset**.

This approach is used by large-scale systems like **Netflix, Amazon, and Facebook** to manage **massive volumes of data** efficiently.

## ****2\. Core Concept****

### ****2.1 What is Sharding?****

Sharding = **Horizontal Partitioning + Distribution Across Multiple Databases**

Each shard contains the **same schema**, but **different subsets of data**.  
For example:

| **Shard** | **Data Range** | **Example** |
| --- | --- | --- |
| **Shard 1** | User ID 1-1,000,000 | Stored in db-shard-1 |
| **Shard 2** | User ID 1,000,001-2,000,000 | Stored in db-shard-2 |

## ****3\. Why Use Sharding?****

| **Challenge** | **Without Sharding** | **With Sharding** |
| --- | --- | --- |
| **Scalability** | One large database struggles with growth. | Data distributed, scalable horizontally. |
| **Performance** | Queries slow due to large indexes and I/O load. | Each shard handles smaller data size, faster queries. |
| **Availability** | A single DB failure impacts all data. | Failure isolated to one shard. |
| **Cost** | Vertical scaling (larger servers) is expensive. | Horizontal scaling uses cheaper commodity nodes. |

## ****4\. Sharding vs Replication****

| **Feature** | **Sharding** | **Replication** |
| --- | --- | --- |
| **Purpose** | Distribute data (scale horizontally) | Duplicate data (for HA/read performance) |
| **Data on Each Node** | Different | Same |
| **Write Operation** | Goes to one shard | Goes to primary/master |
| **Read Operation** | Based on shard key | Can go to replicas |
| **Main Benefit** | Scalability | Availability |

✅ **Often used together** - replication within each shard ensures availability.

## ****5\. Sharding Architectures****

### ****5.1 Key-Based (Hash-Based) Sharding****

- Sharding key is hashed.
- Hash determines the target shard.
- Balances data evenly, but hard to re-shard.
```python
shard_id = hash(user_id) % 4
```

| **user_id** | **hash** | **shard_id** |
| --- | --- | --- |
| 12345 | 5   | 1   |
| 54321 | 9   | 1   |
| 88888 | 2   | 2   |

### ****5.2 Range-Based Sharding****

- Data divided into defined ranges.
- Easier to query sequential data but may cause imbalance.

| **Range** | **Shard** |
| --- | --- |
| 1-1,000,000 | Shard 1 |
| 1,000,001-2,000,000 | Shard 2 |

### ****5.3 Directory-Based (Lookup Table) Sharding****

- A **metadata table** or **router service** maps keys to shards.
- Useful when the sharding key doesn't follow numeric or hash-based rules.

| **User ID** | **Shard** | **DB Host** |
| --- | --- | --- |
| 500 | Shard 1 | db-shard-1.example.com |
| 800 | Shard 2 | db-shard-2.example.com |

## ****6\. Sharding Components****

| **Component** | **Description** |
| --- | --- |
| **Shard Key** | The key used to decide which shard data belongs to. |
| **Shard Manager** | Determines which shard a query should go to. |
| **Router / Proxy** | Middleware that routes requests to correct shard (e.g., PgBouncer, Citus, ProxySQL). |
| **Metadata Store** | Maintains mapping between shard keys and shards. |
| **Shard Nodes** | Independent PostgreSQL databases holding subsets of data. |

## ****7\. PostgreSQL Sharding****

PostgreSQL supports sharding in multiple ways:

| **Method** | **Description** |
| --- | --- |
| **Declarative Partitioning** | Built-in horizontal partitioning by range or hash. |
| **Citus** (extension) | Distributed PostgreSQL that supports true sharding and parallel query execution. |
| **Manual Sharding** | Application-level logic determines which shard to use. |

## ****8\. Architecture Overview****
```scss
           ┌────────────────────────────┐
           │        Application         │
           └────────────┬───────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   Shard Router  │  ← (Citus Coordinator / Proxy)
               └───────┬─────────┘
         ┌─────────────┼───────────────────┐
         ▼             ▼                   ▼
 ┌────────────┐ ┌────────────┐ ┌────────────┐
 │  Shard 1   │ │  Shard 2   │ │  Shard 3   │
 │(users 1–1M)│ │ (1M–2M)    │ │     (2M–3M)│
 └────────────┘ └────────────┘ └────────────┘
```

## ****9\. Production-Level Example: Sharding with PostgreSQL (Citus on AWS)****

We'll use **AWS RDS for PostgreSQL with the Citus extension** for distributed sharding.

### ****9.1 Architecture****

- **Coordinator Node** - entry point for queries.
- **Worker Nodes (Shards)** - store distributed data partitions.
- **Replication within each shard** - optional for HA.

### ****9.2 Setup Steps****

#### Step 1: Launch Citus Cluster

You can use:

- **Amazon RDS for PostgreSQL with Citus**
- **Self-managed EC2 setup**

Install Citus on all nodes:

```bash
sudo apt install postgresql-15-citus
```

Enable the extension in PostgreSQL:
```sql
CREATE EXTENSION citus;
```

#### Step 2: Configure Coordinator Node

Add worker nodes:

```sql
SELECT * from master_add_node('worker1.cluster.local', 5432);
SELECT * from master_add_node('worker2.cluster.local', 5432);
```

#### Step 3: Create Distributed Table

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    region TEXT
);

-- Distribute table across shards using id as shard key
SELECT create_distributed_table('users', 'id');
```

This command tells Citus to:

- Split data across workers
- Manage routing automatically

#### Step 4: Insert Data

```sql
INSERT INTO users (name, email, region)
VALUES ('Alice', 'alice@example.com', 'US'),
       ('Bob', 'bob@example.com', 'EU');
```

Citus automatically hashes the `id` and routes each record to the appropriate shard.

#### Step 5: Query Data

You can query normally:

```sql
SELECT * FROM users WHERE id = 1;
```

The **Coordinator Node**:

- Determines which shard stores id = 1.
- Sends the query only to that shard.
- Combines results and returns to the client.

## ****10\. Read and Write Flow****

| **Operation** | **Flow** | **Explanation** |
| --- | --- | --- |
| **Write (INSERT/UPDATE)** | App → Router → Correct Shard | The router determines the shard using shard key and forwards the write. |
| **Read (SELECT by Key)** | App → Router → Correct Shard | Efficient single-shard reads (no cross-shard scan). |
| **Read (Aggregations)** | App → Router → All Shards → Combine | For global aggregates, coordinator queries all shards and merges results. |
| **Cross-Shard Transactions** | Router → Multiple Shards → Two-phase commit | More complex and slower. Avoid when possible. |

## ****11\. Real-World Example: AWS Aurora PostgreSQL + Sharding via Citus****

In AWS:

- Create **Aurora PostgreSQL cluster** with **Citus** or deploy **Citus via AWS Marketplace**.
- Use **Aurora Reader Endpoints** as read replicas per shard.
- Add **application-level shard mapping** or use **Citus coordinator**.

AWS Example Network:

```pgsql
Aurora Cluster
├── Coordinator Node (writer endpoint)
├── Worker Node 1 (shard1)
├── Worker Node 2 (shard2)
└── Read Replica per shard
```

AWS handles failover and replication; Citus handles data distribution and routing.

## ****12\. Monitoring and Scaling****

### ****Monitoring****

- Use pg_stat_activity and pg_dist_node for Citus.
- Track shard sizes:
    ```sql
        SELECT * FROM citus_shards;
    ```

### ****Scaling Out****

To add new shards:
```sql
SELECT master_add_node('new-worker.cluster.local', 5432);
```

Then rebalance data:
```sql
SELECT rebalance_table_shards('users');
```

## ****13\. Challenges and Solutions****

| **Challenge** | **Description** | **Mitigation** |
| --- | --- | --- |
| **Cross-shard joins** | Slow due to distributed query execution | Choose shard key wisely |
| **Re-sharding** | Moving data when adding/removing shards | Use consistent hashing or rebalance tools |
| **Hotspotting** | One shard gets more load | Use hash sharding instead of range |
| **Complexity** | Harder schema management | Automate via orchestrator (Citus/Proxy) |

## ****14\. Best Practices****

✅ **Choose the right shard key** (high cardinality, uniform distribution).  
✅ **Avoid cross-shard joins** and multi-shard transactions.  
✅ Use **replication within each shard** for fault tolerance.  
✅ Employ **connection pooling** (PgBouncer) per shard.  
✅ Use **metadata tables** for shard routing.  
✅ Plan **re-sharding strategies** in advance (hash-based works best).

## ****15\. Summary****

| **Concept** | **Description** |
| --- | --- |
| **Sharding** | Distributing data horizontally across multiple DBs. |
| **Shard Key** | Attribute used to determine shard placement. |
| **Coordinator / Router** | Handles query routing to correct shard. |
| **Replication** | Can coexist within each shard for HA. |
| **PostgreSQL Implementation** | Best achieved using **Citus** or **application-level routing**. |
| **AWS Integration** | Use **Aurora PostgreSQL + Citus** or **EC2-based sharded setup**. |

## ****16\. References****

- [PostgreSQL Sharding Concepts](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [Citus Data Documentation](https://docs.citusdata.com/en/stable/)
- [AWS Aurora PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-postgresql.html)
- [Sharding Best Practices (AWS Blog)](https://aws.amazon.com/blogs/database/sharding-your-database-for-scalability/)


---

# 🧠 Technical Documentation: Database Sharding in AWS with PostgreSQL and Django

## 🔍 1. What is Database Sharding?

**Database sharding** is the process of **splitting a large database into smaller, faster, and more manageable pieces called "shards."**

Each shard:

- Holds a **subset of the total data**.
- Runs as an **independent database instance**.
- Can be located on **different servers or regions**.

### 🎯 Why Use Sharding?

| **Benefit** | **Description** |
| --- | --- |
| **Scalability** | Handles massive data and high throughput by distributing load. |
| **Performance** | Reduces query latency since each shard handles fewer records. |
| **Fault Isolation** | One shard's failure doesn't affect others. |
| **Cost Efficiency** | Enables horizontal scaling instead of costly vertical upgrades. |

### ⚙️ Sharding vs Replication vs Partitioning

| **Concept** | **Purpose** | **Data Location** |
| --- | --- | --- |
| **Replication** | Copies same data to multiple databases | Same data everywhere |
| **Partitioning** | Splits one table into parts (in the same DB) | Same DB |
| **Sharding** | Splits data across multiple databases | Different DB servers |

## 🧩 2. Sharding Architecture Overview

```scss
                      ┌──────────────────────────┐
                      │       Django App         │
                      │  (Sharding Middleware)   │
                      └───────────┬──────────────┘
                                  │
               ┌──────────────────┴──────────────────┐
               │                                     │
        ┌──────┴────────┐                   ┌────────┴────────┐
        │ Shard 1 (US)  │                   │ Shard 2 (EU)    │
        │ user_id 1–5000│                   │ user_id 5001–∞  │
        └───────────────┘                   └─────────────────┘
```

Each shard is a **separate PostgreSQL database** in AWS (for example, two RDS instances).

## 🏗️ 3. Sharding Strategies

| **Strategy** | **Description** | **Example** |
| --- | --- | --- |
| **Key-based (Hash)** | Data divided based on hash of key. | hash(user_id) % N |
| **Range-based** | Data divided by range. | user_id 1-5000 → shard1 |
| **Geo-based** | Shard by region. | region = "US" → shard1 |
| **Directory-based** | Central lookup table decides shard. | Lookup table: user_id → shard_db |

For PostgreSQL + Django, **range-based or directory-based** is most practical.

## ☁️ 4. AWS Setup for PostgreSQL Sharding

### Step 1: Create Multiple RDS Databases (Shards)

- Go to **AWS RDS → Create database**.
- Select **PostgreSQL**.
- Create:
  - userdb_shard_1
  - userdb_shard_2
  - (Add more as needed)
- Configure each instance (CPU, memory, region, VPC).
- Note down each DB endpoint:
  - shard1-db.abc123.rds.amazonaws.com
  - shard2-db.abc123.rds.amazonaws.com

### Step 2: Create a "Shard Map" or "Shard Router Database"

Create one small RDS DB (or use DynamoDB) to store shard mapping.

**Table: shard_map**

| **id** | **shard_name** | **db_host** | **db_name** | **user_range_start** | **user_range_end** |
| --- | --- | --- | --- | --- | --- |
| 1   | shard_1 | shard1-db.abc123.rds.amazonaws.com | userdb_1 | 1   | 5000 |
| 2   | shard_2 | shard2-db.abc123.rds.amazonaws.com | userdb_2 | 5001 | 10000 |

This helps Django know where a given record belongs.

## ⚙️ 5. Django Configuration for Sharding

### Step 1: Configure Databases in settings.py

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'shard_router',  # Central lookup
        'USER': 'admin',
        'PASSWORD': 'mypassword',
        'HOST': 'router-db.abc123.rds.amazonaws.com',
        'PORT': '5432',
    },
    'shard_1': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'userdb_1',
        'USER': 'admin',
        'PASSWORD': 'mypassword',
        'HOST': 'shard1-db.abc123.rds.amazonaws.com',
        'PORT': '5432',
    },
    'shard_2': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'userdb_2',
        'USER': 'admin',
        'PASSWORD': 'mypassword',
        'HOST': 'shard2-db.abc123.rds.amazonaws.com',
        'PORT': '5432',
    }
}
```

### Step 2: Create a Database Router

db_router.py:

```python
class ShardRouter:
    def db_for_read(self, model, **hints):
        user_id = hints.get('user_id')
        if not user_id:
            return 'default'
        if user_id <= 5000:
            return 'shard_1'
        else:
            return 'shard_2'

    def db_for_write(self, model, **hints):
        user_id = hints.get('user_id')
        if not user_id:
            return 'default'
        if user_id <= 5000:
            return 'shard_1'
        else:
            return 'shard_2'

    def allow_relation(self, obj1, obj2, **hints):
        db_list = ('shard_1', 'shard_2')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db != 'default'  # Prevent schema migration on shard map DB
```

Then add this in settings.py:

```python
DATABASE_ROUTERS = ['path.to.db_router.ShardRouter']
```

### Step 3: Writing Data to Correct Shard

```python
from myapp.models import UserProfile

user_id = 1234  # Based on logic
user = UserProfile.objects.using('shard_1').create(
    id=user_id,
    name="John Doe",
    email="john@example.com"
)
```

Alternatively, with router hints:

```python
user = UserProfile.objects.db_manager(
    None, hints={'user_id': user_id}
).create(name="John Doe", email="john@example.com")
```

### Step 4: Reading Data from Correct Shard

```python
user_id = 1234
user = UserProfile.objects.db_manager(
    None, hints={'user_id': user_id}
).get(id=user_id)
```

### Step 5: Automating Shard Selection Using Middleware

You can automatically detect shard by user session or tenant.

Example: middleware/shard_selector.py

```python
from django.utils.deprecation import MiddlewareMixin

class ShardMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Assume we have user_id in session
        user_id = request.session.get('user_id')
        request.shard_alias = 'shard_1' if user_id <= 5000 else 'shard_2'
```

Then in views:

```python
def dashboard(request):
    shard = request.shard_alias
    data = UserProfile.objects.using(shard).filter(active=True)
    return render(request, "dashboard.html", {"data": data})
```
## 🧩 6. How Read & Write Work in Sharding

| **Operation** | **Logic** | **Example** |
| --- | --- | --- |
| **Write (Insert/Update/Delete)** | Goes to the shard determined by shard key | user_id=123 → shard_1 |
| **Read (Select)** | Directed to same shard where the key resides | Django router handles this |
| **Cross-shard queries** | Must be handled in the application level | Aggregate data manually |

### 🔄 Example Flow

- User with ID 3200 registers → stored in **shard_1**.
- User with ID 8000 registers → stored in **shard_2**.
- Django's router ensures:
  - Writes to correct shard
  - Reads from same shard
- Analytics or admin dashboards may query all shards for global view.

## 🧪 7. Implementing Cross-Shard Query (Optional)

Since PostgreSQL does not natively support cross-shard joins, handle it in Django:

```python
from myapp.models import UserProfile

def get_total_user_count():
    total = 0
    for shard in ['shard_1', 'shard_2']:
        total += UserProfile.objects.using(shard).count()
    return total
```

## 🔍 8. Monitoring & Scaling on AWS

- Use **Amazon RDS Performance Insights** for each shard.
- Scale shards **individually**.
- Use **CloudWatch** for CPU, storage, connections.
- Use **Amazon Route 53** for custom DNS routing if needed.

## 🛡️ 9. Best Practices

✅ Define a clear **shard key** (e.g., user_id, tenant_id)  
✅ Keep shards **balanced** (monitor load distribution)  
✅ Automate **shard discovery** from central shard_map  
✅ Use **connection pooling** for efficiency  
✅ Plan for **re-sharding** (when data grows unevenly)  
✅ Avoid **cross-shard joins** inside PostgreSQL

## 🚀 10. Example Real-World Setup Summary

| **Component** | **Description** |
| --- | --- |
| **AWS** | RDS PostgreSQL instances as shards |
| **Shard Router DB** | Small RDS instance or DynamoDB for mapping |
| **Sharding Key** | user_id (range-based) |
| **Django** | Multi-DB setup with custom ShardRouter |
| **Writes** | Routed by shard key |
| **Reads** | Routed to same shard |
| **Monitoring** | CloudWatch + Performance Insights |

## 🧭 11. Example Architecture Diagram
```markdown
                   ┌───────────────────────┐
                   │ Django Application    │
                   │  (Shard Router + ORM) │
                   └──────────┬────────────┘
                              │
             ┌────────────────┴────────────────┐
             │                                 │
   ┌─────────┴───────────┐         ┌───────────┴──────────┐
   │ AWS RDS Shard 1     │         │ AWS RDS Shard 2      │
   │ user_id 1–5000      │         │ user_id 5001–∞       │
   └─────────────────────┘         └──────────────────────┘
```

## ✅ 12. Key Takeaways

| **Concept** | **Description** |
| --- | --- |
| **Purpose** | Scale horizontally by splitting data |
| **Core AWS Components** | RDS PostgreSQL instances per shard |
| **Django Integration** | Multi-DB + Router logic |
| **Shard Key** | Critical for even data distribution |
| **Read/Write Behavior** | Isolated per shard |
| **Cross-Shard Ops** | Application-managed |