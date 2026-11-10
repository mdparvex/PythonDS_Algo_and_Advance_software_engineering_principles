# Database Internals for Backend Engineers

> A mentor-style deep dive into how relational databases actually work — B+Trees, storage engines,
> query execution, MVCC, locking, recovery, planning, `EXPLAIN ANALYZE`, and replication — written so you can
> **make engineering decisions on your own**, not just recite definitions.

**Audience:** backend engineer, ~4 years of experience (Python / Django / FastAPI, PostgreSQL / MySQL, Redis, Docker, Kubernetes, cloud).
**Primary engine:** PostgreSQL (16/17/18-era behaviour). **Secondary engine:** MySQL 8 / InnoDB — called out in
`MySQL/InnoDB note` boxes, because the two engines make *different* design choices and understanding the contrast is what
makes the concepts stick.
**Last reviewed:** November 2026.

---

## Table of Contents

0. [How to use this document & the mental model](#0-how-to-use-this-document--the-mental-model)
1. [Storage engines, pages and the buffer pool](#1-storage-engines-pages-and-the-buffer-pool)
2. [B+Trees: how an index really works](#2-btrees-how-an-index-really-works)
3. [Index types (and when each one wins)](#3-index-types-and-when-each-one-wins)
4. [Composite indexes, selectivity and multi-column indexing](#4-composite-indexes-selectivity-and-multi-column-indexing)
5. [Query execution, planning and optimization](#5-query-execution-planning-and-optimization)
6. [EXPLAIN ANALYZE: reading plans like a professional](#6-explain-analyze-reading-plans-like-a-professional)
7. [Why database queries become slow (diagnosis playbook)](#7-why-database-queries-become-slow-diagnosis-playbook)
8. [Transactions, isolation, MVCC and locks](#8-transactions-isolation-mvcc-and-locks)
9. [Database recovery: WAL, checkpoints, crash recovery, PITR](#9-database-recovery-wal-checkpoints-crash-recovery-pitr)
10. [Replication](#10-replication)
11. [Putting it together: a large-scale production system](#11-putting-it-together-a-large-scale-production-system)
12. [Hands-on labs (PostgreSQL, Python, Redis, Go)](#12-hands-on-labs-postgresql-python-redis-go)
13. [Common mistakes engineers make (consolidated)](#13-common-mistakes-engineers-make-consolidated)
14. [System design interview questions](#14-system-design-interview-questions)
15. [Cheat sheets, decision frameworks and a study plan](#15-cheat-sheets-decision-frameworks-and-a-study-plan)

---

# 0. How to use this document & the mental model

## 0.1 How each chapter is structured

Every major chapter follows the same ten-step teaching arc you asked for. Where a step is trivial for a topic it is folded into another, but none are skipped:

| Step | Section heading in each chapter |
|---|---|
| 1 | **Concept** — plain-language explanation |
| 2 | **Why it exists** — the problem it solves |
| 3 | **How it works internally** |
| 4 | **Architecture / diagrams** |
| 5 | **Realistic backend examples** |
| 6 | **Trade-offs, limits, failure scenarios** |
| 7 | **At production scale** |
| 8 | **Experiments** (pointers to [Chapter 12](#12-hands-on-labs-postgresql-python-redis-go) labs, or inline) |
| 9 | **Common mistakes** |
| 10 | **Check yourself** (questions; the big system design questions are in [Chapter 14](#14-system-design-interview-questions)) |

**How to study:** read a chapter, then immediately run its lab. Anything you have only read, you will forget; anything you have broken and
repaired on a laptop, you will remember during an incident at 3 a.m.

## 0.2 The one-page mental model

A relational database is five cooperating subsystems. Almost every performance or correctness question you will ever face is a question about
**one of these five** (or the seam between two):

1. **A page cache** — data lives on disk in fixed-size pages; RAM holds a cache of hot pages (the *buffer pool*).
2. **A log** — before any change reaches a data page, it is appended to a sequential *write-ahead log* (WAL / redo log). This gives durability, crash recovery and replication.
3. **Data structures over pages** — heaps and B+Trees (and others) that make "find row(s) by value" fast.
4. **A concurrency controller** — MVCC (versions) plus locks, deciding who sees what and who must wait.
5. **A planner/optimizer + executor** — turns declarative SQL into a physical plan using statistics and a cost model.

```
 Your app (Django ORM / SQLAlchemy / psycopg / pgx)
        │  SQL text, parameters
        ▼
 ┌────────────────────── DATABASE SERVER ───────────────────────────────┐
 │  Connection (1 process per connection in Postgres; 1 thread in MySQL)│
 │        ▼                                                             │
 │  Parser ─► Rewriter ─► PLANNER / OPTIMIZER ─► EXECUTOR               │
 │                          ▲ statistics                │ "give me page 4711"
 │                          │                           ▼
 │                 ┌─────────────────────────────────────────────┐     │
 │                 │ ACCESS METHODS: heap, B-tree, GIN, GiST, …   │     │
 │                 └─────────────┬───────────────────────────────┘     │
 │   MVCC visibility + LOCK MANAGER (who may see / touch what)          │
 │                               ▼                                      │
 │                 ┌───────────────────────────┐                        │
 │                 │ BUFFER POOL (shared RAM)  │──dirty pages──┐        │
 │                 └──────┬────────────────────┘               │        │
 │       WAL record FIRST │ (sequential append)                │ later  │
 │                        ▼                                    ▼        │
 │                 ┌─────────────┐                  ┌────────────────┐  │
 │                 │  WAL / redo │──► replicas,     │  DATA FILES    │  │
 │                 │    log      │    archive, PITR │ (8 KB pages)   │  │
 │                 └─────────────┘                  └────────────────┘  │
 └──────────────────────────────────────────────────────────────────────┘
```

## 0.3 Numbers every backend engineer should have in their head

These are *orders of magnitude* (they vary with hardware), but the **ratios** drive every database design decision.

| Operation | Approx. latency | Ratio vs RAM |
|---|---|---|
| RAM access (cache-resident buffer-pool page) | ~100 ns | 1× |
| NVMe SSD random 4–16 KB read | ~50–150 µs | ~1,000× |
| Cloud network SSD (EBS/managed disk) random read | ~0.5–2 ms | ~5,000–20,000× |
| Same-datacenter network round trip (app ↔ DB) | ~0.3–1 ms | — |
| Spinning disk seek | ~5–10 ms | ~50,000–100,000× |
| `fsync` on cloud SSD (commit latency floor) | ~0.5–5 ms | — |

Two lessons that fall out of this table:

* **A buffer-pool miss is ~1,000×+ more expensive than a hit.** Most "database got slow" stories are really "the working set stopped fitting in RAM".
* **A network round trip costs about as much as a disk read.** The N+1 query problem is slow not because each query is expensive, but because you pay ~0.5 ms × N of pure latency.

## 0.4 The sample schema used throughout this document

All SQL examples use one pharmacy-style order table so the numbers are consistent between chapters. Skewed status values are **deliberate** — real data is skewed, and skew is what makes selectivity interesting.

```sql
-- PostgreSQL. Run in a scratch database.
CREATE TABLE orders (
    id          bigserial     PRIMARY KEY,
    user_id     int           NOT NULL,
    pharmacy_id int           NOT NULL,
    status      text          NOT NULL,   -- DELIVERED 92%, CANCELLED 4%, SHIPPED 3%, PROCESSING 0.9%, PENDING 0.1%
    total       numeric(10,2) NOT NULL,
    created_at  timestamptz   NOT NULL
);

INSERT INTO orders (user_id, pharmacy_id, status, total, created_at)
SELECT (random()*500000)::int + 1,
       (random()*200)::int + 1,
       CASE WHEN r < 0.92  THEN 'DELIVERED'
            WHEN r < 0.96  THEN 'CANCELLED'
            WHEN r < 0.99  THEN 'SHIPPED'
            WHEN r < 0.999 THEN 'PROCESSING'
            ELSE 'PENDING' END,
       (random()*5000)::numeric(10,2),
       now() - (random()*730) * interval '1 day'
FROM (SELECT random() AS r FROM generate_series(1, 5000000)) s;

ANALYZE orders;
```

Easiest way to get a Postgres to play with:

```bash
docker run --name pg -e POSTGRES_PASSWORD=pw -p 5432:5432 -d postgres:17
psql "postgresql://postgres:pw@localhost:5432/postgres"
```

---

# 1. Storage engines, pages and the buffer pool

## 1.1 Concept

A database does not store "rows" on disk. It stores **pages** (also called blocks): fixed-size chunks — **8 KB in PostgreSQL, 16 KB in MySQL/InnoDB**. A page is the unit of:

* disk I/O (you never read half a page),
* caching (the buffer pool caches whole pages),
* locking/latching and logging (WAL records refer to pages),
* indexing (each B+Tree node *is* a page).

Rows (tuples) live inside pages. Indexes are *also* made of pages. Everything is pages.

A **storage engine** is the component that decides *how rows are organized inside pages and files*, how they are found, how they are versioned and how they are logged. PostgreSQL has effectively one (the heap, with a pluggable table-access-method API). MySQL has pluggable engines, of which **InnoDB** is the one that matters.

## 1.2 Why it exists

Disks (and SSDs) are block devices. Reading 1 byte costs the same as reading 8 KB, so the database groups data into blocks, reads blocks into RAM, and works on RAM. The storage engine's whole job is to **minimize the number of block reads and writes** for the operations you actually do, while staying crash-safe.

The core tension every engine resolves differently:

| You want | …but it costs |
|---|---|
| Fast reads by key | Maintain sorted structures (indexes) → slower writes |
| Fast writes | Append-only / unsorted → slower reads, needs background cleanup |
| Durability | Synchronous log flush on commit → commit latency |
| Concurrency without blocking readers | Keep old row versions → space + cleanup (vacuum/purge) |

## 1.3 How it works internally

### 1.3.1 Anatomy of a PostgreSQL heap page (8 KB)

```
 0                                                                    8192
 ┌──────────┬───────────────────────────┬──────────── free ────────┬──────────────────────────┐
 │ Page     │ Line pointer array        │                          │  Tuples (grow backwards) │
 │ header   │ lp1 lp2 lp3 lp4 …  ──────►│                          │◄── tuple4 tuple3 tuple2 tuple1
 │ (24 B)   │ (4 bytes each: offset,len)│                          │                          │
 └──────────┴───────────────────────────┴──────────────────────────┴──────────────────────────┘

 Each tuple:  [ 23-byte header: xmin, xmax, cmin/cmax, ctid, infomask, … ][ null bitmap ][ column data ]
 A tuple's physical address:  ctid = (page_number, line_pointer_index)   e.g. (4711, 3)
```

Key consequences:

* **`ctid` is the row's physical address.** Indexes in PostgreSQL store `(key → ctid)`.
* The line-pointer indirection lets the engine **move tuples within a page** (defragment) without changing any ctid → indexes stay valid.
* **`xmin`/`xmax`** are the transaction IDs that created/deleted this tuple version. This is how MVCC works (Chapter 8): *an UPDATE does not modify a tuple in place; it writes a new tuple version and marks the old one's `xmax`.*
* Values larger than ~2 KB are compressed and/or moved to a side **TOAST** table, so wide `text`/`jsonb` columns do not bloat the main heap.
* A table is a **heap**: an unordered collection of pages. Row order on disk ≈ insertion order (modulo free-space reuse), *not* primary-key order.

### 1.3.2 InnoDB: the table *is* a B+Tree

InnoDB organizes the table as a **clustered index**: a B+Tree keyed on the primary key whose **leaf pages contain the full rows**.
Every *secondary* index stores `(secondary key → primary key value)`, **not** a physical pointer.

```
 PostgreSQL                                         InnoDB
 ──────────                                         ──────
 Index on user_id                                   Secondary index on user_id
   key  → ctid(page,slot)                             key → PRIMARY KEY value
        │                                                    │
        ▼  1 hop                                             ▼  2nd B+Tree descent
 Heap page (unordered)                              Clustered index (PK B+Tree), leaves = rows
```

Why this matters for you (Django + MySQL 8 in production is a very common setup):

| Consequence | Explanation |
|---|---|
| **PK choice is a physical-layout decision.** | Rows are physically sorted by PK. Sequential PKs (auto-increment, UUIDv7/ULID) append to the right edge → compact, cache-friendly. **Random UUIDv4 PKs** insert into random pages → page splits, ~30–50% wasted space, poor cache locality. |
| **Every secondary index silently contains the PK.** | A 36-byte `CHAR(36)` UUID PK is copied into *every* secondary index entry → all indexes balloon. Prefer `BIGINT` PK (8 bytes) or `BINARY(16)`. |
| **Secondary-index lookup = two tree descents** (index → PK → clustered tree) unless the index is **covering**. | Covering indexes are worth more in InnoDB than you might expect. |
| **PK range scans are free and fast.** | Rows with adjacent PKs are physically adjacent. |

### 1.3.3 The buffer pool

```
 Executor needs page P
        │
        ▼
 ┌─────────────────────────┐   hit   ┌─────────────────┐
 │ Is P in the buffer pool?│────────►│ use it (≈100 ns) │
 └──────────┬──────────────┘         └─────────────────┘
            │ miss
            ▼
   find a victim frame  ──(if victim is dirty: its WAL must already be flushed; write it out)──┐
            │                                                                                    │
            ▼                                                                                    │
   read P from disk (≈0.1–2 ms)  ◄──────────────────────────────────────────────────────────────┘
```

* **PostgreSQL** keeps its own cache (`shared_buffers`, commonly starting at ~25% of RAM) *and* relies on the OS page cache for the rest ("double buffering"). Eviction uses a clock-sweep with usage counts.
* **InnoDB** relies on its own big buffer pool (`innodb_buffer_pool_size`, commonly 60–75% of RAM on a dedicated host) and typically bypasses the OS cache (`O_DIRECT`). It uses an LRU with *midpoint insertion* so a one-off big scan doesn't evict your hot pages.
* **Dirty pages** are written back lazily by background processes (bgwriter/checkpointer in Postgres; page cleaners in InnoDB). The *log* guarantees durability, so data pages don't need to be flushed at commit (Chapter 9).

### 1.3.4 Storage engine families

| Engine style | Examples | Write path | Read path | Best at | Weakness |
|---|---|---|---|---|---|
| **Heap + B-tree indexes** | PostgreSQL | Append tuple to a heap page, update each index | Index → ctid → heap | Mixed OLTP, rich SQL, many indexes | Write amplification on UPDATE (new tuple + index entries unless HOT), vacuum needed |
| **Clustered B+Tree (index-organized)** | InnoDB | Insert in PK order into the clustered tree; undo log for old versions | PK lookup = 1 descent; secondary = 2 | PK-centric OLTP, range scans by PK | Random PKs fragment; fat secondary indexes |
| **LSM tree** | RocksDB, MyRocks, Cassandra, LevelDB | Write to memtable + WAL, flush sorted immutable files (SSTables), background compaction | Check memtable + several levels (Bloom filters help) | Very high write throughput, compression | Read amplification, compaction I/O spikes, space amplification |
| **Column store** | ClickHouse, Redshift, Parquet-based | Batch inserts into column chunks | Read only needed columns, vectorized | Analytics/aggregations over huge tables | Poor for point lookups & single-row updates |

> **Rule of thumb:** B-tree engines optimize for *reads* and pay on writes; LSM engines optimize for *writes* and pay on reads. Your OLTP primary database is almost always a B-tree engine; LSM shows up inside queues, caches, search engines and time-series systems.

## 1.4 Architecture summary (write path vs read path)

```
 WRITE (INSERT/UPDATE)                                  READ (SELECT)
 ─────────────────────                                  ─────────────
 1. Find target page (via index if needed)              1. Planner picks access path
 2. Modify page IN THE BUFFER POOL (mark dirty)         2. Index descent (pages from buffer pool or disk)
 3. Append WAL record (sequential I/O)                  3. Fetch heap page (or clustered leaf)
 4. COMMIT → fsync the WAL (this is the durability      4. Check MVCC visibility of each tuple version
    point; the data page is NOT flushed now)            5. Return rows
 5. Later: bgwriter/checkpointer flush dirty pages
```

## 1.5 Realistic backend examples

**Example A — how big is my table?** An `orders` row of ~100 bytes (including the 23-byte header) fits ~75–80 rows per 8 KB page. 10 M rows ≈ 130 k pages ≈ **~1 GB**. A `SELECT *` over the whole table touches 130 k pages; an indexed lookup touches ~4. That ratio (≈30,000×) is why indexing exists.

**Example B — the UUID primary key regret (MySQL).** A team switches `orders.id` from `BIGINT AUTO_INCREMENT` to `CHAR(36)` UUIDv4 "for microservice friendliness". Six months later: table is 2.3× larger, each of 6 secondary indexes carries 36 extra bytes per entry, insert throughput halves, and the buffer-pool hit ratio drops because inserts touch random leaf pages. Fix: time-ordered IDs (UUIDv7/ULID stored as `BINARY(16)`) or `BIGINT` PK with a separate public UUID column.

**Example C — blob in the hot table.** Storing a 200 KB prescription PDF in the `orders` row. In PostgreSQL it is TOASTed (OK but `SELECT *` still drags it); in InnoDB large values go to overflow pages. Either way: store files in object storage, keep the URL in the row.

## 1.6 Trade-offs, limitations and failure scenarios

| Scenario | What happens | Mitigation |
|---|---|---|
| **Heap bloat (PostgreSQL)** | Dead tuple versions pile up when vacuum can't keep up (long transactions, replication slots, hot_standby_feedback) → table and indexes grow, scans slow. | Tune autovacuum per table; kill long-running transactions; monitor `n_dead_tup`; `pg_repack` for repairs. |
| **Transaction ID wraparound** | Postgres XIDs are 32-bit; if `VACUUM` can't freeze old tuples, the DB eventually refuses writes to protect data. | Monitor `age(datfrozenxid)`; never disable autovacuum. |
| **Working set > RAM** | Hit ratio drops, latency jumps 100×, IOPS saturate. | More RAM, better indexes (smaller working set), partitioning, archive cold data. |
| **Torn pages** | A crash mid-write leaves an 8 KB page half-old/half-new (the OS writes 4 KB sectors). | Postgres: `full_page_writes` logs the whole page after each checkpoint. InnoDB: **doublewrite buffer**. Never turn these off to "go faster". |
| **Random PK (InnoDB)** | Page splits, fragmentation, cache churn. | Sequential/time-ordered keys. |
| **Disk full** | Postgres may crash or stop accepting writes; WAL accumulation (stuck replication slot) is a classic cause. | Alert at 70–80%; monitor `pg_replication_slots` retained WAL. |

## 1.7 At production scale

* Track **buffer cache hit ratio**, but treat it with suspicion: 99% sounds great, yet a 1% miss rate at 50 k reads/s is 500 disk reads/s. Watch *absolute* read IOPS and p99 latency, not just the ratio.
* Know your **working set**: the pages touched by the *hot* part of your workload (recent orders, active products), not total table size. Good indexes and partitioning shrink it.
* On cloud disks, you buy **IOPS and throughput** separately from capacity. A query plan that does 20 k random reads/s can hit a gp3/Premium SSD IOPS limit long before CPU is busy → latency cliff.
* **Separate** concerns by hardware where possible: WAL on a low-latency volume; large analytical scans away from the primary (read replica / warehouse).

## 1.8 Experiments

Inline (no setup beyond [section 0.4](#04-the-sample-schema-used-throughout-this-document)):

```sql
-- How big are the table and its PK index? How many pages?
SELECT pg_size_pretty(pg_relation_size('orders'))        AS heap,
       pg_size_pretty(pg_relation_size('orders_pkey'))   AS pk_index,
       (pg_relation_size('orders') / 8192)               AS heap_pages;

-- Physical addresses: ctid = (page, slot)
SELECT ctid, id, status FROM orders LIMIT 5;

-- Peek inside a heap page
CREATE EXTENSION IF NOT EXISTS pageinspect;
SELECT lp, lp_off, lp_len, t_xmin, t_xmax, t_ctid
FROM heap_page_items(get_raw_page('orders', 0)) LIMIT 5;
```

Full labs: **Lab 1** (page inspection & tree height), **Lab 4** (MVCC internals: watch `xmin/xmax/ctid` change on `UPDATE`).

## 1.9 Common mistakes

1. Choosing a random UUIDv4 as a **clustered** primary key (InnoDB) without understanding the physical consequence.
2. Treating the table as ordered by PK in PostgreSQL. It isn't. `SELECT * FROM t LIMIT 10` has no defined order. (`CLUSTER` reorders once but doesn't maintain it.)
3. Storing large blobs in OLTP tables and then `SELECT *`.
4. Sizing RAM by *table size* instead of *working set + index size*.
5. Disabling `fsync`/`full_page_writes`/doublewrite "for performance" on a production primary.

## 1.10 Check yourself

1. Why does PostgreSQL use a line-pointer array instead of storing tuple offsets directly in the index?
2. In InnoDB, a query `SELECT status FROM orders WHERE user_id = ?` uses a secondary index on `(user_id)`. How many B+Tree descents are needed, and how could you reduce it to one?
3. Why does a 99% cache hit ratio not guarantee a healthy database?
4. What problem does the doublewrite buffer / `full_page_writes` solve?

---

# 2. B+Trees: how an index really works

## 2.1 Concept

An **index** is a separate, sorted data structure that maps *column values → row locations*, so the database can jump to matching rows instead of reading the whole table. The structure used in practice by PostgreSQL, MySQL/InnoDB, Oracle, SQL Server, and SQLite is the **B+Tree**:

* **Balanced** — every leaf is at the same depth, so every lookup costs the same number of page reads.
* **Wide (high fan-out)** — each node is a whole page holding *hundreds* of keys, so the tree is extremely shallow (3–4 levels for hundreds of millions of rows).
* **Sorted** — keys are ordered within and across leaves, so range scans and `ORDER BY` are cheap.
* **B+** — *all* row pointers (or rows) live in the **leaves**; internal nodes hold only **separator keys** to guide the search. Leaves are **linked** left↔right for range scans.

Analogy: a phone book. The thumb-index tabs (A–C, D–F …) are the root; the page headers are the internal nodes; the entries are the leaves. You touch ~3 things to find anyone among millions.

## 2.2 Why it exists — the problem it solves

Finding rows where `user_id = 42` among N rows. Options and their cost **in page reads** (the unit that matters):

| Approach | Cost for N = 10 M rows | Supports ranges? | Notes |
|---|---|---|---|
| Sequential scan | ~130,000 pages | yes (but reads everything) | fine for tiny tables or when you need most rows |
| Binary search on a sorted file | log₂(10 M) ≈ **23 random reads** | yes | each step is a *different* page — random I/O; and inserts require shifting data |
| Hash table | ~1–2 | **no** | great for equality; no ordering, no range, no prefix |
| **B+Tree** | **3–4 reads** (top levels are cached → ~1 disk read) | **yes** | slightly costlier writes (splits) |

The B+Tree is binary search's idea redesigned for block devices: instead of 2-way branching per random read, branch **~300–1,000 ways per page read**. log₃₀₀(10 M) ≈ 3, log₂(10 M) ≈ 23.

## 2.3 How it works internally

### 2.3.1 Structure

```
                          ┌───────────────── ROOT (internal node = 1 page) ─────────────────┐
                          │  [ 1  |  3,000,000  |  6,500,000  |  …  ]                        │
                          └──────┬───────────────────┬───────────────────┬──────────────────┘
                 keys < 3M       │      3M ≤ keys < 6.5M                 │   ≥ 6.5M
                    ┌────────────▼──────┐      ┌────────▼─────────┐     ┌▼────────────────┐
   INTERNAL level   │ [ 1 | 9k | 18k …] │      │ [3M | 3.01M | …] │     │ …               │   (~300–1000 children each)
                    └───┬────┬────┬─────┘      └───┬────┬─────────┘     └─────────────────┘
                        │    │    │                │    │
   LEAF level      ┌────▼┐ ┌─▼───┐ ┌▼────┐      ┌──▼──┐ ┌▼────┐
                   │1..9k│►│9k.. │►│18k..│ ◄──► │3M.. │►│3.01M│ ► …      leaves are doubly linked
                   │ptrs │ │ptrs │ │ptrs │      │ptrs │ │ptrs │          (range scan = walk right)
                   └─────┘ └─────┘ └─────┘      └─────┘ └─────┘
        leaf entry (PostgreSQL):  (key, ctid)       leaf entry (InnoDB clustered):  (PK, entire row)
```

Rules (for a B+Tree of "order" m, i.e. max m children per node):

* All leaves are at the same depth.
* Every node except the root is at least ~half full (keeps height small and space reasonable).
* Internal node with *k* separator keys has *k+1* children. Child *i* contains keys `sep[i-1] ≤ key < sep[i]`.
* **Leaves hold the data pointers; internal nodes hold only routing keys.** Because internal nodes are small (just keys + child pointers), more of them fit per page → larger fan-out → shallower tree. That's the entire advantage of B+ over a plain B-tree.

### 2.3.2 Fan-out and height — do the math, it's the whole intuition

*InnoDB* (16 KB page, `BIGINT` key 8 B + child pointer 6 B ≈ 14 B/entry, plus overhead): ~**1,170** children per internal page. Leaf holds full rows; say 1 KB rows → ~16 rows/leaf.

| Height | Rows addressable |
|---|---|
| 2 levels (root + leaves) | 1,170 × 16 ≈ 19 k |
| 3 levels | 1,170² × 16 ≈ **22 million** |
| 4 levels | 1,170³ × 16 ≈ **25 billion** |

*PostgreSQL* (8 KB page, `bigint` key → ~16 B index tuple + 4 B line pointer ≈ 20 B/entry): roughly **300–400** entries per page (at 90% leaf fill).

| Height (levels) | Entries |
|---|---|
| 2 | ~150 k |
| 3 | ~**50–60 million** |
| 4 | ~**20–25 billion** |

**Takeaway:** going from 10 M to 1 B rows adds *one* level. Index lookup cost is essentially constant. The root and most of the second level are always in the buffer pool, so a lookup in a big table is typically **1 disk read** (the leaf) + 1 heap read.

### 2.3.3 Search

```
find(key):
    node = root
    while node is internal:
        i = binary_search(node.separators, key)   # within the page, in RAM
        node = read_page(node.children[i])        # one page read (buffer pool or disk)
    # node is a leaf
    return binary_search(node.entries, key)
```

Range query `BETWEEN lo AND hi`: descend to the leaf containing `lo`, then follow the right-sibling pointers until key > `hi`. **One descent + sequential leaf reads.** `ORDER BY key LIMIT 20` is the same trick: descend once, read 20 entries, stop — no sort.

### 2.3.4 Insert and page splits

```
 Before: leaf is full (max 4 keys in this toy example), inserting 11
        parent: [ 10 | 20 ]
                   │
        leaf:  [ 10  12  15  18 ]  + insert 11   → overflow!

 Split:  leaf splits into two pages; the first key of the new right page is COPIED up to the parent
        parent: [ 10 | 15 | 20 ]
                   │    │
        left:  [ 10 11 12 ]  right: [ 15 18 ]
```

* If the parent overflows it splits too (the middle separator is **moved** up, not copied, for internal nodes). If the **root** splits, a new root is created → the tree grows **one level taller**. That's the only way height increases; the tree grows from the *top*, which is why it stays balanced.
* **Random inserts** split pages ~50/50 → pages end up ~70% full on average.
* **Rightmost (monotonic) inserts** — auto-increment IDs, timestamps — are special-cased by real engines: they split 90/10 (PostgreSQL) so the left pages stay nearly full. Sequential keys give dense, cache-friendly indexes; random keys (UUIDv4) give sparse, cache-hostile ones.
* **Fillfactor** (`CREATE INDEX … WITH (fillfactor = 70)`) deliberately leaves room to absorb future inserts into the middle of the key space, trading space for fewer splits.

A split is a multi-page change, so it must be **atomic and crash-safe**: it is WAL-logged as a unit.

### 2.3.5 Delete and update

* Deleting an index entry rarely merges pages. PostgreSQL leaves mostly-empty pages and reclaims entirely empty ones lazily (via `VACUUM`); heavy delete patterns cause **index bloat**. Fix with `REINDEX CONCURRENTLY`.
* `UPDATE` of an **indexed column** = delete old entry + insert new entry in that index. `UPDATE` of a non-indexed column in PostgreSQL can be a **HOT (Heap-Only Tuple) update**: the new tuple version stays on the same heap page, and **no index changes at all**. So *every extra index on a frequently-updated column makes updates slower and blocks HOT.*

### 2.3.6 Concurrency inside the tree (just enough to be dangerous)

Many sessions read and modify the same tree simultaneously. The tree structure itself is protected by short-lived **latches** (lightweight locks held for microseconds, *different from* transaction locks). PostgreSQL's B-tree uses the **Lehman–Yao** design: every page has a *high key* and a *right-link*, so a reader that lands on a page that has just been split can simply "move right" without holding a lock on the parent. InnoDB uses latch coupling ("crabbing") on the descent path and an optimistic-then-pessimistic strategy for modifications. You rarely tune this, but it explains symptoms like **contention on the rightmost leaf** for monotonic keys under extreme insert rates.

### 2.3.7 Modern improvements worth knowing (PostgreSQL)

* **Deduplication** (PG 13): many equal keys in a non-unique index are stored once with a posting list of ctids → much smaller indexes for low-cardinality columns.
* **Bottom-up index deletion** (PG 14): when an UPDATE-heavy page is about to split, the engine proactively removes dead entries instead of splitting.
* **Suffix truncation** of internal separator keys → larger fan-out.
* **Index-only scans** use the **visibility map** to skip heap fetches for all-visible pages (needs frequent `VACUUM`).

> **MySQL/InnoDB note:** InnoDB also has an **adaptive hash index** (an automatic in-memory hash over hot B+Tree pages — helps point lookups, can become a contention point; many shops disable it), a **change buffer** (defers secondary-index maintenance for non-unique indexes whose pages aren't cached), and **page merging** when pages fall below `MERGE_THRESHOLD`.

## 2.4 Index scan vs. index-only scan vs. heap fetches (what a "lookup" really costs)

```
 Query: SELECT total FROM orders WHERE user_id = 42;      Index on (user_id)

 PostgreSQL Index Scan                          PostgreSQL Index-Only Scan  (index on (user_id) INCLUDE (total))
 ─────────────────────                          ───────────────────────────
 root ─► internal ─► leaf                       root ─► internal ─► leaf
          matches: ctid₁ ctid₂ ctid₃ …                     matches carry `total` in the index
 for each ctid:                                  for each match: check visibility map
     read heap page, check MVCC visibility           page all-visible? → no heap access at all
     (random I/O if rows are scattered!)             else fetch heap page to check
```

* If 3 matching rows sit on 3 *different* heap pages → 3 random heap reads. This is why **low correlation** between index order and physical order matters, and why the planner sometimes picks a **bitmap heap scan** (collect all ctids, sort by page, read each heap page once).
* **Covering indexes** (all needed columns in the index) turn lookup + heap fetch into a lookup only.

## 2.5 Realistic backend examples

```sql
-- 1. Point lookup by PK:                      3–4 page reads regardless of table size
SELECT * FROM orders WHERE id = 987654321;

-- 2. Range + order, "latest 20 orders for a user" — the bread and butter of every app
--    Needs index (user_id, created_at DESC): one descent, read 20 entries, no sort.
SELECT id, status, total FROM orders
WHERE user_id = 42 ORDER BY created_at DESC LIMIT 20;

-- 3. Uniqueness is *implemented by* an index: UNIQUE / PRIMARY KEY create a B-tree.
ALTER TABLE users ADD CONSTRAINT users_email_uq UNIQUE (email);

-- 4. MIN/MAX are free with a B-tree: descend to the leftmost/rightmost leaf.
SELECT max(created_at) FROM orders;
```

**Foreign keys:** PostgreSQL does **not** automatically index the referencing (child) column. `DELETE FROM users WHERE id = ?` must check `orders.user_id` — without an index that is a full scan of `orders` *per delete* (and takes locks while doing it). MySQL/InnoDB *does* create an index for FKs automatically. In Django, `ForeignKey` creates an index by default (`db_index=True`), but raw-SQL or hand-written migrations often forget.

## 2.6 Trade-offs, limitations and failure scenarios

| Aspect | Cost / limitation |
|---|---|
| **Write amplification** | One INSERT = heap write + one write per index (+ WAL for each). 8 indexes ≈ 9 places to write. |
| **Space** | Indexes are often 30–100% the size of the table; several indexes can exceed the table. |
| **Random-key inserts** | Page splits, fragmentation, cache-unfriendly. |
| **Skewed/low-selectivity predicates** | Index on a column where the predicate matches 30% of rows is slower than a seq scan (random I/O × many). |
| **Not every predicate is searchable** | `WHERE lower(email)=…` on an index of `email`, `WHERE date(created_at)=…`, `LIKE '%abc'`, implicit type casts → index unusable (Chapter 7). |
| **Index bloat** | Heavy deletes/updates leave sparse pages; scans and cache efficiency degrade. `REINDEX CONCURRENTLY`. |
| **Corruption** | Rare (bad hardware, OS/glibc collation upgrades silently changing sort order!). Detect with `amcheck`. A glibc/ICU upgrade that changes collation can make an index *logically* corrupt — a real production hazard after OS upgrades or replica promotion onto a different OS image. |
| **Building an index locks writes** | `CREATE INDEX` blocks writes on the table; use `CREATE INDEX CONCURRENTLY` (slower, two table scans, can leave an `INVALID` index on failure). |

## 2.7 At production scale

* **Index size vs. RAM.** A 1-billion-row table with a 25 GB B-tree on `(user_id, created_at)`: the *hot* part of that index (recent users/dates) must stay cached. If your queries touch the whole key space uniformly, you need the whole index in RAM or you'll be disk-bound. Partitioning by time helps because old partitions' indexes go cold and stay out of cache.
* **Monotonic key hotspot.** Everyone inserting into the rightmost leaf of a `bigserial`/timestamp index contends on that page. Usually fine up to tens of thousands of inserts/s; beyond that consider hash-partitioning or sharding.
* **Index maintenance during peak.** Never `CREATE INDEX` (non-concurrent) or heavy `REINDEX` in business hours on a hot table. With Django: use `AddIndexConcurrently` from `django.contrib.postgres.operations` in a migration with `atomic = False`.
* **Unused indexes are pure cost.** Audit regularly:

```sql
SELECT schemaname, relname, indexrelname, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
-- (check replicas too — an index unused on the primary may serve read replicas; and stats reset on restart/failover)
```

## 2.8 Experiments

* **Lab 1** — measure index height with `bt_metap`, see page counts, inspect leaf pages with `bt_page_items`.
* **Lab 10** — build and test the toy B+Tree in this document (`toy_bptree.py`), watch splits and height growth.

## 2.9 Common mistakes

1. "An index makes every query faster." It makes *selective* lookups faster and *every write* slower.
2. Indexing every column "just in case" → write amplification, no HOT updates, bloated memory.
3. Forgetting FK indexes in PostgreSQL.
4. Using a function on the indexed column in `WHERE` without an expression index.
5. Running non-concurrent `CREATE INDEX` on a live, hot table.
6. Assuming the planner *must* use your new index. (It decides by cost — Chapter 5.)
7. Believing B+Trees degrade into O(n); they don't, but **bloat and cache misses** degrade them in practice.

## 2.10 Check yourself

1. Why do B+Trees keep data only in the leaves? What does that buy you in fan-out?
2. What is the *only* operation that increases the height of a B+Tree?
3. Why do monotonic keys produce denser indexes than random keys?
4. Why can adding an index slow down an `UPDATE` of a column that is **not** in that index? (Hint: HOT.)
5. A 1 B-row table's index has 4 levels. Roughly how many *disk* reads does a point lookup need, and why?

---

# 3. Index types (and when each one wins)

## 3.1 Concept

"Index" is a family of structures, each answering a different *question shape*:

| Question shape | Example | Right structure |
|---|---|---|
| Equality, range, order, prefix | `id = 5`, `created_at > …`, `ORDER BY`, `name LIKE 'para%'` | **B-tree** (default) |
| Pure equality | `token = 'abc…'` | Hash (rarely worth it) |
| "Contains" in a composite value | `tags @> '{vegan}'`, `jsonb @> {…}`, full-text, arrays | **GIN** |
| Geometric / range-overlap / nearest-neighbour / exclusion | `tstzrange && …`, PostGIS, "closest" | **GiST / SP-GiST** |
| Huge append-only table, values correlate with physical order | `created_at` on a 5 B-row event table | **BRIN** |
| Fuzzy text | `name ILIKE '%paracet%'`, typo tolerance | GIN/GiST + **pg_trgm** |
| Vector similarity | embeddings | HNSW / IVFFlat (**pgvector**) |

## 3.2 Why it exists

A B-tree answers "is this *key* ≤ / = / ≥ that key?" It cannot answer "does this *document* contain the word X?" or "does this *rectangle* overlap that one?" because those relations have no single total ordering. Different index types encode different *operator classes*.

## 3.3 How each works (internals, briefly but precisely)

### B-tree
Chapter 2. Supports `< <= = >= >`, `BETWEEN`, `IN`, `IS NULL`, `ORDER BY`, and prefix `LIKE 'abc%'` (with a `C` collation or `text_pattern_ops` operator class).

### Hash
A hash table of buckets mapping hash(key) → ctid. Equality only; no ordering, no ranges, can't help `ORDER BY`. WAL-logged and crash-safe since PostgreSQL 10. Rarely better than B-tree in practice (B-trees are already ~1–2 page reads), but can be smaller for long keys (stores hash, not key). *In MySQL, `HASH` indexes exist only for the MEMORY/NDB engines; an InnoDB `USING HASH` is silently a B-tree.*

### GIN (Generalized Inverted Index)
An **inverted index**: for each *element* (word, array item, JSON key/value), a posting list/tree of the rows containing it.

```
   "paracetamol" ─► [ row 12, row 98, row 4410, … ]
   "fever"       ─► [ row 12, row 77, … ]
   Query: contains('paracetamol' AND 'fever')  →  intersect posting lists
```

Fast reads for containment; **slow writes** (one row touches many elements) — mitigated by a *pending list* (`fastupdate`) that batches inserts and merges later, which can cause latency spikes on the unlucky insert that triggers the flush.

### GiST / SP-GiST
Balanced (GiST) or space-partitioned (SP-GiST) trees where internal nodes store a *bounding summary* of children (e.g. bounding box). Query descends every child whose summary *might* match, then rechecks. Used by PostGIS, range types, exclusion constraints (`EXCLUDE USING gist` — e.g. "no two bookings for the same doctor with overlapping time ranges"), trigram, nearest-neighbour (`ORDER BY point <-> point`).

### BRIN (Block Range Index)
Stores just **min/max per range of N heap pages** (default 128 pages). Tiny (kilobytes for a huge table) and nearly free to maintain — **if** the column's value correlates with physical order (append-only timestamps, monotonic IDs). Useless for randomly-ordered columns. It gives *lossy* results: "these block ranges might contain it", then rechecks.

### Bloom (extension)
Multi-column equality filter via a bloom filter signature; useful when you need "any combination of 8 columns" equality filters and can't afford 8 B-trees. Niche.

### Vector indexes (pgvector)
HNSW (graph-based, better recall/speed, bigger/slower to build) and IVFFlat (cluster-based). Approximate nearest neighbour. Mentioned only for completeness.

## 3.4 Index *features* (orthogonal to type)

| Feature | What it does | Example |
|---|---|---|
| **Unique** | Enforces uniqueness (and is the index) | `UNIQUE (email)` |
| **Partial** | Indexes only rows matching a predicate → small, fast, and selective | `CREATE INDEX ON orders (created_at) WHERE status = 'PENDING';` |
| **Expression / functional** | Indexes a computed value | `CREATE INDEX ON users (lower(email));` |
| **Covering (`INCLUDE`)** | Adds payload columns to leaves (not part of the search key) enabling index-only scans | `CREATE INDEX ON orders (user_id, created_at DESC) INCLUDE (status, total);` |
| **Multicolumn** | Sorted by col1, then col2, … (Chapter 4) | `(user_id, created_at)` |
| **Descending / mixed order** | `(a ASC, b DESC)` for mixed `ORDER BY` | `(user_id, created_at DESC)` |
| **Concurrent build** | Doesn't block writes | `CREATE INDEX CONCURRENTLY …` |

> **MySQL 8 notes:** Descending indexes are real (8.0+; before that `DESC` was parsed and ignored). Functional indexes (8.0.13+), multi-valued indexes over JSON arrays (8.0.17+), **invisible indexes** (hide an index from the optimizer to test "what if I drop it?" safely), `FULLTEXT` (InnoDB), `SPATIAL`. No partial indexes — emulate with generated columns, or restructure. No `INCLUDE`; extra columns must be part of the key (they then also affect ordering).

## 3.5 Architecture: choosing an index (decision tree)

```
                         What does the predicate look like?
                                       │
        ┌──────────────┬───────────────┼────────────────────┬───────────────────────┐
        ▼              ▼               ▼                    ▼                       ▼
   =, <, >, BETWEEN,  col @> / ?  / full-text /      overlaps / nearest /     huge append-only table,
   ORDER BY, prefix   array / jsonb containment      geometry / exclusion     col ≈ physical order
        │                    │                              │                       │
     B-TREE                GIN                          GiST/SP-GiST             BRIN
        │
        ├── Only a small, well-defined subset of rows is ever queried (status='PENDING')? → PARTIAL
        ├── Always filtered through lower(x)/date(x)/(a+b)?                              → EXPRESSION
        └── Same few columns returned every time, hot query?                             → COVERING (INCLUDE)
```

## 3.6 Realistic backend examples (pharmacy-flavoured)

```sql
-- (a) Medicine search box. Users type "paracet", "Napa", sometimes with typos.
--     1) Prefix autocomplete: B-tree with text_pattern_ops (works under any collation)
CREATE INDEX idx_medicine_name_prefix ON medicines (lower(name) text_pattern_ops);
SELECT id, name FROM medicines WHERE lower(name) LIKE 'paracet%' ORDER BY lower(name) LIMIT 10;

--     2) "Contains" / fuzzy: trigram GIN
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_medicine_name_trgm ON medicines USING gin (name gin_trgm_ops);
SELECT id, name FROM medicines WHERE name ILIKE '%cetamol%';
SELECT id, name, similarity(name, 'paracetmol') AS s
FROM medicines WHERE name % 'paracetmol' ORDER BY s DESC LIMIT 10;

-- (b) Product attributes in JSONB (e.g. {"form":"tablet","strength_mg":500,"rx":false})
CREATE INDEX idx_products_attrs ON products USING gin (attrs jsonb_path_ops);
SELECT id FROM products WHERE attrs @> '{"form":"tablet","rx":false}';

-- (c) Hot, tiny subset: ops dashboard polls "orders waiting to be packed" every second
CREATE INDEX idx_orders_pending ON orders (created_at) WHERE status IN ('PENDING','PROCESSING');
--   ~1% of 5 M rows → an index 100× smaller than a full one; and it only changes when status flips.

-- (d) Uniqueness that respects soft deletes
CREATE UNIQUE INDEX uq_users_email_active ON users (lower(email)) WHERE deleted_at IS NULL;

-- (e) Append-only audit/event log, 3 billion rows, queried by time window
CREATE INDEX idx_events_created_brin ON events USING brin (created_at) WITH (pages_per_range = 64);
--   a few MB instead of ~60 GB for a B-tree.

-- (f) Doctor availability: forbid overlapping appointments at the database level
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE appointments ADD CONSTRAINT no_double_booking
  EXCLUDE USING gist (doctor_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
```

## 3.7 Trade-offs, limitations and failure scenarios

* **GIN write cost & pending-list latency spikes.** A bulk load into a table with a GIN index can be 5–20× slower; consider dropping and rebuilding the index for bulk loads.
* **Trigram indexes are large** (every 3-character shingle is a key) and slow to build; don't put them on huge text columns you rarely search.
* **BRIN silently degrades** if physical order stops correlating with the column (e.g. after heavy updates/`VACUUM FULL`/backfills that scatter timestamps). Check `correlation` in `pg_stats`.
* **Partial indexes are used only when the planner can *prove* the query predicate implies the index predicate.** With parameterized queries/prepared statements, the planner may not be able to prove `status = $1` implies `status = 'PENDING'` in a generic plan → index not used. Write the literal in the query for those hot paths.
* **Expression indexes require the *exact* expression** in the query (`lower(email)`, not `LOWER(TRIM(email))`).
* **Covering indexes** only produce index-only scans when the visibility map is current — a table with heavy updates and lazy vacuum will show large `Heap Fetches` and lose the benefit.

## 3.8 LSM trees and skiplists — "indexes" that are not B-trees

You will run into these even if you never build them:

* **LSM tree** (RocksDB, Cassandra, LevelDB; MyRocks as a MySQL engine): writes go to an in-memory sorted *memtable* + WAL; flushed as immutable sorted files; background **compaction** merges levels. Reads may check several levels (Bloom filters avoid most). Pros: very high sustained write throughput, great compression. Cons: **read amplification**, **write amplification from compaction**, compaction I/O storms, space amplification.
* **Redis** is not B-tree based: keys live in a hash table (O(1) lookups); **sorted sets (ZSET)** use a **skiplist + hash table** to give O(log N) by-score range queries (`ZRANGEBYSCORE`) — conceptually the same *job* as a B-tree range scan, tuned for RAM instead of disk. That's why a Redis ZSET is a good "leaderboard/index of recent items" but a poor place for data that doesn't fit in memory. (Lab 11.)

## 3.9 Common mistakes

1. Using B-tree for `LIKE '%term%'` or JSONB containment and wondering why it scans.
2. Using GIN on a write-heavy table without measuring.
3. Forgetting `text_pattern_ops` / using a non-C collation for prefix `LIKE`.
4. Creating a hash index "because it's O(1)".
5. Building a partial index and then querying with a predicate the planner can't match.
6. Not using `CONCURRENTLY`.

## 3.10 Check yourself

1. Why can't a B-tree serve `jsonb @> '{"rx":false}'`?
2. You have a 2 B-row append-only table queried by `created_at` windows. Compare B-tree vs BRIN on size, build cost, and failure mode.
3. When is a partial index a *better* answer than a composite index?
4. Why does a GIN index make bulk inserts slow, and what is `fastupdate` trading?

---

# 4. Composite indexes, selectivity and multi-column indexing

## 4.1 Concept

A **composite (multicolumn) index** on `(a, b, c)` is a single B+Tree whose key is the *tuple* `(a, b, c)`, sorted **lexicographically**: first by `a`; among equal `a`, by `b`; among equal `(a, b)`, by `c`. Exactly like a phone book sorted by *last name, then first name*.

```
 Index on (user_id, status, created_at)          Entries in leaf order:
 ─────────────────────────────────────          (1, 'CANCELLED', 2026-01-04)
                                                (1, 'DELIVERED', 2025-12-30)
                                                (1, 'DELIVERED', 2026-02-11)
                                                (1, 'SHIPPED',   2026-03-01)
                                                (2, 'DELIVERED', 2025-11-20)
                                                (2, 'DELIVERED', 2026-01-17)
                                                …
```

Look at that list and the rules write themselves:

* All rows for `user_id = 1` are **contiguous**. ✔ `WHERE user_id = 1`
* Within `user_id = 1`, all `status = 'DELIVERED'` rows are contiguous **and sorted by `created_at`**. ✔ `WHERE user_id = 1 AND status = 'DELIVERED' ORDER BY created_at`
* All rows with `status = 'DELIVERED'` *across all users* are **scattered** throughout the index. ✘ `WHERE status = 'DELIVERED'` alone can't use it efficiently (it'd have to visit every `user_id` group).

## 4.2 Why it exists

Real queries filter on several columns *and* sort. With only single-column indexes the database has to pick one and filter the rest, or combine several (bitmap AND), both of which touch far more pages than one composite descent that lands exactly on the answer — already **sorted**, so no sort step and `LIMIT` can stop early.

## 4.3 How it works internally

### 4.3.1 Leftmost-prefix rule and the "equality, then one range" rule

The index can **seek** (jump to a contiguous slice) using:

1. A **prefix of equality** conditions on the leading columns, then
2. **at most one range** condition on the next column.

Everything after the first range column can no longer narrow the contiguous slice — it can only be **filtered while scanning** the slice (cheaper than going to the heap, but still a scan).

Index `(user_id, status, created_at)`:

| Query predicate | Seeks on | Notes |
|---|---|---|
| `user_id = 1` | `user_id` | ✔ |
| `user_id = 1 AND status = 'DELIVERED'` | both | ✔ |
| `user_id = 1 AND status = 'DELIVERED' AND created_at > X` | all three | ✔ ideal |
| `user_id = 1 AND created_at > X` | `user_id`; `created_at` only as in-index filter | the `status` gap breaks the chain: scans all of user 1's entries |
| `status = 'DELIVERED'` | nothing (full index scan at best) | skipped the leading column |
| `user_id > 100 AND status = 'DELIVERED'` | range on `user_id`; `status` as filter | range column ended the seek |
| `user_id = 1 ORDER BY status, created_at` | ✔ no sort | order matches the index |
| `user_id = 1 ORDER BY created_at` | sort required | `status` sits between |

> **Skip scan:** MySQL 8.0.13+ has a limited *index skip scan* optimization for a missing leading column with few distinct values, and PostgreSQL 18 added B-tree skip scan. Treat these as a nice rescue, **not** a design principle — design the index for the query you actually run.

### 4.3.2 Selectivity and cardinality (what they are, precisely)

* **Cardinality** of a column = number of distinct values.
* **Selectivity** of a *predicate* = fraction of rows it matches. Low fraction (e.g. 0.001%) = *highly selective* = good for an index.
* The planner estimates selectivity from **statistics**: `n_distinct`, most-common-values (MCV) and their frequencies, a **histogram** of the remaining values, `null_frac`, and `correlation` (how closely physical order follows value order). See `pg_stats`.

```
 orders.status (5 M rows)            frequency    predicate selectivity
 DELIVERED                              92.0%       0.92   ← index useless: seq scan wins
 CANCELLED                               4.0%       0.04   ← borderline
 SHIPPED                                 3.0%       0.03   ← bitmap scan maybe
 PROCESSING                              0.9%       0.009  ← index helps
 PENDING                                 0.1%       0.001  ← index shines (partial index!)
```

**Important:** selectivity belongs to the *(column, value)* pair, not the column alone. A column with only 5 distinct values (low cardinality) can be an excellent index target for the rare value and a terrible one for the common value. This is why a plain B-tree on `status` is *usually* wasted, while a **partial index** `WHERE status = 'PENDING'` is superb.

**The crossover point.** Index access = random reads (one heap page per matching row, worst case). Seq scan = sequential reads of the whole table. With `random_page_cost = 4` (default) vs `seq_page_cost = 1`, the planner typically abandons a plain index scan once a predicate matches more than ~a few percent of rows (bitmap scans push this further). On SSD, set `random_page_cost ≈ 1.1–1.5` — otherwise PostgreSQL is too pessimistic about indexes.

### 4.3.3 "Put the most selective column first" — the myth, and the real rule

You will hear: *"order columns by cardinality, highest first."* It's a heuristic that's right sometimes for the wrong reason. The actual design procedure is:

1. **Equality columns first.** (They produce a single contiguous slice.)
2. **Then the column you ORDER BY** (so the slice comes out already sorted → no sort, `LIMIT` stops early).
3. **Then the range column** (`>`, `<`, `BETWEEN`) — **last**, because a range ends the seek.
4. Among several equality columns, the order doesn't change *how many entries* one query touches (all must match anyway). Pick the order that **maximizes reuse across your query set** (put the column that appears in the most queries leftmost) and gives **useful prefixes**.

This is often called **ESR: Equality, Sort, Range.**

Worked example — the query that appears in every order-history screen:

```sql
SELECT id, total, created_at
FROM orders
WHERE user_id = 42 AND status = 'DELIVERED' AND created_at >= now() - interval '90 days'
ORDER BY created_at DESC
LIMIT 20;
```

| Candidate index | Verdict |
|---|---|
| `(user_id)` | finds user's ~10 orders (avg); then filters and sorts in memory. OK here because users are small; **terrible for a B2B pharmacy with 500 k orders**. |
| `(status)` | 92% of the table. Never. |
| `(created_at)` | walks recent orders of *all* users backwards, filtering for user 42 — fast only if user 42 is very active. Unpredictable. |
| `(user_id, created_at DESC)` | ✔ one descent; reads newest entries for user 42, filters status on the way (cheap if most are DELIVERED), stops at 20. **Great default.** |
| `(user_id, status, created_at DESC)` | ✔✔ the exact slice, already ordered. Best for this query; but then `WHERE user_id = 42 ORDER BY created_at DESC` (no status) can't use the order → needs its own index. |
| `(user_id, status, created_at DESC) INCLUDE (total)` | ✔✔✔ plus index-only scan for `id,total,created_at`. Costs more space & write cost. |

Engineering judgment: if you have both query shapes (with and without `status`), `(user_id, created_at DESC)` serves both reasonably, whereas `(user_id, status, created_at)` serves one perfectly. **Choose by measured query mix and by how many rows the extra filter would discard.** If `status='DELIVERED'` is 92% of a user's orders, filtering inside the slice costs nothing; adding `status` to the index buys almost nothing and costs write amplification.

### 4.3.4 The index-vs-bitmap-AND alternative

Two single-column indexes `(a)` and `(b)` can be combined: scan each, build a bitmap of matching heap pages, `AND` them, then fetch. Flexible (supports arbitrary combinations), but: no ordering (still needs a sort), both scans must read all their matches, and the bitmaps are *lossy* when large. A good composite beats BitmapAnd for hot queries; BitmapAnd is the reasonable fallback for ad-hoc filter combinations.

### 4.3.5 Correlated columns and bad estimates

The planner assumes columns are **independent**: `sel(a=x AND b=y) = sel(a=x) × sel(b=y)`. If `city='Dhaka'` and `pharmacy_zone='Banasree'` are strongly correlated, the product underestimates by orders of magnitude → wrong join order/scan choice. Fix with **extended statistics**:

```sql
CREATE STATISTICS orders_city_zone (dependencies, ndistinct, mcv) ON city, zone FROM addresses;
ANALYZE addresses;
```

> **MySQL/InnoDB notes:** (1) Secondary indexes implicitly append the PK: an index on `(user_id, created_at)` is physically `(user_id, created_at, id)` — so `ORDER BY user_id, created_at, id` and PK-covering queries are free. (2) `EXPLAIN` shows `Using index` (covering), `Using filesort` (explicit sort needed), `Using index condition` (index condition pushdown — filtering done inside the engine on index columns before fetching the row), `Using temporary`. (3) MySQL 8.0 supports **histograms** (`ANALYZE TABLE … UPDATE HISTOGRAM ON col`) for non-indexed columns; index statistics come from sampled "dives" (`innodb_stats_persistent_sample_pages`).

## 4.4 Architecture: how the planner combines these facts

```
   query ─► predicates & ORDER BY
                │
                ▼
   for each candidate index:
        usable prefix? (equality chain + ≤1 range)  ──no──► index unusable / full index scan
                │ yes
                ▼
        est. selectivity from pg_stats (MCV, histogram, n_distinct, correlation)
                │
                ▼
        est. cost = index pages + heap pages (× random_page_cost) + CPU
                │            (covering & all-visible? skip heap)
                ▼
        does index order satisfy ORDER BY / LIMIT?  → bonus: skip sort, stop early
                │
                ▼
   compare vs seq scan, bitmap scan, other indexes → cheapest wins
```

## 4.5 More realistic examples

```sql
-- 1. Inventory by pharmacy for a medicine ("who has Napa 500 in stock near me?")
--    Equality on medicine_id, equality on in_stock, then sort by price.
CREATE INDEX idx_inv_med_stock_price ON inventory (medicine_id, price) WHERE quantity > 0;

-- 2. Keyset pagination (Chapter 7): composite key must match the ORDER BY exactly,
--    with a unique tiebreaker so pages are stable.
CREATE INDEX idx_orders_user_created_id ON orders (user_id, created_at DESC, id DESC);
SELECT id, created_at, total FROM orders
WHERE user_id = 42
  AND (created_at, id) < ('2026-03-01 10:00+00', 8123456)      -- row-value comparison, uses the index
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 3. Multi-tenant SaaS: tenant_id first in EVERY index — tenant isolation and locality.
CREATE INDEX ON invoices (tenant_id, status, due_date);

-- 4. Cleaning up redundancy: (user_id) is redundant when (user_id, created_at) exists.
--    The shorter one is a strict subset for lookups; dropping it saves writes and RAM.
DROP INDEX CONCURRENTLY idx_orders_user_id;
```

## 4.6 Trade-offs, limitations and failure scenarios

| Issue | Detail |
|---|---|
| **Write cost grows with every index** | A row with 6 indexes: 6 index inserts + heap + WAL for all. Updating *any indexed column* defeats HOT. |
| **Wide indexes are fat** | Every column in the key is repeated in every internal page entry (modulo truncation) and every leaf entry. A 5-column index may rival the table in size. |
| **Order is a one-way decision** | `(a,b)` ≠ `(b,a)`. Changing means a new index + dropping the old one — on a large table, hours of I/O. Test with real data first (invisible indexes in MySQL; `CREATE INDEX CONCURRENTLY` + `EXPLAIN` in Postgres; **HypoPG** extension for *hypothetical* indexes). |
| **OR conditions** | `WHERE a = 1 OR b = 2` can't use a single composite; planner may BitmapOr two indexes or fall back to seq scan. Rewrite as `UNION ALL` when hot. |
| **Mixed ASC/DESC** | `ORDER BY a ASC, b DESC` needs a matching index definition; otherwise a sort. |
| **`NULL` handling** | PostgreSQL B-trees index NULLs (sorted last by default). `col IS NULL` can use the index. MySQL also indexes NULLs. Unique constraints treat NULLs as distinct (PG 15+ adds `NULLS NOT DISTINCT`). |
| **Stale statistics** | After a big load/delete, `n_distinct`/MCV are wrong → bad plans. `ANALYZE`. |
| **Parameter sniffing / generic plans** | A prepared statement's generic plan chosen for typical values performs terribly for a skewed value (e.g. a whale customer with 5 M orders). PostgreSQL's `plan_cache_mode` (`auto`/`force_custom_plan`) controls this. |

## 4.7 At production scale

Suppose `orders` has **500 M rows**, ~3 k inserts/s, and each insert/update currently maintains **9 indexes**.

* Write amplification: 9 index writes + heap + WAL per insert. At 3 k/s that's ~30 k index-page modifications/s — each potentially a random page → you can be I/O-bound on *writes* caused by indexes nobody uses. **Audit with `pg_stat_user_indexes`** and drop zombies. Going from 9 → 5 indexes can cut write I/O by roughly 40% and shrink the buffer-pool footprint.
* **Partial indexes for hot subsets** (PENDING/PROCESSING orders) keep the *operational* queries fast even as the table grows without bound, because the partial index size tracks only the active subset.
* **Partition by time** (monthly) so that old partitions' indexes go cold; queries with a `created_at` filter get partition pruning, and `DROP PARTITION` replaces slow `DELETE`s (no bloat, no vacuum).
* **Covering indexes for the top 3 hottest queries only.** Each `INCLUDE`d column increases index size and update cost; only do it where `EXPLAIN (ANALYZE, BUFFERS)` shows heap fetches dominating.
* **Review index set quarterly** against real traffic using `pg_stat_statements` (top queries by total time) rather than guessing.

## 4.8 Experiments

* **Lab 2** — selectivity and the planner's crossover from index → bitmap → seq scan as you vary the predicate.
* **Lab 3** — composite index column-order experiments with `EXPLAIN (ANALYZE, BUFFERS)`: measure pages touched for `(a,b)` vs `(b,a)` vs ESR order.

## 4.9 Common mistakes

1. "Most selective column first" applied blindly (ignoring ORDER BY and range placement).
2. Putting the **range** column before an equality column.
3. Creating separate single-column indexes for every column and hoping the planner "combines" them well.
4. Redundant prefix indexes: `(a)`, `(a,b)`, `(a,b,c)` all present.
5. Not including the **tiebreaker** (`id`) in keyset-pagination indexes.
6. Indexing low-cardinality booleans/enums instead of using partial indexes.
7. Ignoring **skew**: designing for the average user, then a whale tenant takes the site down.
8. Forgetting that `ANALYZE` data and real traffic differ from your dev dataset — always test on production-sized data.

## 4.10 Check yourself

1. Why is `(user_id, created_at DESC)` better than `(created_at DESC, user_id)` for "latest orders of a user"? And for "latest orders overall, optionally filtered by user"?
2. 92% of rows have `status = 'DELIVERED'`. Give two different index strategies that make `WHERE status = 'PENDING'` fast without wasting space on the other 99.9% of rows.
3. Explain why `WHERE user_id = ? AND created_at > ? AND status = ?` should use `(user_id, status, created_at)` and not `(user_id, created_at, status)`.
4. Your `UPDATE orders SET status = …` became 3× slower after someone added `INDEX (status, created_at)`. Why, even though that index is "useful"?

# 5. Query execution, planning and optimization

## 5.1 Concept

SQL is **declarative**: you say *what* you want, never *how* to get it. Between your `SELECT` and the rows coming back sits a pipeline that decides *how*:

```
 SQL text
   │
   ▼  PARSER         syntax → raw parse tree
   ▼  ANALYZER       resolve table/column names, types, functions → query tree
   ▼  REWRITER       expand views, apply rules, (inline CTEs, pull up subqueries)
   ▼  PLANNER        enumerate candidate physical plans, estimate each one's COST, pick the cheapest
   ▼  EXECUTOR       run the chosen plan tree, pulling rows through it
   ▼  rows → client
```

The **plan** is a *tree of operators* (scan, join, sort, aggregate, limit …). The executor runs it with the classic **iterator ("Volcano") model**: the root asks its child for "the next row", which asks its child, and so on down to the scans that touch pages. Rows flow **upwards**, one at a time, like a pipeline.

## 5.2 Why it exists

For one query there can be *millions* of equivalent plans: which index to use, which join algorithm, which table to join first (for *n* tables there are up to *n!* orders). The difference between the best and worst plan is routinely **1,000× or more**. A human can't pick per-query at runtime as data changes, so the database does it using a **cost-based optimizer (CBO)**: *statistics → row-count estimates → cost estimates → cheapest plan*.

The crucial implication for you: **the optimizer is only as good as its statistics and its cost model.** Almost every "the database chose a stupid plan" incident is really *"the database was fed a wrong estimate"*.

## 5.3 How it works internally

### 5.3.1 Access paths (how one table is read)

| Node | What it does | Wins when | Loses when |
|---|---|---|---|
| **Seq Scan** | Read every heap page in order, filter rows | Tiny table, or you need a large fraction (>~5–20%) of rows; sequential I/O is very fast | Selective predicate on a big table |
| **Index Scan** | Descend B-tree, then for each match fetch the heap row (random I/O) and check visibility | Few matching rows; or you need **index order** (`ORDER BY … LIMIT`) | Many matches scattered across heap pages |
| **Index Only Scan** | Answer from the index alone if the heap page is all-visible | Covering index + well-vacuumed table | Visibility map stale → many *Heap Fetches* |
| **Bitmap Index Scan → Bitmap Heap Scan** | Collect all matching ctids into a bitmap, sort by page, read each heap page once (sequentially-ish) | Medium selectivity (~1–15%); combining several indexes (BitmapAnd/Or) | Needs `work_mem` for big bitmaps (becomes *lossy*, rechecks rows) |

### 5.3.2 Join algorithms (how two row streams are combined)

```
 NESTED LOOP                       HASH JOIN                          MERGE JOIN
 ───────────                       ─────────                          ──────────
 for each row r in OUTER:          1. BUILD: read smaller input,      1. Both inputs sorted on join key
     probe INNER for matches          build in-memory hash table      2. Walk both with two cursors
     (ideally via index:              on the join key                     like a zipper
      O(log n) per probe)          2. PROBE: stream larger input,
                                      look up each row in the hash
 Cost ≈ N_outer × cost(probe)      Cost ≈ N_small + N_large           Cost ≈ sort(A)+sort(B)+N_A+N_B
                                                                       (free if both come from indexes)
```

| Algorithm | Best for | Needs | Danger |
|---|---|---|---|
| **Nested Loop** (+ index on inner) | Small outer set, indexed inner (typical OLTP: "this order's items") | Index on join column of the inner side | If the planner *thinks* outer = 1 row but it is 2 M → 2 M index probes = disaster |
| **Hash Join** | Large, unsorted inputs; equality joins; no useful index | `work_mem` for the hash table; else **spills to disk in batches** | Memory/disk spill; only equality (`=`) joins |
| **Merge Join** | Both sides already sorted (index order) or very large; supports `<`/`>` join ranges | Sorted inputs | Sorting cost if not pre-sorted |

Other operators: **Sort** (in-memory quicksort; *top-N heapsort* when there is a `LIMIT`; **external merge on disk** when over `work_mem`), **HashAggregate** vs **GroupAggregate** (hash vs sorted input), **Limit** (stops pulling early → huge win with ordered index access), **Gather** (parallel workers).

> **MySQL/InnoDB note:** Historically MySQL only had (block) nested-loop joins; **hash join** arrived in 8.0.18. The optimizer is more heuristic; `EXPLAIN` shows join order in the row order of the output. Index Condition Pushdown, semi-join strategies (`FirstMatch`, `LooseScan`, `Materialization`) and derived-table merging matter. Use `EXPLAIN ANALYZE` (8.0.18+), `EXPLAIN FORMAT=TREE`, and `optimizer_trace` to see decisions.

### 5.3.3 Pipelined vs blocking operators

* **Pipelined** (stream rows as they arrive): Seq/Index scans, Nested Loop, Limit, Filter. A `LIMIT 20` over these can stop after 20 rows → *startup cost is low*.
* **Blocking** (must consume *all* input before emitting the first row): Sort (unless fed ordered), Hash build, HashAggregate, Materialize. Total cost matters, startup cost is high.

This is why `ORDER BY created_at DESC LIMIT 20` is instant with a matching index (pipelined + stop early) and takes seconds without one (read everything → sort → throw away all but 20).

### 5.3.4 The cost model

The planner assigns each node a **cost in abstract units**, built from tunable constants:

| Parameter | Default | Meaning |
|---|---|---|
| `seq_page_cost` | 1.0 | Read one page sequentially |
| `random_page_cost` | 4.0 | Read one page randomly (**lower to ~1.1–1.5 on SSD/NVMe**) |
| `cpu_tuple_cost` | 0.01 | Process one row |
| `cpu_index_tuple_cost` | 0.005 | Process one index entry |
| `cpu_operator_cost` | 0.0025 | Evaluate one operator/function |
| `effective_cache_size` | 4GB | *Hint* of how much of the data is cached (OS+PG); makes index plans look cheaper when large — set to ~50–75% of RAM |

Each node reports `cost=startup..total`. **Cost is not milliseconds**; it is only meaningful for comparing alternative plans for the *same* query.

### 5.3.5 Cardinality estimation — where plans go wrong

For each predicate the planner estimates `selectivity` from `pg_stats`, multiplies through the tree, and gets an estimated **row count per node**:

```
 est_rows(scan)       = table_rows × selectivity(filter)
 est_rows(join A⋈B)   = rows(A) × rows(B) × join_selectivity     (≈ 1 / max(n_distinct_A, n_distinct_B) for equality)
```

Sources of error (memorize this list; it explains 90% of bad plans):

1. **Stale statistics** (after bulk load/delete; autovacuum's analyze threshold not reached).
2. **Column correlation** — independence assumption (fix: `CREATE STATISTICS`).
3. **Skew beyond the MCV list** (raise `ALTER TABLE … ALTER COLUMN … SET STATISTICS 500`).
4. **Expressions/functions** the planner can't see through (`WHERE f(x) = 1` gets a default guess like 0.5% or 33%) — fix with an expression index (which also creates statistics) .
5. **Many joins**: errors multiply with each level. A 10× error per join across 5 joins is 100,000×.
6. **Parameterized/generic plans** with skewed parameters.
7. **Data that changed after planning** (long-lived prepared plans).

### 5.3.6 Join-order search and planner limits

For ≤ `join_collapse_limit` (default 8) relations the planner does a dynamic-programming search over join orders. Above `geqo_threshold` (12) it switches to a **genetic algorithm** (randomized, may be suboptimal). Deeply nested ORM-generated joins (Django `select_related` chains, GraphQL resolvers) can cross these limits and produce unstable plans.

### 5.3.7 Other mechanisms you will meet

* **Predicate pushdown / constant folding / join elimination / partition pruning** — the rewriter and planner move filters as close to the scan as possible and drop unnecessary tables/partitions.
* **CTEs** (`WITH`) are *inlined* by default since PG 12 unless referenced multiple times or marked `MATERIALIZED`. Pre-12 CTEs were optimization fences — old advice about "CTEs are slow" is often outdated.
* **Parallel query**: `Gather` + parallel seq scan / hash join / aggregate across worker processes (`max_parallel_workers_per_gather`). Great for big analytical scans; counter-productive in high-concurrency OLTP (steals CPU from other sessions).
* **Prepared statements**: PostgreSQL plans the first 5 executions with the real parameter values (*custom plans*), then may switch to a *generic plan* if its estimated cost isn't worse. For skewed data this can hurt; control with `plan_cache_mode`.
* **JIT compilation** (LLVM) can add 50–500 ms planning/compile overhead to queries the planner thought were expensive — frequently a net loss for OLTP (`jit = off` is a common production setting).

## 5.4 Architecture: a plan tree for a real query

```sql
SELECT p.name, sum(oi.qty) AS units
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products    p  ON p.id        = oi.product_id
WHERE o.pharmacy_id = 17 AND o.created_at >= now() - interval '7 days'
GROUP BY p.name
ORDER BY units DESC
LIMIT 10;
```

```
 Limit (10)
  └─ Sort (units DESC)  [top-N heapsort]          ← blocking, but only keeps 10 rows
      └─ HashAggregate (group by p.name)           ← blocking
          └─ Hash Join (p.id = oi.product_id)
              ├─ Nested Loop (oi.order_id = o.id)             ← outer: ~3k recent orders of pharmacy 17
              │   ├─ Index Scan on orders o  (idx: pharmacy_id, created_at)   ← equality + range = ideal
              │   └─ Index Scan on order_items oi (idx: order_id)             ← probed ~3k times
              └─ Hash                                        ← build side
                  └─ Seq Scan on products p   (20k rows — cheaper to hash all than probe)
```

Reading it: executor starts at the leaves; `orders` yields ~3 k rows; each probes `order_items`; results probe a hash of `products`; aggregate; top-10 sort; return. If the planner mis-estimates the `orders` scan as 3 rows instead of 3,000, it might choose nested loop all the way — and then the *actual* run does 3,000× more probes than planned.

## 5.5 Realistic backend examples

1. **Why does `WHERE id = $1` pick Index Scan but `WHERE status = 'DELIVERED'` picks Seq Scan?** Selectivity: 1 row vs 92% of the table. (Lab 2 lets you watch the flip as you widen the predicate.)
2. **The Monday-morning plan flip.** A report that ran in 200 ms for months suddenly takes 40 s. Cause: a weekend bulk import doubled a table; autovacuum's auto-analyze hadn't re-sampled yet; estimated 100 rows, got 400 k, nested loop exploded. Fix: `ANALYZE` after bulk loads (in the job itself); raise statistics target on the skewed column; long-term, add `CREATE STATISTICS`.
3. **Prepared-statement skew.** `SELECT … WHERE tenant_id = $1`: 99% of tenants have <100 rows, one has 20 M. After 5 executions PG caches a generic plan tuned for "average" tenant → Index Scan + Nested Loop; whale tenant runs 100× slower. Fix: `plan_cache_mode = force_custom_plan` for that role/query or separate whale tenants.
4. **ORM fan-out.** A Django queryset with three `select_related` + two `prefetch_related` chains yields a 7-way join that the planner times out optimizing (geqo). Fix: break into explicit queries, or flatten with an annotated/`values()` query.

## 5.6 Trade-offs, limitations and failure scenarios

* **The optimizer has no hints in PostgreSQL by design.** You fix plans by fixing inputs: statistics, indexes, query shape, cost constants. (Extensions like `pg_hint_plan` exist; use sparingly. MySQL has optimizer hints and `FORCE INDEX`.)
* **`work_mem` is per sort/hash *node*, per *connection*.** A query with 5 hash/sort nodes × 200 connections × `work_mem = 256MB` = potential 250 GB → OOM kill. Set modest global `work_mem` (4–64 MB), raise per-role/per-session for reporting jobs.
* **Plan instability.** The same query may flip plans when stats refresh or a threshold is crossed. Mitigate with up-to-date stats, extended stats, avoiding fragile query shapes (leading wildcards, function-wrapped columns), and *monitoring plan changes* for critical queries.
* **`enable_seqscan = off` and friends** are diagnostic tools only (to see *what the alternative would cost*), never production settings.

## 5.7 At production scale

* Enable **`pg_stat_statements`**: it aggregates every query by normalized text with calls, total/mean time, rows, shared blocks hit/read. Your tuning backlog = top queries by *total_exec_time*, not just by single-run slowness (a 5 ms query run 10 k times/s is a bigger problem than a 2 s nightly one).
* Enable **`auto_explain`** (`log_min_duration`, `log_analyze`, `log_buffers`) to capture plans of slow queries *as they ran in production* — the only way to see the plan that actually hurt.
* Keep stats healthy: per-table autovacuum/analyze thresholds on large tables (the default 10%-change trigger means a 1 B-row table isn't re-analyzed until 100 M rows change; set `autovacuum_analyze_scale_factor = 0.01` or lower for big tables).
* **Route workloads.** Heavy reporting/ETL → read replica or warehouse; OLTP primary stays predictable.
* **Test on production-shaped data.** A plan on 10 k dev rows tells you nothing about 500 M rows. Use a restored snapshot or a statistically similar generated dataset in CI for critical queries.

## 5.8 Experiments

**Lab 2** (selectivity → plan flips), **Lab 3** (composite order), **Lab 9** (Python: N+1 and OFFSET vs keyset).

## 5.9 Common mistakes

1. Reading `cost=` as milliseconds.
2. "Fixing" a bad plan by adding another index before checking whether the *estimate* was the real problem.
3. Forgetting to `ANALYZE` after bulk loads or restores (a freshly restored dump has **no statistics**).
4. Setting `random_page_cost = 4` on NVMe, so the planner avoids perfectly good index scans.
5. Setting a huge global `work_mem`.
6. Testing queries only on tiny dev databases.
7. Disabling `autovacuum` (it also drives `ANALYZE`).

## 5.10 Check yourself

1. A query has `LIMIT 20`. Why can the best plan differ from the same query without the `LIMIT`?
2. When is a Hash Join better than a Nested Loop, and when is the reverse true? What *single bad estimate* turns the second into a catastrophe?
3. Why can the planner not know the selectivity of `WHERE lower(name) = 'x'` without an expression index?
4. What is the difference between **startup cost** and **total cost**, and which matters for `LIMIT` queries?

---

# 6. `EXPLAIN ANALYZE`: reading plans like a professional

## 6.1 Concept

* `EXPLAIN <query>` — shows the plan the optimizer **would** choose, with **estimated** costs/rows. Doesn't run the query.
* `EXPLAIN ANALYZE <query>` — **executes** the query and adds **actual** timings, row counts and loop counts.
* `EXPLAIN (ANALYZE, BUFFERS)` — also shows page-level I/O: how many pages were found in the buffer pool (`hit`) vs read from the OS/disk (`read`), dirtied or written, and temp-file usage. **This is the form you should use by default.**

The skill is comparing **what the planner believed** (estimates) with **what actually happened** (actuals). The gap is where the bug is.

## 6.2 Why it exists

Without it you tune by superstition ("add an index and pray"). With it you can state, with evidence: *"this query reads 52 k pages to return 9 rows because there's no index on `user_id`; the estimate was right; the fix is an index"* — or *"the planner expected 1 row and got 2 M because the statistics are stale; the fix is ANALYZE, not an index."* Those are different fixes for the same symptom.

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT …;
-- Newer releases turn BUFFERS on automatically with ANALYZE; be explicit anyway so the habit is portable.
```

> ⚠️ **`ANALYZE` really executes the statement.** For `INSERT/UPDATE/DELETE` wrap it: `BEGIN; EXPLAIN ANALYZE UPDATE …; ROLLBACK;`. Never run it on a destructive statement without the rollback.

## 6.3 How to read a plan — annotated

Illustrative output (your numbers will differ) on the 5 M-row `orders` table from §0.4 **with no useful index**:

```
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, total FROM orders
WHERE user_id = 42 AND status = 'DELIVERED'
ORDER BY created_at DESC LIMIT 20;

 Limit  (cost=121530.1..121530.2 rows=20 width=18) (actual time=398.2..398.3 rows=9 loops=1)        ①
   Buffers: shared hit=1250 read=36420                                                              ②
   ->  Sort  (cost=121530.1..121530.2 rows=9 width=18) (actual time=398.2..398.2 rows=9 loops=1)
         Sort Key: created_at DESC
         Sort Method: quicksort  Memory: 25kB
         ->  Seq Scan on orders  (cost=0.00..121529.9 rows=9 width=18)                              ③
                                 (actual time=2.9..398.0 rows=9 loops=1)
               Filter: ((user_id = 42) AND (status = 'DELIVERED'::text))
               Rows Removed by Filter: 4999991                                                      ④
               Buffers: shared hit=1250 read=36420
 Planning Time: 0.2 ms
 Execution Time: 398.4 ms
```

* ① `(cost=startup..total rows=est width=bytes)` is the **estimate**; `(actual time=first_row..last_row rows=N loops=L)` is **reality** (milliseconds).
* ② `Buffers: shared hit=1250 read=36420` → 1,250 pages from cache and **36,420 pages read** from disk/OS: that is the true cost. 36 k × 8 KB ≈ 290 MB touched to return 9 rows.
* ③ `Seq Scan` + selective filter = candidate for an index.
* ④ `Rows Removed by Filter: 4,999,991` is the smoking gun: *five million rows examined, nine kept.* Ratio of removed to returned is your "wasted work" indicator.

After `CREATE INDEX idx_orders_user_status_created ON orders (user_id, status, created_at DESC);`:

```
 Limit  (cost=0.43..8.9 rows=20 width=18) (actual time=0.040..0.058 rows=9 loops=1)
   Buffers: shared hit=12
   ->  Index Scan using idx_orders_user_status_created on orders
         (cost=0.43..8.9 rows=9 width=18) (actual time=0.039..0.055 rows=9 loops=1)
         Index Cond: ((user_id = 42) AND (status = 'DELIVERED'::text))
         Buffers: shared hit=12
 Planning Time: 0.15 ms
 Execution Time: 0.08 ms
```

Sort node gone (index order satisfies `ORDER BY`), 12 pages instead of 37,670, 5,000× faster. This is the whole discipline in miniature.

### The reading checklist (follow in order)

1. **Read inside-out / bottom-up.** The most-indented nodes execute first; parents consume their output.
2. **Estimated vs actual rows.** A mismatch of **>10×** at any node = statistics/estimation problem; that node (and everything above it) was planned on false data. Look for the *lowest* node where it starts.
3. **Multiply by `loops`.** `actual time` and `rows` are **per loop (average)**. A node showing `actual time=0.5 rows=1 loops=200000` costs ≈100 s total. *Inner side of a nested loop is the classic place to find this.*
4. **Buffers.** `shared read` ≫ 0 means cold/disk I/O; `shared hit` is cache. `temp read/written` means a spill (sort/hash exceeded `work_mem`). `dirtied`/`written` appear in write queries.
5. **`Rows Removed by Filter`** (or `Rows Removed by Index Recheck`) large vs rows returned → missing/wrong index or lossy bitmap.
6. **Sort Method**: `quicksort Memory` (good), `top-N heapsort` (good, with LIMIT), `external merge Disk: 120MB` (spilled — raise `work_mem` for that role or add index for order).
7. **Hash node**: `Batches: 1` is good; `Batches: 16` means the hash table spilled to disk.
8. **Index Only Scan** → check `Heap Fetches:`; large numbers mean vacuum/visibility map isn't helping.
9. **Parallel**: `Workers Planned: 2 / Launched: 0` means no workers were available.
10. **Planning vs Execution time**; very high planning time = too many joins/partitions/`JIT` overhead (look for a `JIT:` section with large timing).

### Node cheat sheet

| You see | It means | Usually fine? |
|---|---|---|
| `Seq Scan` + tiny `Rows Removed` | Reading most of the table | Yes |
| `Seq Scan` + huge `Rows Removed by Filter` | Missing/unusable index | **No** |
| `Index Scan` with huge actual rows ×loops | Too many random heap fetches | Check; consider bitmap/covering index |
| `Bitmap Heap Scan` + `Recheck Cond` + `Heap Blocks: lossy` | bitmap exceeded `work_mem` | Raise `work_mem` or narrow |
| `Nested Loop` with inner `loops` in the thousands+ and inner is Seq Scan | Missing index on join column | **No** |
| `Hash Join` with `Batches > 1` | Spill | Maybe raise `work_mem` |
| `Sort Method: external merge` | Spill | Maybe |
| `Materialize` repeated | Inner re-read many times | Suspicious |
| `Gather` / `Parallel Seq Scan` | Parallel big scan | OK for analytics, careful in OLTP |

## 6.4 A failure-mode example: the estimate that was off by a million

```
 Nested Loop  (cost=1.1..95.3 rows=1 width=40) (actual time=0.05..41872 rows=2100000 loops=1)
   ->  Index Scan on campaigns c (cost=0.4..8.4 rows=1 width=8) (actual time=0.03..0.04 rows=1 loops=1)
         Index Cond: (code = 'EIDSALE')
   ->  Index Scan on orders o (cost=0.7..86.7 rows=1 width=32) (actual time=0.01..0.02 rows=2100000 loops=1)
```

(Schematic.) The planner predicted `rows=1` for the join output; reality was **2.1 M**. With a 1-row outer it chose index nested loop — correct *given the belief*. Why was the belief wrong? Perhaps `orders.campaign_id` skew isn't in the MCV list, or the stats were stale after a flash sale loaded 2 M orders in an hour. Diagnosis path: compare `rows=` estimate vs actual at the *lowest* node that disagrees → look at `pg_stats` for that column → `ANALYZE`, raise statistics target, or add extended statistics.

## 6.5 Tooling & variants

* **Django:** `print(Order.objects.filter(user_id=42).explain(analyze=True, buffers=True))`. Also `django-debug-toolbar` (SQL panel → "Explain") in dev.
* **psql helpers:** `\timing on`, `\x`, `\watch`.
* **Visualizers** (paste a plan, get a tree with the slow node highlighted): `explain.dalibo.com` (PEV2), `explain.depesz.com`. Don't paste plans containing sensitive literals into third-party sites.
* **`EXPLAIN (ANALYZE, TIMING OFF)`**: reduces the measurement overhead on slow clocks; row counts remain accurate.
* **MySQL 8:** `EXPLAIN ANALYZE SELECT …` (tree format with actual timing, 8.0.18+), `EXPLAIN FORMAT=JSON`, `EXPLAIN FORMAT=TREE`, `SHOW STATUS LIKE 'Handler_read%'` to count row reads, `optimizer_trace`. Classic `EXPLAIN` columns: `type` (`ALL` = full scan, `index` = full index scan, `range`, `ref`, `eq_ref`, `const`), `key`, `key_len` (how many bytes of a composite index are used → how many columns of the prefix!), `rows`, `filtered`, `Extra`.

## 6.6 Caveats that fool people

1. **Cold vs warm cache.** First run reads from disk; second from cache. Run twice and look at `Buffers read` vs `hit`; reason about the *cold* case for rare queries and the *warm* case for hot ones.
2. **Different data/stats than production** → different plans. Same query, same schema, different plan = look at the statistics, not the SQL.
3. **Timing overhead** of `EXPLAIN ANALYZE` can inflate small, many-loop nodes.
4. **`EXPLAIN` of a prepared/parameterized statement** may show the custom plan; production may be on a generic plan. Use `EXPLAIN (GENERIC_PLAN)` (PG 16+) or `PREPARE … ; EXPLAIN EXECUTE …`.
5. **Triggers, FK checks and constraint validation** appear after the plan as `Trigger …: time=…` lines — easy to miss, sometimes the real cost of a bulk delete.

## 6.7 At production scale

Don't hand-run EXPLAIN as your only tool. Combine: **`pg_stat_statements`** (what to look at) → **`auto_explain`** (plan as it executed) → **`EXPLAIN (ANALYZE, BUFFERS)` on a replica or restored snapshot** (experiment safely). Keep the "before/after" plan pasted in the PR description for every index or query change — it makes reviews factual and builds a searchable history of why an index exists.

## 6.8 Common mistakes

1. Running `EXPLAIN` without `ANALYZE` and trusting estimates.
2. Forgetting `BUFFERS`.
3. Ignoring `loops`.
4. Concluding "Seq Scan = bad" or "Index Scan = good".
5. Running `EXPLAIN ANALYZE` on `DELETE`/`UPDATE` in production without `BEGIN … ROLLBACK`.
6. Tuning a query on a laptop-size dataset.

## 6.9 Check yourself

Given this fragment, what is wrong and what do you do first?

```
->  Nested Loop  (cost=… rows=40 …) (actual time=0.1..9120 rows=900000 loops=1)
      ->  Seq Scan on a (… rows=40 …) (actual … rows=900000 loops=1)
```

*(Answer: the estimate of 40 vs actual 900 k at the **Seq Scan** — the lowest mismatching node — indicates stale/insufficient stats on the filter column(s) of `a`. Run `ANALYZE a`, check `pg_stats`, consider a higher statistics target or extended statistics. Only after that consider indexes/join strategy.)*

---

# 7. Why database queries become slow (diagnosis playbook)

## 7.1 Concept

A query is slow for exactly one of two reasons:

1. It **does too much work** (reads/sorts/transfers too many pages, rows or bytes), or
2. It **waits** (for a lock, I/O, CPU, a connection, or the network).

Everything below is a classification of *which* — because the cure for each is completely different.

## 7.2 The taxonomy

```
 SLOW QUERY
 ├─ A. TOO MUCH WORK
 │    ├─ A1. No usable index / index not used  (see 7.4)
 │    ├─ A2. Returns/handles too many rows (SELECT *, no LIMIT, huge IN lists, OFFSET pagination)
 │    ├─ A3. Bad plan from bad estimates (stale stats, correlation, skew, generic plan)
 │    ├─ A4. Spills: sort/hash exceeding work_mem → temp files
 │    ├─ A5. Structural: N+1 queries, correlated subqueries, accidental cartesian products, COUNT(*) on huge tables
 │    └─ A6. Bloat: table/index much larger than live data
 ├─ B. WAITING
 │    ├─ B1. Lock waits (long transactions, hot rows, DDL lock queue, idle-in-transaction)
 │    ├─ B2. I/O waits (working set > RAM, IOPS throttled, checkpoint storms)
 │    ├─ B3. CPU saturation (too many parallel workers, JIT, expensive functions, too many connections)
 │    └─ B4. Connection waits (pool exhausted, max_connections thrash, no pooler)
 ├─ C. OUTSIDE THE DATABASE
 │    ├─ C1. Network round trips (chatty ORM), cross-AZ latency
 │    ├─ C2. Large result serialization / slow client consuming rows
 │    └─ C3. App-side pool queueing (the "query" is fast; the *wait for a connection* is slow)
 └─ D. TIME BOMBS (fast yesterday, slow today)
      ├─ D1. Data growth crossing the RAM boundary or an index height boundary
      ├─ D2. Plan flip after ANALYZE or threshold crossing
      └─ D3. A new feature adds a filter/sort the indexes don't cover
```

## 7.3 The diagnostic playbook (do these in order)

**Step 1 — Find *what* is slow, by total impact.**

```sql
-- requires: shared_preload_libraries = 'pg_stat_statements'; CREATE EXTENSION pg_stat_statements;
SELECT calls,
       round(total_exec_time::numeric/1000, 1)  AS total_s,
       round(mean_exec_time::numeric, 2)        AS mean_ms,
       rows,
       shared_blks_hit, shared_blks_read,
       left(query, 100)                         AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 15;
```

**Step 2 — Is the time inside the database or around it?** Compare app-measured latency with `Execution Time`. If the DB says 3 ms and the app sees 200 ms → class C (network, pool wait, serialization, N+1).

**Step 3 — Is it working or waiting?**

```sql
SELECT pid, state, wait_event_type, wait_event,
       now() - xact_start  AS xact_age,
       now() - query_start AS query_age,
       left(query, 80)     AS query
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY xact_start NULLS LAST;
-- wait_event_type = Lock       → blocked by another transaction
-- wait_event_type = IO         → disk
-- state = 'idle in transaction' with big xact_age → a leaked/forgotten transaction (holds locks, blocks vacuum)

-- Who blocks whom?
SELECT a.pid AS blocked, pg_blocking_pids(a.pid) AS blocked_by, left(a.query, 60) AS blocked_query
FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0;
```

**Step 4 — Get the real plan:** `EXPLAIN (ANALYZE, BUFFERS)` (Chapter 6), or `auto_explain` logs.

**Step 5 — Classify and fix** (tables below).

**Step 6 — Verify and guard.** Re-measure with production-shaped data; add a regression test or alert (e.g., alert on p95 query time per endpoint, on `Rows Removed by Filter` in `auto_explain`).

## 7.4 Why an index isn't used (the A1 checklist)

| # | Cause | Example | Fix |
|---|---|---|---|
| 1 | **Function/expression on the column** | `WHERE date(created_at) = '2026-03-01'`, `WHERE lower(email) = …` | Rewrite as a **range** (`created_at >= '2026-03-01' AND created_at < '2026-03-02'`) or create an **expression index** |
| 2 | **Type mismatch / implicit cast** | `varchar` column compared to integer param; `timestamptz` vs `timestamp`; Django passing an int for a `CharField` phone number | Pass the right type; cast the *parameter*, not the column |
| 3 | **Leading wildcard** | `LIKE '%para'` | `pg_trgm` GIN, or reversed-string index for suffix search, or full-text search |
| 4 | **Low selectivity** | `WHERE status = 'DELIVERED'` (92%) | Seq scan is *correct*; use partial index for the rare values |
| 5 | **Wrong composite order / skipped leading column** | index `(user_id, created_at)`, query only on `created_at` | New index shaped for the query (ESR) |
| 6 | **`OR` across different columns** | `a = 1 OR b = 2` | `UNION ALL` of two indexed queries, or BitmapOr |
| 7 | **Leading `NOT`/`<>`/`!=`** | `WHERE status <> 'DELIVERED'` | Positive partial index / rewrite |
| 8 | **Stale statistics → planner thinks seq scan is cheaper** | after bulk load | `ANALYZE` |
| 9 | **`random_page_cost` too high for SSD** | planner avoids index scans | `random_page_cost = 1.1` |
| 10 | **Collation/operator class mismatch** | `LIKE 'abc%'` without `text_pattern_ops` under non-C collation | Add the right opclass |
| 11 | **Partial index predicate not provable** | generic plan with `$1` | Literal predicate; custom plan |
| 12 | **Index invalid or being rebuilt** | failed `CREATE INDEX CONCURRENTLY` left `INVALID` | `DROP INDEX` and retry |
| 13 | **Tiny table** | planner correctly prefers seq scan | Nothing to fix |

## 7.5 Worked examples

### 7.5.1 Function on indexed column

```sql
-- ❌ slow: index on created_at unusable (wrapped in date())
SELECT count(*) FROM orders WHERE date(created_at) = '2026-03-01';

-- ✅ sargable (Search-ARGument-able): bare column vs range
SELECT count(*) FROM orders
WHERE created_at >= '2026-03-01' AND created_at < '2026-03-02';
```

(Mind **time zones**: `'2026-03-01'` for a `timestamptz` is interpreted in the session time zone. For Bangladesh-time day boundaries use `'2026-03-01 00:00+06'`.)

### 7.5.2 OFFSET pagination vs keyset pagination

```sql
-- ❌ page 50,000 → the DB must produce and discard 1,000,000 rows. Cost grows linearly with the page number.
SELECT id, created_at, total FROM orders WHERE user_id = 42
ORDER BY created_at DESC, id DESC OFFSET 1000000 LIMIT 20;

-- ✅ keyset ("seek") pagination: remember the last row of the previous page. Constant cost.
SELECT id, created_at, total FROM orders
WHERE user_id = 42 AND (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC LIMIT 20;
-- needs INDEX (user_id, created_at DESC, id DESC) — see §4.5
```

Trade-off: keyset can't "jump to page 37" — which is fine for feeds/infinite scroll/API cursors, and users never actually click page 50,000.

### 7.5.3 The N+1 query (Django)

```python
# ❌ 1 query for orders + N queries for users + N for items  → 201 round trips for 100 orders
for o in Order.objects.filter(pharmacy_id=17)[:100]:
    print(o.user.name, [i.product.name for i in o.items.all()])

# ✅ 3 queries total
orders = (Order.objects.filter(pharmacy_id=17)
          .select_related("user")                         # JOIN for single-valued FK
          .prefetch_related("items__product")[:100])      # separate IN-queries for multi-valued relations
```

Even though each query is ~0.4 ms, 201 × (0.4 ms query + ~0.5 ms RTT) ≈ 180 ms versus ~3 ms. **Detect** with `django-debug-toolbar`, `assertNumQueries` in tests, `pg_stat_statements` showing a trivially cheap query with enormous `calls`. **Beware the opposite failure:** `select_related` on many to-many chains creates a Cartesian row explosion — prefetch instead.

### 7.5.4 `COUNT(*)` on a big table

PostgreSQL must check visibility per row (MVCC) → `count(*)` on 500 M rows scans an index/heap: seconds to minutes. Options: approximate (`reltuples` from `pg_class`) for UI "about 500 M"; maintain a counter table/materialized view updated asynchronously; restrict with a selective predicate; don't show exact totals in infinite lists.

### 7.5.5 The DDL lock-queue outage (a real classic)

```
 t0  tx A:  long report query holds ACCESS SHARE on orders (running 10 min)
 t1  you:   ALTER TABLE orders ADD COLUMN note text;   → needs ACCESS EXCLUSIVE, waits behind A
 t2  every other query on orders now QUEUES BEHIND THE ALTER (lock queue is FIFO-ish)
 t3  site is down — although the ALTER itself would take 5 ms.
```

Prevention: `SET lock_timeout = '3s';` before DDL (fail fast and retry), run DDL when no long transactions exist, set `idle_in_transaction_session_timeout` and `statement_timeout` for app roles, use *online* patterns (add nullable column, backfill in batches, add constraint `NOT VALID` then `VALIDATE`, `CREATE INDEX CONCURRENTLY`). MySQL's analogue is the **metadata lock (MDL)** pile-up; use `pt-online-schema-change`/`gh-ost`/online DDL (`ALGORITHM=INSTANT/INPLACE`).

## 7.6 Symptom → cause → verify → fix

| Symptom | Likely cause | Verify | Fix |
|---|---|---|---|
| One endpoint slow, always | Missing/wrong index | `EXPLAIN` shows Seq Scan, big `Rows Removed` | Index shaped for query (ESR) |
| Fast for most users, slow for one big tenant | Skew / generic plan | Compare plans for the whale's parameter | Custom plan, partial/composite index, separate tenant |
| Everything slow at the same moment | I/O saturation, checkpoint, noisy neighbor, lock pile-up | `pg_stat_activity` wait events; cloud IOPS metrics | Throttle the culprit; spread checkpoints (`checkpoint_completion_target`); more IOPS |
| Gradual degradation over weeks | Bloat, data outgrew RAM, stats drift | `pg_stat_user_tables.n_dead_tup`, table/index size, hit ratio | Tune autovacuum, `REINDEX CONCURRENTLY`/`pg_repack`, archive/partition, more RAM |
| Sudden regression after deploy | New query shape, ORM change, missing index in migration | `pg_stat_statements` diff | Fix query / add index |
| Fast in DB, slow in app | N+1, pool exhaustion, serialization | App traces; query count per request | `select_related`/`prefetch_related`, resize pool, pagination |
| Timeouts with low CPU and I/O | Lock waits / idle in transaction | `pg_blocking_pids`, `pg_stat_activity` | Shorten transactions, timeouts, fix ordering |
| Replica reads slow/stale | Replication lag, recovery conflicts | `pg_stat_replication`, `pg_stat_database_conflicts` | Tune, scale replica, route fewer queries |
| `too many connections` | Connection per request, no pooler | `count(*) FROM pg_stat_activity` | PgBouncer; right-size app pools |

## 7.7 At production scale

* **Latency budgets:** give every endpoint a DB-time budget (e.g., ≤ 5 queries, ≤ 30 ms total DB time p95). Fail CI when a request exceeds the query-count budget.
* **Defaults that prevent incidents:** `statement_timeout` (e.g., 5–30 s for OLTP roles), `idle_in_transaction_session_timeout` (e.g., 30–60 s), `lock_timeout` for migrations, `log_min_duration_statement`, `log_lock_waits = on`, `track_io_timing = on`.
* **Connection pooling:** PostgreSQL uses a **process per connection** (~5–10 MB each + context-switch cost); thousands of direct connections thrash. Put **PgBouncer** (transaction pooling) in front; keep total backend connections ≈ a small multiple of CPU cores (e.g., 50–200) regardless of how many app pods you scale to. In Kubernetes, N pods × pool size silently multiplies — compute it.
* **Capacity thinking:** throughput limit ≈ (connections) / (avg transaction duration). Halving transaction time doubles capacity at the same connection count.

## 7.8 Common mistakes

1. Adding indexes without looking at the plan.
2. Optimizing the slowest single query instead of the highest *total* time.
3. Measuring on an empty dev DB.
4. Ignoring waits; assuming "slow query = bad SQL".
5. Fixing symptoms (bigger instance) instead of causes (unbounded `OFFSET`, N+1).
6. Long transactions from "begin; call external API; commit".
7. No timeouts anywhere.

## 7.9 Check yourself

1. A page's DB time is 8 ms but the endpoint takes 900 ms. List five places the time could be and how you'd tell them apart.
2. Why does `WHERE phone = 01712345678` (integer literal against a `varchar` column) kill the index, while `WHERE phone = '01712345678'` doesn't?
3. Why does one forgotten `BEGIN` in a REPL session eventually degrade the entire database, even if it never runs another query?

---

# 8. Transactions, isolation, MVCC and locks

## 8.1 Concept

A **transaction** groups statements into one logical unit of work: *all of it happens or none of it does*, and while it runs it behaves *as if* it were alone. The classic acronym:

| Letter | Promise | Primary mechanism |
|---|---|---|
| **A**tomicity | All-or-nothing | Abort discards new versions (PG: just mark xid aborted; InnoDB: roll back via **undo log**) |
| **C**onsistency | Constraints hold before and after | Constraints, triggers, FKs, *your application invariants* (the DB can enforce only what you declare) |
| **I**solation | Concurrent transactions don't see each other's half-done work | **MVCC** + **locks** |
| **D**urability | Committed = survives crash | **WAL / redo log** flushed (`fsync`) at commit (Chapter 9) |

**MVCC (Multi-Version Concurrency Control)** is the central idea of modern databases: *keep multiple versions of a row; give each transaction a consistent snapshot; therefore **readers never block writers and writers never block readers***. Only writers conflict with writers (on the same row).

## 8.2 Why it exists

Two customers buy the last strip of a medicine at the same instant; a wallet debit races a refund; a report scans the orders table while checkout writes to it. Without a concurrency model you get corruption (lost updates), nonsense (reports summing half-committed data), or throughput collapse (one giant lock around everything). The design goal: **maximum concurrency with correctness you can reason about.**

## 8.3 How it works internally

### 8.3.1 Anomalies — the vocabulary of things that go wrong

| Anomaly | Story |
|---|---|
| **Dirty read** | You read data another transaction has written but not committed (and may roll back). |
| **Non-repeatable read** | You read a row twice in one transaction and get different values because someone committed between. |
| **Phantom read** | You run the same *range* query twice and get different **sets** of rows (someone inserted/deleted matching rows). |
| **Lost update** | Two transactions read `stock=10`, each computes `10-1`, each writes `9`. One decrement vanishes. |
| **Write skew** | Two transactions each read an overlapping set of rows, then *write different rows* based on what they read; the combined result violates an invariant neither saw broken. Example below. |
| **Read skew** | You read row A before and row B after someone's transaction commits; the pair is inconsistent (e.g., money "disappears" mid-transfer). |

**Write skew example (telemedicine on-call rule: "at least one doctor must remain online"):**

```
 doctors: A online, B online          Rule: count(online) ≥ 1

 Tx1 (Dr A):  SELECT count(*) WHERE online → 2     OK to leave
 Tx2 (Dr B):  SELECT count(*) WHERE online → 2     OK to leave
 Tx1:  UPDATE doctors SET online=false WHERE id=A;  COMMIT
 Tx2:  UPDATE doctors SET online=false WHERE id=B;  COMMIT   ← different rows → no row conflict!
 Result: 0 doctors online. Invariant broken, each transaction was "correct" alone.
```

Snapshot isolation cannot see this conflict because the two transactions **write disjoint rows**. Only SERIALIZABLE (or explicit locking of the *read set*) catches it.

### 8.3.2 Isolation levels — what the standard says vs. what engines do

| Level | PostgreSQL | MySQL / InnoDB |
|---|---|---|
| **READ UNCOMMITTED** | Same as READ COMMITTED (no dirty reads ever) | Dirty reads possible |
| **READ COMMITTED** | **Default.** Each *statement* sees a fresh snapshot of data committed before it began. Non-repeatable reads & phantoms possible. | Per-statement snapshot; no gap locks (fewer deadlocks) |
| **REPEATABLE READ** | **Snapshot isolation:** one snapshot for the whole transaction. No dirty/non-repeatable/phantom reads. Concurrent update of a row you want to update → **serialization failure (40001)**, you retry. **Write skew still possible.** | **Default.** Consistent (snapshot) reads for plain `SELECT`; *locking reads and writes* act on the **latest** committed data, using **next-key (gap) locks** to prevent phantoms. Subtle: you can see "newer" data after you've modified a row. Lost updates possible for app-level read-modify-write. |
| **SERIALIZABLE** | **SSI** (Serializable Snapshot Isolation): optimistic; tracks read/write dependencies, **aborts** a transaction that would create a cycle (40001). No blocking added, but requires **retry logic**. | Plain `SELECT` becomes `SELECT … FOR SHARE` (locking) → more blocking and **deadlocks** |

Summary matrix (✔ = prevented, ✘ = possible):

| | Dirty | Non-repeatable | Phantom | Lost update | Write skew |
|---|---|---|---|---|---|
| PG READ COMMITTED | ✔ | ✘ | ✘ | ✘ (read-modify-write in app) | ✘ |
| PG REPEATABLE READ | ✔ | ✔ | ✔ | ✔ (errors out) | ✘ |
| PG SERIALIZABLE | ✔ | ✔ | ✔ | ✔ | ✔ |
| MySQL READ COMMITTED | ✔ | ✘ | ✘ | ✘ | ✘ |
| MySQL REPEATABLE READ | ✔ | ✔ (consistent reads) | ✔* | ✘ (app read-modify-write) | ✘ |
| MySQL SERIALIZABLE | ✔ | ✔ | ✔ | ✔ | ✔ |

\* in InnoDB RR, phantoms are prevented for snapshot reads and blocked via gap locks for locking reads; a transaction that *modifies* rows can see rows another transaction committed — a corner case.

> **Rule of thumb:** an atomic single-statement update (`UPDATE … SET qty = qty - 1 WHERE qty >= 1`) is safe at *any* level because it executes against the latest row version under a row lock. Danger lives in **read-then-write across statements.**

### 8.3.3 MVCC in PostgreSQL: versions live in the heap

Every tuple carries **`xmin`** (txid that created it) and **`xmax`** (txid that deleted/updated it; 0 if live). An `UPDATE` = *mark old version's xmax, insert a new version*. Indexes get new entries pointing to the new version (unless HOT).

```
  Heap page, row id=7 (stock):

  t=1  INSERT  by tx 100 →   v1: (id=7, stock=10)  xmin=100 xmax=0
  t=2  tx 201 BEGIN; UPDATE stock=9
                         →   v1: xmin=100 xmax=201                (old version, now "being deleted by 201")
                             v2: (id=7, stock=9)   xmin=201 xmax=0   (new version; v1.ctid → v2)
  t=3  tx 150 (older snapshot) SELECT → sees v1 (201 not committed / not visible to it)
  t=4  tx 201 COMMIT
  t=5  READ COMMITTED reader: next statement → sees v2.   REPEATABLE READ reader (snapshot taken before t=4): still sees v1.
  t=6  VACUUM: v1 is dead once NO snapshot older than 201 exists → its space becomes reusable.
```

**Visibility rule (simplified):** a tuple is visible to a snapshot if its `xmin` is committed *and* visible to the snapshot, **and** its `xmax` is unset / aborted / not-yet-visible to the snapshot. The snapshot is essentially *(xmin_horizon, xmax_boundary, list of in-progress txids)*. Commit status is looked up in the commit log (`pg_xact`), cached in tuple **hint bits** after first lookup.

Consequences you will feel:

* **Rollback is instant** in PostgreSQL (the new tuple is simply never visible).
* **UPDATE-heavy tables bloat** (dead versions) → **VACUUM** is not optional. **HOT updates** (non-indexed column changed *and* free space on the same page) avoid index churn: leave headroom with `fillfactor = 80–90` on hot-update tables.
* **A long-running transaction holds the "xmin horizon" back**: VACUUM cannot remove any version newer than the oldest active snapshot → cluster-wide bloat. Also: a forgotten replication slot or `hot_standby_feedback` replica does the same.
* **XID wraparound:** 32-bit transaction ids; `VACUUM` *freezes* old tuples. Never let autovacuum fall behind indefinitely.

### 8.3.4 MVCC in InnoDB: versions live in the **undo log**

The clustered-index row always holds the *latest* version plus hidden fields `DB_TRX_ID` (last modifier) and `DB_ROLL_PTR` (pointer into the undo log). Older versions are reconstructed on demand by following the undo chain.

```
  Clustered index leaf: row id=7 [stock=9, trx_id=201, roll_ptr ─┐]
                                                                  ▼
  Undo log:                    [stock=10, trx_id=100, roll_ptr ─► …]   (previous version delta)

  A consistent read opens a READ VIEW (list of active trx ids at that moment). For each row:
     if row.trx_id is visible to the read view → use it
     else follow roll_ptr into undo and test the older version … until a visible one is found.
```

| | PostgreSQL | InnoDB |
|---|---|---|
| Where old versions live | In the table heap (with the live ones) | Separate undo log (rollback segments) |
| Cleanup | `VACUUM` / autovacuum | **purge** threads |
| Cost of ROLLBACK | Cheap (mark aborted) | Expensive for big transactions (must apply undo) |
| Cost of long-running snapshot | Table/index bloat | Undo growth ("history list length"), reads must walk long chains → slow |
| In-place update? | No (new tuple) | Yes (clustered row updated; old image in undo) |
| Secondary index handling | New entries per new tuple unless HOT | Delete-mark + new entries; purge cleans |
| Failure signature | `n_dead_tup`, table bloat, wraparound | `History list length` growth, undo tablespace growth, slow consistent reads |

### 8.3.5 Locks — what actually blocks what

**Row-level locks (PostgreSQL).** Stored *in the tuple header* (`xmax` + infomask), so locking 1 M rows doesn't need 1 M lock-table entries. Taken by `UPDATE`/`DELETE` and explicitly by `SELECT … FOR …`:

| Mode | Blocks | Typical use |
|---|---|---|
| `FOR KEY SHARE` | only `FOR UPDATE` | taken implicitly by FK checks |
| `FOR SHARE` | updates/deletes | "don't let this row change while I read it" |
| `FOR NO KEY UPDATE` | most; not `KEY SHARE` | normal `UPDATE` that doesn't touch key columns |
| `FOR UPDATE` | everything | "I'm going to modify this row; queue behind me" |

Modifiers: `NOWAIT` (error instead of waiting), `SKIP LOCKED` (skip locked rows → **work queues**), `lock_timeout`.

**Table-level locks (PostgreSQL)** — 8 modes from `ACCESS SHARE` (plain `SELECT`) to `ACCESS EXCLUSIVE` (`ALTER TABLE`, `DROP`, `VACUUM FULL`, `TRUNCATE`, and some `CREATE INDEX`). `ACCESS EXCLUSIVE` conflicts with *everything including plain SELECT*. Locks are granted in a **queue**, which is why a waiting DDL blocks later readers (§7.5.5).

**InnoDB locks.**

| Lock | Meaning |
|---|---|
| **Record lock** | on one index record |
| **Gap lock** | on the *gap between* index records → prevents inserts into a range (stops phantoms under REPEATABLE READ) |
| **Next-key lock** | record + gap before it (default for locking range reads in RR) |
| **Insert intention lock** | signals intent to insert in a gap; conflicts with gap locks |
| **Intention locks (IS/IX)** | table-level "I intend to take row locks" markers |
| **Auto-inc lock** | for `AUTO_INCREMENT` generation (lightweight mode in 8.0 by default) |
| **Metadata lock (MDL)** | protects schema while statements/transactions use the table — the source of DDL pile-ups |

Important InnoDB consequence: **locking reads on a non-indexed or poorly-indexed predicate lock many rows/gaps** (it locks everything it scans). A missing index can turn `UPDATE … WHERE unindexed_col = x` into a *table-wide lock* under RR. Index design is also lock design.

**Latches vs. locks:** latches protect in-memory structures for microseconds (internal); locks protect logical data for the duration of a transaction (what you tune).

**Deadlocks.**

```
 Tx1: UPDATE accounts SET … WHERE id = 1;     Tx2: UPDATE accounts SET … WHERE id = 2;
 Tx1: UPDATE accounts SET … WHERE id = 2;  ⇢ waits for Tx2
 Tx2: UPDATE accounts SET … WHERE id = 1;  ⇢ waits for Tx1      ← cycle: neither can proceed
```

PostgreSQL waits `deadlock_timeout` (1 s) then runs cycle detection and aborts one transaction (`40P01`). InnoDB detects immediately (wait-for graph) and rolls back the cheaper victim (error 1213). **Prevention:** always lock rows in a consistent order (e.g., `ORDER BY id`), keep transactions short, touch fewer rows per transaction, and **retry** on deadlock — a deadlock is not a bug you can fully eliminate, it's an expected event you handle.

### 8.3.6 Concurrency-control strategies for your application code

| Strategy | How | Good when | Cost |
|---|---|---|---|
| **Atomic statement** | `UPDATE inv SET qty = qty - :n WHERE id = :id AND qty >= :n` and check rowcount | Counters, stock decrements, balances with guard | None; **best default** |
| **Pessimistic lock** | `SELECT … FOR UPDATE` then modify | Complex read-validate-write; high conflict | Holds lock; blocks others; deadlock risk |
| **Optimistic lock** | `version` column: `UPDATE … WHERE id=:id AND version=:v` → retry if 0 rows | Low conflict, long "think time" (user edits) | Retries under contention |
| **`SKIP LOCKED` queue** | Workers claim rows with `FOR UPDATE SKIP LOCKED` | Job queues, outbox pollers, order-fulfilment pickers | Needs index on status/order; ordering is approximate |
| **Unique constraint as arbiter** | `INSERT … ON CONFLICT DO NOTHING` | Idempotency keys, dedup, "one active booking per slot" | None; extremely robust |
| **SERIALIZABLE + retry** | Whole transaction retried on 40001 | Complex invariants spanning many rows (write-skew risk) | Abort rate; requires retry-safe code |
| **Advisory lock** | `pg_advisory_xact_lock(key)` | Mutual exclusion on an *application* concept (e.g., one cron per tenant) | Not tied to rows; careless use leaks; **not safe across PgBouncer transaction pooling when session-level** |
| **Exclusion constraint** | `EXCLUDE USING gist` | No-overlap bookings | None; declarative |

### 8.3.7 Distributed transactions (a short, honest paragraph)

A transaction is only atomic *within one database*. Across services (Orders DB + Payments gateway + Inventory service) you do **not** get ACID. Real systems use the **outbox pattern** (write business row + event row in one local transaction; a relay publishes the event), **idempotent consumers**, and **sagas** (compensating actions). Two-phase commit (`PREPARE TRANSACTION`) exists but is operationally fragile; avoid it unless you truly need it.

## 8.4 Architecture: where MVCC and locks sit

```
 App ── BEGIN ───────────────────────────────────────────────────────────────┐
        │                                                                     │
        ▼                                                                     ▼
  assign txid, take SNAPSHOT (what is visible)            Lock manager (row/table/advisory)
        │                                                                     │
  SELECT: scan ─► for each tuple version: is it visible to my snapshot? ──────┤  (readers take no row locks)
  UPDATE: find latest visible version ─► try to lock row ─►──── conflict? ────┘  wait / error / retry
              │ ok
              ▼
         write new version + WAL record  ──► COMMIT: flush WAL (durable) → mark txid committed (visible to later snapshots)
```

## 8.5 Realistic backend examples

### (a) Stock reservation — three implementations, ranked

```python
# Django. Table: Inventory(pharmacy_id, medicine_id, quantity)

# ❌ 1. Read-modify-write without a lock: LOST UPDATES under concurrency
inv = Inventory.objects.get(pk=pk)
if inv.quantity >= qty:
    inv.quantity -= qty
    inv.save()

# ✅ 2. Atomic conditional update (best default). One statement, row lock held only for that statement.
from django.db import transaction
from django.db.models import F

def reserve(pk, qty):
    with transaction.atomic():
        updated = (Inventory.objects
                   .filter(pk=pk, quantity__gte=qty)
                   .update(quantity=F("quantity") - qty))
        if updated == 0:
            raise OutOfStock(pk)
        # ... insert reservation row etc. in the same transaction

# ✅ 3. Pessimistic lock — when you must run logic between read and write
def reserve_locked(pk, qty):
    with transaction.atomic():
        inv = Inventory.objects.select_for_update().get(pk=pk)   # SELECT … FOR UPDATE
        if inv.quantity < qty:
            raise OutOfStock(pk)
        inv.quantity -= qty
        inv.save(update_fields=["quantity"])
```

### (b) Optimistic locking for edits (admin editing a product while another admin does)

```python
updated = (Product.objects
           .filter(pk=pk, version=client_version)
           .update(name=new_name, price=new_price, version=F("version") + 1))
if updated == 0:
    raise Conflict("Someone else modified this product; reload.")   # HTTP 409
```

### (c) Job queue with `SKIP LOCKED` (e.g., prescription-verification worker pool)

```sql
-- Each worker, in its own short transaction:
WITH next_jobs AS (
    SELECT id FROM verification_jobs
    WHERE status = 'PENDING'
    ORDER BY id
    LIMIT 10
    FOR UPDATE SKIP LOCKED
)
UPDATE verification_jobs j
SET status = 'RUNNING', started_at = now()
FROM next_jobs
WHERE j.id = next_jobs.id
RETURNING j.*;
-- needs: CREATE INDEX ON verification_jobs (id) WHERE status = 'PENDING';
```

100 workers can poll one table with no double-processing and no blocking each other.

### (d) Retrying on serialization failures and deadlocks

```python
import random, time
from django.db import transaction, OperationalError

RETRYABLE_SQLSTATES = {"40001", "40P01"}      # serialization_failure, deadlock_detected

def run_in_txn(fn, attempts=5):
    for i in range(attempts):
        try:
            with transaction.atomic():
                return fn()
        except OperationalError as e:
            code = getattr(e.__cause__, "sqlstate", None) or getattr(e.__cause__, "pgcode", None)
            if code not in RETRYABLE_SQLSTATES or i == attempts - 1:
                raise
            time.sleep(random.uniform(0, 0.05 * (2 ** i)))     # exponential backoff with full jitter
```

**The function you retry must be side-effect-free outside the DB** (no emails, no payment API calls) — or must be idempotent.

### (e) Deadlock-safe transfer

```python
def transfer(src_id, dst_id, amount):
    first, second = sorted((src_id, dst_id))                  # consistent lock order!
    with transaction.atomic():
        accts = {a.id: a for a in Account.objects.select_for_update().filter(id__in=[first, second]).order_by("id")}
        if accts[src_id].balance < amount: raise InsufficientFunds()
        accts[src_id].balance -= amount; accts[dst_id].balance += amount
        Account.objects.bulk_update(accts.values(), ["balance"])
```

## 8.6 Trade-offs, limitations and failure scenarios

| Scenario | Mechanism | Prevention |
|---|---|---|
| **Lost update** | Read-modify-write across statements at RC | Atomic update, `FOR UPDATE`, optimistic version, or RR/SERIALIZABLE + retry |
| **Write skew** | Disjoint-row writes based on overlapping reads | SERIALIZABLE, lock the *read set* (`FOR UPDATE` on the rows you read), or a constraint (`EXCLUDE`, unique) |
| **Hot-row throughput ceiling** | All transactions queue on one row (a global counter, "total_sales", a popular SKU in a flash sale) | Max rate ≈ 1 / lock-hold time (e.g., 5 ms → 200 tx/s/row). Shorten transaction, shard the counter (N rows, sum on read), queue + single writer, or admission-control in Redis |
| **Deadlock storms** | Inconsistent lock order under load | Order locks, retry with jitter, smaller transactions |
| **Idle in transaction** | App opened a transaction and went away (exception path, debugger, awaiting HTTP call) | `idle_in_transaction_session_timeout`, never do network I/O inside a transaction |
| **Long transaction** | Holds locks, holds back vacuum/purge, bloats | Batch big jobs (1–10 k rows per transaction), statement timeouts |
| **Gap-lock contention (InnoDB RR)** | Range locking blocks inserts in whole ranges | Use READ COMMITTED where phantom protection isn't needed; index your predicates |
| **SERIALIZABLE abort rate** | Dependency cycles under contention | Keep transactions small; retry; consider RR + explicit locks |
| **Autocommit surprises** | Each statement is its own transaction | Wrap multi-statement invariants in explicit transactions; Django `ATOMIC_REQUESTS` is convenient but makes *every request* hold a transaction (including external calls!) — prefer explicit `atomic()` blocks around DB work only |
| **PgBouncer transaction pooling** | Session state (advisory locks, `SET`, prepared statements, temp tables) isn't preserved between transactions | Use transaction-scoped features (`pg_advisory_xact_lock`, `SET LOCAL`) |

## 8.7 At production scale

* **Keep transactions short and DB-only.** Compute and call external services *before* `BEGIN` or *after* `COMMIT`; pass results in. Target p99 transaction time in the tens of milliseconds.
* **Flash-sale design** (10 k users, 200 units): don't let 10 k transactions contend for one inventory row. Common pattern: **Redis atomic admission** (`DECR`/Lua) hands out the 200 "tickets" in microseconds and rejects the rest instantly; winners proceed to create orders in Postgres (idempotency key unique constraint), and a reconciliation job heals Redis ↔ DB drift. The database remains the **source of truth**; Redis is the **traffic shaper**.
* **Set timeouts at every layer** (`lock_timeout`, `statement_timeout`, `idle_in_transaction_session_timeout`, HTTP and pool timeouts) so a stall becomes a fast error, not a cascade.
* **Monitor:** long transactions (`now() - xact_start`), lock waits (`log_lock_waits`), deadlock count (`pg_stat_database.deadlocks`), `n_dead_tup`/autovacuum lag, InnoDB history list length, replication lag.
* **Idempotency everywhere** for retried operations (payment webhooks, order creation) using unique idempotency keys enforced by the database.
* **Isolation choice by default:** PostgreSQL → READ COMMITTED + atomic statements + targeted `FOR UPDATE`; reach for REPEATABLE READ (for consistent multi-query reports) or SERIALIZABLE (for tricky invariants) deliberately, with retries. MySQL → consider READ COMMITTED for write-heavy OLTP to reduce gap locking, if your correctness doesn't need RR semantics.

## 8.8 Experiments

* **Lab 4** — MVCC internals (`xmin`, `xmax`, `ctid`, dead tuples, `VACUUM`).
* **Lab 5** — reproduce lost update, non-repeatable read, and **write skew**; then fix with `FOR UPDATE` / SERIALIZABLE.
* **Lab 6** — create and observe a deadlock; fix by ordering.
* **Lab 12** — Go retry loop on `40001`/`40P01`.

## 8.9 Common mistakes

1. Read-modify-write in application code without a lock/atomic update.
2. Assuming REPEATABLE READ prevents all anomalies (write skew!) — or assuming MySQL RR == PostgreSQL RR.
3. Holding a transaction open across an HTTP call / user think-time.
4. `SELECT … FOR UPDATE` without an index (locks far more than intended, especially InnoDB).
5. No retry on `40001`/`40P01`/deadlock error 1213 — treating them as bugs rather than normal events.
6. Using advisory locks with PgBouncer transaction pooling at session level.
7. Using SERIALIZABLE everywhere "to be safe" without retries.
8. `ATOMIC_REQUESTS = True` plus slow external calls in views.
9. Believing transactions span microservices.

## 8.10 Check yourself

1. Two requests concurrently run `UPDATE inventory SET qty = qty - 1 WHERE id=7 AND qty >= 1` with qty=1. Walk through, step by step, what each sees in PostgreSQL at READ COMMITTED, and which one gets rowcount 0. (Hint: the second blocks on the row lock, then **re-evaluates the WHERE against the newly committed version**.)
2. Why doesn't snapshot isolation (PG REPEATABLE READ) prevent the on-call doctors write skew, and what are three ways to prevent it?
3. Why can one idle-in-transaction session cause table bloat on tables it never touched?
4. In InnoDB RR, why can `UPDATE orders SET … WHERE status='PENDING'` without an index on `status` block unrelated inserts?
5. Why is rollback O(1) in PostgreSQL but potentially very slow in InnoDB for a huge transaction?

# 9. Database recovery: WAL, checkpoints, crash recovery, PITR

## 9.1 Concept

Servers crash: power loss, kernel panic, OOM-kill, a bad deploy of the host. When the database restarts it must come back **consistent**:

* every transaction that was acknowledged as **committed** is present, and
* no half-finished transaction leaves visible traces.

The technique used by essentially every serious database is **Write-Ahead Logging (WAL)**: *before* a change to a data page may be written to disk, a description of that change must already be safely in an **append-only log** on disk. After a crash, the database **replays the log** to rebuild whatever was lost from memory.

> One-sentence version: *the log is the truth; data files are a cache of the log's effects.*

## 9.2 Why it exists

Think about what happens at `COMMIT` without a log. You have modified 5 data pages (heap page, 3 index pages, a split page) that sit in RAM. Options:

1. **Force** all 5 pages to their home locations on disk at commit → 5 *random* writes on the critical path (slow), and a crash between writes leaves a **torn, inconsistent structure** (e.g., an index entry pointing to a tuple that never landed).
2. **Don't** flush at commit → fast, but a crash loses committed data.

WAL resolves this with the **"no-force / steal"** policy:

* **No-force:** at commit, only the *log* is flushed (one small, **sequential** write + `fsync`). Data pages are written later, lazily, in batches.
* **Steal:** the buffer manager may write a *dirty page of an uncommitted transaction* to disk to free memory. This is only safe because the log lets recovery undo (or in PostgreSQL's MVCC, simply ignore) the uncommitted changes.

Sequential appends are 10–100× cheaper than scattered page writes, and the log makes multi-page operations (B-tree splits) atomic: replay either completes the whole record or it never became durable.

## 9.3 How it works internally

### 9.3.1 The write path with WAL

```
 UPDATE stock SET qty = qty - 1 WHERE id = 7;   then COMMIT

 1. Modify heap page 4711 in the BUFFER POOL (page becomes dirty, page.LSN = L₁)
 2. Build WAL record:  "page 4711 of rel X: tuple 3 xmax := 201; insert new tuple …"   → WAL buffer (RAM)
 3. COMMIT:  append a COMMIT record, then  write() + fsync() the WAL up to that LSN   ◄── durability point
              └─ if fsync returns, the transaction is durable even if the process dies right now
 4. Reply "COMMIT OK" to the client
 5. (much later) bgwriter/checkpointer writes dirty page 4711 to the data file.
              Rule: before writing a page, WAL up to that page's LSN must already be flushed.   ◄── the "write-ahead" rule
```

* **LSN (Log Sequence Number):** a monotonically increasing byte position in the WAL (`0/16B3748`). Every data page stores the LSN of the last WAL record applied to it (`pd_lsn`). That's the key to idempotent replay.
* **WAL record granularity:** *physiological* — physical to a page, logical within it ("insert tuple at slot 3 of page 4711"). Compact, and replay is deterministic.
* **Group commit:** while one session waits for `fsync`, others append their records; one `fsync` then makes many commits durable → throughput of tens of thousands of commits/s on a device that can do only ~1–10 k `fsync`/s.

### 9.3.2 Checkpoints

If recovery had to replay the log from the beginning of time it would take forever. A **checkpoint** periodically:

1. Records a **redo pointer** (the LSN from which replay must start),
2. Flushes all dirty pages that were dirty at that moment (spread over `checkpoint_completion_target × checkpoint_timeout` to avoid an I/O spike),
3. Writes a checkpoint record and updates `pg_control`.

After a checkpoint, WAL older than the redo pointer is no longer needed *for crash recovery* (it may still be retained for replicas/archiving).

Triggered by time (`checkpoint_timeout`, default 5 min) or WAL volume (`max_wal_size`, default 1 GB). **Frequent checkpoints** = faster recovery, more I/O and more **full-page writes**; **infrequent** = less I/O but longer crash recovery and more WAL to hold. Typical production: `checkpoint_timeout = 15min`, `max_wal_size = 4–16 GB`, `checkpoint_completion_target = 0.9`.

### 9.3.3 Crash recovery (what happens on restart)

```
   time ─────────────────────────────────────────────────────────────────────────►
   WAL:  …─[ckpt N: REDO@L₁]────── records ────────────────────────────── 💥 crash (end of flushed WAL L₂)

   Restart:
     1. Read pg_control → find last checkpoint and its REDO pointer L₁.
     2. REPLAY every WAL record from L₁ to L₂ in order ("repeat history"):
           for record r touching page P:
               if P.LSN < r.LSN:  apply r to P          (page missed this change)
               else:               skip                  (page already contains it → idempotent)
     3. Done: all committed work is present. Transactions with no COMMIT record are simply
        never visible (PostgreSQL: their xid is not marked committed → MVCC hides their tuples; VACUUM reclaims them).
     4. Open for business.
```

**Recovery time ≈ time to replay WAL since the last checkpoint** (seconds to a couple of minutes for sane settings).

> **PostgreSQL vs InnoDB:** The textbook algorithm is **ARIES**: *Analysis → Redo → Undo*. PostgreSQL needs **no undo phase** — uncommitted tuple versions are invisible by MVCC rules, so there's nothing to roll back. InnoDB does: after redo it **rolls back uncommitted transactions using the undo log** (which is why recovery with a huge in-flight transaction can be slow). InnoDB's redo log is a circular buffer (`innodb_redo_log_capacity` in 8.0.30+; older: `innodb_log_file_size × files`); if it fills before dirty pages are flushed, writes stall ("log checkpoint pressure").

### 9.3.4 Torn pages and full-page writes

The OS/disk writes in 512 B–4 KB units; a PostgreSQL page is 8 KB. A crash mid-write can leave a **torn page**. WAL replay can't fix a page it can't trust as a base. Solutions:

* **PostgreSQL:** `full_page_writes = on`: after each checkpoint, the *first* modification of a page writes the **entire page image** into WAL. Replay starts from that image. (This is also why WAL volume spikes right after each checkpoint; `wal_compression = on` helps a lot.)
* **InnoDB:** **doublewrite buffer**: pages are written first to a doublewrite area, then to their home location; on recovery, a torn page is restored from the doublewrite copy.
* **Page checksums** (`data_checksums`, default in new PG 18 clusters, opt-in earlier) detect corruption on read.

### 9.3.5 Durability knobs — what exactly does "committed" mean?

| Setting | Meaning | Risk |
|---|---|---|
| PG `synchronous_commit = on` (default) | Wait for local WAL `fsync` (and sync standby *flush*, if configured) | None for acknowledged commits |
| `remote_write` / `remote_apply` | Wait for standby to receive / replay | Stronger, slower (apply → read-your-writes on that standby) |
| `local` | Local flush only, ignore sync standbys | Standby may lack the commit on failover |
| `off` | Acknowledge before flush; WAL writer flushes within ~3×`wal_writer_delay` (~600 ms) | **May lose the last fraction of a second of commits on crash; never corrupts.** Valid for logging/analytics tables, not for payments. Settable **per transaction** (`SET LOCAL synchronous_commit = off`). |
| `fsync = off` | Skip fsync | **Corruption on crash. Never in production.** |
| MySQL `innodb_flush_log_at_trx_commit = 1` | Flush redo at each commit (durable) | — |
| `= 2` | Write to OS cache each commit, fsync once/second | Lose ~1 s on **OS/power** crash (survive mysqld crash) |
| `= 0` | Write+flush once/second | Lose ~1 s even on mysqld crash |
| MySQL `sync_binlog = 1` | fsync the binary log each commit | Needed (with the above =1) so redo and binlog agree after crash |

A subtle real-world hazard: **disks and virtualization that lie about `fsync`** (volatile write cache without power-loss protection, misconfigured hypervisors). The database *did* everything right, and you still lose data. Use enterprise SSDs/cloud volumes with documented durability; test with `pg_test_fsync`.

### 9.3.6 Backups and Point-In-Time Recovery (PITR)

Crash recovery fixes *"the server died"*. It does **not** fix *"someone ran `DELETE FROM orders` without a WHERE at 14:03"* or *"the disk is gone"*. For that you need backups.

| Type | How | Restore | Notes |
|---|---|---|---|
| **Logical** (`pg_dump`, `mysqldump`) | SQL/CSV dump of data | Replays SQL; rebuilds indexes | Portable, cross-version; **slow for TB-scale**; point-in-time of dump start only |
| **Physical base backup** (`pg_basebackup`, pgBackRest, Barman, WAL-G; MySQL: XtraBackup) | Copy of data files (consistent via WAL) | Copy back + replay WAL | Fast restore; PG 17 adds **incremental** backups (`pg_basebackup --incremental` + `pg_combinebackup`) |
| **Continuous WAL archiving + base backup = PITR** | Ship every WAL segment (`archive_command`/`archive_library`) to object storage | Restore base, then replay WAL **to a chosen moment** (`recovery_target_time`, `recovery_target_lsn`, or a named restore point) | The gold standard; MySQL equivalent = full backup + **binlog** replay |

```
  base backup (Sun 02:00) ─────────── WAL segments archived continuously ───────────────────────────►
                                                                          ▲
                                         accident @ 14:03                 │ restore base → replay WAL until 14:02:59
```

Definitions you must be able to state in a design review:

* **RPO** (Recovery Point Objective): how much data you can afford to lose. WAL archiving with 60 s `archive_timeout` → RPO ≈ 1 min for *disaster* scenarios; sync replication → RPO ≈ 0 for node failure.
* **RTO** (Recovery Time Objective): how long you can be down. A 3 TB restore from object storage + WAL replay might be **hours** → this must be *measured*, not assumed.

## 9.4 Architecture diagram

```
        ┌──────────── PRIMARY ────────────┐
        │ backends ──► WAL buffers        │
        │                │  fsync at COMMIT
        │                ▼                │      ┌──► walsender ──► STANDBY(s)  (replay WAL; Chapter 10)
        │            WAL segments  ───────┼──────┤
        │  (16 MB files, pg_wal/)         │      └──► archiver ───► OBJECT STORAGE (S3/Blob): WAL archive
        │                │                │
        │  checkpointer / bgwriter        │          pg_basebackup / pgBackRest ──► OBJECT STORAGE: base backups
        │                ▼                │
        │          DATA FILES             │          PITR restore = base backup + WAL archive → any moment
        └─────────────────────────────────┘
```

## 9.5 Realistic backend examples

1. **Payment confirmation.** Webhook marks `payments.status='PAID'` and inserts a ledger row; commit returns; the server is power-cycled 2 ms later. With `synchronous_commit=on` the row is present after recovery; with `off` it might not be — and you've already told the gateway "OK". Use `on` (default) for anything money-shaped.
2. **"We dropped the wrong table."** Run PITR to a **new** instance at `T-1 min` before the mistake, export the lost table, import into production. Time to recover = restore time + replay time. Practiced teams do this in under an hour; unpracticed teams discover their `archive_command` has been failing for 3 weeks.
3. **Replica ≠ backup.** A replica faithfully replays your `DROP TABLE` within milliseconds. Use a **delayed replica** (`recovery_min_apply_delay = '1h'`) as a cheap human-error cushion, in addition to real backups.
4. **Backup you've never restored.** Treat as non-existent. Schedule monthly automated restore + validation (`pg_amcheck`, row counts, application smoke test).

## 9.6 Trade-offs, limitations and failure scenarios

| Issue | Detail | Mitigation |
|---|---|---|
| **Commit latency = fsync latency** | Each commit waits for a device flush (0.2–2+ ms on cloud disks) | Group commit; low-latency WAL volume; batch writes in one transaction; `synchronous_commit=off` only for non-critical data |
| **WAL volume** | Every index entry, full-page images, and vacuum generate WAL; heavy bulk updates can produce GBs/min | `wal_compression`, fewer indexes, batch + checkpoint tuning; monitor `pg_stat_wal` |
| **WAL accumulation → disk full** | Failed `archive_command`, stuck replication slot, or lagging replica retains WAL | Alert on `pg_wal` size and slot lag; `max_slot_wal_keep_size`; fix archiver failures immediately |
| **Checkpoint I/O spikes** | Large burst of dirty-page writes | Spread with `checkpoint_completion_target = 0.9`, larger `max_wal_size`, faster storage |
| **Long crash recovery** | Large WAL since last checkpoint (or InnoDB with a giant in-flight txn) | Reasonable checkpoint settings; avoid mega-transactions |
| **Silent corruption** | Bad RAM/disk/firmware, collation changes | Checksums, `pg_amcheck`, replicas verifying, periodic restore tests |
| **PITR to wrong timeline** | Promoted standby created a new timeline | Understand timelines (`timeline_id`); rehearse |
| **Backup untested** | Most common real-world failure | Automate restore drills |

## 9.7 At production scale

* **Choose RPO/RTO first, then architecture.** RPO ≈ 0 + RTO < 1 min → synchronous standby in another AZ + automated failover (Patroni, managed HA). RPO of minutes + RTO of hours → async standby + WAL archiving + PITR.
* Managed services (RDS/Aurora, Azure Database for PostgreSQL Flexible Server, Cloud SQL) automate WAL archiving and PITR; you still own **restore testing**, retention windows, and cross-region copies.
* **Separate failure domains:** backups in a different account/region from the primary; protect against ransomware/credential compromise (object lock/immutability).
* **Capacity:** WAL disk sized for `max_wal_size` + retention for the slowest consumer; alerts at 70% usage.
* **Document the runbook** ("restore to timestamp T into a new server") and time it quarterly.

## 9.8 Experiments

**Lab 7** — measure WAL generated by statements (and by extra indexes), `pg_waldump` a few records, `kill -9` the server mid-transaction and watch crash recovery in the log, and benchmark `synchronous_commit` on/off.

## 9.9 Common mistakes

1. Turning off `fsync`/`full_page_writes` to "fix" performance.
2. Treating replication as backup.
3. Never testing restores; never measuring restore time.
4. Ignoring failing `archive_command` alerts → disk fills with WAL → outage.
5. `synchronous_commit = off` globally "because benchmarks".
6. Assuming "the cloud disk is durable" without understanding write-cache and fsync semantics.
7. Running mega-transactions (hours long, hundreds of millions of rows) → huge WAL/undo, long rollback/recovery.

## 9.10 Check yourself

1. Why is it safe to acknowledge a commit before the data page is written to the data file?
2. A page has LSN 100. WAL records at LSN 90 and 110 both target it during replay. What happens to each, and why does this make replay idempotent?
3. Why does PostgreSQL not need an undo phase on recovery while InnoDB does?
4. You have WAL archiving but no base backup from the last 6 months. What can you restore?
5. Define RPO and RTO for: (a) a payments ledger, (b) a product-view analytics table. Would you choose different `synchronous_commit` settings?

---

# 10. Replication

## 10.1 Concept

**Replication** continuously copies changes from one database server (the **primary**/leader) to one or more others (**replicas**/followers/standbys). Almost all relational replication works by **shipping the log**: the WAL (physical) or a decoded stream of row changes (logical / binlog), and *replaying* it elsewhere.

## 10.2 Why it exists

| Goal | How replication helps | Caveat |
|---|---|---|
| **High availability** | If the primary dies, promote a replica | Possible data loss (async) and failover complexity |
| **Read scaling** | Spread read-only queries across replicas | Stale reads; **does not scale writes** |
| **Isolation of workloads** | Reports/analytics/ETL on a replica | Replica conflicts/lag |
| **Geographic proximity** | Read replicas near users | Cross-region lag |
| **Zero-downtime upgrades / migrations** | Logical replication to a new version/cluster | Operationally intricate |
| **Disaster recovery** | Cross-region standby | Lag = RPO |
| **Change data capture (CDC)** | Stream row changes to Kafka/search/warehouse | Needs replication slots; schema evolution |

## 10.3 How it works internally

### 10.3.1 Physical (streaming) replication — PostgreSQL

The standby is a **byte-for-byte copy** of the primary's data directory, kept current by continuously **replaying the primary's WAL**.

```
   PRIMARY                                              STANDBY (hot standby: read-only queries allowed)
   ───────                                              ────────
   backend ─► WAL buffers ─► WAL files                  walreceiver ─► writes WAL to disk ─► startup/recovery process
                    │                                        ▲                                   │ replays records
                    └──► walsender ──── TCP stream ──────────┘                                   ▼
                                                              data files (same page layout as primary)  ◄── read-only SELECTs
   Acks:  write_lsn (received) → flush_lsn (fsynced on standby) → replay_lsn (applied, visible to queries)
```

* **Asynchronous (default):** primary doesn't wait. Lowest latency; on primary loss you may **lose the last few transactions** you already acknowledged.
* **Synchronous:** `synchronous_standby_names = 'FIRST 1 (replica_a, replica_b)'` or quorum `'ANY 1 (a, b, c)'`. Commit waits for the standby's WAL **flush** (or write/apply depending on `synchronous_commit`). RPO ≈ 0, but **commit latency now includes a network round trip**, and if *all* eligible sync standbys are down, **commits hang** (by design — availability is traded for durability).
* **Replication slots:** the primary remembers each consumer's position and **retains WAL until the consumer has it**. Prevents "standby fell behind and WAL was recycled", but an *abandoned slot fills the primary's disk*. Cap with `max_slot_wal_keep_size`.
* **Lag** has several meanings; measure the right one:

```sql
-- on the PRIMARY
SELECT application_name, state, sync_state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- on a STANDBY
SELECT now() - pg_last_xact_replay_timestamp() AS apparent_lag;   -- misleading if the primary is idle!
SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

* **Recovery conflicts (the hot-standby gotcha).** Replay must apply VACUUM cleanups from the primary, which may remove row versions a **long query on the standby** still needs. Postgres then either **delays replay** (`max_standby_streaming_delay`, default 30 s → lag) or **cancels the query** ("canceling statement due to conflict with recovery"). `hot_standby_feedback = on` tells the primary not to vacuum those versions — fewer cancellations, but **bloat on the primary**. Classic trade-off: *long analytics on a replica vs. primary bloat vs. replica lag*.

### 10.3.2 Logical replication

Instead of page-level WAL, the primary **decodes** WAL into **row-level changes** (INSERT/UPDATE/DELETE of table X with these values) and a subscriber applies them as SQL-like operations.

```sql
-- publisher (wal_level = logical)
CREATE PUBLICATION pub_orders FOR TABLE orders, order_items;
-- subscriber (can be a different major version, different indexes, extra tables)
CREATE SUBSCRIPTION sub_orders CONNECTION 'host=primary dbname=app user=repl' PUBLICATION pub_orders;
```

* Selective (tables, even row/column filters in PG 15+), **cross-version** (major upgrades with minimal downtime), writable subscriber (but you own conflicts), and the basis of **CDC** (Debezium reads the logical slot into Kafka).
* Limits: **DDL isn't replicated** (you apply schema changes on both sides, subscriber first for additive changes), tables need a **replica identity** (usually the PK), sequences and large objects need separate handling (check your version's release notes), and apply is more CPU-expensive than physical replay. Large transactions are applied when they commit (or streamed in newer versions).

### 10.3.3 MySQL replication

* Primary writes row changes to the **binary log** (`binlog_format = ROW`, recommended). Replica's **I/O thread** copies binlog events into a **relay log**; **applier (SQL) thread(s)** replay them. With **GTIDs** (global transaction ids), failover/re-pointing is much simpler.
* **Single-threaded apply** historically caused lag; use **multi-threaded replicas** (`replica_parallel_workers`, `replica_parallel_type = LOGICAL_CLOCK`).
* **Semi-sync:** commit waits for at least one replica to *receive* the event (not apply). **Group Replication / InnoDB Cluster:** Paxos-based, consistent multi-node group for HA.
* Because binlog is logical (statement/row-level), **replica indexes and even engines can differ** from the primary — handy, and a source of drift if misused.

### 10.3.4 Consistency from the application's point of view

Replicas are **eventually consistent** with the primary. Real user-visible bugs:

| Anomaly | Story | Fix |
|---|---|---|
| **Read-your-writes violation** | User places an order (→ primary), the next page reads "My orders" from a replica 80 ms behind: *order missing*, user orders again | Read from the primary for N seconds after a write (sticky session/cookie), or for that user's own data; or **wait for LSN** (`pg_wal_replay_lsn() ≥ commit_lsn`) before reading from the replica; or `remote_apply` sync standby |
| **Monotonic read violation** | Two successive requests hit two replicas with different lag; the second shows *older* data than the first | Pin a session to one replica |
| **Stale decisions** | Admin dashboard uses a replica to check stock, then writes to the primary | **Never make write decisions from replica data.** Reads that feed writes go to the primary. |
| **Cross-table inconsistency** | Replica is consistent *as a snapshot of the primary* (physical), so referential consistency holds — but **cache + replica + search index** can disagree | Version fields, event ordering, tolerate eventual consistency in non-critical UI |

### 10.3.5 Failover

```
   Failure detected (health checks, consensus store: etcd/Consul)
        │
        ▼ FENCING: ensure the old primary can no longer accept writes (STONITH, revoke VIP, shut down)  ◄── prevents split-brain
        ▼ choose the most up-to-date replica (highest received/replayed LSN)
        ▼ PROMOTE it (pg_promote → new timeline)
        ▼ re-point other replicas (pg_rewind / re-clone the old primary), update DNS/VIP/proxy
        ▼ applications reconnect (pooler/driver retry), idempotent retries finish in-flight work
```

**Split-brain** (two primaries accepting writes) is the nightmare: divergent data that cannot be automatically merged. Prevention is architecture: consensus-based leader election (Patroni + etcd), fencing, and a quorum/majority rule. **Async failover can lose acknowledged commits** (those not yet streamed) — your RPO is the lag at the moment of failure.

Tools: **Patroni**, repmgr, pg_auto_failover; managed HA (RDS Multi-AZ, Azure Flexible Server zone-redundant HA); MySQL: InnoDB Cluster/Orchestrator.

## 10.4 Architecture: a typical production topology

```
                         ┌─────────────── application pods (Django / FastAPI) ───────────────┐
                         │  writes + read-your-writes + reads that feed decisions            │ eventually-consistent reads
                         ▼                                                                   ▼
                   ┌────────────┐                                                   ┌────────────┐
                   │ PgBouncer  │ (transaction pooling)                             │ PgBouncer  │ (read pool, round-robin)
                   └─────┬──────┘                                                   └──────┬─────┘
                         ▼                                                                 ▼
   AZ-a        ┌──────────────────┐   sync (ANY 1)    AZ-b ┌──────────────────┐   async  ┌───────────────┐ ┌───────────────┐
               │     PRIMARY      │──────────────────────► │ STANDBY (sync)   │ ───────► │ READ REPLICA 1│ │ READ REPLICA 2│
               └───────┬──────────┘                        └──────────────────┘  cascade └───────────────┘ └───────────────┘
                       │ WAL archive + base backups                │
                       ▼                                           └── promoted on failover (Patroni + etcd quorum)
                 OBJECT STORAGE (PITR)        + delayed replica (1 h) for human-error protection
                       │ logical slot (CDC)
                       ▼
                 Debezium ─► Kafka ─► search index / warehouse / cache invalidation
```

## 10.5 Realistic backend examples

### Django read/write router with read-your-writes stickiness

```python
# settings.py
DATABASES = {
    "default": {...},            # primary (via PgBouncer)
    "replica": {...},            # read pool
}
DATABASE_ROUTERS = ["app.db_router.PrimaryReplicaRouter"]

# app/db_router.py
import contextvars
_use_primary = contextvars.ContextVar("use_primary", default=False)

def force_primary(flag: bool = True):
    _use_primary.set(flag)

class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        return "default" if _use_primary.get() else "replica"
    def db_for_write(self, model, **hints):
        return "default"
    def allow_relation(self, obj1, obj2, **hints):
        return True
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"

# middleware.py — after any write request, pin the user to the primary for 5 s
import time
class ReadYourWritesMiddleware:
    TTL = 5
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        pinned_until = float(request.COOKIES.get("pin_primary_until", 0))
        force_primary(time.time() < pinned_until)
        response = self.get_response(request)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            response.set_cookie("pin_primary_until", str(time.time() + self.TTL), max_age=self.TTL, httponly=True)
        return response
```

(5 s must exceed your p99 replication lag — measure it. A more precise design records the commit LSN and waits for the replica to reach it.)

### Routing by *criticality*, not just by verb

| Query | Where | Why |
|---|---|---|
| Checkout: stock check + order creation | Primary | Decides a write |
| "My orders" immediately after placing | Primary (pinned) | Read-your-writes |
| Product catalog browse, search results | Replica / cache | Staleness of seconds is fine |
| Admin analytics, exports | Dedicated analytics replica | Long queries; set `hot_standby_feedback` consciously |
| Order-status polling by mobile app | Replica | Slightly stale OK; add `updated_at` so client can ignore older states |

## 10.6 Trade-offs, limitations and failure scenarios

| Scenario | What happens | Mitigation |
|---|---|---|
| **Lag spike from a huge transaction** | A 10 M-row `UPDATE` generates GBs of WAL; replica replay is single-threaded and falls minutes behind | Batch big jobs; replica with fast disks/CPU; alert on lag |
| **Replica query canceled / lag from recovery conflict** | Long reporting query vs vacuum cleanup | Dedicated analytics replica with larger `max_standby_streaming_delay`; understand `hot_standby_feedback` bloat |
| **Stuck/abandoned replication slot** | Primary retains WAL forever → disk full → **primary outage** | Alert on slot lag; `max_slot_wal_keep_size`; drop unused slots |
| **Split-brain** | Two nodes accept writes | Consensus + fencing; never script naive "promote if ping fails" |
| **Async failover data loss** | Acknowledged commits not on the promoted replica | Sync/quorum replication for critical data; reconcile with idempotent retries |
| **Sync standby down → commits hang** | Availability sacrificed for durability | `ANY n` quorum with ≥ n+1 candidates; automation to demote sync state with alerts |
| **Replica read stale data** | Read-your-writes bug | Stickiness / LSN wait |
| **Schema change vs replicas** | Long-running `ALTER` on primary blocks replay on standby (ACCESS EXCLUSIVE lock replicated) | Online DDL patterns; short lock timeouts |
| **"We have 5 replicas so writes scale"** | They don't — every write still goes through the primary and every replica replays all of it | Partitioning / sharding (functional split, tenant sharding) |
| **Failback** | Old primary has diverged WAL | `pg_rewind` or re-clone |

## 10.7 At production scale

* **Quantify staleness tolerance per feature** and write it into the design doc (checkout: 0; catalog: 5 s; analytics: 15 min). Route accordingly.
* **Monitor**: replication lag in bytes *and* seconds, slot retained WAL, replica query cancellations (`pg_stat_database_conflicts`), connection counts per pool, failover drills.
* **Failover rehearsals** (game days). A failover design that has never failed over is a hypothesis.
* **Replica count** = read throughput needs + redundancy; beyond ~5–10, cascade replicas to reduce primary walsender load.
* **Write scaling path (in order):** fix queries/indexes → batch writes → connection pooling → partitioning → move cold data → vertical scale → functional split (separate services/databases) → **sharding** (by tenant/user/pharmacy; Citus or application-level). Each step is far more costly than the previous; don't skip ahead.

## 10.8 Experiments

**Lab 8** — build a primary + streaming replica with Docker, pause replay to create lag, watch `pg_stat_replication`, see what a synchronous standby outage does to commits, and promote the replica.

## 10.9 Common mistakes

1. Using a replica for reads that feed decisions/writes.
2. Not handling read-your-writes (the "ghost order" bug).
3. Ignoring replication slots until the disk fills.
4. Treating replicas as backups.
5. Auto-failover without fencing/quorum.
6. Assuming replicas scale writes.
7. Letting analytics queries run on a replica with `hot_standby_feedback = on` and then wondering why the primary bloats.
8. Forgetting to test the application's behaviour during failover (connection retry, idempotency).

## 10.10 Check yourself

1. Why can't you "just add replicas" to fix a write bottleneck?
2. Your sync standby dies and all writes stall. What setting/design choice caused that, and what are two alternatives?
3. A user creates an address, then the next screen shows "no addresses". Give two distinct fixes and the trade-off of each.
4. Why does a long `SELECT` on a replica sometimes get cancelled with "conflict with recovery"? What does `hot_standby_feedback` change, and at what cost?
5. Compare physical and logical replication for a zero-downtime major-version upgrade.

---

# 11. Putting it together: a large-scale production system

This chapter integrates everything. The scenario is deliberately close to a real medicine-delivery marketplace; the **decision-making** is what matters, not the specific numbers.

## 11.1 The scenario

An online pharmacy marketplace (B2C app + web, plus a B2B wholesale portal for pharmacies):

| Dimension | Today | Target in 18 months |
|---|---|---|
| Orders/day | 40 k | 400 k |
| Peak order writes | ~15/s | ~150/s (evening spike + promo campaigns, up to 1,500 checkout attempts/s in flash campaigns) |
| Catalog | 60 k SKUs, 2 k pharmacies, per-pharmacy inventory/price rows (~20 M `inventory` rows) | 150 k SKUs, 10 k pharmacies (~100 M rows) |
| Read traffic | ~2 k QPS (browse/search/status) | ~25 k QPS |
| Data | 300 GB | ~3 TB (orders, items, events, audit) |
| Requirements | p99 checkout < 600 ms; no oversell; no lost paid orders; RPO ≈ 0 for orders; RTO < 5 min; regulatory audit trail | same |

## 11.2 Architecture

```
  Mobile / Web ──► CDN/WAF ──► API gateway ──► Stateless API pods (Django/FastAPI on Kubernetes)
                                                    │            │             │
                                  ┌─────────────────┘            │             └──────────────┐
                                  ▼                              ▼                            ▼
                           ┌────────────┐                ┌────────────┐               ┌──────────────┐
                           │   Redis    │                │ PgBouncer  │               │ Search index │ (OpenSearch/ES or PG FTS)
                           │ cache      │                └─────┬──────┘               │ catalog,     │
                           │ rate-limit │                      ▼                      │ autocomplete │
                           │ stock      │          ┌──────────────────────┐           └──────▲───────┘
                           │ admission  │          │ PostgreSQL PRIMARY   │──sync──► STANDBY (AZ-b)       │
                           └────────────┘          │ orders, payments,    │──async─► READ REPLICAS (2–3)  │
                                  ▲                │ inventory, ledger    │                               │
                                  │                └─────────┬────────────┘                               │
                                  │ invalidate               │ outbox rows (same transaction as the order)│
                                  │                          ▼                                            │
                              ┌───┴────────────────────  Outbox relay / CDC (Debezium) ──► Kafka/RabbitMQ ┘
                                                                           │
                       consumers: payment capture, notifications, fulfilment/packing, analytics (warehouse), search indexer
                       backups: base backups + WAL archive → object storage (cross-region copy, immutable), delayed replica
```

## 11.3 Data-store decisions (who owns what, and why)

| Data | Store | Why / consistency level |
|---|---|---|
| Orders, order items, payments, ledger, inventory | **PostgreSQL primary** | ACID, constraints, source of truth; strong consistency |
| Product catalog (read-mostly, hot) | PG + **Redis cache** + search index | Staleness of seconds is fine; protect the DB with cache-aside + TTL jitter |
| Search/autocomplete | OpenSearch/ES (or `pg_trgm` while small) | Relevance ranking, typo tolerance; fed by CDC/outbox |
| Stock *admission control* during campaigns | **Redis** atomic ops (Lua) | Microsecond decisions, shields the DB from 10 k contenders; **DB remains truth** |
| Sessions, rate limits, idempotency fast-path | Redis | Ephemeral |
| Events/analytics | Kafka → warehouse (ClickHouse/BigQuery/Redshift) | Heavy scans don't belong on OLTP |
| Files (prescriptions, invoices) | Object storage | Keep blobs out of rows |

## 11.4 Schema & index design for the hot tables

```sql
CREATE TABLE orders (
    id              bigint GENERATED ALWAYS AS IDENTITY,
    public_id       uuid        NOT NULL DEFAULT gen_random_uuid(),    -- exposed to clients; not the PK
    user_id         bigint      NOT NULL,
    pharmacy_id     int         NOT NULL,
    status          text        NOT NULL CHECK (status IN ('PENDING','PAID','PACKING','SHIPPED','DELIVERED','CANCELLED')),
    total_minor     bigint      NOT NULL,                              -- integer money: never floats
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)                                       -- partition key must be in the PK
) PARTITION BY RANGE (created_at);                                     -- monthly partitions

-- Retry safety lives in a small, separate, NON-partitioned table (see the bullet below):
CREATE TABLE idempotency_keys (
    user_id    bigint      NOT NULL,
    key        text        NOT NULL,
    order_id   bigint,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, key)                                         -- the arbiter of "is this a retry?"
);
CREATE INDEX idx_orders_user_recent  ON orders (user_id, created_at DESC, id DESC);     -- "my orders", keyset pagination
CREATE INDEX idx_orders_active       ON orders (pharmacy_id, created_at) WHERE status IN ('PAID','PACKING');  -- pharmacy work queue
CREATE INDEX idx_orders_pub          ON orders (public_id);                              -- lookup by external id
```

* **Why partition** by month: queries nearly always carry a time bound; old partitions' indexes go cold; retention = detach/drop partition (instant, no bloat, no vacuum storm); `VACUUM`/`ANALYZE` work per partition.
* **Idempotency keys get their own table.** A unique index on a partitioned table *must include the partition key*, so `UNIQUE (user_id, idempotency_key)` on `orders` is impossible — and `UNIQUE (user_id, idempotency_key, created_at)` would be useless, because a retry gets a *new* `created_at` and never conflicts. A small non-partitioned `idempotency_keys(user_id, key, order_id)` table with `PRIMARY KEY (user_id, key)` (plus TTL cleanup) is the arbiter that makes retries safe.
* **Inventory**: `(pharmacy_id, medicine_id)` PK; hot rows → atomic conditional `UPDATE … WHERE quantity >= :n`. For campaign SKUs split into **N stock buckets** (`inventory_bucket(sku, bucket, qty)`), pick `bucket = hash(order) % N`, spill to the next bucket when empty — turns one hot row into N parallel ones.
* **Fillfactor 80–90** on frequently updated tables (status transitions) to keep HOT updates; indexes on **status** are partial and narrow so HOT remains likely for non-status updates.
* **`status` transitions**: enforce legal transitions in SQL (`UPDATE … WHERE status = 'PAID'` returns rowcount) rather than read-then-write.

## 11.5 The checkout transaction (put the earlier chapters to work)

```
 1. [Redis] admission: Lua script decrements stock:{pharmacy}:{sku}; if insufficient → instant "sold out" (no DB touched)
 2. [App]   validate prices etc. from cache (no DB)                                  ← outside any transaction
 3. [PG]    BEGIN  (READ COMMITTED; lock_timeout = 500ms; statement_timeout = 2s)
            INSERT INTO idempotency_keys (user_id, key) VALUES (:u, :k) ON CONFLICT DO NOTHING
              └─ 0 rows inserted → this is a retry; fetch & return the existing order (idempotent)
            INSERT INTO orders (…) … RETURNING id;   UPDATE idempotency_keys SET order_id = :id WHERE user_id = :u AND key = :k
            UPDATE inventory SET quantity = quantity - :n WHERE pharmacy_id=:p AND medicine_id=:m AND quantity >= :n   (rowcount check)
            INSERT INTO order_items …
            INSERT INTO outbox(event_type, payload) VALUES ('order.created', …)       ← same transaction → atomic with the order
            COMMIT          (synchronous_commit = on; sync standby in AZ-b → RPO ≈ 0)
 4. [Relay] outbox relay publishes to the broker; consumers charge payment, notify, trigger packing (idempotent consumers)
 5. [Redis] on failure of step 3: compensate (INCRBY) or let the reconciler heal drift from the DB truth
 Retries: on 40001/40P01/lock_timeout → retry with jitter (≤3 attempts); client retries re-send the same idempotency_key
```

Why each piece exists: **Redis** absorbs the contention that would otherwise be 1,500 transactions queueing on a row lock (Chapter 8 hot-row math: 3 ms hold → 333 tx/s/row max); **idempotency key** makes at-least-once client/network retries safe; **outbox** gives atomicity between "order exists" and "downstream will hear about it" without distributed transactions; **conditional UPDATE** gives oversell protection with no explicit lock; **timeouts** convert stalls into fast failures.

## 11.6 Capacity arithmetic (do this on paper before you buy hardware)

* **Storage growth:** 400 k orders/day × (order ≈ 250 B + 4 items × 120 B + outbox/events ≈ 300 B ≈ 1 KB heap) ≈ 400 MB/day heap; indexes ≈ 1–1.5× → ~1 GB/day ≈ **0.35 TB/year** for orders. With audit/event tables, 1–3 TB in 18 months. **Plan for 2–3× headroom** (bloat, backups, temp, WAL).
* **Write IOPS:** 150 orders/s × (1 order + ~4 items + ~6 index entries each + outbox) ≈ 150 × ~40 page touches ≈ 6 k page modifications/s, mostly absorbed by the buffer pool and WAL; actual disk write rate is governed by checkpoints. WAL ≈ maybe 5–20 MB/s average, with post-checkpoint full-page-write bursts → size WAL volume and `max_wal_size` accordingly.
* **Connections:** 40 API pods × pool 10 = 400 app-side connections. PgBouncer transaction mode maps them to ~60–100 server connections (≈ 4× vCPU of a 16–32 vCPU primary). Beyond this you add pgbouncer capacity, not Postgres connections.
* **Memory:** hot working set = last ~30–60 days of orders (~30–60 GB heap+indexes) + active catalog/inventory (~20–40 GB) → **128–256 GB RAM** primary keeps hit ratio > 99.5%; replicas same.
* **Replica sizing:** 25 k read QPS, with Redis/CDN absorbing 70–80% of catalog reads → ~5 k QPS to replicas; 3 replicas ≈ 1.7 k QPS each — comfortable.
* **Restore time (RTO):** 3 TB from object storage at ~500 MB/s ≈ 100 min + WAL replay. If RTO is 5 min, **restore isn't the plan — failover is** (sync standby); restore is the plan for *logical* disasters (bad deploy, dropped table, ransomware).

## 11.7 Failure modes and runbook sketch

| Failure | Detection | Automatic response | Manual follow-up |
|---|---|---|---|
| Primary host dies | Patroni health, `pg_isready`, error rate | Fence, promote sync standby (RPO 0), pooler re-points | Rebuild old node as replica; verify no divergence |
| Replica lag > 10 s | Alert on `replay_lag` | App router sheds replica reads to primary or cache; | Find culprit (big txn / analytics query / IO) |
| Redis down | Health + error rate | Fail-open to DB-only with **stricter rate limiting** (accept degraded throughput, never oversell) | Rebuild stock counters from DB; reconcile |
| Hot-row pile-up | Lock-wait metrics, `pg_stat_activity` | `lock_timeout` → fast failures; shed load | Add buckets/queue |
| Bad migration lock-queue | Connection pile-up | `lock_timeout` aborts the DDL | Re-run in a quiet window; online pattern |
| Disk 80% | Alert | — | Retention drop partitions; extend; find WAL/slot retention |
| Accidental data deletion | User report/audit | — | PITR to side instance → extract → restore rows |
| Autovacuum starved (bloat, wraparound) | `n_dead_tup`, `age(datfrozenxid)` | — | Tune; kill blockers (long txn/stale slot); `pg_repack` |

## 11.8 The scaling ladder (resist the urge to jump rungs)

1. **Measure** (`pg_stat_statements`, `auto_explain`, wait events).
2. **Fix queries and indexes**; remove N+1; remove unused indexes.
3. **Pool connections** (PgBouncer); right-size pools; timeouts.
4. **Cache** hot reads (Redis/CDN) with correct invalidation/TTL.
5. **Read replicas** for tolerant reads; handle read-your-writes.
6. **Partition** big tables by time; archive/drop cold data.
7. **Vertical scale** (RAM first — it's usually the highest-ROI knob; then IOPS, then CPU).
8. **Functional split** (separate DBs/services: catalog, orders, analytics).
9. **Shard** (by tenant/pharmacy/user) only when a single primary's *write* capacity is genuinely exhausted.

Each rung up multiplies operational complexity. The best production database is the one that is boring.

## 11.9 Check yourself

1. Why is the checkout flow built as *Redis admission → one short PG transaction → outbox*, rather than one big transaction that also calls the payment gateway?
2. Why does the `orders` primary key include `created_at`? What does that cost you?
3. Pick RPO/RTO for (a) orders, (b) catalog, (c) analytics. How do the backup/replication choices differ?
4. Estimate the buffer-pool RAM you need for the *working set*. What changes if the business starts running long date-range reports on the primary?

# 12. Hands-on labs (PostgreSQL, Python, Redis, Go)

**Rules of the labs:** run every command, *predict the result before you run it*, write the prediction down, then compare. Wrong predictions are where learning happens.

**Prerequisites:** Docker; `psql`; Python 3.11+ with `pip install "psycopg[binary]" redis`; Go 1.22+ (Lab 12). Use the schema and data from [§0.4](#04-the-sample-schema-used-throughout-this-document) unless a lab says otherwise. Run `VACUUM ANALYZE orders;` once after loading.

| Lab | Topic | Chapter |
|---|---|---|
| 1 | B+Tree height, page inspection, sequential vs random inserts | 1, 2 |
| 2 | Selectivity, correlation and the index → bitmap → seq scan flip | 4, 5 |
| 3 | Composite index column order | 4 |
| 4 | MVCC internals: `xmin`, `xmax`, `ctid`, vacuum, long transactions | 8 |
| 5 | Isolation anomalies: lost update, non-repeatable read, write skew | 8 |
| 6 | Deadlocks and the DDL lock queue | 8, 7 |
| 7 | WAL volume, `pg_waldump`, crash recovery, commit durability benchmark | 9 |
| 8 | Streaming replication, lag, sync standby outage, promotion | 10 |
| 9 | Python: N+1 and OFFSET vs keyset pagination | 7 |
| 10 | Build and test a B+Tree in Python | 2 |
| 11 | Redis: sorted-set index, atomic stock admission, cache stampede, persistence | 3, 11 |
| 12 | Go: transaction retry on serialization failure / deadlock | 8 |
| 13 | Capstone: prove (and break) "no oversell" under concurrency with `pgbench` | 8 |

---

## Lab 1 — B+Tree height, page inspection, sequential vs random inserts

```sql
CREATE INDEX idx_orders_user ON orders (user_id);

CREATE EXTENSION IF NOT EXISTS pageinspect;
CREATE EXTENSION IF NOT EXISTS pgstattuple;

SELECT pg_size_pretty(pg_relation_size('orders'))         AS heap,
       pg_size_pretty(pg_relation_size('idx_orders_user')) AS index;

-- 'level' = height of the root above the leaves (0 means the root IS a leaf). 5 M entries → expect level 2 (3 levels).
SELECT root, level FROM bt_metap('idx_orders_user');

-- The root page: how many children (fan-out)?
SELECT type, live_items, avg_item_size, free_size
FROM bt_page_stats('idx_orders_user', (SELECT root FROM bt_metap('idx_orders_user')));

-- A leaf page's contents (key bytes in hex + the heap ctid each entry points to)
SELECT itemoffset, ctid, left(data, 24) AS key_hex FROM bt_page_items('idx_orders_user', 1) LIMIT 10;
```

**Questions:** What is the root's `live_items`? Using it, compute the theoretical capacity of a 3-level tree. Does the answer match §2.3.2?

**Sequential vs random insertion (same keys, different order):**

```sql
CREATE TABLE t_seq  (id bigint PRIMARY KEY, pad text);
CREATE TABLE t_rand (id bigint PRIMARY KEY, pad text);
\timing on
INSERT INTO t_seq  SELECT g, 'x' FROM generate_series(1, 2000000) g;
INSERT INTO t_rand SELECT g, 'x' FROM generate_series(1, 2000000) g ORDER BY random();

SELECT 't_seq' AS tbl, avg_leaf_density, leaf_fragmentation, leaf_pages, pg_size_pretty(index_size) AS size
FROM pgstatindex('t_seq_pkey')
UNION ALL
SELECT 't_rand', avg_leaf_density, leaf_fragmentation, leaf_pages, pg_size_pretty(index_size)
FROM pgstatindex('t_rand_pkey');
```

**Expected:** sequential ≈ 90% leaf density (right-edge splits are 90/10); random notably lower (~70%) → a physically larger index for *identical* keys, and the insert was slower. This is the **UUIDv4 vs sequential PK** effect, measured.

---

## Lab 2 — Selectivity, correlation and the plan flip

```sql
CREATE INDEX idx_orders_status  ON orders (status);
CREATE INDEX idx_orders_created ON orders (created_at);
VACUUM ANALYZE orders;

-- What does the planner know?
SELECT attname, n_distinct, most_common_vals, most_common_freqs, correlation
FROM pg_stats WHERE tablename = 'orders' AND attname IN ('status', 'created_at');

-- sum(total) forces heap access (so index-only scans don't muddy the experiment)
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE status = 'PENDING';     -- predict the plan
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE status = 'SHIPPED';
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE status = 'DELIVERED';   -- predict the plan
```

**Sweep the predicate width** and write down the plan type and `Buffers` each time:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE created_at >= now() - interval '1 hour';
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE created_at >= now() - interval '1 day';
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE created_at >= now() - interval '7 days';
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE created_at >= now() - interval '30 days';
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total) FROM orders WHERE created_at >= now() - interval '180 days';
```

You should see **Index Scan → Bitmap Heap Scan → Seq Scan** as the window widens. Our `created_at` values were generated randomly, so `correlation ≈ 0`: matching rows are scattered over all heap pages, which is why the index stops paying off early.

**Now change the physical layout** (takes a lock and rewrites the table — fine in a lab):

```sql
CLUSTER orders USING idx_orders_created;
ANALYZE orders;
SELECT correlation FROM pg_stats WHERE tablename='orders' AND attname='created_at';   -- ≈ 1.0
-- rerun the sweep: index/bitmap plans now stay attractive for much wider windows
```

**Then change the cost model:**

```sql
SET random_page_cost = 1.1;        -- SSD-realistic
-- rerun the sweep and note where the flip point moved
RESET random_page_cost;
```

**Takeaway to write in your notes:** plan choice depends on (a) selectivity, (b) physical correlation, (c) cost constants — not on "whether an index exists".

---

## Lab 3 — Composite index column order

```sql
DROP INDEX IF EXISTS idx_orders_user, idx_orders_status;   -- keep it clean
CREATE INDEX i_a ON orders (user_id, status, created_at DESC);
CREATE INDEX i_b ON orders (status, user_id, created_at DESC);
CREATE INDEX i_c ON orders (created_at DESC, user_id, status);
CREATE INDEX i_d ON orders (user_id, created_at DESC);
ANALYZE orders;
```

**Isolate one index at a time using transactional DDL** (PostgreSQL DDL is transactional — roll it back and nothing happened):

```sql
BEGIN;
DROP INDEX i_b, i_c, i_d;        -- only i_a remains
EXPLAIN (ANALYZE, BUFFERS) <query>;
ROLLBACK;
```

Run these four queries against each single-index configuration (a, b, c, d) and fill the table with the plan node, `Buffers`, and whether a `Sort` node appeared:

| Query | i_a `(user,status,created)` | i_b `(status,user,created)` | i_c `(created,user,status)` | i_d `(user,created)` |
|---|---|---|---|---|
| **Q1** `WHERE user_id=42 AND status='DELIVERED' ORDER BY created_at DESC LIMIT 20` | | | | |
| **Q2** `WHERE user_id=42 ORDER BY created_at DESC LIMIT 20` | | | | |
| **Q3** `WHERE user_id=42 AND created_at > now()-interval '90 days' AND status='DELIVERED'` | | | | |
| **Q4** `WHERE status='PENDING' ORDER BY created_at DESC LIMIT 50` | | | | |

**Predictions to check:** i_a is perfect for Q1/Q3 and *cannot order* Q2 (status sits between); i_d is perfect for Q2 and decent for Q1 (filters `status` inline); i_b serves Q1 *and* Q4 but not Q2; i_c is poor for per-user queries. Then answer: *which minimal set of indexes would you ship for this query mix, and why?* Finally, try `CREATE INDEX i_e ON orders (created_at DESC) WHERE status = 'PENDING';` and re-measure Q4.

---

## Lab 4 — MVCC internals

```sql
CREATE TABLE stock (id int PRIMARY KEY, qty int);
INSERT INTO stock VALUES (7, 10);

SELECT ctid, xmin, xmax, * FROM stock;
UPDATE stock SET qty = 9 WHERE id = 7;
SELECT ctid, xmin, xmax, * FROM stock;        -- ctid moved: (0,2). xmin changed. An UPDATE = new tuple version.

-- Both versions physically exist (the old one is dead but not yet vacuumed):
SELECT lp, t_xmin, t_xmax, t_ctid FROM heap_page_items(get_raw_page('stock', 0));
SELECT n_live_tup, n_dead_tup, n_tup_upd, n_tup_hot_upd FROM pg_stat_user_tables WHERE relname='stock';

VACUUM (VERBOSE) stock;
SELECT lp, lp_flags, t_xmin, t_xmax FROM heap_page_items(get_raw_page('stock', 0));   -- old slot now reusable
```

**Snapshot isolation by hand — two psql sessions (A and B):**

```
 A: BEGIN ISOLATION LEVEL REPEATABLE READ;
 A: SELECT qty FROM stock WHERE id = 7;                 -- 9
 B: UPDATE stock SET qty = 8 WHERE id = 7;              -- autocommit
 A: SELECT qty FROM stock WHERE id = 7;                 -- still 9 (snapshot)
 A: UPDATE stock SET qty = qty - 1 WHERE id = 7;        -- ERROR: could not serialize access due to concurrent update
 A: ROLLBACK;
```

Repeat with `READ COMMITTED`: A's second `SELECT` sees 8, and the `UPDATE` succeeds (it re-reads the latest version).

**A long transaction blocks cleanup:**

```
 A: BEGIN ISOLATION LEVEL REPEATABLE READ; SELECT count(*) FROM stock;     -- takes a snapshot, then idles
 B (shell): for i in $(seq 1 20000); do echo "UPDATE stock SET qty = qty + 1 WHERE id = 7;"; done | psql -q postgresql://postgres:pw@localhost:5432/postgres
            # 20,000 separate autocommit updates = 20,000 dead versions that A's snapshot prevents from being removed
 B: VACUUM (VERBOSE) stock;     -- look for: "dead row versions cannot be removed yet, oldest xmin: …"
 A: COMMIT;
 B: VACUUM (VERBOSE) stock;     -- now they are removed
```

**Takeaway:** an idle open transaction pins the *xmin horizon* for the whole cluster. Find culprits with `SELECT pid, state, now()-xact_start AS age, backend_xmin FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER BY age DESC;`.

---

## Lab 5 — Isolation anomalies

**5a. Lost update (READ COMMITTED, read-modify-write in the app):**

```
 setup: UPDATE stock SET qty = 10 WHERE id = 7;
 A: BEGIN;  SELECT qty FROM stock WHERE id = 7;           -- 10
 B: BEGIN;  SELECT qty FROM stock WHERE id = 7;           -- 10
 A: UPDATE stock SET qty = 9 WHERE id = 7;  COMMIT;       -- (computed in the "app": 10 - 1)
 B: UPDATE stock SET qty = 9 WHERE id = 7;  COMMIT;       -- (10 - 1 again!)   → qty is 9, should be 8
```

Fix it three ways and verify each: (i) `UPDATE stock SET qty = qty - 1 …` (atomic); (ii) `SELECT … FOR UPDATE` in both sessions (second SELECT waits, then sees 9); (iii) run both at `REPEATABLE READ` and observe the 40001 error you must retry.

**5b. Non-repeatable read:** in session A at READ COMMITTED run the same `SELECT` twice around B's committed `UPDATE`; repeat at REPEATABLE READ.

**5c. Write skew (the on-call doctors):**

```sql
CREATE TABLE doctors (id int PRIMARY KEY, name text, online bool NOT NULL);
INSERT INTO doctors VALUES (1,'A',true), (2,'B',true);
```

```
 A: BEGIN ISOLATION LEVEL REPEATABLE READ;  SELECT count(*) FROM doctors WHERE online;      -- 2
 B: BEGIN ISOLATION LEVEL REPEATABLE READ;  SELECT count(*) FROM doctors WHERE online;      -- 2
 A: UPDATE doctors SET online = false WHERE id = 1;  COMMIT;
 B: UPDATE doctors SET online = false WHERE id = 2;  COMMIT;       -- succeeds!  → 0 doctors online. Invariant broken.
```

Reset (`UPDATE doctors SET online = true;`) and repeat with **`ISOLATION LEVEL SERIALIZABLE`** in both: one of the transactions fails with `40001` (`could not serialize access due to read/write dependencies…`). Then fix with a *different technique*: both sessions at READ COMMITTED run `SELECT * FROM doctors WHERE online FOR UPDATE;` first — the second waits, re-checks the count, and correctly refuses.

---

## Lab 6 — Deadlocks and the DDL lock queue

**6a. Deadlock:**

```sql
CREATE TABLE acct (id int PRIMARY KEY, bal int);
INSERT INTO acct VALUES (1, 100), (2, 100);
```

```
 A: BEGIN; UPDATE acct SET bal = bal - 10 WHERE id = 1;
 B: BEGIN; UPDATE acct SET bal = bal - 10 WHERE id = 2;
 A: UPDATE acct SET bal = bal + 10 WHERE id = 2;       -- waits for B
 B: UPDATE acct SET bal = bal + 10 WHERE id = 1;       -- ~1 s later: ERROR: deadlock detected (one session is the victim)
```

While A waits (before B's second statement), inspect from a third session:

```sql
SELECT pid, locktype, relation::regclass, mode, granted FROM pg_locks WHERE NOT granted;
SELECT pid, wait_event_type, wait_event, state, left(query, 50) FROM pg_stat_activity WHERE datname = current_database();
SELECT pid, pg_blocking_pids(pid) FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

Fix: rewrite both transactions to touch rows in `id` order. Confirm no deadlock.

**6b. The DDL lock queue (the "5 ms ALTER that took the site down"):**

```
 A: BEGIN; SELECT * FROM acct;                          -- holds ACCESS SHARE, stays open
 B: ALTER TABLE acct ADD COLUMN note text;              -- needs ACCESS EXCLUSIVE → waits behind A
 C: SELECT * FROM acct;                                 -- HANGS, queued behind B's pending lock request!
```

Now `ROLLBACK` in A and watch everything drain. Repeat with `SET lock_timeout = '2s';` in B before the `ALTER`: the DDL gives up after 2 s, C proceeds. **This is why every migration script should start with `SET lock_timeout`.**

---

## Lab 7 — WAL, crash recovery, durability cost

```bash
docker run -d --name pgwal -e POSTGRES_PASSWORD=pw postgres:17
docker exec -it pgwal psql -U postgres
```

**7a. How much WAL does a statement generate?**

```sql
CREATE TABLE w (id serial PRIMARY KEY, v text);
SELECT pg_current_wal_lsn() AS before \gset
INSERT INTO w (v) SELECT md5(i::text) FROM generate_series(1, 200000) i;
SELECT pg_size_pretty(pg_current_wal_lsn() - :'before'::pg_lsn) AS wal_for_200k_inserts;

-- Now add three more indexes and repeat with a new table or TRUNCATE: WAL grows. Why?
CREATE INDEX ON w (v);
CREATE INDEX ON w (md5(v));
CREATE INDEX ON w (length(v), v);
TRUNCATE w;
SELECT pg_current_wal_lsn() AS before \gset
INSERT INTO w (v) SELECT md5(i::text) FROM generate_series(1, 200000) i;
SELECT pg_size_pretty(pg_current_wal_lsn() - :'before'::pg_lsn) AS wal_with_4_indexes;
```

**7b. Look at actual WAL records:**

```bash
docker exec -u postgres pgwal bash -c 'cd $PGDATA/pg_wal && pg_waldump $(ls | grep -E "^[0-9A-F]{24}$" | head -1) | tail -15'
# you will see records like:  Heap/INSERT, Btree/INSERT_LEAF, Transaction/COMMIT, XLOG/CHECKPOINT_ONLINE …
docker exec -u postgres pgwal pg_controldata | grep -iE "checkpoint location|REDO location|state"
```

**7c. Crash recovery.** In psql:

```sql
CREATE TABLE crash_test (id serial PRIMARY KEY, note text);
INSERT INTO crash_test (note) SELECT 'committed-' || g FROM generate_series(1, 1000) g;     -- autocommit: durable
BEGIN;
INSERT INTO crash_test (note) SELECT 'UNCOMMITTED-' || g FROM generate_series(1, 1000) g;   -- leave this session open!
```

In another terminal, kill the server hard (no clean shutdown, no checkpoint):

```bash
docker kill -s KILL pgwal
docker start pgwal
docker logs --tail 25 pgwal
# look for: "database system was not properly shut down; automatic recovery in progress"
#           "redo starts at 0/…"  …  "redo done at 0/…"  …  "database system is ready to accept connections"
docker exec pgwal psql -U postgres -c \
 "SELECT count(*) FILTER (WHERE note LIKE 'committed%') AS committed,
         count(*) FILTER (WHERE note LIKE 'UNCOMMITTED%') AS uncommitted FROM crash_test;"
# expected: committed = 1000, uncommitted = 0
```

You just watched: log replay restoring committed work that never reached the data files, and uncommitted work being invisible.

**7d. What does durability cost? (`synchronous_commit`)**

```bash
docker exec -u postgres pgwal pgbench -i -s 10 postgres
docker exec -u postgres pgwal pgbench -c 8 -j 4 -T 20 postgres                                   # default: synchronous_commit=on
docker exec -u postgres -e PGOPTIONS="-c synchronous_commit=off" pgwal pgbench -c 8 -j 4 -T 20 postgres
```

Compare TPS and latency average. (Numbers inside Docker Desktop/VMs mostly reflect the VM's `fsync` path — the *ratio* is the lesson. Remember what you traded: up to ~0.6 s of acknowledged commits on a crash.)

---

## Lab 8 — Streaming replication, lag, sync outage, promotion

*(Lab only: `trust` authentication is used to keep the lab short. Never do this in production.)*

```bash
docker network create pgnet
docker run -d --name primary --network pgnet -e POSTGRES_PASSWORD=pw postgres:17

docker exec primary psql -U postgres -c "CREATE ROLE repl WITH REPLICATION LOGIN;"
docker exec primary bash -c 'echo "host replication repl all trust" >> $PGDATA/pg_hba.conf'
docker exec primary psql -U postgres -c "SELECT pg_reload_conf();"

# Clone the primary into a volume with pg_basebackup (-R writes standby.signal + primary_conninfo)
docker volume create replica_data
docker run --rm --network pgnet -v replica_data:/var/lib/postgresql/data postgres:17 bash -c \
  "rm -rf /var/lib/postgresql/data/* && pg_basebackup -h primary -U repl -D /var/lib/postgresql/data -R -X stream -P \
   && chown -R postgres:postgres /var/lib/postgresql/data && chmod 700 /var/lib/postgresql/data"

docker run -d --name replica --network pgnet -v replica_data:/var/lib/postgresql/data postgres:17
```

**8a. It replicates, and it's read-only:**

```bash
docker exec primary psql -U postgres -c "CREATE TABLE r (id serial, v text); INSERT INTO r (v) VALUES ('hello');"
docker exec replica psql -U postgres -c "SELECT * FROM r;"                     # hello
docker exec replica psql -U postgres -c "INSERT INTO r (v) VALUES ('x');"      # ERROR: cannot execute INSERT in a read-only transaction
docker exec primary psql -U postgres -x -c "SELECT application_name, state, sync_state, sent_lsn, replay_lsn, replay_lag FROM pg_stat_replication;"
```

**8b. Manufacture replication lag:**

```bash
docker exec replica psql -U postgres -c "SELECT pg_wal_replay_pause();"
docker exec primary psql -U postgres -c "INSERT INTO r (v) SELECT md5(g::text) FROM generate_series(1, 100000) g;"
docker exec primary psql -U postgres -c "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes, replay_lag FROM pg_stat_replication;"
docker exec replica psql -U postgres -c "SELECT count(*) FROM r;"              # stale! (1 row) — your 'ghost order' bug
docker exec replica psql -U postgres -c "SELECT pg_wal_replay_resume();"
docker exec replica psql -U postgres -c "SELECT count(*) FROM r;"              # catches up
```

**8c. What synchronous replication really means:**

```bash
docker exec primary psql -U postgres -c "ALTER SYSTEM SET synchronous_standby_names = '*';"
docker exec primary psql -U postgres -c "SELECT pg_reload_conf();"
docker exec primary psql -U postgres -c "INSERT INTO r (v) VALUES ('sync ok');"       # works; check sync_state = 'sync'
docker stop replica
docker exec primary psql -U postgres -c "INSERT INTO r (v) VALUES ('will hang');"     # HANGS: commit waits for a standby that is gone
# Ctrl-C it, then: (the row is already visible locally; only the *acknowledgement* waited — what does that imply for the client?)
docker start replica                                                                  # commits flow again
```

**8d. Failover:**

```bash
docker exec primary psql -U postgres -c "ALTER SYSTEM RESET synchronous_standby_names;" -c "SELECT pg_reload_conf();"
docker stop primary                                                   # simulate primary failure
docker exec replica psql -U postgres -c "SELECT pg_promote();"        # replica becomes the new primary (new timeline)
docker exec replica psql -U postgres -c "INSERT INTO r (v) VALUES ('written on new primary'); SELECT pg_is_in_recovery();"
```

**Questions:** What did you *not* do that a production failover must do (fencing the old primary, reconnecting apps, rebuilding the old primary with `pg_rewind`)? What would have happened to any commit that hadn't reached the replica when you stopped the primary in async mode?

Cleanup: `docker rm -f primary replica pgwal; docker volume rm replica_data; docker network rm pgnet`.

---

## Lab 9 — Python: N+1 and OFFSET vs keyset pagination

```sql
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_created_id   ON orders (created_at DESC, id DESC);
ANALYZE orders;
```

```python
# lab9_bench.py      pip install "psycopg[binary]"
import statistics, time
import psycopg

DSN = "postgresql://postgres:pw@localhost:5432/postgres"


def timed_ms(fn, runs=5):
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return statistics.median(samples)


with psycopg.connect(DSN, autocommit=True) as conn:
    cur = conn.cursor()

    # ---------- 1. N+1 vs one batched query ----------
    user_ids = list(range(1, 201))

    def n_plus_one():
        for uid in user_ids:
            cur.execute(
                "SELECT id, total FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 5",
                (uid,),
            )
            cur.fetchall()

    def batched():
        cur.execute(
            """
            SELECT user_id, id, total FROM (
                SELECT user_id, id, total,
                       row_number() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn
                FROM orders WHERE user_id = ANY(%s)
            ) t WHERE rn <= 5
            """,
            (user_ids,),
        )
        cur.fetchall()

    print(f"N+1 (200 queries):   {timed_ms(n_plus_one):8.1f} ms")
    print(f"batched (1 query):   {timed_ms(batched):8.1f} ms")

    # ---------- 2. OFFSET vs keyset ----------
    print("\npage offset     OFFSET ms    keyset ms")
    for offset in (0, 1_000, 100_000, 1_000_000, 3_000_000):
        # find the cursor row for this offset (not timed): the last row of the previous page
        cur.execute(
            "SELECT created_at, id FROM orders ORDER BY created_at DESC, id DESC OFFSET %s LIMIT 1",
            (max(offset - 1, 0),),
        )
        last_created, last_id = cur.fetchone()

        def with_offset():
            cur.execute(
                "SELECT id, total FROM orders ORDER BY created_at DESC, id DESC OFFSET %s LIMIT 20",
                (offset,),
            )
            cur.fetchall()

        def with_keyset():
            cur.execute(
                """SELECT id, total FROM orders
                   WHERE (created_at, id) < (%s, %s)
                   ORDER BY created_at DESC, id DESC LIMIT 20""",
                (last_created, last_id),
            )
            cur.fetchall()

        print(f"{offset:>10,}   {timed_ms(with_offset):10.1f}   {timed_ms(with_keyset):10.2f}")
```

**Expected:** N+1 pays ~200 round trips (against `localhost` the gap is modest; against a DB in another AZ it's dramatic — try `tc`/Docker network latency or point `DSN` at a remote instance). OFFSET time grows linearly with the page number; keyset stays flat. Run `EXPLAIN (ANALYZE, BUFFERS)` on both pagination queries and compare the `Buffers` counts.

---

## Lab 10 — Build and test a B+Tree in Python

Save as `toy_bptree.py` and run it. (This is the exact file that was executed while preparing this document.)

```python
"""
A minimal in-memory B+Tree (insert + point lookup + range scan).
Purpose: to SEE how splits, separator keys and leaf links work.
Not thread-safe, no deletion, no disk pages.
"""
from bisect import bisect_left, bisect_right


class Node:
    def __init__(self, leaf: bool):
        self.leaf = leaf
        self.keys = []        # sorted keys
        self.children = []    # internal: child nodes; leaf: values (row pointers)
        self.next = None      # leaf only: right sibling (for range scans)


class BPlusTree:
    def __init__(self, order: int = 4):
        # order = max number of keys per node. Real DBs: hundreds, bounded by page size.
        assert order >= 3
        self.order = order
        self.root = Node(leaf=True)

    # ---------- search ----------
    def _find_leaf(self, key):
        node = self.root
        while not node.leaf:
            # keys[i] is the smallest key reachable under children[i+1]
            node = node.children[bisect_right(node.keys, key)]
        return node

    def get(self, key):
        leaf = self._find_leaf(key)
        i = bisect_left(leaf.keys, key)
        if i < len(leaf.keys) and leaf.keys[i] == key:
            return leaf.children[i]
        return None

    def range(self, lo, hi):
        """Yield (key, value) for lo <= key <= hi by walking the leaf chain."""
        leaf = self._find_leaf(lo)
        while leaf:
            for k, v in zip(leaf.keys, leaf.children):
                if k > hi:
                    return
                if k >= lo:
                    yield k, v
            leaf = leaf.next

    # ---------- insert ----------
    def insert(self, key, value):
        split = self._insert(self.root, key, value)
        if split:  # root was split -> tree grows one level taller
            sep, right = split
            new_root = Node(leaf=False)
            new_root.keys = [sep]
            new_root.children = [self.root, right]
            self.root = new_root

    def _insert(self, node, key, value):
        if node.leaf:
            i = bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                node.children[i] = value          # upsert
                return None
            node.keys.insert(i, key)
            node.children.insert(i, value)
            if len(node.keys) > self.order:
                return self._split_leaf(node)
            return None

        i = bisect_right(node.keys, key)
        split = self._insert(node.children[i], key, value)
        if split:
            sep, right = split
            node.keys.insert(i, sep)
            node.children.insert(i + 1, right)
            if len(node.keys) > self.order:
                return self._split_internal(node)
        return None

    def _split_leaf(self, node):
        mid = len(node.keys) // 2
        right = Node(leaf=True)
        right.keys, node.keys = node.keys[mid:], node.keys[:mid]
        right.children, node.children = node.children[mid:], node.children[:mid]
        right.next, node.next = node.next, right
        return right.keys[0], right          # separator is COPIED up (stays in leaf)

    def _split_internal(self, node):
        mid = len(node.keys) // 2
        sep = node.keys[mid]
        right = Node(leaf=False)
        right.keys = node.keys[mid + 1:]
        right.children = node.children[mid + 1:]
        node.keys = node.keys[:mid]
        node.children = node.children[:mid + 1]
        return sep, right                    # separator is MOVED up

    # ---------- introspection ----------
    def height(self):
        h, n = 1, self.root
        while not n.leaf:
            h, n = h + 1, n.children[0]
        return h

    def dump(self):
        level, out = [self.root], []
        while level:
            out.append(" | ".join(str(n.keys) for n in level))
            level = [c for n in level if not n.leaf for c in n.children]
        return "\n".join(out)


if __name__ == "__main__":
    import random

    t = BPlusTree(order=4)
    for k in [10, 20, 5, 6, 12, 30, 7, 17, 3, 25, 40, 1]:
        t.insert(k, f"row-{k}")
    print(t.dump())
    print("height:", t.height())
    assert t.get(17) == "row-17" and t.get(99) is None
    assert [k for k, _ in t.range(6, 25)] == [6, 7, 10, 12, 17, 20, 25]

    # randomized check against a dict
    random.seed(1)
    keys = random.sample(range(1_000_000), 20_000)
    big = BPlusTree(order=64)
    for k in keys:
        big.insert(k, k * 2)
    assert all(big.get(k) == k * 2 for k in keys)
    assert [k for k, _ in big.range(0, 10**9)] == sorted(keys)
    print("20k keys, order=64 -> height", big.height())
    print("OK")
```

Actual output when run:

```
[5, 10, 17, 25]
[1, 3] | [5, 6, 7] | [10, 12] | [17, 20] | [25, 30, 40]
height: 2
20k keys, order=64 -> height 3
OK
```

Read the first two lines against §2.3: the root holds separators `5, 10, 17, 25`; the five leaves hold the actual keys; each separator equals the smallest key of the child to its right.

**Exercises (do these — they are the point):**

1. Add a `page_reads` counter incremented in `_find_leaf` per node visited. Insert 1 M sequential keys with `order = 4, 64, 512` and print `height()` and average `page_reads` for 10 k random `get`s. Compare with `log_order(N)`.
2. Insert keys in **ascending** vs **random** order and measure average leaf fill (`sum(len(leaf.keys)) / (leaves × order)`). You'll reproduce the 90/10-vs-50/50 split story from §2.3.4 — then modify `_split_leaf` so that when the new key is the largest, it splits 90/10 and watch sequential fill rise.
3. Implement `delete(key)` with leaf borrowing/merging. (Notice why real engines postpone merges: they're expensive and often undone by the next insert.)
4. Add a `lower_bound(key)` iterator and implement a composite key `(user_id, created_at)` as tuples; implement `WHERE user_id = 42 AND created_at > X` as one range scan, and `WHERE created_at > X` alone as a *full* scan. Congratulations: you've re-derived the leftmost-prefix rule.

---

## Lab 11 — Redis: sorted-set index, atomic stock admission, cache stampede, persistence

```bash
docker run -d --name redis -p 6379:6379 redis:7
docker exec -it redis redis-cli
```

**11a. A sorted set as a tiny "index" — latest orders per user** (conceptually a B-tree range scan, in RAM):

```
ZADD user:42:orders 1767225600 o_1001 1767312000 o_1002 1767398400 o_1003
ZREVRANGE user:42:orders 0 1 WITHSCORES          # newest two  (≈ ORDER BY created_at DESC LIMIT 2)
ZRANGEBYSCORE user:42:orders 1767300000 +inf     # range by score (≈ created_at > X)
ZREMRANGEBYRANK user:42:orders 0 -101            # keep only the newest 100 (bounded memory)
ZCARD user:42:orders
```

Discussion: this is a *derived index*; the database is the source of truth. What happens on Redis restart? (Rebuild from DB or tolerate gaps.)

**11b. Atomic admission control (the flash-sale shield):**

```python
# lab11_admit.py      pip install redis
import threading
import redis

r = redis.Redis()
ADMIT = r.register_script("""
local stock = tonumber(redis.call('GET', KEYS[1]) or '0')
local want  = tonumber(ARGV[1])
if stock >= want then
    redis.call('DECRBY', KEYS[1], want)
    return 1
end
return 0
""")

r.set("stock:med:7", 200)
winners = []
lock = threading.Lock()

def buyer():
    ok = ADMIT(keys=["stock:med:7"], args=[1])
    if ok:
        with lock:
            winners.append(1)

threads = [threading.Thread(target=buyer) for _ in range(1000)]
[t.start() for t in threads]; [t.join() for t in threads]
print("admitted:", len(winners), " remaining:", r.get("stock:med:7"))   # admitted: 200  remaining: b'0'
```

Lua scripts execute atomically in Redis's single command thread, so "check then decrement" cannot interleave. Compare with the pure-Python `GET` → check → `SET` version and watch it oversell.

**11c. Cache-aside with stampede protection:**

```python
import json, random, time
import redis

r = redis.Redis()

def get_product(pid, load_from_db, ttl=300, attempts=40):
    key = f"product:{pid}"
    for _ in range(attempts):
        if (v := r.get(key)) is not None:
            return json.loads(v)
        # Only ONE caller rebuilds; others wait briefly and re-check (prevents N concurrent DB hits on a hot key expiry)
        if r.set(f"lock:{key}", "1", nx=True, px=5000):
            try:
                row = load_from_db(pid)
                r.set(key, json.dumps(row), ex=ttl + random.randint(0, 60))   # TTL jitter avoids synchronized expiry
                return row
            finally:
                r.delete(f"lock:{key}")
        time.sleep(0.05)
    return load_from_db(pid)          # fall back rather than fail
```

Measure DB calls with 200 concurrent threads requesting the same cold key: with the lock → ~1; without → ~200. (Production hardening: lock token + Lua compare-and-delete, `stale-while-revalidate`.)

**11d. Persistence is a choice:**

```
CONFIG GET save                      # RDB snapshot schedule: you can lose everything since the last snapshot
CONFIG SET appendonly yes            # AOF
CONFIG SET appendfsync everysec      # lose ≤ ~1 s on crash;  'always' = fsync each write (slower)
```

```bash
docker exec redis redis-cli DEBUG POPULATE 100000     # 100k keys
docker kill -s KILL redis && docker start redis
docker exec redis redis-cli DBSIZE                    # try with AOF off vs on — what survived?
docker exec redis redis-benchmark -q -n 100000 -t set,get
```

**Takeaway:** Redis is superb as a cache, rate limiter, admission controller and derived index. Do not make it the sole record of money or orders.

---

## Lab 12 — Go: retry transactions on `40001` / `40P01`

Since you're learning Go, this doubles as practice with `context`, goroutines, `errors.As` and pgx.

```bash
mkdir lab12 && cd lab12 && go mod init lab12 && go get github.com/jackc/pgx/v5
```

(Recreate the `doctors` table from Lab 5c with both rows `online = true`.)

```go
// main.go
package main

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

// 40001 = serialization_failure, 40P01 = deadlock_detected
func isRetryable(err error) bool {
	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		return pgErr.Code == "40001" || pgErr.Code == "40P01"
	}
	return false
}

// withRetry runs fn in a transaction, retrying the WHOLE transaction on retryable errors,
// with exponential backoff and full jitter. fn must have no side effects outside the database.
func withRetry(ctx context.Context, pool *pgxpool.Pool, opts pgx.TxOptions, fn func(pgx.Tx) error) error {
	const maxAttempts = 5
	for attempt := 0; attempt < maxAttempts; attempt++ {
		err := func() error {
			tx, err := pool.BeginTx(ctx, opts)
			if err != nil {
				return err
			}
			defer tx.Rollback(ctx) // harmless after a successful Commit
			if err := fn(tx); err != nil {
				return err
			}
			return tx.Commit(ctx)
		}()
		if err == nil || !isRetryable(err) || attempt == maxAttempts-1 {
			return err
		}
		backoff := time.Duration(rand.Int63n(int64(50*time.Millisecond) << attempt))
		select {
		case <-time.After(backoff):
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	return nil
}

func goOffline(ctx context.Context, pool *pgxpool.Pool, id int) error {
	return withRetry(ctx, pool, pgx.TxOptions{IsoLevel: pgx.Serializable}, func(tx pgx.Tx) error {
		var online int
		if err := tx.QueryRow(ctx, "SELECT count(*) FROM doctors WHERE online").Scan(&online); err != nil {
			return err
		}
		if online < 2 {
			return errors.New("business rule: at least one doctor must stay online")
		}
		time.Sleep(200 * time.Millisecond) // widen the race window
		_, err := tx.Exec(ctx, "UPDATE doctors SET online = false WHERE id = $1", id)
		return err
	})
}

func main() {
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, "postgres://postgres:pw@localhost:5432/postgres")
	if err != nil {
		panic(err)
	}
	defer pool.Close()

	results := make(chan error, 2)
	for _, id := range []int{1, 2} {
		go func(id int) { results <- goOffline(ctx, pool, id) }(id)
	}
	for i := 0; i < 2; i++ {
		fmt.Println("result:", <-results)
	}
}
```

**Expected:** exactly one goroutine succeeds; the other first hits `40001`, is retried by `withRetry`, re-reads `count = 1`, and returns the *business-rule* error. Both can never succeed. Now change the isolation level to `pgx.RepeatableRead` and re-run — you will reproduce write skew (both succeed).

---

## Lab 13 — Capstone: prove (and break) "no oversell" with `pgbench`

```sql
CREATE TABLE inventory (id int PRIMARY KEY, qty int NOT NULL CHECK (qty >= 0));
INSERT INTO inventory SELECT g, 100000 FROM generate_series(1, 20) g;     -- 20 hot SKUs
CREATE TABLE sold (id bigserial PRIMARY KEY, inv_id int NOT NULL);
```

`atomic.sql` (correct):

```sql
\set pid random(1, 20)
WITH d AS (UPDATE inventory SET qty = qty - 1 WHERE id = :pid AND qty >= 1 RETURNING id)
INSERT INTO sold (inv_id) SELECT id FROM d;
```

`buggy.sql` (read-modify-write in "application" logic):

```sql
\set pid random(1, 20)
BEGIN;
SELECT qty AS q FROM inventory WHERE id = :pid \gset
INSERT INTO sold (inv_id) SELECT :pid WHERE :q >= 1;
UPDATE inventory SET qty = :q - 1 WHERE id = :pid AND :q >= 1;
COMMIT;
```

```bash
pgbench -n -f atomic.sql -c 32 -j 4 -T 15 postgres
psql postgres -c "SELECT (SELECT 20*100000 - sum(qty) FROM inventory) AS decremented, (SELECT count(*) FROM sold) AS sold_rows;"
# atomic: decremented == sold_rows  (always)

psql postgres -c "UPDATE inventory SET qty = 100000; TRUNCATE sold;"
pgbench -n -f buggy.sql  -c 32 -j 4 -T 15 postgres
psql postgres -c "SELECT (SELECT 20*100000 - sum(qty) FROM inventory) AS decremented, (SELECT count(*) FROM sold) AS sold_rows;"
# buggy: decremented < sold_rows   → you sold items the inventory never subtracted = lost updates = oversell
```

Then fix `buggy.sql` three ways (`FOR UPDATE` on the `SELECT`; `REPEATABLE READ` + retry on 40001 (`PGOPTIONS='-c default_transaction_isolation=repeatable\ read' pgbench --max-tries=10 …`); or convert to the atomic form) and compare **throughput** and **correctness** of each. Write down which you would choose and why — that is the engineering judgement this document exists to build.

# 13. Common mistakes engineers make (consolidated)

Grouped by the *kind of thinking error*, because the error pattern repeats across topics.

## 13.1 Indexing and schema

| Mistake | Why it hurts | Do instead |
|---|---|---|
| "Index everything just in case" | Every index = write amplification, memory, no HOT updates | Index for **measured** queries; audit `idx_scan = 0` quarterly |
| Index per column instead of per query | Planner can't combine well; no ordering | Design composites from query shapes (ESR) |
| Range column before equality column | Range ends the seek | Equality → sort → range |
| Redundant prefix indexes | Pure cost | Keep the longest useful one |
| Low-cardinality plain index (`status`, `is_active`) | Planner ignores it; costs writes | **Partial** index for the rare value |
| Function/cast on the indexed column | Index unusable | Sargable rewrite or expression index |
| Random UUIDv4 as clustered PK (InnoDB) | Page splits, fat secondary indexes | Time-ordered IDs / `BIGINT` PK + public UUID column |
| Missing FK index (PostgreSQL) | Slow parent deletes, lock amplification | Index every referencing column |
| `FLOAT` for money; timestamps without time zone | Rounding errors; DST/offset bugs | Integer minor units / `numeric`; `timestamptz` |
| Storing blobs in hot tables | Bloat, slow `SELECT *` | Object storage + URL |
| Soft deletes without partial unique indexes | Duplicate "active" rows | `UNIQUE … WHERE deleted_at IS NULL` |

## 13.2 Queries and the optimizer

| Mistake | Do instead |
|---|---|
| `SELECT *` everywhere | Select needed columns (enables covering/index-only) |
| `OFFSET` pagination for deep pages | Keyset pagination with a unique tiebreaker |
| N+1 queries from the ORM | `select_related`/`prefetch_related`; budget queries per request |
| `COUNT(*)` of a big table on every page load | Approximate/cached counters |
| Reading `cost=` as milliseconds | Use `EXPLAIN (ANALYZE, BUFFERS)` |
| Ignoring `loops` and estimate-vs-actual | Find the *lowest* node where estimate ≠ actual |
| Forgetting `ANALYZE` after bulk loads/restores | Analyze in the job itself |
| `random_page_cost = 4` on SSD; huge global `work_mem` | `1.1`; small global, raise per role |
| Testing on a tiny dev DB | Production-shaped data and stats |
| "Fixing" with hints/`enable_*` in production | Fix statistics, indexes, query shape |

## 13.3 Transactions and concurrency

| Mistake | Do instead |
|---|---|
| Read-modify-write across statements | Atomic `UPDATE … SET x = x - 1 WHERE x >= 1`, or `FOR UPDATE` |
| Assuming REPEATABLE READ stops all anomalies; assuming MySQL RR == PostgreSQL RR | Know the matrix (§8.3.2); use SERIALIZABLE + retry or explicit locks for write-skew risks |
| Transactions around network calls / user think time | DB-only, short transactions; outbox for side effects |
| No retries for `40001`/`40P01`/MySQL 1213 | Retry the whole transaction with jittered backoff |
| Inconsistent lock ordering | Lock in a canonical order |
| `FOR UPDATE` on unindexed predicates | Index it (esp. InnoDB gap locks) |
| One hot row (counter, SKU) in a high-throughput path | Buckets, queue, Redis admission, or restructure |
| Believing a transaction spans services | Outbox, idempotency, sagas |
| No `statement_timeout`/`lock_timeout`/`idle_in_transaction_session_timeout` | Set sane defaults per role |
| Session-level advisory locks behind PgBouncer transaction pooling | `pg_advisory_xact_lock` |

## 13.4 Operations, durability and replication

| Mistake | Do instead |
|---|---|
| Replica as backup | Backups + PITR + (optional) delayed replica |
| Never restoring a backup | Automated monthly restore drills; measure RTO |
| `fsync=off`, `synchronous_commit=off` on money data | Keep defaults for critical data; per-transaction relaxation for logs |
| Ignoring replication slots / failing `archive_command` | Alert on retained WAL; cap with `max_slot_wal_keep_size` |
| Reads that feed writes from replicas | Primary for decision reads |
| Read-your-writes ignored | Pin to primary / LSN wait |
| Auto-failover without fencing or quorum | Patroni + consensus store; rehearse |
| Non-concurrent `CREATE INDEX`/DDL on hot tables; no `lock_timeout` | `CONCURRENTLY`, online patterns, `lock_timeout` |
| Disabling autovacuum; ignoring `n_dead_tup`/XID age | Tune per table; alert |
| One connection per request, no pooler | PgBouncer; right-size pools across pods |
| Scaling by "bigger instance" before understanding the bottleneck | Walk the scaling ladder (§11.8) |

## 13.5 The meta-mistakes (these cause the others)

1. **Cargo-culting.** "Add an index", "use Redis", "use SERIALIZABLE", "shard it" — without a measurement or a mechanism.
2. **Optimizing averages.** Production is run by tails (p99) and by skew (the whale tenant, the viral product).
3. **Treating the database as a black box.** Every incident in this document was a *predictable consequence of a mechanism* you now know.
4. **Not writing down the invariants.** If you can't say "this must always be true", you can't choose a lock or an isolation level.
5. **No feedback loop.** No `pg_stat_statements`, no `auto_explain`, no slow-query review → you learn about problems from customers.

---

# 14. System design interview questions

Format: attempt each **before** opening the answer. Time yourself (≈ 35–45 minutes for the big one). The answers are *reference outlines*, not the only valid design — what counts is explicit **requirements → numbers → mechanisms → trade-offs → failure modes**.

## 14.1 Main question — Flash-sale checkout on a pharmacy marketplace

> You run an online pharmacy marketplace on PostgreSQL (one 16 vCPU / 128 GB primary, 2 read replicas, Redis, Django/FastAPI services on Kubernetes). Marketing plans a **flash campaign**: 300 discounted SKUs, **500 units each (150,000 units total)**, starting at 20:00. Expect ~400,000 users in the first minute and a peak of **~20,000 checkout attempts per second** for the first ~10 seconds. Requirements:
>
> * Never oversell. Never create duplicate orders when clients/networks retry.
> * p99 "place order" API latency < 1 s for admitted users; rejected users should learn "sold out" in < 200 ms.
> * Paid orders must never be lost (RPO ≈ 0 for orders).
> * The rest of the site (browse, order history) must stay up.
> * One primary database — do **not** answer "just shard it".
>
> Design the data layer and the checkout flow. Discuss schema, indexes, isolation/locking, failure modes, capacity math, and how you'd test and monitor it.

<details>
<summary><strong>Reference answer (open after you've attempted it)</strong></summary>

**1. Clarify (ask these first).** Per-user purchase limits? Payment synchronous or redirect/async (usually async with a hold)? Is "sold out in < 200 ms" allowed to be eventually right? Reservation hold time (e.g., 10 min)? Can order confirmation be asynchronous ("we're processing")? Are SKUs per-pharmacy or global? Which inventory is authoritative today?

**2. Back-of-envelope.**
* Successful orders are bounded by stock: ≤ 150,000. So **≥ ~85–95% of the 20 k/s attempts must be rejected** — the key insight: *rejections must be nearly free*.
* Naive design: each attempt = a DB transaction updating the SKU row. Load skew: if the top 10 SKUs attract half the traffic that's ~1,000 attempts/s/SKU. A row lock held ~3–5 ms for the transaction ⇒ ≤ ~200–330 commits/s/row. The queue behind each hot row grows, pool connections (say 100) are all waiting, **every other query (browse!) starves** → full outage. Also 20 k connections' worth of attempts would blow past any sane `max_connections`.
* Successful write volume: if all 150 k units sell in 60 s that's ~2.5 k orders/s (up to 5 k/s if 30 s). Each order ≈ 1 order + ~3 items + 1 reservation + 1 outbox + movements ≈ 7 rows + ~15 index entries → ~20–40 k row/index modifications per second at peak. Too spiky for comfort on one primary → **level the load** with a queue.

**3. Architecture.**
```
 clients ─► CDN (static "sold out" page, product data) ─► API
                                   │ (1) rate limit + per-user dedupe (Redis)
                                   │ (2) ADMISSION: Lua script atomically DECRs stock:{campaign}:{sku}; per-user limit via SADD
                                   ├─ rejected ───────────────────────────► "sold out" in ~ms (no DB touched)
                                   └─ admitted ─► enqueue order command (durable: Redis Stream/Kafka/RabbitMQ) ─► 202 Accepted + order_ref
                                                         │
                                          N controlled workers (e.g., 64) ─► PgBouncer ─► PostgreSQL primary
                                              each: one short transaction (below); idempotent
                                                         │ outbox
                                                         ▼
                                  payment hold / notification / fulfilment consumers;   status via push or polling (cached)
```
*Why the queue:* it converts a 20 k/s spike into a steady ≤ 1–2 k orders/s the DB can sustain (queue-based load levelling), bounded by worker concurrency instead of by user concurrency.

**4. Data model (PostgreSQL).**
```sql
inventory(pharmacy_id, sku_id, qty_available int CHECK (qty_available >= 0), PRIMARY KEY (pharmacy_id, sku_id))
-- campaign SKUs: split into buckets to parallelise the hot row:
inventory_bucket(campaign_id, sku_id, bucket smallint, qty int CHECK (qty >= 0), PRIMARY KEY (campaign_id, sku_id, bucket))
reservations(id, order_id, sku_id, qty, expires_at, status, …)  -- partial index (expires_at) WHERE status='HELD'
orders(…)  -- partitioned by month; see §11.4
idempotency_keys(user_id, key, order_id, PRIMARY KEY (user_id, key))     -- the arbiter of retries
purchase_limits(campaign_id, user_id, sku_id, PRIMARY KEY(...))         -- unique constraint enforces "1 per user"
inventory_movements(id, sku_id, delta, reason, order_id, at)             -- append-only audit ledger for reconciliation
outbox(id, event_type, payload, created_at, published_at)                -- partial index WHERE published_at IS NULL
```

**5. The worker transaction** (READ COMMITTED; `lock_timeout = 300ms`; `statement_timeout = 2s`):
1. `INSERT INTO idempotency_keys … ON CONFLICT DO NOTHING` → if no row inserted: duplicate → return the existing order. *(DB constraint as arbiter; works across retries and across workers.)*
2. `INSERT INTO purchase_limits …` → unique violation ⇒ user already bought → reject.
3. `UPDATE inventory_bucket SET qty = qty - :n WHERE campaign_id=:c AND sku_id=:s AND bucket=:b AND qty >= :n` → rowcount 0 ⇒ try next bucket; none ⇒ sold out (and **re-sync Redis**: this is the safety net if Redis over-admitted).
4. `INSERT` order, items, reservation, movement, outbox row. `COMMIT` (sync standby in the other AZ ⇒ RPO ≈ 0).
5. Retry on `40001/40P01/lock_timeout` with jitter, same idempotency key.

*Isolation:* READ COMMITTED + atomic conditional updates + unique constraints. No SERIALIZABLE needed: every invariant (stock ≥ 0, one per user, one order per key) is enforced by a **single-statement atomic operation or a unique/check constraint** — the cheapest correct mechanism.

**6. Why this is correct (oversell proof sketch).** Redis admission is an *optimization* (traffic shaper). The *authoritative* stock check is the conditional `UPDATE` with `CHECK (qty >= 0)` in PostgreSQL. Even if Redis over-admits (crash/rollback/bug), the DB can never go negative; the worst case is admitted-but-rejected users (a UX problem, not a correctness problem). Under-admission (Redis lost counters) is handled by rebuilding counters from `qty` minus active reservations.

**7. Failure modes.**
| Failure | Behaviour |
|---|---|
| Redis crash mid-sale | Fail **closed** (pause admission for ≤ seconds), rebuild counters from DB truth, resume; or fall back to DB-only path with strict rate limit (accept slower, never oversell) |
| Worker crashes mid-transaction | Transaction rolls back; message redelivered; idempotency key makes it safe |
| DB failover (~10–30 s) | Workers retry with backoff; queue absorbs the backlog; users see "processing" |
| Payment never completes | Reservation expires (`expires_at`); a janitor job releases stock using `SKIP LOCKED` batches, re-credits Redis |
| Duplicate payment webhooks | Idempotent handler keyed by gateway event id (unique constraint) |
| Queue backlog grows | Autoscale workers *up to the DB's safe concurrency*, not beyond; shed load at admission |
| Replica lag shows "no order" | Status endpoint reads Redis/primary by `order_ref`, not a replica |
| Thundering herd on product page | CDN + cache-aside with stampede lock + TTL jitter |

**8. Capacity.** Workers 64 → PgBouncer pool ≈ 64 server connections for the campaign path; reserve separate pools for browse/read traffic so the campaign cannot starve them (bulkheads). Bucket count ≈ expected peak attempts-per-SKU ÷ per-row ceiling (e.g., 1,000/s ÷ 250/s → 4–8 buckets for top SKUs).

**9. Testing & monitoring.** Reproduce with a load test (k6/Locust + the Lab 13 invariant checker): after the run assert `Σ(initial) − Σ(qty) = Σ(movements) = count(order_items)` and `qty ≥ 0`. Chaos-test: kill Redis, kill a worker, fail over the DB mid-run. Dashboards: admission reject ratio, queue depth/age, worker error/retry rate, PG commit latency, lock waits, pool saturation, replication lag, WAL rate, Redis ops/s; **an automated oversell invariant checker** running every minute during the campaign.

**10. Evolution.** If campaigns grow 10×: shard Redis by SKU, add queue partitions, move campaign inventory to its own PG (a "cell") to isolate blast radius, pre-warm caches and connection pools, rehearse with a game day a week before.

**Scoring rubric.**
* *Junior:* uses transactions and `SELECT … FOR UPDATE`; maybe mentions Redis; doesn't do capacity math.
* *Mid:* atomic conditional update, idempotency key, indexes, mentions replicas/caching; limited failure analysis.
* *Senior:* identifies the **hot-row ceiling with numbers**, admission control vs source of truth, queue levelling, outbox, constraints as arbiters, explicit failure matrix, test plan with invariants.
* *Staff:* adds blast-radius isolation (bulkheads/cells), business trade-offs (async confirmation UX), operational readiness (game days, kill switches, runbooks), cost, and a migration/evolution path.

**Common follow-ups:** What if Redis and Postgres disagree? How do you deploy a schema change during campaign week? What if marketing wants one global limit per user across SKUs? How do you roll back a bad release mid-sale?
</details>

## 14.2 More questions (with answer outlines)

<details>
<summary><strong>Q2. A job queue on PostgreSQL handling ~10,000 jobs/second.</strong> Is it viable? How?</summary>

Viable with care. Claim with `FOR UPDATE SKIP LOCKED` in **batches** (e.g., 50–500 per transaction) using a **partial index** `ON jobs (id) WHERE status='PENDING'`; separate `jobs_done` archive or **time-partitioned** tables so you drop partitions instead of deleting (avoids bloat/vacuum storms); `fillfactor` and aggressive autovacuum on the hot table; **lease + heartbeat** (`locked_until`) so crashed workers' jobs are reclaimed; retries with exponential backoff and a dead-letter state; **at-least-once** delivery ⇒ idempotent handlers; keep payloads small; monitor queue age and dead tuples. Limits: dead-tuple churn, single-primary write ceiling, no fan-out/pub-sub, no back-pressure semantics — switch to a real broker (Kafka/RabbitMQ/SQS) when you need consumer groups, replay, or ≫ 10 k/s. Advantage of PG queue: **transactional enqueue with business data** (outbox) and operational simplicity.
</details>

<details>
<summary><strong>Q3. Diagnose: after a deploy at 14:10, API p99 went from 40 ms to 4 s. CPU is 35%, disk read IOPS are saturated, replicas look fine.</strong></summary>

Reasoning chain: *low CPU + high read IOPS ⇒ I/O-bound, probably a query reading many pages, evicting hot pages (cache pollution).* (1) `pg_stat_statements` sorted by `shared_blks_read`/total time, compare with pre-deploy snapshot ⇒ find new/changed query. (2) `pg_stat_activity` wait events (`IO:DataFileRead`), long-running queries. (3) `EXPLAIN (ANALYZE, BUFFERS)` of the culprit: expect Seq Scan/`Rows Removed by Filter` huge, or an index scan with huge heap fetches, or a plan flip. (4) Likely causes: new filter/sort without an index; ORM change generating a different query (lost `LIMIT`, `OFFSET`, `select_related` explosion); type mismatch killing an index; N+1. (5) Mitigate immediately (rollback deploy / feature flag / `CREATE INDEX CONCURRENTLY` / `pg_terminate_backend` of runaways / `statement_timeout`), then fix and add a regression guard (query count/plan checks in CI, alerts on buffers read per request). Mention why replicas "look fine": the offending path may be primary-only, or replicas are simply not receiving that query.
</details>

<details>
<summary><strong>Q4. Multi-tenant SaaS: 20,000 tenants, one has 10,000× the data of the median. Design indexing/partitioning/isolation.</strong></summary>

`tenant_id` as the leading column of (almost) every index and in every query; enforce isolation (RLS or an explicit query layer, with tests); watch **skew**: generic plans and statistics are wrong for whales (`plan_cache_mode`, extended statistics, per-tenant partial indexes if justified); per-tenant rate limits/quotas and statement timeouts; noisy-neighbour control via separate pools/bulkheads; **cell-based architecture**: place whales on dedicated databases/clusters and keep a tenant→cell directory; avoid per-tenant tables/schemas at 20 k tenants (catalog bloat, vacuum overhead); hash/list partitioning by tenant only if it matches access patterns; backup/restore per tenant strategy (logical export vs PITR of a cell); migration tooling that rolls through cells.
</details>

<details>
<summary><strong>Q5. Analysts need dashboards over a 2-billion-row orders table without slowing checkout.</strong></summary>

Do **not** run it on the primary. Options by freshness need: a dedicated analytics read replica (mind `hot_standby_feedback`, conflicts); CDC (Debezium) → Kafka → columnar warehouse (ClickHouse/BigQuery/Redshift) for minute-level freshness; nightly ETL for daily reports. Inside Postgres: time partitioning + partition pruning, BRIN on `created_at`, **pre-aggregated rollup tables/materialized views** refreshed incrementally, covering indexes for the few hot report shapes. Explain trade-offs: freshness vs cost vs complexity, schema-drift handling in CDC, and idempotent/ordered loads.
</details>

<details>
<summary><strong>Q6. Zero-downtime migration: change <code>orders.total</code> from <code>integer</code> to <code>bigint</code> and add an index on a 1-billion-row table.</strong></summary>

Know which operations **rewrite the table** (`ALTER COLUMN TYPE` does; adding a nullable column or one with a constant default doesn't in modern PG) and which take **ACCESS EXCLUSIVE**. Expand/contract: add `total_big bigint` (nullable) → dual-write via application/trigger → **backfill in small keyset batches** (throttle by replication lag and I/O; short transactions) → add `CHECK … NOT VALID` then `VALIDATE` → build indexes `CONCURRENTLY` → switch reads → drop the old column later. Always `SET lock_timeout` on DDL, retry on failure, run during low traffic, monitor lag/bloat/WAL, have a rollback plan at each step, and for MySQL use online DDL/gh-ost/pt-osc. Watch for invalid indexes left by failed concurrent builds.
</details>

<details>
<summary><strong>Q7. Design a wallet with balance, transfers, refunds. Money must never be created or lost.</strong></summary>

Double-entry **ledger** (append-only entries; each transfer = two entries summing to zero in one transaction), balance either derived or a cached column updated atomically with a guard (`UPDATE … SET balance = balance - :x WHERE id=:id AND balance >= :x`); integer minor units; **idempotency keys** with a unique constraint; lock accounts in canonical order (deadlock avoidance) or use single-statement CTE transfers; READ COMMITTED is enough with conditional updates, SERIALIZABLE + retry for complex multi-row invariants; reconciliation job (Σ entries = Σ balances), immutable audit, outbox for notifications, PITR + sync replication for RPO ≈ 0, reversals as new entries (never edits).
</details>

<details>
<summary><strong>Q8. "Users sometimes don't see their newly created address." Root cause and options.</strong></summary>

Replica lag (read-your-writes violation). Options with trade-offs: pin the user's reads to the primary for a short window after writes (simple; load shifts to primary; window must exceed p99 lag); LSN/causal token wait (precise; more plumbing); `synchronous_commit = remote_apply` to a replica (strong; commit latency + availability coupling); read-from-primary for the user's own data only; client-side optimistic UI. Plus: measure lag, alert, and never use replica reads for decisions.
</details>

<details>
<summary><strong>Q9. Why B+Trees for OLTP indexes — and not binary trees, hash tables, or LSM trees?</strong></summary>

Binary trees: depth log₂N with node-per-page ⇒ ~23 random I/Os for 10 M keys. Hash: O(1) but no range/order/prefix, resizing pain. B+Tree: fan-out ≈ page-size/entry-size ⇒ 3–4 levels for billions, sorted leaves ⇒ range scans & `ORDER BY`, in-place updates, predictable read latency. LSM: superior write throughput and compression via sequential writes + compaction, but read/space/write amplification and compaction stalls — chosen when writes dominate (time-series, logs, KV stores). OLTP workloads are read-heavy with point and range lookups and need predictable latency ⇒ B+Tree default.
</details>

<details>
<summary><strong>Q10. A search screen filters by any combination of 8 optional columns. One composite index or many single-column indexes?</strong></summary>

No composite can serve all 2⁸ combinations. Strategies: identify the **dominant** filter combinations from real traffic and build 2–4 composites for them; for the long tail rely on BitmapAnd of a few selective single-column indexes (accept slower); always include a selective *mandatory* filter (tenant/date range) as the leading column; use partial indexes for hot subsets; GIN/`bloom` for arbitrary equality combos; consider a search engine (OpenSearch) if it's truly faceted search. Quantify write cost per index and verify with `EXPLAIN`.
</details>

## 14.3 Quick-fire round (one-line answers in the details)

<details>
<summary><strong>Answer key — try to answer all 20 aloud first</strong></summary>

1. **Page size of PG/InnoDB?** 8 KB / 16 KB.
2. **What does `ctid` mean?** Physical tuple address (page, slot).
3. **Why is `UPDATE` "delete+insert" in PG?** MVCC keeps the old version for older snapshots.
4. **What is HOT?** Heap-only tuple update: same page, no indexed column changed ⇒ no index writes.
5. **When does the tree get taller?** Only on a root split.
6. **Why leftmost prefix?** Entries are sorted by column 1 first; non-prefix predicates don't map to a contiguous slice.
7. **ESR?** Equality, Sort, Range column order.
8. **Selectivity vs cardinality?** Fraction of rows matched by a predicate vs. number of distinct values of a column.
9. **Why might the planner pick a seq scan with an index available?** Low selectivity / low correlation / cheap table / stale stats / costs.
10. **What does `Rows Removed by Filter` tell you?** Wasted work: rows examined but discarded.
11. **Read committed vs repeatable read in PG?** Per-statement vs per-transaction snapshot.
12. **What is write skew?** Disjoint writes based on overlapping reads violating an invariant; needs serializable or read-set locking.
13. **Why can't readers block writers in MVCC?** Readers use old versions; no read locks on rows.
14. **What does VACUUM do?** Removes dead versions, updates visibility map/free space, freezes old xids; autovacuum drives `ANALYZE` too.
15. **Why is a long transaction dangerous?** Pins the xmin horizon (bloat), holds locks, delays DDL.
16. **What is the WAL rule?** Log record must be durable before the changed page is written; commit = WAL flush.
17. **Checkpoint purpose?** Bound recovery time by flushing dirty pages and advancing the redo pointer.
18. **Replica vs backup?** Replica copies mistakes instantly; backups + WAL archive give PITR.
19. **Why does sync replication reduce availability?** Commit waits for a standby; if none is available, commits stall.
20. **Biggest cause of bad plans?** Wrong cardinality estimates (stale stats, correlation, skew).
</details>

---

# 15. Cheat sheets, decision frameworks and a study plan

## 15.1 Index design checklist

1. List the **top queries by total time** (`pg_stat_statements`) — design for those, not for imagination.
2. For each: equality columns → ORDER BY column → range column (**ESR**).
3. Is the predicate on a rare value or subset? → **Partial index.**
4. Is a function applied to the column? → **Expression index** or rewrite sargably.
5. Is the query hot and returns few columns? → **INCLUDE** them (verify index-only scans have low `Heap Fetches`).
6. Does it replace an existing index (prefix-redundant)? → Drop the old one **concurrently**.
7. Estimate write cost: how often are these columns updated? Does it break HOT?
8. Create **CONCURRENTLY**; verify with `EXPLAIN (ANALYZE, BUFFERS)`; record before/after in the PR.
9. Re-audit unused indexes quarterly (check replicas too).

## 15.2 "My query is slow" flow

```
 slow?
  │
  ├─ Is the DB the bottleneck?  (DB execution time vs app-observed latency)
  │      no ─► N+1? pool wait? serialization? network? → fix in app
  │      yes
  ▼
  Is it working or waiting?  (pg_stat_activity wait_event; pg_blocking_pids)
  │      waiting on Lock ─► find blocker; long/idle txn? hot row? DDL queue? → timeouts, shorten txn, restructure
  │      waiting on IO   ─► working set > RAM? IOPS cap? checkpoint? big scan? → index/partition/RAM/IOPS
  │      working (CPU)
  ▼
  EXPLAIN (ANALYZE, BUFFERS)
  │      estimate ≠ actual (>10×) at lowest node? ─► ANALYZE, stats target, CREATE STATISTICS, avoid fragile predicates
  │      Seq Scan + huge Rows Removed?            ─► missing/unusable index (see §7.4)
  │      Sort/Hash spill?                          ─► work_mem (per role), index for order
  │      Nested Loop with huge loops?              ─► index inner side / fix estimate
  │      Too many rows returned?                   ─► LIMIT, keyset pagination, select fewer columns, aggregate in DB
  ▼
  Fix → measure on production-shaped data → add guardrail (alert / test)
```

## 15.3 Which concurrency tool for which problem

| Problem | First choice | Why |
|---|---|---|
| Decrement stock / balance with a guard | Atomic conditional `UPDATE` | Single statement, minimal lock time |
| Complex read→decide→write on a few rows | `SELECT … FOR UPDATE` (ordered) | Serializes the critical rows |
| Edit conflicts in admin UIs | Optimistic `version` column | No lock held during think time |
| Work queue | `FOR UPDATE SKIP LOCKED` | Parallel workers, no blocking |
| "Only one X per Y" | Unique/partial unique/exclusion constraint | DB enforces it; race-free |
| Invariant over a *set* of rows (write skew) | SERIALIZABLE + retry, or lock the read set | Snapshot isolation misses it |
| Retried requests | Idempotency key + unique constraint | Exactly-once *effect* |
| Cross-service consistency | Outbox + idempotent consumers (+ saga) | No distributed ACID |
| Scheduled job must run once cluster-wide | `pg_advisory_xact_lock` or leader election | Mutual exclusion |
| Consistent multi-query report | `REPEATABLE READ` (read-only) | One snapshot |

## 15.4 PostgreSQL starting configuration (OLTP, 64 GB RAM, NVMe/SSD) — *starting points, then measure*

| Parameter | Starting value | Note |
|---|---|---|
| `shared_buffers` | 16 GB (~25%) | OS cache covers the rest |
| `effective_cache_size` | 44–48 GB | Planner hint only |
| `work_mem` | 16 MB | Per sort/hash node per connection; raise per role for reports |
| `maintenance_work_mem` | 1–2 GB | Index builds, vacuum |
| `random_page_cost` | 1.1 | SSD/NVMe |
| `effective_io_concurrency` | 200 | SSD/NVMe |
| `max_connections` | 100–200 | **With PgBouncer** in front |
| `checkpoint_timeout` / `max_wal_size` / `checkpoint_completion_target` | 15min / 8–16GB / 0.9 | Fewer, smoother checkpoints |
| `wal_compression` | on | Cuts full-page-write volume |
| `autovacuum_vacuum_scale_factor` / `autovacuum_analyze_scale_factor` | 0.02 / 0.01 (lower, per table, for huge tables) | Default 0.2/0.1 is too lax for big tables |
| `autovacuum_vacuum_cost_limit` | 1000–2000 | Let vacuum keep up on fast disks |
| `jit` | off (OLTP) | Avoid compile overhead |
| `statement_timeout` / `lock_timeout` / `idle_in_transaction_session_timeout` | per role: e.g., 10 s / 3 s (migrations) / 60 s | Fail fast |
| `log_min_duration_statement`, `log_lock_waits`, `track_io_timing` | 500 ms, on, on | Observability |
| `shared_preload_libraries` | `pg_stat_statements,auto_explain` | Plus `pg_cron`/others as needed |

## 15.5 MySQL 8 / InnoDB starting configuration

| Parameter | Starting value | Note |
|---|---|---|
| `innodb_buffer_pool_size` | 60–75% of RAM | Dedicated host |
| `innodb_redo_log_capacity` (8.0.30+) | 4–16 GB | Avoid checkpoint stalls |
| `innodb_flush_log_at_trx_commit` / `sync_binlog` | 1 / 1 | Full durability |
| `innodb_flush_method` | `O_DIRECT` | Avoid double buffering |
| `binlog_format` | `ROW` | Safe replication/CDC |
| `transaction_isolation` | `READ-COMMITTED` *(consider)* | Fewer gap locks/deadlocks, if RR semantics aren't required |
| `innodb_lock_wait_timeout` | 5–10 s | Default 50 s hides problems |
| `max_connections` | modest + ProxySQL/pooling | Thread per connection |
| `slow_query_log`, `long_query_time` | on, 0.5 | Plus `performance_schema`, `sys` schema |
| `innodb_adaptive_hash_index` | evaluate (often off) | Contention on busy servers |

## 15.6 PostgreSQL vs MySQL/InnoDB at a glance

| Aspect | PostgreSQL | MySQL / InnoDB |
|---|---|---|
| Table storage | Heap (unordered) + separate indexes | Clustered B+Tree on PK |
| Secondary index → row | ctid (physical) | Primary key value (2nd descent) |
| MVCC old versions | In heap; VACUUM | Undo log; purge |
| Default isolation | READ COMMITTED | REPEATABLE READ (with gap/next-key locks) |
| Serializable | SSI (optimistic, aborts) | Locking (SELECT → FOR SHARE) |
| Rollback cost | Instant | Proportional to work done |
| DDL transactional | Yes (mostly) | Atomic DDL, not transactional with DML |
| Partial / expression indexes | Yes / yes | No partial; functional indexes (8.0.13+) |
| Index types | B-tree, Hash, GIN, GiST, SP-GiST, BRIN, extensions | B-tree, FULLTEXT, SPATIAL (+ multi-valued JSON) |
| Covering indexes | `INCLUDE`, index-only scans (visibility map) | Any index covering the query ("Using index"), PK appended |
| Join algorithms | Nested loop, hash, merge | Nested loop (+block), hash (8.0.18+) |
| Replication | WAL physical streaming + logical | Binlog (row) + GTID, Group Replication |
| Connections | Process per connection → pooler essential | Thread per connection |
| Maintenance burden | Autovacuum tuning, bloat, XID age | Purge/history length, optimize/online DDL |
| Strengths | Rich SQL, extensibility, planner sophistication | Simple PK-centric OLTP, mature replication tooling |

## 15.7 Monitoring query pack (save these)

```sql
-- 1. Long transactions / idle in transaction
SELECT pid, usename, state, now()-xact_start AS xact_age, left(query,80) FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 20;

-- 2. Blocked sessions and their blockers
SELECT a.pid, pg_blocking_pids(a.pid) AS blocked_by, now()-a.query_start AS waiting, left(a.query,60) FROM pg_stat_activity a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0;

-- 3. Cache hit ratio per database (treat with suspicion; watch absolute reads too)
SELECT datname, round(100.0*blks_hit/nullif(blks_hit+blks_read,0),2) AS hit_pct FROM pg_stat_database;

-- 4. Tables with heavy seq scans and dead tuples
SELECT relname, seq_scan, seq_tup_read, idx_scan, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables ORDER BY seq_tup_read DESC LIMIT 20;

-- 5. Biggest tables and indexes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total, pg_size_pretty(pg_relation_size(relid)) AS heap
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;

-- 6. Transaction-ID age (wraparound safety)
SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY 2 DESC;

-- 7. Replication slots retaining WAL
SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal FROM pg_replication_slots;

-- 8. Replication lag
SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;

-- 9. Checkpoint pressure (PG ≤16: pg_stat_bgwriter; PG17+: pg_stat_checkpointer)
SELECT * FROM pg_stat_bgwriter;

-- 10. Deadlocks & conflicts
SELECT datname, deadlocks, conflicts, temp_files, pg_size_pretty(temp_bytes) FROM pg_stat_database;
```

## 15.8 Glossary

* **Page / block** — fixed-size unit of storage and I/O (8 KB PG, 16 KB InnoDB).
* **Heap** — unordered table storage (PostgreSQL). **Clustered index** — table stored as a B+Tree on the PK (InnoDB).
* **Fan-out** — children per B+Tree node; determines height.
* **Selectivity** — fraction of rows a predicate matches. **Cardinality** — distinct values.
* **Sargable** — a predicate form an index can be used for (`col op constant`).
* **Covering index / index-only scan** — query answered from the index alone.
* **HOT** — heap-only tuple update (no index maintenance).
* **MVCC** — multi-version concurrency control. **Snapshot** — the set of versions visible to a transaction.
* **xmin / xmax** — creating / deleting transaction ids on a PG tuple. **Dead tuple** — a version no snapshot can see.
* **VACUUM** — cleans dead versions, freezes old xids. **Bloat** — wasted space from dead tuples / sparse pages.
* **WAL / redo log** — append-only log of changes. **LSN** — position in WAL. **Checkpoint** — flush point bounding recovery.
* **PITR** — point-in-time recovery from base backup + WAL. **RPO / RTO** — tolerable data loss / downtime.
* **Primary / replica / standby** — writer / read copies. **Replication slot** — server-side bookmark retaining WAL for a consumer.
* **Write skew** — anomaly from disjoint writes based on overlapping reads. **Phantom** — new rows matching an earlier range query.
* **Deadlock** — cycle of lock waits. **Gap lock / next-key lock** — InnoDB range locks.
* **Outbox** — table written in the same transaction as business data to reliably publish events. **Idempotency key** — client-supplied unique token making retries safe.
* **CBO** — cost-based optimizer. **Cardinality estimate** — predicted rows at a plan node.

## 15.9 "You understand this material when you can…" (self-assessment)

- [ ] Draw a 3-level B+Tree, show an insert causing a leaf split and a root split, and compute fan-out and height for a given page/key size.
- [ ] Explain why `(a, b)` and `(b, a)` differ, and design an index for a query with equality, sort and range using ESR — and say when you'd *not* add `status`.
- [ ] Predict, before running, whether the planner will use Index / Bitmap / Seq scan for a given selectivity, and what changes it (correlation, `random_page_cost`).
- [ ] Read an `EXPLAIN (ANALYZE, BUFFERS)` and locate the lowest node where estimate ≠ actual; compute true node cost from `loops`.
- [ ] Classify any slow query as *too much work* vs *waiting*, and name the first three commands you'd run.
- [ ] State, for PG and InnoDB, what each isolation level prevents, and construct a write-skew example and three fixes.
- [ ] Explain MVCC in both engines (where versions live, who cleans them, what long transactions break).
- [ ] Walk through a commit from client to durable state and a crash recovery from checkpoint to ready state.
- [ ] Choose between sync/async replication, logical/physical, and justify RPO/RTO with a topology diagram; handle read-your-writes.
- [ ] Design a checkout/inventory flow that cannot oversell, survives retries and failover, and prove it with an invariant test.
- [ ] Run a zero-downtime schema change on a billion-row table without a lock-queue outage.
- [ ] Say *no* to an unnecessary index, cache, replica, or shard — with numbers.

## 15.10 A 30-day study plan

| Days | Focus | Do |
|---|---|---|
| 1–3 | Pages, heap vs clustered, buffer pool (Ch. 1) | Lab 1; compute table/index sizes for your own production tables |
| 4–6 | B+Trees (Ch. 2) | Lab 10 and all four exercises; derive fan-out for your own key types |
| 7–9 | Index types, composite, selectivity (Ch. 3–4) | Labs 2 and 3; audit one real table's indexes with `pg_stat_user_indexes` |
| 10–12 | Planner and EXPLAIN (Ch. 5–6) | Read 20 real plans; fill in a "estimate vs actual" log; Lab 9 |
| 13–15 | Slow-query playbook (Ch. 7) | Install `pg_stat_statements` + `auto_explain` on staging; fix the top 3 queries; write the PR with before/after plans |
| 16–19 | Transactions, MVCC, locks (Ch. 8) | Labs 4, 5, 6, 13 (Go: Lab 12); write a design note for one real race condition in your codebase |
| 20–22 | WAL and recovery (Ch. 9) | Lab 7; **do a real restore drill** and time it |
| 23–25 | Replication (Ch. 10) | Lab 8; implement read-your-writes in your Django project |
| 26–28 | Production case study (Ch. 11) | Redo the capacity math for your own system; Lab 11 |
| 29–30 | Interviews (Ch. 14) | Whiteboard Q1 out loud, timed; then Q3 and Q6 |

## 15.11 Further reading (in the order I'd read them)

1. **Use The Index, Luke!** (Markus Winand, free online) — indexing from first principles; SQL-engine agnostic with PG/MySQL notes.
2. **PostgreSQL documentation** — chapters *Indexes*, *Concurrency Control*, *Performance Tips*, *Reliability and the Write-Ahead Log*, *High Availability, Load Balancing, and Replication*. Dense, accurate, and underrated.
3. **The Internals of PostgreSQL** (Hironobu Suzuki, interdb.jp, free) and **PostgreSQL 14 Internals** (Egor Rogov, free PDF from Postgres Professional) — the best deep dives on MVCC, vacuum, WAL, planner.
4. **Designing Data-Intensive Applications** (Martin Kleppmann) — storage engines, replication, transactions, consistency; the conceptual spine.
5. **Database Internals** (Alex Petrov) — B-trees, LSM trees, recovery, distributed protocols in implementation detail.
6. **CMU 15-445/645 Intro to Database Systems** and **15-721 Advanced Database Systems** (Andy Pavlo, lectures free on YouTube) — structured university-level course material.
7. **High Performance MySQL** (Schwartz et al.) and the **MySQL 8 Reference Manual** chapters on InnoDB locking, transactions, and the optimizer — for your MySQL production systems.
8. **Papers:** *ARIES* (Mohan et al.) — recovery; *A Critique of ANSI SQL Isolation Levels* (Berenson et al.) — why the standard levels are inadequate; *Serializable Snapshot Isolation in PostgreSQL* (Ports & Grittner) — how SSI works; *The Log-Structured Merge-Tree* (O'Neil et al.).
9. **Hermitage** (Martin Kleppmann, GitHub `ept/hermitage`) — test suites showing exactly which anomalies each engine permits at each isolation level.
10. **Jepsen** analyses (jepsen.io) — a masterclass in how real systems fail under partitions and concurrency.

---

### Closing advice from your mentor

The goal of this document is not memorization; it is a **mental model that lets you predict**: *what will the planner do, what will this lock block, what survives a crash, what does this replica show right now.* When you can predict, you can decide — and when you can decide with numbers, you stop adding indexes, caches and replicas by superstition.

Do the labs. Break things on purpose. Keep a notebook of *predictions vs outcomes*. After a month of that you will have more real database intuition than most engineers acquire in years of "it works in production, don't touch it."

*End of document.*
