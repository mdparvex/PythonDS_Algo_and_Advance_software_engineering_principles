# Columnar Databases — A Technical Guide (with ClickHouse)

> A practical, production-oriented guide to columnar storage and columnar databases, using
> **ClickHouse** as the running example throughout. All SQL examples are ClickHouse SQL unless
> noted otherwise.
>
> **Core idea:** row-oriented databases store a record together on disk; columnar databases store
> each field together across every record. That single decision changes almost everything else
> about how the database is built and what it's good at.

---

## Table of Contents

1. [The Problem Columnar Storage Solves](#1-the-problem-columnar-storage-solves)
2. [Row-Oriented vs. Column-Oriented Storage](#2-row-oriented-vs-column-oriented-storage)
3. [Why Columnar Layout Enables Better Compression](#3-why-columnar-layout-enables-better-compression)
4. [Why Columnar Layout Enables Faster Scans](#4-why-columnar-layout-enables-faster-scans)
5. [The Trade-off: What Columnar Is Bad At](#5-the-trade-off-what-columnar-is-bad-at)
6. [ClickHouse Architecture Overview](#6-clickhouse-architecture-overview)
7. [The MergeTree Engine Family](#7-the-mergetree-engine-family)
8. [Creating a Table](#8-creating-a-table)
9. [The Primary Key Is Not What You Think](#9-the-primary-key-is-not-what-you-think)
10. [How Merges Work](#10-how-merges-work)
11. [Choosing an Engine Variant](#11-choosing-an-engine-variant)
12. [Data Types and Why They Matter More Here](#12-data-types-and-why-they-matter-more-here)
13. [Compression Codecs](#13-compression-codecs)
14. [Inserting Data Correctly](#14-inserting-data-correctly)
15. [Materialized Views](#15-materialized-views)
16. [Sharding and Distributed Tables](#16-sharding-and-distributed-tables)
17. [Replication](#17-replication)
18. [Query Patterns That Work Well](#18-query-patterns-that-work-well)
19. [Query Patterns That Work Poorly](#19-query-patterns-that-work-poorly)
20. [Monitoring and Observability](#20-monitoring-and-observability)
21. [Common Production Pitfalls](#21-common-production-pitfalls)
22. [ClickHouse vs. Other Columnar Systems](#22-clickhouse-vs-other-columnar-systems)
23. [When *Not* to Use a Columnar Database](#23-when-not-to-use-a-columnar-database)
24. [Production Checklist](#24-production-checklist)
25. [Summary](#25-summary)

---

# 1. The Problem Columnar Storage Solves

Consider a table of 500 million order events, and a dashboard query that needs one thing: total
revenue by day, for the last 90 days.

```sql
SELECT toDate(created_at) AS day, sum(amount)
FROM orders
WHERE created_at >= now() - INTERVAL 90 DAY
GROUP BY day;
```

This query touches exactly **two columns** — `created_at` and `amount` — out of what might be 40
columns on the `orders` table (customer name, shipping address, payment method, notes, item list,
and so on). A traditional row-oriented database still has to read every one of those 40 columns for
every matching row, because a row is stored as one contiguous block on disk; there is no way to
fetch `amount` without also pulling `shipping_address` and everything else along with it.

```text
Row-oriented disk layout (simplified):

Row 1: [id][created_at][customer_name][shipping_address][amount][payment_method][notes]...
Row 2: [id][created_at][customer_name][shipping_address][amount][payment_method][notes]...
Row 3: [id][created_at][customer_name][shipping_address][amount][payment_method][notes]...

To read "amount" for 500M rows, you still read all 40 columns' worth of bytes for each row.
```

For analytical queries — aggregations over millions or billions of rows, touching a handful of
columns — this means reading 10-40x more data from disk than the query actually needs. Columnar
storage exists specifically to eliminate that waste.

---

# 2. Row-Oriented vs. Column-Oriented Storage

A columnar database physically stores each column's values contiguously, separate from every other
column.

```text
Column-oriented disk layout (simplified):

created_at column: [t1][t2][t3][t4][t5]...[t500,000,000]
amount column:      [a1][a2][a3][a4][a5]...[a500,000,000]
customer_name col:  [c1][c2][c3][c4][c5]...[c500,000,000]
...
```

The same revenue-by-day query now reads only the `created_at` and `amount` columns from disk —
nothing else exists to read. This single structural change is the source of nearly every
performance characteristic discussed in this document.

| | Row-oriented (PostgreSQL, MySQL) | Column-oriented (ClickHouse, BigQuery, Redshift) |
|---|---|---|
| Physical layout | One row's fields stored together | One column's values stored together |
| Reads for `SELECT amount FROM orders` | All columns of every scanned row | Only the `amount` column |
| Best at | Fetching/updating whole records: "get order #42," "update this row" | Aggregating over few columns, many rows: "sum revenue by day" |
| Worst at | Full-table scans over many columns | Fetching one whole record repeatedly ("get order #42" by primary key, one at a time) |
| Typical workload | OLTP (transaction processing) | OLAP (analytical processing) |

This is not "columnar is better" — it is a different physical layout optimized for a different
access pattern. Section 5 covers exactly what columnar gives up in return.

---

# 3. Why Columnar Layout Enables Better Compression

Storing a column contiguously does more than reduce bytes *read* — it also dramatically improves
how well those bytes *compress*, because adjacent values in a single column tend to be far more
similar to each other than adjacent fields within a row.

```text
A single row (heterogeneous, compresses poorly as a unit):
  [8821][2026-09-14][ "Jane Doe" ][ "Dhaka, Bangladesh" ][49.99][ "credit_card" ]

One column, 8 consecutive values (homogeneous, compresses very well):
  payment_method: "credit_card","credit_card","credit_card","bkash","credit_card","bkash",...
```

A column of `payment_method` values has only a handful of distinct strings repeated millions of
times — this is close to a best case for dictionary encoding and general-purpose compressors.
A column of `created_at` timestamps is often nearly sorted and increases steadily — a near-best
case for delta encoding. Neither pattern is visible to a compressor when it's interleaved with
unrelated fields in a row-oriented layout.

In practice, this is why ClickHouse tables routinely compress 5-10x smaller than the equivalent row
store, sometimes more for low-cardinality or naturally sorted columns. Smaller data on disk also
means less I/O per query — compression and scan speed compound rather than trade off against each
other. See Section 13 for choosing specific codecs.

---

# 4. Why Columnar Layout Enables Faster Scans

Beyond "fewer bytes to compress," a columnar layout is a much better fit for how modern CPUs
actually execute code.

- **Vectorized execution.** ClickHouse processes columns in batches ("chunks" of a few thousand
  values at a time) rather than one row at a time. Operating on a contiguous array of same-typed
  values lets the CPU use SIMD instructions to apply an operation (a comparison, a sum) to many
  values in a single instruction, instead of branching per row.
- **Better cache locality.** A contiguous run of `amount` values fits far more usefully into CPU
  cache than a scattering of `amount` fields separated by unrelated bytes from other columns.
- **Cheap column pruning.** The query planner can skip reading a column's files entirely if the
  query never references it — there's no equivalent "skip a field" operation possible in a
  row-oriented layout, because a field can't be read independently of its row.

These effects combine with the storage-level pruning covered in Section 9 (skip index) — fewer
bytes are read from disk, and the bytes that are read are processed far faster once they're in
memory.

---

# 5. The Trade-off: What Columnar Is Bad At

None of the above comes for free. The same layout that makes "sum a column over a billion rows"
fast makes other, equally common operations slow or awkward.

```text
"Get the full order record for order_id = 8821"

Row store:    one seek, one contiguous read — the whole row is together.
Column store: one seek PER COLUMN — reassembling a full row means touching
              every column file and stitching the pieces back together.
```

Concretely, columnar databases are a poor fit for:

- **Point lookups by a single record's ID**, fetched one at a time, at high frequency (a typical
  web request path: "load this user's profile"). This is what row stores like PostgreSQL or MySQL
  are built for.
- **Frequent single-row updates or deletes.** ClickHouse's `ALTER TABLE ... UPDATE/DELETE` are
  heavyweight, asynchronous, background-rewrite operations (Section 10) — not the cheap in-place
  row update a transactional database performs.
- **Transactional guarantees.** ClickHouse does not provide multi-statement ACID transactions in
  the way a traditional RDBMS does; it is built for append-heavy analytical ingestion, not for
  being the system of record for, say, a bank balance.
- **High-concurrency small writes.** ClickHouse is designed around **large, infrequent batch
  inserts** (thousands of rows per insert), not thousands of individual single-row `INSERT`
  statements per second (Section 14).

The practical rule of thumb: **use a row store for OLTP (the system your application writes to on
every user action), and a columnar store for OLAP (the system your dashboards and analysts query)**
— and move data from the former to the latter, rather than trying to make one system do both well.

---

# 6. ClickHouse Architecture Overview

```text
                    Client (HTTP, native TCP, or MySQL/PostgreSQL wire protocol)
                                       |
                                       v
                          +------------------------+
                          |    ClickHouse Server    |
                          |                          |
                          |  Query parser/planner    |
                          |  Vectorized execution     |
                          |  Table engines            |
                          +------------+-------------+
                                       |
                     +-----------------+-----------------+
                     |                                   |
                     v                                   v
           +------------------+               +--------------------+
           |  Local disk       |               |  Object storage     |
           |  (default)        |               |  (S3/GCS/Azure,     |
           |  column files per |               |   optional tiering) |
           |  table part       |               +--------------------+
           +------------------+

For multi-node deployments:

  Shard 1 (subset of data)  --+
  Shard 2 (subset of data)  --+---> queried together via a Distributed table
  Shard N (subset of data)  --+           (Section 16)

  Each shard can have replicas for durability/read scaling (Section 17),
  coordinated via ClickHouse Keeper (or ZooKeeper) for replicated engines.
```

A single ClickHouse node is already a complete, highly capable analytical database — sharding and
replication (Sections 16-17) are things you add when data volume or availability requirements
demand them, not things every deployment needs from day one.

---

# 7. The MergeTree Engine Family

`MergeTree` is the storage engine that gives ClickHouse tables their core properties: sorted
on-disk storage, background merging of newly inserted data, and the sparse primary index described
in Section 9. Almost every production ClickHouse table uses `MergeTree` or one of its variants
(Section 11).

```text
INSERT -> writes a new "part" (a self-contained mini table: one folder per column, sorted)

Part 1 (100,000 rows, sorted by ORDER BY key)
Part 2 (50,000 rows, sorted by ORDER BY key)
Part 3 (200,000 rows, sorted by ORDER BY key)
        |
        | background merge process, continuously
        v
Merged, larger part (350,000 rows, still sorted)
```

Each `INSERT` creates an immutable **part** on disk. A background merge process continuously
combines smaller parts into larger ones (similar in spirit to LSM-tree compaction), which is also
where `ReplacingMergeTree`/`SummingMergeTree` variants (Section 11) actually apply their
deduplication or aggregation logic — **only when parts merge**, not at insert time or query time.
This is precisely why those engines require you to understand merge timing, not just table syntax.

---

# 8. Creating a Table

```sql
CREATE TABLE orders
(
    order_id      UInt64,
    customer_id   UInt64,
    created_at    DateTime,
    amount        Decimal(10, 2),
    payment_method LowCardinality(String),
    status        Enum8('pending' = 1, 'paid' = 2, 'shipped' = 3, 'cancelled' = 4)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (customer_id, created_at)
SETTINGS index_granularity = 8192;
```

Reading this table definition top to bottom:

- **`ENGINE = MergeTree`** — the storage engine (Section 7).
- **`PARTITION BY toYYYYMM(created_at)`** — splits data into physically separate directories per
  month. This is a coarse, structural split (mainly useful for efficiently dropping old data —
  `ALTER TABLE orders DROP PARTITION '202501'` is nearly instant), and is a *different* mechanism
  from the sort/index key below. Don't confuse the two.
- **`ORDER BY (customer_id, created_at)`** — the physical sort order of every part, and the basis
  of the sparse primary index (Section 9). This is the single most important design decision for
  query performance on this table.
- **`SETTINGS index_granularity = 8192`** — the sparse index (Section 9) stores one entry per 8,192
  rows by default; this is rarely changed.

---

# 9. The Primary Key Is Not What You Think

Coming from PostgreSQL or MySQL, `ORDER BY` in a `CREATE TABLE` looks like it's just for output
ordering. In ClickHouse it defines the **primary key** and the physical sort order of the data on
disk — and ClickHouse's primary key works nothing like a B-tree index in a row-oriented database.

```text
Traditional B-tree index: one entry PER ROW, points directly to that row's location.

ClickHouse sparse index: one entry per GRANULE (a block of index_granularity rows,
                          default 8192), storing only the first row's key values in that granule.

Index (sparse, tiny — fits in memory easily):
  granule 0: (customer_id=1,   created_at=2026-01-01) -> rows 0..8191
  granule 1: (customer_id=104, created_at=2026-01-03) -> rows 8192..16383
  granule 2: (customer_id=204, created_at=2026-01-02) -> rows 16384..24575
  ...
```

A query filtering on `customer_id` doesn't look up "the row" — it uses this sparse index to
identify which *granules* could possibly contain matching rows, then reads only those granules from
disk (a technique ClickHouse calls **index pruning** / "skipping"). Because the index is sparse
(one entry per 8,192 rows, not per row), it stays tiny — often small enough to be held entirely in
memory even for a table with billions of rows.

**The practical consequence:** put the columns you filter on most often — in order of how
selective they are, and in the order queries actually filter on them — first in `ORDER BY`. A query
that filters on `created_at` alone against a table ordered by `(customer_id, created_at)` cannot
use the index nearly as effectively as one ordered by `(created_at, customer_id)`, because the
index's pruning power depends on the filtered column being a *prefix* of the sort key.

```sql
-- Good fit for ORDER BY (customer_id, created_at):
SELECT * FROM orders WHERE customer_id = 8821;
SELECT * FROM orders WHERE customer_id = 8821 AND created_at >= '2026-01-01';

-- Poor fit for the same ORDER BY — created_at alone is not a prefix of the sort key,
-- so this scans far more granules than necessary:
SELECT * FROM orders WHERE created_at >= '2026-01-01';
```

For secondary filter patterns that don't fit the primary sort key, ClickHouse also supports
lightweight **data skipping indexes** (`minmax`, `set`, `bloom_filter`) added per-column, which
provide coarser pruning for columns outside the primary key.

---

# 10. How Merges Work

Understanding merges matters because several ClickHouse table engines derive their entire behavior
from what happens *during* a merge — not at insert or query time.

```text
Part A: (customer_id=1, status='pending', version=1)
Part B: (customer_id=1, status='paid',    version=2)   <- an "update" via ReplacingMergeTree
        |
        | background merge (runs on its own schedule — NOT immediate)
        v
Merged part: (customer_id=1, status='paid', version=2)   <- older version dropped
```

Two things follow directly from this:

- **Merges are asynchronous and not guaranteed to have happened by the time you query.** If you
  query a `ReplacingMergeTree` table immediately after inserting an "update" row, you may still see
  both the old and new versions until the background merge runs (see `FINAL` in Section 11).
- **`OPTIMIZE TABLE ... FINAL`** can force a merge on demand, but it is expensive — it rewrites the
  affected data — and should not be run casually or frequently on large tables in production.

---

# 11. Choosing an Engine Variant

The `MergeTree` family includes several variants that apply special logic **during merges**
(Section 10), each solving a different "I need something other than plain append-only rows" need.

| Engine | What it does | When to use it |
|---|---|---|
| `MergeTree` | Plain sorted storage, no dedup/aggregation | Default choice — immutable event/log data |
| `ReplacingMergeTree(version_column)` | Keeps only the row with the highest `version_column` per sort key, once merged | Modeling "latest state" from a stream of updates (e.g. current order status) |
| `SummingMergeTree(columns)` | Sums numeric columns together for rows sharing the same sort key, once merged | Pre-aggregated counters (e.g. running totals by dimension) |
| `AggregatingMergeTree` | Stores partial aggregate states (via `-State` functions), merged incrementally | Backing store for materialized views doing rollups (Section 15) |
| `CollapsingMergeTree` / `VersionedCollapsingMergeTree` | Cancels out row pairs marked with `+1`/`-1` sign columns | Representing mutable state as an append-only "correction" stream |
| `ReplicatedMergeTree` (and Replicated* variants) | Adds multi-replica replication (Section 17) on top of any of the above | Any production table that needs durability beyond a single node |

**Practical guidance:** default to plain `MergeTree` for raw event data (the most common case by
far). Reach for `ReplacingMergeTree` or `AggregatingMergeTree` specifically when you need
"latest row wins" or incremental rollups, and remember that both depend on background merges having
run — query with `FINAL` (correct but slower) or design your queries to tolerate duplicates/partial
states in the interim (faster, more idiomatic ClickHouse).

```sql
-- ReplacingMergeTree: correct-but-slow way to force deduplication at query time
SELECT * FROM orders_latest FINAL WHERE customer_id = 8821;

-- Idiomatic alternative: let the query itself pick the latest row, without forcing a merge
SELECT * FROM orders_latest
WHERE customer_id = 8821
ORDER BY version DESC
LIMIT 1 BY order_id;
```

---

# 12. Data Types and Why They Matter More Here

Column-store performance is unusually sensitive to type choices, because every byte you save is a
byte saved *for every single value in that column* — the multiplier effect is much larger than in a
row store.

- **Use the narrowest integer type that fits.** `UInt8`/`UInt16`/`UInt32` instead of a default
  `Int64` for small-range values (status codes, small counters) directly shrinks that column's
  on-disk size and the amount read per scan.
- **`LowCardinality(String)`** for any string column with a small number of distinct values
  (country codes, payment methods, categories) — ClickHouse dictionary-encodes it automatically,
  often shrinking that column dramatically and speeding up filters/group-bys on it.
- **`Decimal(P, S)` for money, never `Float64`.** Floating point rounding errors compound across
  aggregation the same way they would anywhere else — this isn't ClickHouse-specific, but it's
  worth stating plainly next to a `sum(amount)` example.
- **Use `DateTime`/`DateTime64` and `Date`, not strings, for timestamps.** Beyond storage
  efficiency, this is what makes `PARTITION BY toYYYYMM(created_at)`-style expressions and time
  range filters efficient in the first place.
- **`Nullable(T)` costs something.** It adds a separate bitmap column tracking nullability per row.
  Prefer a sentinel value (e.g. `0` or an empty string) over `Nullable` for high-volume columns
  where the business meaning of "no value" can be represented that way instead.

---

# 13. Compression Codecs

Beyond the general-purpose codec applied to every column by default (`LZ4` — fast, low CPU
overhead), ClickHouse lets you specify a codec per column, and combining a **specialized encoding**
with a general compressor often beats either alone.

```sql
CREATE TABLE orders
(
    order_id    UInt64      CODEC(Delta, LZ4),
    created_at  DateTime    CODEC(DoubleDelta, LZ4),
    amount      Decimal(10, 2) CODEC(T64, LZ4),
    description String      CODEC(ZSTD(3))
)
ENGINE = MergeTree
ORDER BY (order_id, created_at);
```

| Codec | Good for | Why |
|---|---|---|
| `Delta` | Monotonically increasing values (auto-increment IDs) | Stores differences between consecutive values, which are small and repetitive |
| `DoubleDelta` | Timestamps, especially at regular intervals | Encodes the *change in the delta* — near-zero for evenly spaced time series |
| `T64` | Integer/decimal columns with a limited value range | Bit-packs values into a smaller effective width |
| `ZSTD(level)` | General text, when you want better ratio than LZ4 and can spend more CPU | Higher compression ratio than `LZ4`, slower to compress and decompress |
| `LZ4` (default) | Everything else, or as the second stage after a specialized codec above | Fast decompression — usually the right default when in doubt |

Specialized codecs (`Delta`, `DoubleDelta`, `T64`) are typically layered with `LZ4` or `ZSTD` as a
second pass, as shown above — the specialized codec transforms the data into a more compressible
form, then the general compressor squeezes it further.

---

# 14. Inserting Data Correctly

ClickHouse is built around **large, infrequent batch inserts** — this is not a tuning suggestion,
it is close to a hard architectural requirement.

```text
GOOD:  1 insert of 50,000 rows every few seconds
BAD:   50,000 individual single-row INSERT statements per second
```

Every `INSERT` creates a new part on disk (Section 7), regardless of how many rows it contains.
Thousands of tiny inserts per second create thousands of tiny parts, which:

- Overwhelms the background merge process, which can't keep up with the arrival rate of new tiny
  parts.
- Triggers ClickHouse's built-in protection, `"Too many parts"`, which will start rejecting further
  inserts until merges catch up — a very common first production incident for teams new to
  ClickHouse.

```sql
-- Bad: one row per statement, issued thousands of times per second
INSERT INTO orders VALUES (1, 100, now(), 49.99, 'credit_card', 'paid');

-- Good: batch many rows into a single INSERT
INSERT INTO orders VALUES
    (1, 100, now(), 49.99, 'credit_card', 'paid'),
    (2, 101, now(), 12.50, 'bkash', 'pending'),
    (3, 102, now(), 89.00, 'credit_card', 'paid');
    -- ... thousands more rows in the same statement
```

If your data naturally arrives as a stream of small events (e.g. from Kafka, or individual
application events), buffer and batch them before inserting — either in application code, via
ClickHouse's `Buffer` table engine, or via a dedicated ingestion tool (e.g. `clickhouse-bulk`, or a
Kafka Engine table consuming in batches) — rather than inserting each event as it arrives.

---

# 15. Materialized Views

A ClickHouse materialized view is a trigger, not a cache: it runs a query against every newly
inserted block of data and writes the *result* into a separate target table, incrementally, as data
arrives. It never re-scans historical data on read.

```sql
CREATE TABLE daily_revenue
(
    day    Date,
    total  AggregateFunction(sum, Decimal(10, 2))
)
ENGINE = AggregatingMergeTree
ORDER BY day;

CREATE MATERIALIZED VIEW daily_revenue_mv TO daily_revenue AS
SELECT
    toDate(created_at) AS day,
    sumState(amount)   AS total
FROM orders
GROUP BY day;
```

```sql
-- Querying the pre-aggregated result (fast, regardless of how large `orders` has grown)
SELECT day, sumMerge(total) AS revenue
FROM daily_revenue
GROUP BY day
ORDER BY day;
```

This pattern — an `AggregateFunction` column paired with `-State`/`-Merge` function suffixes — lets
you maintain rollups incrementally on a table with billions of underlying rows, with query latency
that depends only on the (much smaller) size of the aggregated result table, not on the size of
`orders`. The trade-off is the same one covered in Section 10: the materialized view only reflects
data that has already been inserted into the source table — it does not retroactively backfill
existing rows when first created, so backfilling history requires a separate one-time `INSERT ...
SELECT` into the target table.

---

# 16. Sharding and Distributed Tables

A single ClickHouse node can comfortably handle very large datasets — sharding is for when a single
node's disk, memory, or CPU genuinely can't keep up, not a default starting point.

```text
Distributed table "orders_all" (a thin routing layer, stores no data itself)
        |
   +----+----+----+
   |         |         |
   v         v         v
Shard 1   Shard 2   Shard 3     <- each holds a DIFFERENT subset of rows
(orders)  (orders)  (orders)       (the actual local MergeTree tables)
```

```sql
-- On each shard node: the real table
CREATE TABLE orders (...) ENGINE = MergeTree ORDER BY (customer_id, created_at);

-- A Distributed table, typically created on every node, that fans a query out to all shards
CREATE TABLE orders_all AS orders
ENGINE = Distributed(my_cluster, default, orders, rand());
```

Queries against `orders_all` are automatically split across the shards defined in
`my_cluster`, executed in parallel, and the partial results merged. The sharding key
(`rand()` above, or a column like `cityHash64(customer_id)` for a more deterministic distribution)
determines which shard a given row lands on at insert time — choose it to spread data (and query
load) evenly, and consider colocating rows that are frequently joined or grouped together on the
same shard to avoid expensive cross-shard shuffles.

---

# 17. Replication

Replication and sharding are independent concerns: sharding splits data across nodes for scale,
replication copies each shard's data across nodes for durability and read availability.

```text
Shard 1
  ├── Replica A  (holds a full copy of shard 1's data)
  └── Replica B  (holds a full copy of shard 1's data)

Coordinated via ClickHouse Keeper (or ZooKeeper):
  - tracks which parts exist on which replicas
  - coordinates merges so replicas converge on the same result
  - handles replica failure/recovery
```

```sql
CREATE TABLE orders
(
    order_id    UInt64,
    customer_id UInt64,
    created_at  DateTime,
    amount      Decimal(10, 2)
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/orders', '{replica}')
ORDER BY (customer_id, created_at);
```

Any of the `MergeTree` variants from Section 11 has a `Replicated` counterpart
(`ReplicatedMergeTree`, `ReplicatedReplacingMergeTree`, etc.) — replication is an orthogonal layer
added on top of whichever merge behavior you need, not a separate table type to choose instead of
those in Section 11.

---

# 18. Query Patterns That Work Well

- **Aggregations over a small number of columns, across many rows** — the canonical use case
  (Sections 1-4). `SELECT date, sum(amount), count() FROM orders GROUP BY date`.
- **Filtering on a prefix of the sort key** — leans directly on the sparse index (Section 9).
- **`GROUP BY` on low-cardinality columns**, especially ones declared `LowCardinality(String)`
  (Section 12) — dictionary encoding makes grouping on them cheap.
- **Large, wide time-range scans** with column pruning — a query selecting 3 columns out of 50 only
  pays for those 3, regardless of table width.
- **Approximate aggregate functions** (`uniqHLL12`, `quantileTDigest`) when an exact answer isn't
  required — these trade a small, bounded error for dramatically lower memory and CPU cost on
  very large `GROUP BY` cardinalities.

---

# 19. Query Patterns That Work Poorly

- **`SELECT * FROM orders WHERE order_id = 8821`** — a single-row point lookup by an
  unindexed-for-this-purpose key forces scanning every granule unless `order_id` happens to be a
  prefix of `ORDER BY`. This is the wrong tool for "fetch one record by ID" workloads generally
  (Section 5) — that belongs in a row store.
- **Row-by-row `UPDATE`/`DELETE`** — `ALTER TABLE ... UPDATE/DELETE` are asynchronous "mutations"
  that rewrite entire affected parts in the background; they are not a cheap, immediate operation
  like a row-store `UPDATE ... WHERE id = 8821`.
- **Many small, frequent `JOIN`s against large tables**, especially without `LowCardinality` join
  keys — ClickHouse's join implementations are improving but are still generally weaker than a
  mature row-store's, especially for many-to-many joins on large tables. Denormalizing (storing
  the joined value directly in the fact table at insert time) is a common and idiomatic ClickHouse
  pattern precisely because of this.
- **High-frequency single-row inserts** — see Section 14; this degrades the whole table's health,
  not just the query issuing the inserts.
- **Deeply nested transactional business logic** (multi-step, all-or-nothing updates across several
  tables) — ClickHouse does not provide the ACID transaction guarantees this requires.

---

# 20. Monitoring and Observability

ClickHouse exposes most of what you need through system tables — no external agent required to get
started.

```sql
-- Is the background merge process keeping up? (see "Too many parts", Section 14)
SELECT database, table, count() AS active_parts
FROM system.parts
WHERE active
GROUP BY database, table
ORDER BY active_parts DESC;

-- Slowest recent queries
SELECT query, query_duration_ms, read_rows, memory_usage
FROM system.query_log
WHERE type = 'QueryFinish'
ORDER BY query_duration_ms DESC
LIMIT 20;

-- Replication lag / broken replicas (if using ReplicatedMergeTree)
SELECT database, table, is_leader, absolute_delay
FROM system.replicas
WHERE absolute_delay > 0;
```

| Metric | Why it matters | Where to find it |
|---|---|---|
| Active parts per table | Rising sharply signals merges falling behind inserts | `system.parts` |
| Query duration / rows read | Catches queries that fell off the sort-key prefix (Section 9) | `system.query_log` |
| Replica delay | Detects a replica falling behind, before it becomes stale reads | `system.replicas` |
| Merge/mutation queue depth | Backlog of pending background work | `system.merges`, `system.mutations` |
| Memory usage per query | ClickHouse can and will OOM-kill a runaway aggregation | `system.query_log`, `system.metrics` |

---

# 21. Common Production Pitfalls

| Symptom | Usual cause | Fix |
|---|---|---|
| `"Too many parts"` insert errors | High-frequency small inserts (Section 14) | Batch inserts; use a `Buffer` table or upstream batching |
| A query is slow despite filtering | Filter column isn't a prefix of `ORDER BY` (Section 9) | Redesign `ORDER BY`, or add a data-skipping index |
| `ReplacingMergeTree` shows duplicate rows | Merge hasn't run yet (Section 10) | Query with `FINAL`, or use `LIMIT 1 BY` / `argMax` patterns instead |
| Disk fills up unexpectedly | No TTL/cleanup policy on an ever-growing table | Add `TTL` clauses or partition-drop retention (Section 8) |
| Join query is much slower than expected | Large table joined on a high-cardinality, non-`LowCardinality` key | Denormalize at insert time, or restructure the join |
| Materialized view "missing" old data | MVs only process rows inserted after creation (Section 15) | Backfill manually with `INSERT ... SELECT` into the target table |
| Memory spikes / OOM on aggregation queries | Very high-cardinality `GROUP BY` with exact aggregate functions | Use approximate functions (`uniqHLL12`) or tune `max_memory_usage` |

---

# 22. ClickHouse vs. Other Columnar Systems

| | ClickHouse | Amazon Redshift | Google BigQuery | Apache Druid |
|---|---|---|---|---|
| Deployment model | Self-hosted or ClickHouse Cloud | Managed AWS service | Fully managed, serverless | Self-hosted or managed |
| Pricing model | Infrastructure cost (self-hosted) or usage-based (cloud) | Cluster-hours (or serverless usage) | Per-query bytes scanned (or flat-rate slots) | Infrastructure cost |
| Best at | Very low query latency, high ingest throughput, real-time dashboards | Data-warehouse-style BI workloads tightly integrated with the AWS ecosystem | Ad hoc analytics with zero infrastructure management, huge scale | Real-time analytics on streaming event data with sub-second lookups |
| Query language | SQL (with many ClickHouse-specific extensions) | SQL (Postgres-derived) | SQL | SQL (via a query layer) + native JSON-based queries |
| Update/delete support | Weak (async mutations, Section 19) | Reasonable (still not OLTP-grade) | Weak, batch-oriented | Weak, append/rollup-oriented |
| Where it fits in this stack | The analytical store you replicate/ETL into from your OLTP database (e.g. the MySQL/PostgreSQL system in the [Celery + Redis guide](./README_celery_redis.md)) | Same role, if already on AWS | Same role, if avoiding infrastructure management entirely | Overlaps with ClickHouse for streaming/real-time dashboards specifically |

All four are columnar at their core and share the properties described in Sections 1-5; they differ
mainly in operational model (self-hosted vs. managed), pricing, and which workload shape each one
has been most heavily optimized for.

---

# 23. When *Not* to Use a Columnar Database

- **The system of record for your application's transactional data.** If it needs row-level ACID
  transactions, frequent single-row updates, and point lookups by primary key at low latency, use a
  row-oriented database (PostgreSQL, MySQL) — that is what OLTP systems are for, and it is not what
  ClickHouse (or any columnar store) is built to do well (Section 5).
- **Low query/write volume, where a row store's analytics are already fast enough.** If your
  reporting queries against PostgreSQL already return in an acceptable time and your data fits
  comfortably in memory, adding a second database system and an ETL/replication pipeline to feed it
  is added operational cost for a problem you don't have yet.
- **Workloads dominated by joins across many normalized tables**, where denormalization
  (Section 19) isn't practical — a row-oriented warehouse or a system with mature join
  optimization may be a better fit.
- **You need it to also serve as a message queue, cache, or search index.** Columnar databases are
  not a substitute for Redis, Elasticsearch, or a proper queue — resist the urge to make one system
  do everything.

---

# 24. Production Checklist

## Schema design

- [ ] `ORDER BY` reflects the actual, most common query filter pattern — not just "the primary key."
- [ ] `PARTITION BY` is chosen for data lifecycle management (e.g. dropping old months), not as a
      substitute for the primary key.
- [ ] Column types are as narrow as correctness allows (Section 12).
- [ ] `LowCardinality(String)` is applied to low-cardinality string columns.
- [ ] Specialized codecs are applied where the value distribution clearly benefits (Section 13).

## Ingestion

- [ ] Inserts are batched (thousands of rows per `INSERT`), not issued per-row (Section 14).
- [ ] A buffering strategy exists for naturally streaming data sources.
- [ ] `"Too many parts"` is monitored, not just discovered when inserts start failing.

## Query design

- [ ] Dashboards and reports filter on a prefix of the table's `ORDER BY` where possible.
- [ ] Joins on large tables use `LowCardinality` keys or are avoided via denormalization.
- [ ] Approximate aggregate functions are used where exact cardinality isn't required.

## Operations

- [ ] Merge/mutation queues and active part counts are monitored (Section 20).
- [ ] TTL or partition-drop retention exists for tables that shouldn't grow unbounded.
- [ ] If replicated: replica delay is monitored and alerted on (Section 17).
- [ ] Materialized view backfill was performed explicitly for any historical data (Section 15).

---

# 25. Summary

Row-oriented and column-oriented databases are not competing implementations of the same idea —
they are different physical layouts, each a near-ideal fit for a different access pattern, and a
poor fit for the other's.

```text
Row-oriented:                          Column-oriented:
  Optimized for                          Optimized for
  "give me this whole record"            "give me this one field,
                                           for every record"
        |                                        |
        v                                        v
   OLTP: your application's                OLAP: your dashboards,
   transactional database                  reports, and analytics
```

ClickHouse (and columnar systems generally) earn their performance specifically by reading less
data per query (column pruning, Section 4), compressing what remains more effectively (Section 3),
and processing it in a way that suits modern CPUs (vectorized execution, Section 4) — in exchange
for weak point-lookup performance, weak transactional guarantees, and an insert model built around
large batches rather than frequent small writes (Section 5).

The practical architecture this leads to, in almost every production system: **keep your row store
as the system of record for transactional writes, and replicate or stream data into a columnar
store for everything analytical** — never try to make one system be excellent at both.
