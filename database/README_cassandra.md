# Technical Documentation: Apache Cassandra

## Overview
Apache Cassandra is an open-source, highly scalable, distributed NoSQL database designed to handle large amounts of data across many commodity servers, providing high availability with no single point of failure. It is optimized for write-heavy workloads and real-time big data applications.

---

## Key Properties

| Property | Description |
|-----------|-------------|
| **Data Model** | Wide-column store (similar to a key-value model but with flexible schema per row). |
| **Replication** | Supports configurable replication strategies for fault tolerance. |
| **Consistency** | Tunable consistency levels from *ONE* to *ALL*. |
| **Scalability** | Linear horizontal scalability by adding nodes. |
| **Fault Tolerance** | Automatic replication and failure recovery. |
| **Query Language** | CQL (Cassandra Query Language), similar to SQL but without joins or transactions. |

---

## Architecture

Cassandra is built on a **peer-to-peer architecture** where all nodes are equal. Each node communicates with others using the **Gossip Protocol**. Data is distributed across nodes using **consistent hashing**.

### Key Components
- **Node**: A single Cassandra instance.
- **Cluster**: A collection of nodes.
- **Keyspace**: The top-level namespace that defines replication strategy.
- **Table (Column Family)**: Stores rows and columns similar to relational tables.
- **Partitioner**: Determines which node stores which data.
- **Commit Log**: Ensures durability for every write operation.
- **Memtable**: In-memory data structure for writes.
- **SSTable**: Immutable disk storage files written from Memtables.

---

## Data Model

Cassandra uses a **wide-column data model** that allows dynamic schema per row.

### Example Schema
```sql
CREATE KEYSPACE student_data WITH REPLICATION = {
  'class': 'SimpleStrategy',
  'replication_factor': 3
};

USE student_data;

CREATE TABLE students (
  student_id UUID PRIMARY KEY,
  name TEXT,
  grade TEXT,
  scores MAP<TEXT, INT>
);
```

### Example Insert & Query
```sql
INSERT INTO students (student_id, name, grade, scores)
VALUES (uuid(), 'Alice', 'A', {'math': 95, 'science': 90});

SELECT name, scores['math'] FROM students WHERE student_id = <UUID>;
```

---

## Write Path (Step-by-Step)
1. **Client Request:** The client sends a write request to any node (coordinator node).
2. **Coordinator Node:** The coordinator forwards the write to replica nodes based on the partition key.
3. **Commit Log Write:** Each replica writes the data to its commit log (for durability).
4. **Memtable Write:** Data is stored in memory (memtable).
5. **Acknowledgement:** Once the consistency level requirement is met, the client receives a success response.
6. **Flush to Disk:** When memtable is full, it’s flushed to SSTable files on disk.

---

## Read Path (Step-by-Step)
1. **Client Request:** Client sends a read request to any node (coordinator node).
2. **Coordinator Node:** Identifies replicas that hold the data.
3. **Read from Replicas:** Coordinator queries replicas and merges results.
4. **Bloom Filter Check:** Quickly checks whether data exists in SSTables.
5. **Read Repair:** If replicas return different results, Cassandra initiates a read repair to synchronize them.

---

## Scaling Cassandra

### Horizontal Scaling
- **Add Nodes:** Simply add new nodes to the cluster.
- **Data Rebalancing:** Cassandra automatically redistributes data using consistent hashing.

### Example
1. Add a new node to the cluster.
2. Cassandra runs the **bootstrap process** to stream the appropriate data to the new node.
3. No downtime is required during scaling.

---

## Replication Strategies

### 1. SimpleStrategy
Used for single data center deployments.
```sql
WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 3}
```

### 2. NetworkTopologyStrategy
Used for multi-data center setups.
```sql
WITH REPLICATION = {
  'class': 'NetworkTopologyStrategy',
  'us-east': 3,
  'us-west': 2
}
```

---

## Consistency Levels

Cassandra offers **tunable consistency** per query:
- **ONE** – One replica must respond.
- **QUORUM** – Majority of replicas must respond.
- **ALL** – All replicas must respond.

**Formula for Consistency Guarantee:**  
`R + W > N`  ⇒ Strong Consistency

Where:
- `R` = Number of replicas read from
- `W` = Number of replicas written to
- `N` = Replication factor

---

## Common Use Cases

| Use Case | Description |
|-----------|-------------|
| **IoT Data Storage** | Handles time-series sensor data efficiently. |
| **Messaging Systems** | Supports real-time message persistence. |
| **Recommendation Engines** | Stores user activity data for quick retrieval. |
| **Financial Services** | High-availability data replication across regions. |
| **Analytics Pipelines** | Works as a fast ingestion layer before Hadoop/Spark. |

---

## Real-World Example

**Netflix** is one of the most well-known adopters of Cassandra. It uses Cassandra to store and manage user viewing history, preferences, and streaming metadata across globally distributed data centers. Cassandra’s ability to scale horizontally and remain highly available even during regional outages makes it ideal for Netflix’s massive global user base.

---

## Python Example: Connecting and Querying Cassandra

You can interact with Cassandra using the official `cassandra-driver` library.

### Installation
```bash
pip install cassandra-driver
```

### Python Code Example
```python
from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

# Connect to Cassandra cluster
cluster = Cluster(['127.0.0.1'])  # Replace with your Cassandra node IP
session = cluster.connect()

# Create a keyspace
session.execute('''
CREATE KEYSPACE IF NOT EXISTS demo
WITH REPLICATION = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
}
''')

# Use the keyspace
session.set_keyspace('demo')

# Create a table
session.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY,
    name TEXT,
    email TEXT
)
''')

# Insert data
from uuid import uuid4
session.execute(
    "INSERT INTO users (user_id, name, email) VALUES (%s, %s, %s)",
    (uuid4(), 'Alice', 'alice@example.com')
)

# Read data
rows = session.execute('SELECT * FROM users')
for row in rows:
    print(f"User: {row.name}, Email: {row.email}")

# Close connection
cluster.shutdown()
```

---

## Performance Optimizations

### 1. **Data Modeling Best Practices**
- Design around **queries**, not normalization.
- Use **partition keys** wisely to prevent hotspots.
- Avoid large partitions (>100 MB).

### 2. **Compaction Strategies**
- **SizeTieredCompactionStrategy (STCS):** Default, merges SSTables of similar size.
- **LeveledCompactionStrategy (LCS):** Better read performance.
- **TimeWindowCompactionStrategy (TWCS):** Ideal for time-series data.

### 3. **Caching**
- **Key Cache:** Speeds up key lookups.
- **Row Cache:** Stores entire rows for frequent queries.

### 4. **Hardware Tuning**
- Use SSDs for faster I/O.
- Allocate sufficient heap memory (but not too large, typically <8GB).

---

## Advanced Features

### 1. **Materialized Views**
Automatically updates denormalized tables for alternate query patterns.
```sql
CREATE MATERIALIZED VIEW students_by_grade AS
  SELECT * FROM students WHERE grade IS NOT NULL AND student_id IS NOT NULL
  PRIMARY KEY (grade, student_id);
```

### 2. **Secondary Indexes**
Provides index lookup for non-primary key columns.
```sql
CREATE INDEX ON students (grade);
```

### 3. **Lightweight Transactions (LWT)**
Ensures conditional updates using Paxos protocol.
```sql
INSERT INTO students (student_id, name)
VALUES (uuid(), 'Bob') IF NOT EXISTS;
```

### 4. **Change Data Capture (CDC)**
Captures data changes for external systems.
```yaml
cdc_enabled: true
cdc_raw_directory: /var/lib/cassandra/cdc_raw
```

### 5. **Repair and Maintenance**
- **nodetool repair:** Synchronizes replicas.
- **nodetool cleanup:** Removes data belonging to other nodes after scaling.
- **nodetool compact:** Manually triggers compaction.

---

## Example: Scaling Workflow

### Scenario: Adding a Node to Cluster
1. Install Cassandra on the new machine.
2. Update `cassandra.yaml` with the cluster’s name and seed nodes.
3. Start the Cassandra service.
4. Node bootstraps automatically and joins the cluster.
5. Verify using:
```bash
nodetool status
```
6. Cassandra redistributes data automatically using consistent hashing.

---

## Monitoring and Tools

| Tool | Purpose |
|------|----------|
| **nodetool** | Cluster management and diagnostics. |
| **JMX / Metrics** | JVM metrics for performance tuning. |
| **Prometheus + Grafana** | Visualization of performance metrics. |
| **DataStax OpsCenter** | GUI-based cluster management tool. |

---

## Summary
Apache Cassandra is an ideal choice for applications requiring **massive scalability**, **high availability**, and **tunable consistency**. Its decentralized architecture and fault tolerance make it suitable for modern distributed systems like IoT, social media, and financial platforms.

---

**Key Takeaways:**
- Peer-to-peer architecture ensures no single point of failure.
- Tunable consistency enables trade-offs between latency and durability.
- Linear scalability with minimal operational complexity.
- Ideal for write-heavy and real-time analytics workloads.

---
# 🗃️ Using Apache Cassandra with Django: Full Technical Guide

## 📘 1. Overview

**Apache Cassandra** is a distributed, NoSQL columnar database designed for **high availability**, **horizontal scalability**, and **fast writes**.  
Unlike relational databases, Cassandra **does not support JOINs or transactions** in the same way - instead, it's optimized for **high-speed reads/writes** and **denormalized data models**.

### ⚙️ Why Use Cassandra with Django?

- Handles **massive write throughput** (e.g., logs, sensor data, user activity).
- Scales horizontally across nodes.
- Fault-tolerant (no single point of failure).
- Can be integrated with Django using drivers like **django-cassandra-engine** or **cassandra-driver**.

## 🧩 2. Cassandra Architecture in Brief

| **Component** | **Description** |
| --- | --- |
| **Node** | A single Cassandra instance |
| **Cluster** | A collection of nodes |
| **Keyspace** | Like a "database" in SQL |
| **Table (Column Family)** | Stores data (rows are sparse and flexible) |
| **Partition Key** | Determines data placement on nodes |
| **Clustering Columns** | Determines data sorting within a partition |

**Data is distributed** based on the partition key and replicated across multiple nodes depending on the **replication factor**.

## 🏗️ 3. Setting Up Cassandra with Django

### Step 1: Install Dependencies

```bash
pip install django-cassandra-engine cassandra-driver
```

### Step 2: Configure settings.py

```python
DATABASES = {
    'default': {
        'ENGINE': 'django_cassandra_engine',
        'NAME': 'my_keyspace',
        'TEST_NAME': 'test_my_keyspace',
        'HOST': '127.0.0.1',
        'OPTIONS': {
            'replication': {
                'strategy_class': 'SimpleStrategy',
                'replication_factor': 1
            },
            'connection': {
                'consistency': 'LOCAL_ONE',
                'retry_connect': True
            }
        }
    }
}
```

### Step 3: Create a Model

```python
from django_cassandra_engine.models import DjangoCassandraModel
from cassandra.cqlengine import columns

class UserActivity(DjangoCassandraModel):
    user_id = columns.UUID(primary_key=True)
    timestamp = columns.DateTime(primary_key=True, clustering_order="DESC")
    activity_type = columns.Text()
    metadata = columns.Map(columns.Text, columns.Text)
```

⚠️ Cassandra uses primary_key and clustering_order instead of id auto fields like in SQL.

## ✍️ 4. Writing Data

### ✅ Basic Create

```python
UserActivity.create(
    user_id=uuid4(),
    timestamp=datetime.now(),
    activity_type="login",
    metadata={"device": "mobile"}
)
```

### ✅ Batch Writes (for efficiency)

```python
from cassandra.cqlengine.query import BatchQuery
batch = BatchQuery()

UserActivity.batch(batch).create(
    user_id=uuid4(),
    timestamp=datetime.now(),
    activity_type="page_view",
    metadata={"page": "home"}
)

UserActivity.batch(batch).create(
    user_id=uuid4(),
    timestamp=datetime.now(),
    activity_type="logout",
    metadata={"device": "web"}
)

batch.execute()
```

💡 **Batch queries** are useful when inserting multiple rows for the same partition key - it reduces network hops.

## 🔍 5. Reading Data

### ✅ Retrieve All Rows

```python
activities = UserActivity.objects.all()
```
### ✅ Filtering by Partition Key

```python
user_activities = UserActivity.objects.filter(user_id=my_user_id)
```

### ✅ Filtering by Clustering Key

```python
recent = UserActivity.objects.filter(user_id=my_user_id).order_by('-timestamp')[:5]
```

### ✅ Using Raw CQL Queries

```python
from django_cassandra_engine.connection import get_connection

connection = get_connection()
session = connection.session

rows = session.execute("SELECT * FROM useractivity WHERE user_id = %s", [my_user_id])
for row in rows:
    print(row)
```

## ⚙️ 6. Query Techniques and Best Practices

Cassandra's **query model is built around the partition key**. You can only query efficiently by partition key (and clustering keys inside it).

### ✅ 1. Query by Partition Key Always

Bad:

```python
UserActivity.objects.filter(activity_type="login")  # inefficient
```

Good:

```python
UserActivity.objects.filter(user_id=my_user_id)
```

### ✅ 2. Use Secondary Indexes Sparingly

You can create a secondary index but they **don't scale well**.

```sql
CREATE INDEX activity_type_idx ON useractivity (activity_type);
```

Use only when:

- The table is small.
- Queries are frequent and selective.

### ✅ 3. Use Materialized Views (MV)

Pre-compute alternate query patterns.

```sql
CREATE MATERIALIZED VIEW useractivity_by_type AS
    SELECT * FROM useractivity
    WHERE activity_type IS NOT NULL AND user_id IS NOT NULL
    PRIMARY KEY (activity_type, user_id, timestamp);
```

Now you can query:

```sql
SELECT * FROM useractivity_by_type WHERE activity_type = 'login';
```

### ✅ 4. Denormalize for Query Speed

Cassandra favors duplication for faster reads.  
Store the same data in multiple tables, each optimized for a specific query.

## 🚀 7. Performance Optimization

| **Optimization** | **Description** |
| --- | --- |
| **Data Modeling** | Design based on queries, not normalization |
| **Batch Writes** | Combine inserts in one batch for same partition |
| **Clustering Order** | Optimize for sorted reads |
| **Partition Size** | Keep partitions under 100MB |
| **Consistency Level** | Use LOCAL_ONE or LOCAL_QUORUM for balance |
| **Avoid Tombstones** | Avoid frequent updates/deletes on same row |
| **Use Prepared Statements** | Speeds up repeated queries |

### Example: Prepared Statement

```python
prepared = session.prepare("SELECT * FROM useractivity WHERE user_id = ?")
rows = session.execute(prepared, [my_user_id])
```

## ⚡ 8. Caching Strategies

Cassandra itself provides **in-memory caching**, but Django can complement it.

### ✅ 1. Cassandra's Native Caches

- **Key cache:** Caches primary key lookups.
- **Row cache:** Caches entire rows (less common).
- **Counter cache:** Used for counter tables.

These are configured in cassandra.yaml.

### ✅ 2. Django-Level Caching

Combine with:

- **Redis** or **Memcached** for frequently accessed queries.

Example using Django cache:

```python
from django.core.cache import cache

def get_user_activity(user_id):
    key = f"user_activity_{user_id}"
    data = cache.get(key)
    if not data:
        data = list(UserActivity.objects.filter(user_id=user_id))
        cache.set(key, data, timeout=60)
    return data
```

### ✅ 3. Application Caching Layer

- Cache aggregated data (e.g., analytics summary)
- Use **Celery** to pre-warm caches

## 🧠 9. Common Pitfalls to Avoid

| **Pitfall** | **Fix** |
| --- | --- |
| Querying without partition key | Always model data around access patterns |
| Too large partitions | Design keys carefully |
| Overusing secondary indexes | Use materialized views or denormalization |
| Using Django ORM queries like SQL | Cassandra is not relational |
| Updating frequently | Avoid updates; prefer inserts |
| Not handling eventual consistency | Adjust consistency_level properly |

## 🧩 10. Example: Real-world Use Case

### 📘 Scenario

A reading platform logs every student's activity (page viewed, words read, etc.) in real time.

### Data Model

```python
class ReadingLog(DjangoCassandraModel):
    student_id = columns.UUID(primary_key=True)
    session_id = columns.UUID(primary_key=True)
    timestamp = columns.DateTime(primary_key=True, clustering_order="DESC")
    page_number = columns.Integer()
    words_read = columns.Integer()
```

### Write Operation

```python
ReadingLog.create(
    student_id=student_id,
    session_id=session_id,
    timestamp=datetime.now(),
    page_number=5,
    words_read=120
)
```

### Read Operation

```python
recent_logs = ReadingLog.objects.filter(student_id=student_id).order_by('-timestamp')[:10]
```

### Caching Layer

```python
cache_key = f"reading_log_{student_id}"
logs = cache.get(cache_key)
if not logs:
    logs = list(ReadingLog.objects.filter(student_id=student_id))
    cache.set(cache_key, logs, timeout=120)
```

## 🧭 Summary

| **Feature** | **Description** |
| --- | --- |
| **Integration** | django-cassandra-engine |
| **Best for** | Write-heavy, scalable, time-series data |
| **Query Model** | Partition + clustering keys |
| **Optimization** | Query-based modeling, batching, clustering order |
| **Caching** | Use Redis or Cassandra key cache |
| **Pitfalls** | Avoid SQL mindset - think in denormalized models |

Let's break everything down clearly - **step-by-step** - so you'll have a full mental model of how **replication** works in Cassandra (and how it affects writes, reads, and consistency).

# 🧠 Understanding Replication in Cassandra

When you define this in your Django settings.py:

```python
'replication': {
    'strategy_class': 'SimpleStrategy',
    'replication_factor': 3
}
```

you're telling Cassandra:

"For every piece of data I write, make **3 copies (replicas)** of it across different nodes in the cluster."

Let's unpack what this really means.

## 🗂️ 1. Replication Factor (RF)

| **Term** | **Meaning** |
| --- | --- |
| **Replication Factor (RF)** | Number of copies of each piece of data that Cassandra maintains across different nodes. |

So:

- **RF = 1** → Only one copy (no redundancy).
- **RF = 3** → Three copies across **three different nodes**.
- **RF = 5** → Five copies (used for multi-region setups).

### 📍 Example

You have a 6-node Cassandra cluster.

| **Partition Key** | **Node Responsible** | **Replicas Stored** |
| --- | --- | --- |
| user_id = 1 | Node A | Node A, Node B, Node C |
| user_id = 2 | Node D | Node D, Node E, Node F |

So every partition (group of data sharing the same partition key) gets replicated **RF times** on different nodes.

## ⚙️ 2. How Cassandra Chooses Replica Nodes

Cassandra uses a **consistent hashing ring** to decide which nodes store the replicas.

- Each node is assigned a "token range".
- The partition key (like user_id) is hashed.
- That hash determines **the primary node** responsible for that key.
- Then, Cassandra replicates the same data to the **next N-1 nodes clockwise** around the ring.

So if your replication factor = 3:

- 1 node holds the primary copy
- 2 other nodes hold replicas

## ✍️ 3. What Happens on ****Write****

When you insert or update data:

- **Client writes to a coordinator node.**
  - Any node in the cluster can act as a coordinator.
- **Coordinator sends the write to all replicas.**
  - The number of replicas that must acknowledge depends on the **consistency level**.

Example consistency levels:

| **Level** | **Meaning** |
| --- | --- |
| ONE | Write must succeed on 1 replica |
| TWO | Write must succeed on 2 replicas |
| QUORUM | Must succeed on majority of replicas (e.g., 2 out of 3) |
| ALL | Must succeed on all replicas |

- **Hinted Handoff:**
  - If one replica is down, the coordinator stores a "hint" and delivers it later.
- **All replicas eventually become consistent.**
  - Cassandra ensures eventual consistency using background processes like **read repair** and **anti-entropy repair**.

✅ Example:

```python
session.execute(
    "INSERT INTO users (id, name) VALUES (%s, %s)",
    [1, 'Alice'],
    consistency_level=ConsistencyLevel.QUORUM
)
```

Here:

- Data is sent to 3 replicas.
- Coordinator waits for acknowledgment from at least **2 replicas** (majority).

## 🔍 4. What Happens on ****Read****

When you perform a read:

- **Coordinator node receives the request.**
- **It contacts replicas** depending on the read **consistency level**.
- The replicas respond with the requested data.
- Cassandra uses a **digest comparison** (checksum) to ensure all replicas agree.
- If a replica has stale data, **read repair** updates it in the background.

Example consistency levels for reads:

| **Level** | **Description** |
| --- | --- |
| ONE | Reads from one replica (fast, possibly stale) |
| QUORUM | Reads from majority of replicas (balanced) |
| ALL | Reads from all replicas (slow, but most consistent) |

## 🧮 5. Write/Read Consistency Relationship

Cassandra offers **tunable consistency**:

For strong consistency, the rule is:

**W + R > RF**

Where:

- W = number of replicas that must acknowledge a write
- R = number of replicas that must respond to a read
- RF = replication factor

### Example

If RF = 3:

- Write at QUORUM (2 replicas)
- Read at QUORUM (2 replicas)

→ 2 + 2 = 4 > 3  
✅ So you'll always get the most recent data.

## 🌍 6. Replica Placement Strategy

There are **two main strategies**:

### 1\. SimpleStrategy

- Used for **single datacenter** clusters.
- Places replicas on the next N-1 nodes clockwise on the ring.

Example:
```scss
Node1 → Node2 → Node3 (3 replicas)
```
### 2\. NetworkTopologyStrategy

- Used for **multi-datacenter or multi-region** clusters.
- Allows specifying **different replication factors per datacenter**.

Example:

```python
'replication': {
    'class': 'NetworkTopologyStrategy',
    'DC1': 3,
    'DC2': 2
}
```

This means:

- 3 replicas in data center DC1
- 2 replicas in DC2

✅ Useful for global systems - you can read locally and still maintain global consistency.

## 🧠 7. How Cassandra Decides Which Replica to Read

When reading:

- The **coordinator node** checks the **snitch** and **load balancing policy** to choose the closest or least loaded replica.

**Snitches** are responsible for knowing topology:

- SimpleSnitch: same datacenter
- GossipingPropertyFileSnitch: detects racks and data centers (default)
- EC2MultiRegionSnitch: for AWS, uses availability zones

So the coordinator usually chooses:

- The **nearest replica** (to minimize latency)
- Or one that's **less loaded**

Then it verifies consistency by checking digests from other replicas.

## 💾 8. Replica Placement (Visualization)

Assume:

- 4 nodes (N1, N2, N3, N4)
- Replication factor = 3
```scss
Ring: N1 → N2 → N3 → N4 → N1
```
| **Partition Key** | **Primary Node** | **Replica 1** | **Replica 2** |
| --- | --- | --- | --- |
| user_1 | N1  | N2  | N3  |
| user_2 | N2  | N3  | N4  |
| user_3 | N3  | N4  | N1  |

Each node holds data for multiple partitions.

## 🧩 9. What Happens When a Node Fails

If one replica node goes down:

- Writes still succeed (depending on consistency level).
- Hints are stored by coordinator (Hinted Handoff).
- When the node comes back online, it's repaired.
- **Read repair** ensures stale replicas are updated when reading.

If **RF=3**, you can tolerate up to **2 node failures** depending on your consistency setting.

## ⚡ 10. Summary Table

| **Concept** | **Description** |
| --- | --- |
| **Replication Factor** | Number of copies of data |
| **Replica Nodes** | Nodes holding identical data |
| **Write Consistency** | How many replicas must confirm write |
| **Read Consistency** | How many replicas must confirm read |
| **W + R > RF** | Ensures strong consistency |
| **SimpleStrategy** | Same datacenter replication |
| **NetworkTopologyStrategy** | Multi-region replication |
| **Read Repair** | Fixes outdated replicas |
| **Hinted Handoff** | Catches up failed replicas |
| **Snitch** | Decides which replica to read from |

## 🧠 Real-World Analogy

Imagine you store a document in 3 offices (replication_factor=3).

- When you **write**, you send it to all 3 offices.
  - You can consider the job done when 2 of them confirm (QUORUM).
- When you **read**, you can ask 2 offices.
  - If both agree, you're sure it's the latest version.
- If one office burns down, the other two still have copies.

## ✅ Practical Recommendation for Django + Cassandra

- For **single datacenter**, use:
```python
'replication': {
    'strategy_class': 'SimpleStrategy',
    'replication_factor': 3
}
```
- For **multi-region**:
```python
'replication': {
    'class': 'NetworkTopologyStrategy',
    'us_east_1': 3,
    'eu_west_1': 3
}
```
- Use **LOCAL_QUORUM** consistency for balanced performance.
- Monitor with tools like **Datastax OpsCenter** or **Prometheus + Grafana**.

# 🧩 Working with Nested JSON Data in Cassandra + Django

## ⚙️ 1. Cassandra and JSON: The Core Idea

Cassandra **does not have a JSON type natively**,  
but it supports:

- **Map**, **List**, and **Set** collections
- **Text fields** that can hold JSON strings

These are the two main ways to handle nested or JSON-like data:

| **Approach** | **Description** | **When to Use** |
| --- | --- | --- |
| **A. Cassandra Collections (Map/List/Set)** | Store structured JSON-like data directly | When the JSON structure is known and not too deep |
| **B. JSON as Text (stringified)** | Store full JSON string | When JSON structure is dynamic or unstructured |

Django (with django-cassandra-engine) lets you use both approaches easily.

## 🧠 Example Use Case

Let's say you're storing **student reading progress** per chapter.

A JSON object might look like this:

```json
{
  "chapter_id": "ch_01",
  "page": 5,
  "duration": 240,
  "mistakes": [
    {"word": "apple", "attempts": 2},
    {"word": "orange", "attempts": 1}
  ],
  "device": {"type": "tablet", "os": "android"}
}
```

## 🏗️ 2. Approach A - Using Cassandra Collections (Structured JSON)

Cassandra supports:

- `Map<Text, Text>` (key-value)
- `List<Text>`
- `Set<Text>`

### ✅ Model Example

```python
from django_cassandra_engine.models import DjangoCassandraModel
from cassandra.cqlengine import columns
from uuid import uuid4
from datetime import datetime

class ReadingProgress(DjangoCassandraModel):
    student_id = columns.UUID(primary_key=True)
    chapter_id = columns.Text(primary_key=True)
    timestamp = columns.DateTime(default=datetime.now)
    
    # Nested data stored in collections
    mistakes = columns.List(columns.Map(columns.Text, columns.Text))  # [{"word": "apple", "attempts": "2"}, ...]
    device = columns.Map(columns.Text, columns.Text)  # {"type": "tablet", "os": "android"}
    stats = columns.Map(columns.Text, columns.Text)   # {"page": "5", "duration": "240"}
```

### ✅ Writing Data

```python
ReadingProgress.create(
    student_id=uuid4(),
    chapter_id="ch_01",
    mistakes=[
        {"word": "apple", "attempts": "2"},
        {"word": "orange", "attempts": "1"}
    ],
    device={"type": "tablet", "os": "android"},
    stats={"page": "5", "duration": "240"}
)
```

### ✅ Reading Data

```python
progress = ReadingProgress.objects.get(student_id=my_id, chapter_id="ch_01")
print(progress.device["type"])  # tablet
print(progress.mistakes[0]["word"])  # apple
```

### ✅ Updating Nested Data

```python
progress.device["os"] = "ios"
progress.save()
```

### ✅ Querying by Map Key

You can filter using map keys if the key is indexed:

```sql
SELECT * FROM readingprogress WHERE device['type'] = 'tablet';
```

But note:

Cassandra map key queries are limited - they can be slow unless properly indexed or flattened.

## 🧱 3. Approach B - Store Full JSON in a Text Field (Unstructured JSON)

When your JSON schema varies across records (e.g., dynamic metadata or analytics),  
it's better to store JSON as a **stringified JSON blob**.

### ✅ Model Example

```python
class StudentActivity(DjangoCassandraModel):
    student_id = columns.UUID(primary_key=True)
    timestamp = columns.DateTime(primary_key=True, clustering_order="DESC")
    activity_data = columns.Text()  # JSON string
```

### ✅ Writing JSON Data

```python
import json

data = {
    "chapter_id": "ch_02",
    "page": 3,
    "duration": 180,
    "device": {"type": "mobile", "os": "android"}
}

StudentActivity.create(
    student_id=my_id,
    timestamp=datetime.now(),
    activity_data=json.dumps(data)
)
```

### ✅ Reading JSON Data

```python
activity = StudentActivity.objects.filter(student_id=my_id).first()
data = json.loads(activity.activity_data)
print(data["device"]["type"])  # mobile
```

### ✅ Updating JSON Partially

To update JSON efficiently:

- Fetch
- Modify in Python
- Save again

```python
data = json.loads(activity.activity_data)
data["page"] = 4
activity.activity_data = json.dumps(data)
activity.save()
```

## ⚡ 4. Optimized Hybrid Model (Structured + JSON)

For high-frequency queries, keep **key searchable fields as columns**,  
and store the rest of the dynamic structure as JSON.

### ✅ Example

```python
class ChapterPerformance(DjangoCassandraModel):
    student_id = columns.UUID(primary_key=True)
    chapter_id = columns.Text(primary_key=True)
    score = columns.Integer(index=True)
    duration = columns.Integer()
    extra_data = columns.Text()  # holds nested JSON
```

### ✅ Usage

```python
ChapterPerformance.create(
    student_id=uuid4(),
    chapter_id="ch_01",
    score=85,
    duration=230,
    extra_data=json.dumps({
        "mistakes": [{"word": "cat", "attempts": 1}],
        "feedback": {"clarity": "good", "speed": "slow"}
    })
)
```

✅ **Advantages**

- Frequently queried fields (like score) are indexed and fast.
- Rare/dynamic fields are inside extra_data.

## 🔍 5. Query Techniques

### 1\. Querying Structured Columns

```python
high_scores = ChapterPerformance.objects.filter(score__gte=90)
```

### 2\. Querying JSON Fields (in Python)

Since JSON fields are strings, Cassandra cannot natively query inside them.  
You query in Python after fetching:

```python
records = ChapterPerformance.objects.all()
for record in records:
    data = json.loads(record.extra_data)
    if data.get("feedback", {}).get("clarity") == "good":
        print(record)
```

### 3\. Using Materialized Views

To optimize querying on a nested field, create a **materialized view** for that property:

```sql
CREATE MATERIALIZED VIEW chapterperformance_by_score AS
  SELECT * FROM chapterperformance
  WHERE score IS NOT NULL AND student_id IS NOT NULL AND chapter_id IS NOT NULL
  PRIMARY KEY (score, student_id, chapter_id);
```

Now:

```sql
SELECT * FROM chapterperformance_by_score WHERE score = 85;
```

## 🧠 6. Optimization Tips

| **Strategy** | **Description** |
| --- | --- |
| **Use Maps for small structured JSON** | If keys are consistent |
| **Use Text (JSON)** | For unstructured or deeply nested data |
| **Hybrid approach** | For query + flexibility balance |
| **Avoid frequent updates on same row** | Causes tombstones |
| **Pre-compute materialized views** | For common queries |
| **Compress JSON string** | If JSON is large |
| **Use Redis for cached JSON lookups** | Improves read speed |

## 🚀 7. Caching JSON Data

Combine Cassandra with Redis or Django cache to speed up nested lookups.

```python
from django.core.cache import cache

def get_student_activity(student_id):
    cache_key = f"student_activity_{student_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    activity = StudentActivity.objects.filter(student_id=student_id).first()
    if not activity:
        return None

    data = json.loads(activity.activity_data)
    cache.set(cache_key, data, timeout=120)
    return data
```

## 🧩 8. Real-World Example: Complete Model

```python
class StudentSession(DjangoCassandraModel):
    student_id = columns.UUID(primary_key=True)
    session_id = columns.UUID(primary_key=True)
    start_time = columns.DateTime()
    end_time = columns.DateTime()
    
    # Fast-query columns
    total_words = columns.Integer(index=True)
    accuracy = columns.Float()

    # Nested JSON data
    details = columns.Text()  # {"chapters": [{"id": "ch_1", "score": 95}], "feedback": {...}}
```
### Writing

```python
StudentSession.create(
    student_id=uuid4(),
    session_id=uuid4(),
    start_time=datetime.now(),
    end_time=datetime.now(),
    total_words=500,
    accuracy=92.5,
    details=json.dumps({
        "chapters": [
            {"id": "ch_1", "score": 95, "mistakes": ["apple", "banana"]}
        ],
        "feedback": {"overall": "great"}
    })
)
```

### Reading

```python
session = StudentSession.objects.filter(student_id=uuid4()).first()
details = json.loads(session.details)
print(details["feedback"]["overall"])
```

## 🧠 Summary Table

| **Approach** | **Data Type** | **Query Support** | **Best For** | **Example** |
| --- | --- | --- | --- | --- |
| **Map/List/Set** | Native Cassandra collections | Partial (by key) | Structured JSON | device={"os":"android"} |
| **Text (JSON string)** | Unstructured | None (manual parse) | Dynamic JSON | activity_data=json.dumps({...}) |
| **Hybrid** | Mix of both | Optimized | Flexible + performant | Structured + extra_data |
| **Materialized Views** | Derived tables | High | Precomputed queries | Query on nested key like "score" |
| **Cache layer** | Redis or Django Cache | N/A | Fast retrieval | Cache complex JSON lookups |