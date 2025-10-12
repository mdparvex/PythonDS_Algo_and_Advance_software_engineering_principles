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

