# Distributed Consensus: Raft & Paxos

## 1. Introduction

In distributed systems, multiple independent nodes (servers) must work together to provide a single, reliable service. These nodes can fail, restart, or become temporarily unreachable due to network issues. **Consensus algorithms** solve the fundamental problem of **how multiple nodes agree on a single value or sequence of values**, even in the presence of failures.

Examples of what needs consensus:
- Who is the leader?
- What is the current configuration/state?
- In which order should operations be applied?

Two of the most influential consensus algorithms are **Paxos** and **Raft**.

---

## 2. Why Consensus Is Needed

Without consensus:
- Data can diverge between nodes
- Multiple leaders may act at once (split-brain)
- Clients may see inconsistent results

Consensus is essential for:
- **Distributed databases** (etcd, Consul, ZooKeeper)
- **Configuration management**
- **Service discovery**
- **Leader election**
- **Strong consistency guarantees**

> In short: consensus ensures *safety* (nothing bad happens) and *liveness* (something good eventually happens).

---

## 3. Core Properties of Consensus Algorithms

A correct consensus algorithm typically guarantees:

1. **Safety** – No two nodes decide on different values
2. **Liveness** – The system eventually makes progress
3. **Fault Tolerance** – Continues to work despite node failures
4. **Determinism** – Same inputs lead to the same outputs

Most modern consensus systems tolerate **fail-stop failures** and assume an **asynchronous network**.

---

## 4. Paxos

### 4.1 Overview

Paxos is a family of algorithms introduced by **Leslie Lamport**. It is mathematically elegant but notoriously difficult to understand and implement correctly.

Paxos focuses on **agreeing on a single value**. Repeated execution is required to agree on a sequence of values.

---

### 4.2 Paxos Roles

1. **Proposer** – Suggests a value
2. **Acceptor** – Votes on proposed values
3. **Learner** – Learns the chosen value

A single node can play multiple roles.

---

### 4.3 Paxos Phases

#### Phase 1: Prepare
- Proposer sends a *prepare request* with a proposal number
- Acceptors promise not to accept smaller proposal numbers

#### Phase 2: Accept
- Proposer sends an *accept request* with a value
- Acceptors accept if they haven't promised a higher proposal

Once a **majority** accepts, the value is chosen.

---

### 4.4 Strengths of Paxos

- Proven correctness
- Extremely fault tolerant
- Foundation for many systems (Multi-Paxos)

### 4.5 Weaknesses of Paxos

- Very hard to understand
- Difficult to implement correctly
- Poor readability for engineers

> Paxos is often said to be *simple, but not easy*.

---

## 5. Raft

### 5.1 Overview

Raft was designed specifically to be **understandable** while providing the same guarantees as Paxos.

Raft breaks consensus into **three clearly separated concerns**:
1. Leader election
2. Log replication
3. Safety

---

### 5.2 Raft Node Roles

1. **Leader** – Handles all client requests
2. **Follower** – Replicates log entries
3. **Candidate** – Competes to become leader

At any time, there is **at most one leader**.

---

### 5.3 Raft Leader Election

- Followers start an election if they don't hear from a leader
- Candidates request votes
- Majority wins
- Elections are randomized to avoid split votes

---

### 5.4 Log Replication

1. Client sends request to leader
2. Leader appends entry to its log
3. Leader replicates entry to followers
4. Entry is committed once a majority acknowledges
5. Leader applies entry to the state machine

---

### 5.5 Safety Guarantees

- Logs are identical up to the committed index
- A leader always has the most up-to-date log
- Once committed, entries are never lost

---

### 5.6 Strengths of Raft

- Easy to reason about
- Clear leader-based design
- Widely adopted (etcd, Consul)

### 5.7 Weaknesses of Raft

- Leader can become a bottleneck
- Less flexible than Paxos variants

---

## 6. Paxos vs Raft (Comparison)

| Feature | Paxos | Raft |
|------|------|------|
| Understandability | Very hard | Easy |
| Leader concept | Optional | Mandatory |
| Adoption | Academic / Core infra | Industry standard |
| Implementation | Complex | Straightforward |

---

## 7. Real-Life Use Cases

### 7.1 Systems Using Paxos
- Google Chubby
- Google Spanner (internally)

### 7.2 Systems Using Raft
- etcd (Kubernetes)
- Consul
- Nomad
- RethinkDB

---

## 8. Real-Life Example with Django

Django itself does **not** implement consensus, but often **depends on systems that do**.

### 8.1 Example: Leader Election for Background Jobs

Imagine multiple Django instances running Celery beat-like scheduled tasks.

**Problem:**
- If every instance runs the scheduler, tasks execute multiple times.

**Solution using Raft-backed etcd:**
- Store leader information in etcd
- Only the elected leader runs scheduled jobs

Flow:
1. Django instances register with etcd
2. Raft elects a leader
3. Leader acquires a distributed lock
4. Only leader executes periodic jobs

---

### 8.2 Example: Strongly Consistent Feature Flags

Using etcd:
- Feature flags stored in Raft-replicated logs
- All Django instances read the same committed state
- Updates are atomic and strongly consistent

---

### 8.3 Example: Distributed Locks

```python
# Pseudo-code using etcd client
with etcd.lock("order_processing"):
    process_order()
```

Raft ensures:
- Only one node holds the lock
- Lock state survives node crashes

---

## 9. When NOT to Use Consensus

Avoid consensus when:
- Eventual consistency is acceptable
- High write throughput is needed
- Network latency is unpredictable

Examples:
- Caching layers
- Analytics pipelines
- Logging systems

Consensus trades **performance** for **correctness**.

---

## 10. Design Guidelines

- Prefer **Raft** unless you have deep expertise
- Use existing libraries (etcd, Consul)
- Never implement Paxos from scratch in production
- Minimize consensus scope (small critical data only)

---

## 11. Summary

- Consensus is fundamental to distributed systems
- Paxos is powerful but complex
- Raft provides the same guarantees with clarity
- Django applications commonly rely on Raft-based systems indirectly

> If you understand Raft, you understand practical consensus.

---

## 12. Further Reading

- "In Search of an Understandable Consensus Algorithm" – Diego Ongaro
- Leslie Lamport’s Paxos papers
- etcd & Raft documentation

---

Let's do this **hands-on and minimal**, so you clearly see:

- **What problem consensus solves**
- **Why it's hard without it**
- **How Raft (via etcd) fixes it**
- **A small Django-based project you can actually run**

**Simple Project: Distributed Leader Election for Django Cron Jobs**

**The Problem (Very Real)**

Imagine this setup:

- You run **3 Django instances** behind a load balancer
- Each instance runs a **background task** every minute
- Example task:
  - Send appointment reminders
  - Reconcile payments
  - Sync courier statuses

**❌ Without Consensus**

Each instance runs the same task:

```css
Instance A → sends reminders
Instance B → sends reminders
Instance C → sends reminders
```

Result:

- Duplicate emails
- Double payments
- Corrupted state

**❌ Naive Fixes (that fail)**

- Database row lock ❌ (DB overload, split brain during failover)
- Redis lock ❌ (lock lost on restart, no safety guarantees)
- ENV variable "IS_LEADER=true" ❌ (manual, unsafe)

👉 **This is exactly the problem consensus solves.**

**What Consensus Gives You**

Using **Raft** (via etcd):

- Exactly **ONE leader** at a time
- Leader automatically changes if a node crashes
- Strong consistency
- No split-brain

**Project Overview**

**🎯 Goal**

Only **one Django instance** runs a scheduled job at any time.

**🧠 Tooling**

- **Django** (your app)
- **etcd** (Raft-based consensus system)
- **python-etcd3** client

**Architecture (Simple)**

```pgsql
+-------------------+
|   etcd cluster    |
|  (Raft consensus) |
+---------+---------+
          |
          |
+---------+----------+----------+
| Django A | Django B | Django C |
| (worker) | (worker) | (worker) |
+----------+----------+----------+

Only the elected leader runs the job
```

**Step 1: Run etcd (Single Node - OK for learning)**

```bash
docker run -d \
  -p 2379:2379 \
  -p 2380:2380 \
  --name etcd \
  quay.io/coreos/etcd:latest \
  etcd \
  --advertise-client-urls http://0.0.0.0:2379 \
  --listen-client-urls http://0.0.0.0:2379
```

etcd internally uses **Raft**, even if you run one node.

**Step 2: Install Dependency**
```bash
pip install etcd3
```
**Step 3: Leader Election Logic (Core Idea)**

**leader.py**

```python
import etcd3
import socket
import time

client = etcd3.client(host='localhost', port=2379)
INSTANCE_ID = socket.gethostname()

def try_become_leader():
    """
    Try to become leader using a lease (TTL-based lock)
    """
    lease = client.lease(ttl=10)

    success, _ = client.transaction(
        compare=[
            client.transactions.version('/leader') == 0
        ],
        success=[
            client.transactions.put('/leader', INSTANCE_ID, lease)
        ],
        failure=[]
    )

    return success, lease
```

**Step 4: Periodic Job (Only Leader Runs It)**

**job.py**

```python
def run_critical_job():
    print("Running critical job: sending reminders...")
```

**Step 5: Worker Loop**

**worker.py**

```python
from leader import try_become_leader
from job import run_critical_job
import time

while True:
    is_leader, lease = try_become_leader()

    if is_leader:
        print("I am the leader")
        while True:
            run_critical_job()
            lease.refresh()  # keep leadership
            time.sleep(5)
    else:
        print("Follower: waiting for leader")
        time.sleep(3)
```

**What's Happening Internally (Important)**

**1️⃣ Leader Election**

- All Django instances try to write /leader
- Raft guarantees **only one succeeds**

**2️⃣ Lease (TTL)**

- If leader crashes → lease expires
- New election happens automatically

**3️⃣ Safety**

- Two leaders **cannot exist**
- Raft ensures majority agreement

**Kill the Leader (Try This)**

- Run the worker in 2-3 terminals
- Kill the leader process
- Watch another instance become leader automatically

✅ **This is consensus in action**

**What Problem Did We Solve?**

| **Problem** | **Without Consensus** | **With Raft** |
| --- | --- | --- |
| Duplicate jobs | Yes | No  |
| Split brain | Possible | Impossible |
| Manual failover | Required | Automatic |
| Safety guarantee | Weak | Strong |

**Why This Works (Raft Under the Hood)**

Raft ensures:

- Only **one committed value** for /leader
- Majority agreement
- Order of operations
- Automatic recovery

You didn't implement Raft - **you used it correctly**.

**Where This Appears in Real Systems**

- Kubernetes leader election
- Celery Beat HA
- Django cron jobs
- Feature flags
- Distributed locks
- Service discovery

**Mental Model (Remember This)**

**Consensus = one truth, agreed by many, even when some fail**

---

if you understand this well, **Raft / Paxos / CAP / modern databases will all make sense**.

I'll explain this in a **clean, progressive way**:

- What a distributed database system is
- When you should (and should not) use it
- Why consensus is needed
- A concrete failure scenario (step-by-step)
- How consensus fixes it

No hand-waving.

**1️⃣ What Is a Distributed Database System?**

A **distributed database system** is a database where:

**Data is stored across multiple machines  
but appears as a single logical database to the user.**

**Key Characteristics**

- Multiple nodes (servers)
- Data is **replicated** and/or **sharded**
- Nodes communicate over a **network**
- System continues to work even if some nodes fail

**Examples**

- CockroachDB
- Google Spanner
- Cassandra
- MongoDB (Replica Sets)
- DynamoDB

**Single Database vs Distributed Database**

| **Feature** | **Single DB** | **Distributed DB** |
| --- | --- | --- |
| Location | One machine | Many machines |
| Failure | Total outage | Partial failure |
| Scaling | Vertical | Horizontal |
| Complexity | Low | High |

**2️⃣ When Should You Use a Distributed Database?**

**✅ Use When**

- You need **high availability**
- You need **horizontal scaling**
- You need **fault tolerance**
- You serve **multiple regions**
- Downtime is unacceptable

**❌ Do NOT Use When**

- Single-node DB handles your load
- Strong consistency is not required
- You don't have distributed systems expertise
- Simplicity is more important than availability

**Rule of thumb:**  
If one PostgreSQL instance can handle it, don't distribute.

**3️⃣ The Core Problem: Why Distributed Is Hard**

In a distributed database:

- Nodes can crash
- Network can delay or drop messages
- Messages can arrive out of order
- You cannot distinguish:

_Is the node slow, or is it dead?_

This is called the **partial failure problem**.

**4️⃣ Why Consensus Is Needed**

**Definition (Simple)**

**Consensus is how multiple nodes agree on one truth,  
even when some of them fail.**

Without consensus:

- Each node may believe a different truth
- Data diverges
- System becomes unsafe

**5️⃣ Failure Scenario (Very Important)**

**Scenario: Distributed Orders Table**

**Setup**

- 3 database nodes: **A, B, C**
- Data is **replicated**
- We want to generate **order IDs**

```ini
order_id = last_id + 1
```

**Step 1: Normal Operation**
```python
Last order_id = 100
```
All nodes agree.

**Step 2: Network Partition Occurs**

```css
A  <——>  B      C (isolated)
```

Node C cannot communicate with A and B.

**Step 3: Writes Without Consensus (DISASTER)**

Client writes order on **Node A**:
```ini
A writes order_id = 101
```
Client writes order on **Node C**:
```ini
C writes order_id = 101
```
Both accept writes.

**❌ Result**

- Duplicate primary keys
- Data divergence
- Corruption

This is called **split-brain**.

**6️⃣ Why Locks or Master DB Alone Don't Fix This**

**❌ DB Locks**

- Locks don't cross networks reliably
- Lock holder may be dead, but others can't tell

**❌ "Primary" Node Alone**

- How do others know primary is dead?
- Two primaries may exist during partition

👉 **This is the root of the problem.**

**7️⃣ How Consensus Fixes This**

Consensus introduces a rule:

**A write is valid only if a majority agrees.**

In a 3-node system:

- Majority = 2 nodes

**Step-by-Step with Consensus (Raft)**

**Step 1: Leader Exists**

- One leader elected (say Node A)
- Only leader accepts writes

**Step 2: Client Writes**

Client sends write to leader A.

Leader:

- Appends write to log
- Sends log to B and C
- Waits for **majority acknowledgment**
- Commits write

**Step 3: Partition Happens**

```css
A <——> B     C isolated
```

- A + B = majority → writes allowed
- C = minority → **writes rejected**

**✅ Result**

- No duplicate IDs
- No divergence
- Safety preserved

Availability is reduced, but correctness is preserved.

**8️⃣ Concrete Example (Pseudo-Code)**

```python
def write_order(order):
    if not majority_alive():
        raise Exception("Cannot commit write")

    append_to_log(order)
    replicate_to_followers(order)
    commit()
```

This is what Raft/Paxos automate for you.

**9️⃣ What Consensus Actually Guarantees**

✔ Single global order of writes  
✔ No conflicting commits  
✔ Safe recovery after crashes  
✔ Deterministic state rebuild

**🔑 Mental Model (Memorize This)**

**Distributed database = replicated log + deterministic state machine**

Consensus controls the **log**.  
Database applies the **state machine**.

**10️⃣ CAP Theorem (Brief but Critical)**

You cannot have all three:

- **C**onsistency
- **A**vailability
- **P**artition tolerance

Consensus systems choose:

**Consistency + Partition tolerance**

They sacrifice availability **temporarily**.

**11️⃣ Real Systems**

| **System** | **Consensus** |
| --- | --- |
| etcd | Raft |
| CockroachDB | Raft |
| Spanner | Paxos |
| MongoDB | Raft |
| ZooKeeper | Zab |

**12️⃣ Final Summary**

- Distributed databases exist to scale and survive failures
- Networks fail - always
- Without consensus, data becomes corrupt
- Consensus ensures one agreed truth
- Raft is the practical, understandable solution

---

distributed databases are **where consensus really clicks**.  
Let's build a **very small, concrete project** that shows:

**Why distributed databases break without consensus  
and how Raft fixes it**

No theory first - **problem → failure → fix**.

**Example Project**

**Strongly Consistent Counter (Distributed Database Core)**

We'll build a **distributed counter** shared by multiple Django instances.

**1️⃣ The Real Problem**

Imagine this table in a distributed system:
```ini
order_number = 105
```
Multiple API servers generate order IDs:
```ini
order_id = order_number + 1
```
**❌ Without Consensus**

Two servers read at the same time:

```css
Server A reads: 105
Server B reads: 105
```

Both write:

```css
106 ❌ DUPLICATE
```

This is **NOT a Django bug**.  
This is a **distributed systems problem**.

**2️⃣ Naive Fixes (And Why They Fail)**

**❌ Database Auto Increment**

- Works only with **single primary**
- Breaks with multi-master or sharding

**❌ Redis INCR**

- Redis crash → data loss
- Failover → split brain
- No safety guarantees

**❌ Eventual Consistency**

- Still creates duplicate IDs
- Not acceptable for money / orders

**What Consensus Solves**

Consensus ensures:

✔ Every write is **ordered**  
✔ Every node agrees on the **same sequence**  
✔ No two nodes commit conflicting values

This is how **etcd, CockroachDB, Spanner** work.

**The Mini Project**

**🎯 Goal**

A **distributed counter** that:

- Never generates duplicates
- Survives node crashes
- Is consistent across instances

**🧠 Tool**

- etcd (Raft-based)
- Django-style service code

**3️⃣ Architecture**

```pgsql
+-------------------+
|   etcd cluster    |
|  (Raft log)       |
+---------+---------+
          |
+---------+----------+----------+
| Django A | Django B | Django C |
+----------+----------+----------+
          |
   All writes go through Raft
```

**4️⃣ How Raft Solves This (Key Insight)**

Raft provides:

- **One leader**
- **Replicated log**
- **Strict ordering**

Every write becomes:

```nginx
LOG ENTRY #17 → increment counter
```

All nodes apply logs **in the same order**.

**5️⃣ Project Code (Simplified)**

**Install**

```bash
pip install etcd3
```

**6️⃣ Distributed Counter Service**

**counter_service.py**

```python
import etcd3

client = etcd3.client(host='localhost', port=2379)

COUNTER_KEY = "/db/order_counter"

def get_next_order_id():
    """
    Strongly consistent increment using Raft
    """

    while True:
        value, meta = client.get(COUNTER_KEY)
        current = int(value) if value else 0
        next_value = current + 1

        success, _ = client.transaction(
            compare=[
                client.transactions.version(COUNTER_KEY) == (meta.version if meta else 0)
            ],
            success=[
                client.transactions.put(COUNTER_KEY, str(next_value))
            ],
            failure=[]
        )

        if success:
            return next_value
```

**7️⃣ Django View (Simulated)**

```python
def create_order(request):
    order_id = get_next_order_id()

    # save order with order_id
    print(f"Order created with ID: {order_id}")

    return JsonResponse({"order_id": order_id})
```

**8️⃣ What Just Happened (Critical Part)**

**Internally:**

- Django calls get_next_order_id()
- etcd leader appends log entry:
- ```bash
    [increment counter]
  ```
- Raft replicates to majority
- Entry is committed
- Value becomes visible

**Guarantee:**

**Only one value can win at each log index**

**9️⃣ Try Breaking It**

Run create_order concurrently from:

- Multiple Django servers
- Multiple threads
- Multiple processes

Result:
```css
1, 2, 3, 4, 5, 6, 7 ...
```
✔ No duplicates  
✔ No gaps  
✔ Crash-safe

**🔥 Why This Is a Distributed Database Core**

This is **literally how distributed DBs work**:

| **Database** | **What Raft Does** |
| --- | --- |
| etcd | Config & metadata |
| CockroachDB | Transaction ordering |
| TiDB | Metadata & placement |
| Spanner | Paxos instead of Raft |

The **actual data** is just a **state machine** applied on logs.

**10️⃣ Failure Scenario (Important)**

**Leader crashes mid-write**

- Entry not committed → discarded
- New leader elected
- Counter remains correct

**Network partition**

- Minority cannot commit
- Safety preserved
- No split-brain writes

👉 **Availability is sacrificed for correctness**  
(That's the CAP theorem in action)

**11️⃣ Mental Model (Very Important)**

**Distributed database = state machine + replicated log**

Raft provides the **replicated log**  
Your DB provides the **state machine**

**12️⃣ What Problem Did We Solve?**

| **Problem** | **Without Raft** | **With Raft** |
| --- | --- | --- |
| Duplicate IDs | Yes | No  |
| Ordering | Undefined | Strict |
| Crash safety | Weak | Strong |
| Split brain | Possible | Impossible |

**13️⃣ When You NEED This**

Use consensus when:

- Money is involved
- IDs must be unique
- Strong consistency is required
- Writes must be ordered

Do **not** use it for:

- Logs
- Metrics
- Analytics
- Caches