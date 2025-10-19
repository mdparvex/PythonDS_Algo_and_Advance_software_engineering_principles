# 🧭 Technical Documentation: **Database Replication**

## ****1\. Introduction****

**Database replication** is the process of **copying and maintaining database objects (tables, schema, indexes, etc.) in multiple databases** that make up a distributed database system.  
The goal is to **increase availability, improve read performance, ensure fault tolerance**, and **provide disaster recovery**.

In production environments-especially those handling **high read/write traffic** or requiring **high availability**-replication is a **core component** of database architecture.

## ****2\. Core Concepts****

### ****2.1 What is Database Replication?****

Database replication means that **data written to one database (primary/master)** is automatically **copied to one or more secondary (replica/slave)** databases.

This replication can be:

- **Synchronous:** Changes are written to replicas at the same time as the primary.
- **Asynchronous:** Changes are written to replicas after the primary commits.

### ****2.2 Goals of Replication****

| **Goal** | **Description** |
| --- | --- |
| **High Availability (HA)** | If the primary fails, replicas can take over (failover). |
| **Load Balancing** | Read queries can be distributed among replicas. |
| **Disaster Recovery** | Backups can be done from replicas to offload primary. |
| **Geo-distribution** | Place replicas closer to users in different regions. |

### ****2.3 Replication Models****

| **Replication Type** | **Description** | **Example** |
| --- | --- | --- |
| **Single-Master Replication** | One master handles all writes; replicas only read. | PostgreSQL primary → read replicas |
| **Multi-Master Replication** | All nodes can handle writes; conflict resolution needed. | Galera Cluster, AWS Aurora Multi-Master |
| **Peer-to-Peer Replication** | All peers replicate changes to each other. | CouchDB, Cassandra |
| **Log-Based Replication** | Changes captured from database logs (WAL, binlog). | PostgreSQL, MySQL |
| **Trigger-Based Replication** | Database triggers capture changes. | Used in logical replication tools like SymmetricDS |

## ****3\. PostgreSQL Replication Overview****

PostgreSQL supports two major replication types:

- **Streaming Replication (Physical Replication):**
  - Byte-level copy of WAL (Write-Ahead Log) files.
  - The replica is a binary copy of the primary.
  - Best for failover and read-only queries.
- **Logical Replication:**
  - Replicates data at the logical level (tables, rows).
  - Allows filtering specific tables or schemas.
  - Used for migration, selective sync, and cross-version replication.

## ****4\. How Synchronization Works (Internally)****

When a write happens on the **Primary**:

- PostgreSQL writes the change to the **WAL (Write-Ahead Log)**.
- The **WAL is sent** to all configured replicas.
- Replicas **replay** the WAL records in order.
- Depending on replication mode:
  - **Synchronous:** The primary waits for at least one replica to confirm.
  - **Asynchronous:** The primary does not wait.

This guarantees **data consistency** and **crash recovery** integrity.

## ****5\. Architecture Diagram****

```pgsql
               ┌───────────────────────────┐
               │        Application         │
               │   (Writes + Reads)         │
               └──────────┬────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  Primary Database   │
                │ (WAL Producer)      │
                └───────┬─────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│ Read Replica 1   │        │ Read Replica 2   │
│ (WAL Consumer)   │        │ (WAL Consumer)   │
└──────────────────┘        └──────────────────┘

```

## ****6\. Production-Level Example: PostgreSQL Streaming Replication on AWS****

### ****6.1 Prerequisites****

- **Two EC2 instances (Ubuntu 22.04 or Amazon Linux):**
  - db-primary
  - db-replica
- **PostgreSQL 15+**
- **Network Access:** Allow TCP port **5432**
- **SSH Access** between primary and replica

### ****6.2 On Primary Node (db-primary)****

#### Step 1: Edit PostgreSQL configuration

Edit `/etc/postgresql/15/main/postgresql.conf`:

```bash
wal_level = replica
max_wal_senders = 5
wal_keep_size = 256MB
listen_addresses = '*'
```

#### Step 2: Update `pg_hba.conf`

Allow replication connection from replica:

```bash
host replication replicator <replica_ip>/32 md5
```

#### Step 3: Create Replication User

```sql
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replica_pass';
```

#### Step 4: Restart PostgreSQL

```bash
sudo systemctl restart postgresql
```

### ****6.3 On Replica Node (db-replica)****

#### Step 1: Stop PostgreSQL

```bash
sudo systemctl stop postgresql
```

#### Step 2: Clear old data directory

```bash
sudo rm -rf /var/lib/postgresql/15/main/*
```

#### Step 3: Base backup from primary

```bash
pg_basebackup -h <primary_ip> -D /var/lib/postgresql/15/main -U replicator -P -v -R
```

#### Step 4: Start PostgreSQL

```bash
sudo systemctl start postgresql
```

### ****6.4 Verify Replication****

Run on replica:

```sql
SELECT * FROM pg_stat_wal_receiver;
```

Run on primary:

```sql
SELECT client_addr, state FROM pg_stat_replication;
```

## ****7\. How Queries Work in Different Replicas****

| **Query Type** | **Executed On** | **Description** |
| --- | --- | --- |
| **Write (INSERT/UPDATE/DELETE)** | **Primary** | Writes are always performed on the primary. |
| **Read (SELECT)** | **Replica(s)** | Read queries can be offloaded to replicas. |
| **DDL (ALTER, CREATE TABLE)** | **Primary** | Schema changes propagate via WAL replication. |
| **System Catalog Queries** | **Primary only** | Replicas are read-only. |

To balance read traffic, applications or load balancers (like **PgPool-II**, **HAProxy**, or **AWS RDS Proxy**) route queries:

```bash
SELECT * FROM users;        -- Sent to replica
INSERT INTO users ...       -- Sent to primary
```

## ****8\. Tools and Technologies for Efficient Synchronization****

| **Tool / Service** | **Description** | **Use Case** |
| --- | --- | --- |
| **AWS RDS Read Replicas** | Managed read replicas for PostgreSQL, MySQL. | Cloud-native high availability |
| **PgPool-II / HAProxy** | Connection pooling & query routing. | Load balancing between replicas |
| **Patroni + etcd** | Automatic failover management for PostgreSQL. | High availability clusters |
| **Barman / WAL-G** | WAL archiving and recovery. | Backup and disaster recovery |
| **AWS Aurora Replication** | Proprietary storage-level replication. | Multi-AZ fault tolerance |

## ****9\. Failover Mechanism****

If the primary fails:

- The monitoring system (e.g., **Patroni**, **AWS RDS**) detects failure.
- Promotes one replica to **become the new primary**:
    ```sql
    SELECT pg_promote();
    ```
- Applications reconnect to the new primary.
- Former primary can be reinitialized as a replica.

## ****10\. Replication Monitoring Queries****

Check replication lag:

```sql
SELECT 
  client_addr, 
  state, 
  pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replication_lag
FROM pg_stat_replication;
```

Monitor WAL receiver status (on replica):

```sql
SELECT status, last_msg_receipt_time FROM pg_stat_wal_receiver;
```

## ****11\. Real-World AWS Example****

Using **Amazon RDS for PostgreSQL**:

- Create an RDS PostgreSQL instance.
- From AWS Console → select **"Create Read Replica"**.
- AWS automatically:
  - Sets up replication.
  - Manages WAL streaming.
  - Enables automated failover (if Multi-AZ is enabled).
- You can connect:
    ```bash
        psql -h primary-instance.us-east-1.rds.amazonaws.com
        psql -h read-replica.us-east-1.rds.amazonaws.com
    ```

AWS RDS uses **asynchronous streaming replication** for high efficiency, and replicas can be promoted automatically or manually.

## ****12\. Best Practices****

✅ Use **asynchronous replication** for performance unless strict consistency is required.  
✅ Always use **monitoring tools** (e.g., pg_stat_replication).  
✅ **Encrypt replication traffic** using SSL.  
✅ For production, consider **automatic failover** with **Patroni** or **AWS Multi-AZ**.  
✅ **Use connection pooling** (PgBouncer/PgPool-II).  
✅ Regularly **test failover and backups**.

## ****13\. Summary****

| **Concept** | **Explanation** |
| --- | --- |
| **Primary** | Main database that handles writes. |
| **Replica** | Copy of primary for reads and failover. |
| **Replication Type** | Physical or Logical. |
| **Synchronization Mechanism** | WAL-based streaming. |
| **Performance Tools** | PgPool-II, HAProxy, RDS Proxy. |
| **Failover Tools** | Patroni, AWS Multi-AZ, Repmgr. |

---

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

---

# 📘 Technical Documentation: Database Replication in AWS with PostgreSQL and Django

## 🧠 1. Understanding Database Replication

**Database replication** is the process of **copying and maintaining database objects** (like tables, indexes, and data) **across multiple databases**.  
In a production system, replication ensures:

- **High Availability (HA)** - if the primary (master) database fails, a replica can take over.
- **Load Balancing** - read queries can be distributed among replicas.
- **Disaster Recovery (DR)** - replicas act as backups for rapid recovery.
- **Geographical Distribution** - replicas can be placed closer to users to reduce latency.

### 🔁 Types of Replication

| **Type** | **Description** | **Example** |
| --- | --- | --- |
| **Physical Replication** | Copies the entire data files (byte-level) from primary to replica. | PostgreSQL streaming replication |
| **Logical Replication** | Copies specific data or tables (row-level changes using WAL decoding). | PostgreSQL logical replication |
| **Synchronous** | The replica confirms the transaction before commit. | Ensures zero data loss |
| **Asynchronous** | The primary commits first, then sends data to replicas. | Faster, but risk of data lag |

## 🧩 2. PostgreSQL Replication in AWS (Production Setup)

Let's use **Amazon RDS for PostgreSQL** as our example.

### ****Architecture Overview****
```pgsql
                  ┌──────────────────┐
                  │   Web Server(s)  │
                  │  (Django App)    │
                  └──────┬───────────┘
                         │
                 ┌───────┴────────┐
                 │   Primary DB   │  (Writer)
                 │  RDS PostgreSQL│
                 └──────┬─────────┘
                        │
        ┌───────────────┴────────────────────┐
        │ Replication (Streaming or Logical) │
        └───────┬───────────┬────────────────┘
                │           │
        ┌───────┴─────┐ ┌───┴────────┐
        │ Read Replica│ │Read Replica│
        └─────────────┘ └────────────┘
```

### ****Step-by-Step Setup in AWS RDS****

#### **Step 1: Create Primary Database**

- Go to **AWS RDS → Databases → Create database**.
- Choose:
  - **Engine:** PostgreSQL
  - **Deployment:** Multi-AZ (recommended for HA)
- Configure instance (CPU, memory, storage).
- Set credentials and security group rules (allow access from your app EC2/VPC).
- Create the database.

#### **Step 2: Create Read Replica**

- Select your **primary RDS instance**.
- Choose **Actions → Create read replica**.
- Configure:
  - Instance type
  - Availability Zone
  - Enable **Multi-AZ** if needed for the replica
- AWS will automatically set up **streaming replication**.
- Once complete, you'll have:
  - **Writer Endpoint:** &lt;primary-endpoint&gt;.rds.amazonaws.com
  - **Reader Endpoint:** &lt;replica-endpoint&gt;.rds.amazonaws.com

AWS uses **asynchronous physical replication** by default for replicas.

#### **Step 3: Connect Django to Multiple Databases**

In Django, we can use **database routers** to direct read/write queries to the appropriate database.

**settings.py:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'USER': 'admin',
        'PASSWORD': 'mypassword',
        'HOST': 'primary-db.rds.amazonaws.com',
        'PORT': '5432',
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'USER': 'admin',
        'PASSWORD': 'mypassword',
        'HOST': 'replica-db.rds.amazonaws.com',
        'PORT': '5432',
    }
}
```

### ****Step 4: Create a Database Router****

Create a file db_router.py:

```python
import random

class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        """Route all read operations to replica."""
        return 'replica'

    def db_for_write(self, model, **hints):
        """Route all write operations to primary."""
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if both objects are in same DB."""
        db_list = ('default', 'replica')
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only on primary DB."""
        return db == 'default'
```

Then in settings.py:

```python
DATABASE_ROUTERS = ['path.to.db_router.PrimaryReplicaRouter']
```

### ****Step 5: Using the Router in Queries****

```python
from django.db import connections
from myapp.models import Student

# Write Operation → Goes to Primary
student = Student.objects.create(name="John Doe")

# Read Operation → Goes to Replica
students = Student.objects.using('replica').all()

# Or automatically handled by the router
students = Student.objects.all()
```

## ⚙️ 3. Synchronization in PostgreSQL

### ****Mechanism****

PostgreSQL uses **WAL (Write-Ahead Logging)** for replication.

- Every change in the primary is written into a WAL log.
- The WAL records are streamed to replicas.
- Replicas **replay the WAL logs** to maintain a consistent state.

### ****Efficient Synchronization Technologies****

| **Technology** | **Description** | **Use Case** |
| --- | --- | --- |
| **Streaming Replication** | Default in PostgreSQL. Uses WAL files to stream data to standby. | AWS RDS default setup |
| **Logical Replication** | Replicates selected tables; used for partial data replication. | Multi-tenant or analytics systems |
| **pglogical** | PostgreSQL extension offering advanced logical replication. | Cross-version or hybrid cloud setups |

## 📖 4. Query Behavior in Replicated Systems

| **Operation** | **Routed To** | **Reason** |
| --- | --- | --- |
| **SELECT** | Replica | Load balancing, reduce primary load |
| **INSERT** | Primary | Write operations are only allowed in the primary |
| **UPDATE** | Primary | Maintains data consistency |
| **DELETE** | Primary | Avoid data drift |
| **ANALYTICS / REPORTS** | Replica | Read-heavy, non-critical queries |

**Note:**  
If replication lag is high, you can:

- Use **read-your-writes consistency** (force reads from primary after write)
- Monitor lag via pg_stat_replication table

## 🧪 5. Monitoring and Maintenance

### Monitor using

```sql
SELECT
  client_addr,
  state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  (sent_lsn - replay_lsn) AS replication_lag
FROM pg_stat_replication;
```

### AWS Tools

- **Amazon RDS Performance Insights**
- **CloudWatch metrics:**  
    ReplicaLag, CPUUtilization, FreeStorageSpace

## 🛡️ 6. Best Practices

✅ Always enable **Multi-AZ Deployment** for automatic failover  
✅ Use **parameter groups** to tune WAL retention  
✅ Regularly monitor **replica lag**  
✅ Use **SSL connections** between replicas  
✅ Automate **failover** with AWS Route 53 or RDS Failover Policies  
✅ Test **disaster recovery** quarterly

## 🚀 Example Flow: Read and Write in Django

**User Registration (Write)**  
→ Django writes to Primary (default)  
→ WAL updated  
→ AWS streams changes to Replica

**Dashboard View (Read)**  
→ Django router sends read to Replica  
→ Replica serves query instantly

This ensures **scalability**, **fault tolerance**, and **cost efficiency**.

## 🧭 Summary

| **Aspect** | **Description** |
| --- | --- |
| **Technology** | PostgreSQL Streaming Replication |
| **Environment** | AWS RDS Multi-AZ + Read Replica |
| **Django Integration** | Multi-DB setup with custom routers |
| **Read/Write Logic** | Writes → Primary, Reads → Replica |
| **Synchronization** | WAL-based streaming |
| **Efficiency** | High availability, fault-tolerant, scalable |