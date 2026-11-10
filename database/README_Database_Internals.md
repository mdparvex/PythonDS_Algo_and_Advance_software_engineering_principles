# Database Internals for Backend Engineers

A practical, architecture-first guide to B+ Trees, storage engines,
query execution, transactions, recovery, and query optimization.

> **Audience:** Backend engineers with roughly 3--5 years of experience
> who already build APIs and work with relational databases.
>
> **Primary database:** PostgreSQL. MySQL/InnoDB and Redis are used for
> comparison where useful.
>
> **Goal:** Build a mental model that lets you predict database
> behavior, diagnose production incidents, and make defensible design
> decisions---not merely memorize database terminology.

------------------------------------------------------------------------

## Table of contents

1.  [How to use this guide](#1-how-to-use-this-guide)
2.  [The database's place in a backend
    request](#2-the-databases-place-in-a-backend-request)
3.  [Pages, rows, and storage
    engines](#3-pages-rows-and-storage-engines)
4.  [B+ Trees and indexes](#4-b-trees-and-indexes)
5.  [Query execution](#5-query-execution)
6.  [Query optimization and planner
    decisions](#6-query-optimization-and-planner-decisions)
7.  [Transactions and ACID](#7-transactions-and-acid)
8.  [Concurrency control: locks and
    MVCC](#8-concurrency-control-locks-and-mvcc)
9.  [Database recovery and
    durability](#9-database-recovery-and-durability)
10. [Production-scale design and failure
    scenarios](#10-production-scale-design-and-failure-scenarios)
11. [Practical PostgreSQL lab](#11-practical-postgresql-lab)
12. [Python experiments](#12-python-experiments)
13. [MySQL/InnoDB and Redis
    comparisons](#13-mysqlinnodb-and-redis-comparisons)
14. [Common engineering mistakes](#14-common-engineering-mistakes)
15. [Decision-making checklist](#15-decision-making-checklist)
16. [System design interview
    exercise](#16-system-design-interview-exercise)
17. [Learning sequence and
    references](#17-learning-sequence-and-references)

------------------------------------------------------------------------

# 1. How to use this guide

Do not try to memorize the entire document in one sitting. Work through
one mechanism at a time:

1.  Read the concept and draw the diagram yourself.
2.  Predict what the database will do before running a query.
3.  Run the experiment against a disposable PostgreSQL instance.
4.  Inspect `EXPLAIN (ANALYZE, BUFFERS)`, locks, and table statistics.
5.  Change one variable---data distribution, index, query shape, or
    concurrency---and predict the result again.
6.  Write down the operational trade-off, not just the SQL syntax.

The most useful habit is to ask:

-   What data must be read or changed?
-   How many pages might be touched?
-   Is the operation CPU-, memory-, or I/O-bound?
-   What does the optimizer know about the data?
-   Which other transactions can observe or modify the same records?
-   What happens if the process, host, or storage device fails at this
    exact point?

## The mental model

A relational database is not simply a place where rows are stored. It is
a system that coordinates:

-   A **storage engine** that represents data as pages and manages
    files.
-   **Indexes** that reduce the amount of data that must be searched.
-   A **query processor** that parses, rewrites, plans, and executes
    SQL.
-   A **transaction manager** that gives concurrent operations defined
    behavior.
-   A **recovery system** that makes committed changes survive failures.
-   A **planner/statistics system** that estimates the cost of
    alternative execution strategies.

These subsystems interact. For example, adding an index can make a read
faster but make writes slower, increase storage, change vacuum behavior,
and even cause the planner to choose a worse plan if statistics are
stale.

------------------------------------------------------------------------

# 2. The database's place in a backend request

Consider a Django endpoint:

``` python
def get_customer_orders(request):
    return Order.objects.filter(
        customer_id=request.user.id,
        status="delivered",
    ).order_by("-created_at")[:20]
```

The application expresses *what* it wants. PostgreSQL decides *how* to
retrieve it.

``` text
Client
  |
  v
Load balancer / API gateway
  |
  v
Django / FastAPI application
  |
  | SQL + parameters over a database connection
  v
PostgreSQL backend process
  |
  +--> Parse and validate SQL
  |
  +--> Rewrite query
  |
  +--> Planner: estimate rows and costs
  |
  +--> Executor: run chosen plan
  |       |
  |       +--> Buffer manager / shared buffers
  |       +--> Index access method
  |       +--> Heap/table pages
  |       +--> Lock and visibility checks
  |
  +--> Return rows through the connection
  |
  v
Serializer / response
  |
  v
Client
```

The database may satisfy a read from memory, or it may need to read
pages from storage. A query returning 20 rows can still read thousands
of pages if the access path is poor.

### Why this matters to API engineers

A slow endpoint is not necessarily caused by slow Python. It may be
caused by:

-   An index that does not match the filter and ordering.
-   A sequential scan over a large relation.
-   A join that multiplies rows.
-   A bad cardinality estimate.
-   Lock contention.
-   Too many round trips (N+1 queries).
-   A cold cache or storage latency.
-   A connection pool exhausted by long-running queries.

The API's response time includes connection acquisition, query
execution, row transfer, object construction, serialization, and network
time. Measure these separately where possible.

------------------------------------------------------------------------

# 3. Pages, rows, and storage engines

## 3.1 Why databases use pages

A database could theoretically read or write each row independently.
Real storage devices and operating systems move data in blocks, and
managing millions of tiny independent I/O operations would be expensive.

Databases therefore group records into fixed-size **pages**. PostgreSQL
commonly uses 8 KiB pages by default (the size is fixed at database
build time). A table is a collection of pages; an index is also a
collection of pages.

``` text
Table relation (conceptual)
+---------+---------+---------+---------+---------+
| Page 0  | Page 1  | Page 2  | Page 3  | Page 4  |
+---------+---------+---------+---------+---------+
     |         |
     v         v
   tuples    tuples
```

A PostgreSQL heap page contains a page header, line-pointer array, free
space, and tuple data. A line pointer identifies where a tuple version
lives inside the page. This indirection helps PostgreSQL move tuple data
within a page without changing every reference to it.

``` text
One PostgreSQL heap page (simplified)
+--------------------------------------+
| Page header                          |
+--------------------------------------+
| Line pointer 1 -> tuple location     |
| Line pointer 2 -> tuple location     |
| Line pointer 3 -> tuple location     |
+--------------------------------------+
| Free space                           |
|                                      |
+--------------------------------------+
| Tuple data ...                       |
| Tuple data ...                       |
+--------------------------------------+
```

A row is not necessarily a single permanent byte sequence. In
PostgreSQL, updates under MVCC generally create a new tuple version. The
old version can remain until it is safe to reclaim.

## 3.2 Heap storage versus clustered storage

PostgreSQL tables are heap-organized: rows are not automatically kept in
primary-key order. An index entry points to a tuple location identified
by a tuple identifier (TID), conceptually a page number plus an item
offset.

InnoDB uses a clustered primary-key organization: the table's leaf pages
are organized by the primary key, and secondary index entries contain
the primary-key value. This difference affects secondary-index size,
primary-key choice, and lookup behavior.

Do not assume that "primary key" means the same physical layout across
database engines.

## 3.3 Buffer pool / shared buffers

Reading a page from storage is much slower than accessing a page already
in memory. PostgreSQL uses shared buffers, while InnoDB has a buffer
pool.

``` text
Executor requests page
        |
        v
  Is page in buffer cache?
      /       \
    yes        no
     |          |
     v          v
  use memory  read page from storage
                  |
                  v
              cache page
                  |
                  v
              use memory
```

The operating-system page cache can also participate. Therefore, "not in
PostgreSQL shared buffers" does not always mean "must read from physical
disk."

**Important:** A cache hit is not free. CPU work, latch coordination,
tuple visibility checks, and memory bandwidth still matter.

## 3.4 Heap bloat and dead tuples

When PostgreSQL updates or deletes rows, old tuple versions may remain
until no active transaction can need them. `VACUUM` marks space reusable
and maintains visibility information; it does not normally compact every
page into a smaller file. `VACUUM FULL` rewrites the table and takes a
stronger lock.

A long-running transaction can prevent cleanup of old versions. This can
cause table and index bloat, more page reads, and increased
backup/storage costs.

### Engineering implications

-   Avoid transactions that remain open while waiting for user input or
    external APIs.
-   Keep batch updates bounded.
-   Monitor dead tuples, autovacuum activity, long-running transactions,
    and table/index growth.
-   Do not run `VACUUM FULL` casually on a busy production table.

------------------------------------------------------------------------

# 4. B+ Trees and indexes

## 4.1 The problem an index solves

Suppose an `orders` table has 50 million rows and the application
executes:

``` sql
SELECT *
FROM orders
WHERE customer_id = 8127;
```

Without an index, PostgreSQL may inspect every table page to find
matching rows. This is a sequential scan: approximately O(N) tuple
checks.

An index is an additional data structure that helps locate matching rows
without examining the entire table. It costs disk space and makes
inserts, updates, and deletes more expensive.

## 4.2 B-Tree versus B+ Tree

A B-Tree is a balanced search tree designed for nodes with many
children. A B+ Tree is a common variant in which internal nodes
primarily guide the search and values/record references are stored at
the leaf level. Leaf pages are commonly linked, making ordered and range
scans efficient.

Database documentation often calls the PostgreSQL access method `btree`;
it is a balanced tree implementation with B-tree-style behavior. It is
useful to understand the B+ Tree model, but do not assume every engine
implements an identical textbook structure.

Simplified example:

``` text
                    [ 40 | 80 ]
                   /     |     \
                  /      |      \
          [10|20|30] [50|60|70] [90|100|110]
              |           |           |
              +-----------+-----------+
                  linked leaf pages
```

For a search key of 60:

1.  Start at the root.
2.  Compare 60 with separator keys 40 and 80.
3.  Follow the middle child.
4.  Search the leaf page.
5.  Return the matching key's row reference(s).

The tree remains balanced as entries are inserted and removed. When a
page fills, the engine may split it and update parent pages.

## 4.3 Why high fan-out matters

A page can hold many index entries. If each internal page has hundreds
of children, a tree indexing millions or billions of keys can remain
only a few levels deep.

For a rough illustration, if fan-out is 200:

-   Level 1: 1 page
-   Level 2: up to 200 pages
-   Level 3: up to 40,000 pages
-   Level 4: up to 8,000,000 pages

This is illustrative, not a promise about a particular database's real
fan-out. Actual capacity depends on key size, page size, tuple overhead,
fill factor, and implementation details.

A lookup touches roughly one page per tree level, plus any heap pages
needed to fetch rows. If upper levels are cached, the physical I/O cost
may be even lower.

## 4.4 Point lookups and range scans

B-Tree indexes support equality and ordered comparisons:

``` sql
-- Point lookup
SELECT * FROM orders WHERE id = 10001;

-- Range lookup
SELECT * FROM orders
WHERE created_at >= TIMESTAMP '2026-11-01'
  AND created_at <  TIMESTAMP '2026-11-08'
ORDER BY created_at;
```

The linked leaf pages make it possible to find the first qualifying key
and then walk forward through the range.

This is why B-Tree indexes are useful for:

-   `=`, `<`, `<=`, `>`, `>=`
-   `BETWEEN`
-   ordered retrieval
-   left-anchored prefix matching in supported collations/operator
    classes
-   many join and uniqueness checks

A normal B-Tree is not the best structure for every search. PostgreSQL
also offers Hash, GIN, GiST, SP-GiST, and BRIN indexes for different
data and operator patterns.

## 4.5 Composite indexes and leftmost-prefix reasoning

Suppose the application frequently runs:

``` sql
SELECT id, created_at, total
FROM orders
WHERE customer_id = 8127
  AND status = 'delivered'
ORDER BY created_at DESC
LIMIT 20;
```

A candidate index is:

``` sql
CREATE INDEX idx_orders_customer_status_created
ON orders (customer_id, status, created_at DESC);
```

The key order matters. A multicolumn B-Tree is most effective when
leading columns are constrained. The index can narrow to one customer's
delivered orders and produce them in the requested order.

An index on `(status, customer_id, created_at)` may be less suitable if
the common query starts with a selective customer filter. Conversely, if
most queries filter by status across all customers, that order may be
useful.

Do not apply "put the most selective column first" mechanically.
Consider the actual workload, equality/range predicates, ordering,
joins, data distribution, and other queries that need the index.

## 4.6 Covering indexes and index-only scans

If a query needs only columns present in an index, PostgreSQL may be
able to use an index-only scan:

``` sql
CREATE INDEX idx_orders_customer_status_created_cover
ON orders (customer_id, status, created_at DESC)
INCLUDE (id, total);
```

`INCLUDE` columns are stored in leaf tuples but are not search-key
columns. They can cover output columns without affecting key ordering.

PostgreSQL still needs visibility information. An index-only scan avoids
heap access only when the visibility map indicates that the relevant
heap page is all-visible. Otherwise, it may visit the heap to check
tuple visibility.

Covering indexes are not automatically better: they increase index size
and write amplification.

## 4.7 Selectivity and the sequential-scan surprise

An index is not always faster. If a query returns 70% of a table,
following index entries and visiting scattered heap pages may cost more
than reading the table sequentially.

The planner compares estimated costs. It may correctly choose a
sequential scan even when an index exists.

Think in terms of **selectivity**:

\[ `\text{selectivity}`{=tex} =
`\frac{\text{matching rows}}{\text{total rows}}`{=tex} \]

A lower fraction is usually more selective, but physical locality and
row width also matter.

## 4.8 Index write costs and page splits

Every additional index must be maintained when relevant rows are
inserted, deleted, or updated. A write may modify:

-   The heap page.
-   One or more index leaf pages.
-   Parent index pages if a split propagates.
-   WAL records needed for recovery.
-   Visibility and free-space metadata over time.

Randomly distributed insert keys can cause page splits across the index.
Monotonically increasing keys tend to concentrate inserts near the right
edge of a B-Tree, which can create a hot area under high concurrency.
Neither pattern is universally best.

PostgreSQL's `fillfactor` can leave free space on pages to reduce page
splits or allow HOT updates in some workloads, but it trades space for
future write flexibility.

## 4.9 Other index types in PostgreSQL

  -------------------------------------------------------------------------
  Index type              Useful for              Example
  ----------------------- ----------------------- -------------------------
  B-Tree                  Equality, ranges,       `customer_id = 5`
                          ordering                

  Hash                    Equality comparisons    `token = 'abc'`

  GIN                     Multi-valued data such  `tags @> ARRAY['sale']`
                          as arrays, JSONB,       
                          full-text               

  GiST                    Geometric, range, and   spatial/range queries
                          extensible operators    

  BRIN                    Very large tables whose append-heavy timestamp
                          values correlate with   table
                          physical order          
  -------------------------------------------------------------------------

Example JSONB GIN index:

``` sql
CREATE INDEX idx_events_payload_gin
ON events USING GIN (payload);
```

A GIN index can accelerate supported JSONB containment queries, but it
is typically larger and more expensive to update than a simple B-Tree.

### When to choose an index

Ask these questions:

1.  Is the query frequent and important?
2.  How many rows does it usually return?
3.  Does it filter, join, sort, or group?
4.  Does the proposed key order match the query?
5.  Will it make writes or storage materially more expensive?
6.  Can a partial or covering index reduce the cost?
7.  Have I measured the actual plan with representative data?

------------------------------------------------------------------------

# 5. Query execution

A SQL statement passes through several stages.

``` text
SQL text
   |
   v
Parser
   |  syntax tree
   v
Analyzer / binder
   |  resolve tables, columns, types, functions
   v
Rewriter
   |  views, rules, transformations
   v
Planner / optimizer
   |  candidate plans + cost estimates
   v
Chosen execution plan
   |
   v
Executor
   |  scan, join, sort, aggregate, limit
   v
Rows returned to client
```

The exact internal names and boundaries vary by database, but this is a
useful conceptual model.

## 5.1 Logical SQL versus physical execution

SQL describes a result, not a step-by-step algorithm.

``` sql
SELECT c.id, COUNT(o.id)
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.created_at >= DATE '2026-11-01'
GROUP BY c.id
HAVING COUNT(o.id) >= 3;
```

The database may choose:

-   A sequential scan or index scan on `orders`.
-   A hash join, nested-loop join, or merge join.
-   A hash aggregate or sort-based aggregate.
-   A sort, or an index-provided ordering.

The optimizer selects a physical plan based on estimated cost.

## 5.2 Common scan operators

-   **Sequential scan:** reads table pages and checks rows. Good for
    small tables or broad scans.
-   **Index scan:** walks an index and fetches matching heap tuples.
-   **Index-only scan:** reads index entries and avoids heap fetches
    when visibility information permits.
-   **Bitmap index/heap scan:** combines index matches into a bitmap,
    then visits heap pages in a more page-oriented order. Useful when
    many scattered rows match.

A bitmap scan can combine multiple indexes with `BitmapAnd` or
`BitmapOr`.

## 5.3 Join algorithms

### Nested-loop join

For each row from the outer input, search the inner input for matches.

``` text
Outer rows
  | row 1 ----> inner lookup
  | row 2 ----> inner lookup
  | row 3 ----> inner lookup
  v
Joined output
```

Excellent when the outer side is small and the inner side has an
appropriate index. Dangerous when both sides are large and the inner
side must be repeatedly scanned.

### Hash join

Build a hash table from one input, then probe it with rows from the
other input.

``` text
Build input --> hash table
                     ^
                     | probe
Probe input ----------+
                     |
                     v
                 joined rows
```

Often effective for equality joins over substantial inputs. The hash
table consumes memory; if it exceeds available memory, the operation may
batch or spill to temporary files.

### Merge join

Both inputs are ordered by the join key. The executor advances through
them in order, matching equal keys.

It can be efficient for large ordered inputs, especially when useful
ordering already exists. Sorting both inputs just for the merge can make
it less attractive.

## 5.4 Sorts, aggregates, and memory

Operations such as `ORDER BY`, `DISTINCT`, and some `GROUP BY` plans may
require sorting or hashing.

PostgreSQL's `work_mem` is a per-operation memory limit, not a
per-connection or per-query global cap. One query can have multiple
memory-consuming nodes, and many concurrent queries can multiply memory
usage. Raising it globally without understanding concurrency can cause
memory pressure.

When a sort or hash operation exceeds its memory budget, it can spill to
temporary disk files. Inspect `EXPLAIN (ANALYZE, BUFFERS)` and logs for
evidence of disk usage.

## 5.5 Read an execution plan

Run:

``` sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM orders
WHERE customer_id = 8127
  AND status = 'delivered'
ORDER BY created_at DESC
LIMIT 20;
```

Important fields:

-   `cost`: planner estimate, not milliseconds.
-   `rows`: estimated output rows.
-   `actual time`: observed execution timing.
-   `actual rows`: observed output rows.
-   `loops`: number of executions of a plan node.
-   `Buffers`: shared/local/temp blocks hit or read/written.
-   `Rows Removed by Filter`: rows examined but rejected at that node.
-   `Heap Fetches`: heap visits during an index-only scan.

A large estimated-versus-actual row-count difference is a clue that
statistics or assumptions may be wrong.

**Caution:** `EXPLAIN ANALYZE` executes the query. Do not run it blindly
on destructive statements or expensive production queries. `EXPLAIN`
without `ANALYZE` does not execute the statement.

------------------------------------------------------------------------

# 6. Query optimization and planner decisions

## 6.1 Cost-based optimization

The planner estimates the cost of candidate plans using statistics and
configuration parameters. It does not know the future; it estimates.

The estimate depends on factors such as:

-   Number of pages and tuples.
-   Column value distribution.
-   Number of distinct values.
-   Null fraction and most-common values.
-   Correlation between logical key order and physical row order.
-   Estimated selectivity of predicates.
-   CPU and I/O cost settings.
-   Join cardinality.

PostgreSQL maintains statistics through `ANALYZE` and autovacuum's
analyze activity.

## 6.2 Cardinality estimation

Cardinality is the estimated number of rows produced by an operation.

If PostgreSQL estimates 10 rows but the operation actually produces
500,000, downstream join and memory choices can be disastrous.

Correlated predicates are especially difficult:

``` sql
WHERE country = 'BD'
  AND city = 'Dhaka'
```

If the planner assumes independence, it may estimate the combined
selectivity incorrectly. PostgreSQL extended statistics can capture some
dependencies:

``` sql
CREATE STATISTICS stats_customer_location
    (dependencies, ndistinct, mcv)
ON country, city
FROM customers;

ANALYZE customers;
```

Extended statistics are not magic; choose the statistics kind that
addresses the observed estimation problem.

## 6.3 Query shape matters

Avoid wrapping indexed columns in functions unless an appropriate
expression index exists:

``` sql
-- Often prevents a normal index on created_at from being used efficiently
WHERE DATE(created_at) = DATE '2026-11-10';

-- Prefer a half-open range
WHERE created_at >= TIMESTAMP '2026-11-10 00:00:00'
  AND created_at <  TIMESTAMP '2026-11-11 00:00:00';
```

For a case-insensitive lookup, consider a normalized column, suitable
collation/operator, or expression index:

``` sql
CREATE INDEX idx_users_lower_email ON users (lower(email));

SELECT id FROM users WHERE lower(email) = lower('A@example.com');
```

The best solution depends on uniqueness requirements, collation, and
application semantics.

## 6.4 Pagination: OFFSET versus keyset

Offset pagination:

``` sql
SELECT id, created_at
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 100000;
```

The database may still need to walk past many rows before returning the
requested page. Large offsets become progressively expensive and can be
unstable when rows are inserted between requests.

Keyset pagination:

``` sql
SELECT id, created_at
FROM orders
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

With a matching index:

``` sql
CREATE INDEX idx_orders_created_id
ON orders (created_at DESC, id DESC);
```

Keyset pagination provides stable forward traversal when the cursor
fields and ordering are designed carefully. It is not a direct
replacement when users need arbitrary page numbers.

## 6.5 N+1 is a round-trip and execution problem

A Django loop that fetches related objects one at a time can generate
hundreds of queries:

``` python
for order in Order.objects.all():
    print(order.customer.email)
```

Use `select_related()` for suitable foreign-key/one-to-one relationships
and `prefetch_related()` for many-to-many or reverse relationships. Then
verify query count and memory use. Prefetching everything can create
large in-memory result sets.

## 6.6 A practical optimization workflow

1.  Identify a user-visible latency or database-load problem.
2.  Capture the exact SQL and representative parameters.
3.  Measure frequency, p50/p95/p99 latency, rows returned, and
    concurrency.
4.  Run `EXPLAIN (ANALYZE, BUFFERS)` with representative data.
5.  Find the expensive node and compare estimated versus actual rows.
6.  Check indexes, statistics, query shape, joins, sorts, and spills.
7.  Change one thing at a time.
8.  Re-run the same workload and compare latency, buffers, CPU, writes,
    and index size.
9.  Validate write-path impact and concurrent behavior.
10. Deploy with monitoring and a rollback plan.

Do not optimize a query only because its SQL looks complicated. Optimize
measured bottlenecks.

------------------------------------------------------------------------

# 7. Transactions and ACID

A transaction groups operations into a logical unit.

Example: transferring money between accounts.

``` sql
BEGIN;

UPDATE accounts
SET balance = balance - 100
WHERE id = 1;

UPDATE accounts
SET balance = balance + 100
WHERE id = 2;

COMMIT;
```

If the process fails before commit, the transaction should not leave
only the debit applied. The database provides the transactional
guarantees.

## 7.1 ACID

-   **Atomicity:** all transactional changes happen, or none do.
-   **Consistency:** a transaction preserves declared constraints and
    application invariants when used correctly.
-   **Isolation:** concurrent transactions behave according to the
    selected isolation semantics.
-   **Durability:** once commit is acknowledged under the configured
    durability guarantees, committed changes survive the failures
    covered by those guarantees.

ACID does not automatically make business logic correct. For example, a
transaction can atomically execute an incorrect balance update.

## 7.2 Constraints are concurrency tools

Prefer database constraints for invariants that must hold regardless of
which application worker performs the write:

``` sql
ALTER TABLE accounts
ADD CONSTRAINT accounts_balance_nonnegative CHECK (balance >= 0);

CREATE UNIQUE INDEX uq_users_email ON users (email);
```

An application-side "check then insert" is unsafe under concurrency
unless the check and write are protected appropriately. A unique
constraint is the final authority.

## 7.3 Isolation levels and anomalies

Common anomalies:

-   **Dirty read:** read another transaction's uncommitted changes.
-   **Non-repeatable read:** read the same row twice and see different
    committed values.
-   **Phantom:** repeat a predicate query and see a different set of
    rows.
-   **Lost update:** concurrent updates overwrite one another's intended
    effect.
-   **Write skew:** concurrent transactions each make a decision based
    on a snapshot, and their combined writes violate a cross-row
    invariant.

PostgreSQL's default isolation level is `READ COMMITTED`. Each statement
sees a snapshot as of the beginning of that statement. PostgreSQL's
`REPEATABLE READ` uses snapshot isolation and prevents many anomalies,
but it can still permit write skew. `SERIALIZABLE` detects dangerous
dependency patterns and may abort a transaction; the application must
retry serialization failures.

Do not assume isolation-level names have perfectly identical behavior
across engines.

## 7.4 Lost update example

Two requests try to decrement inventory:

``` text
Initial stock = 1

Transaction A reads stock = 1
Transaction B reads stock = 1
A computes 1 - 1 = 0
B computes 1 - 1 = 0
A writes 0
B writes 0

Two orders accepted, but only one unit was available.
```

Safer atomic conditional update:

``` sql
UPDATE inventory
SET available_quantity = available_quantity - 1
WHERE product_id = 42
  AND available_quantity >= 1
RETURNING available_quantity;
```

If no row is returned, there was not enough stock. This single statement
avoids the application-level read-modify-write race for this invariant.

Another approach is `SELECT ... FOR UPDATE` followed by validation and
update in one transaction. Choose based on workflow complexity and
contention.

## 7.5 Transaction boundaries in web applications

Keep transactions focused on database work. Avoid holding locks while:

-   Calling a payment provider.
-   Sending email or SMS.
-   Waiting for a user.
-   Uploading a large file.
-   Performing slow CPU-heavy work.

A common pattern is the **transactional outbox**:

1.  In one database transaction, update business state and insert an
    outbox event.
2.  A background worker reads unsent outbox records.
3.  The worker publishes the event and marks it delivered.
4.  Consumers are idempotent because delivery can happen more than once.

This avoids the dual-write problem where the database commits but
publishing to a message broker fails, or vice versa.

------------------------------------------------------------------------

# 8. Concurrency control: locks and MVCC

## 8.1 Why concurrency control exists

A production database serves many requests simultaneously. Without
concurrency control, writes could overwrite one another, reads could
observe inconsistent intermediate states, and constraints could be
violated.

Two broad mechanisms are:

-   **Pessimistic coordination:** locks prevent conflicting operations
    from proceeding simultaneously.
-   **Optimistic/version-based coordination:** transactions work against
    versions/snapshots and validate conflicts.

Real systems combine these mechanisms.

## 8.2 MVCC in PostgreSQL

Multi-Version Concurrency Control (MVCC) lets readers see a consistent
snapshot without generally blocking writers, and writers create new row
versions.

Simplified timeline:

``` text
Time ----->

Transaction A:  BEGIN ---- SELECT row(version 1) -------- COMMIT
Transaction B:       BEGIN ---- UPDATE creates version 2 -- COMMIT

A continues to see the version visible to A's snapshot.
A does not suddenly see B's new version halfway through its transaction.
```

PostgreSQL tuple headers contain transaction visibility metadata. A
transaction's snapshot determines which tuple versions are visible.

An update generally creates a new tuple version rather than overwriting
the old version in place. Old versions become reclaimable only when no
active snapshot can still need them.

### MVCC benefits

-   Readers usually do not block writers.
-   Writers usually do not block ordinary readers.
-   Transactions can work with consistent snapshots.
-   It supports high read concurrency.

### MVCC costs

-   Dead tuple versions consume space until cleanup.
-   Long-running transactions delay cleanup.
-   Updates generate WAL and can modify multiple indexes.
-   Vacuum and visibility-map maintenance are operationally important.

## 8.3 Row locks and `SELECT FOR UPDATE`

For a workflow that must inspect and then modify a row:

``` sql
BEGIN;

SELECT available_quantity
FROM inventory
WHERE product_id = 42
FOR UPDATE;

-- Validate and update while holding the row lock.

UPDATE inventory
SET available_quantity = available_quantity - 1
WHERE product_id = 42;

COMMIT;
```

`FOR UPDATE` locks selected rows against conflicting updates/locks until
transaction end. It does not lock the entire table. Other lock modes and
clauses (`NOWAIT`, `SKIP LOCKED`) support different coordination
patterns.

A job queue can use `SKIP LOCKED` to let workers claim different jobs
without waiting on jobs already claimed:

``` sql
BEGIN;

SELECT id
FROM jobs
WHERE status = 'pending'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 10;

-- Mark selected jobs as processing.

COMMIT;
```

The claim and status update should be in the same transaction. Design
recovery for workers that crash after claiming work.

## 8.4 Deadlocks

A deadlock occurs when transactions wait on each other in a cycle.

``` text
Transaction A locks row 1, waits for row 2
Transaction B locks row 2, waits for row 1

A ---> waits for B
^          |
|          v
+----------+
```

The database detects a deadlock and aborts one transaction. The
application should handle the error and may retry the whole transaction
when safe.

Reduce deadlocks by:

-   Acquiring rows in a consistent order.
-   Keeping transactions short.
-   Avoiding unnecessary locks.
-   Using appropriate indexes so updates do not scan/lock excessive
    rows.
-   Retrying deadlock victims with bounded backoff and idempotent logic.

## 8.5 Optimistic concurrency with version columns

For APIs where collisions are uncommon, a version column can detect
stale writes:

``` sql
UPDATE documents
SET body = :new_body,
    version = version + 1
WHERE id = :id
  AND version = :expected_version;
```

If zero rows are updated, another writer changed the document first.
Return a conflict (often HTTP 409) or ask the client to reload.

This is useful for editing workflows, but it is not a substitute for
database constraints or transactions.

------------------------------------------------------------------------

# 9. Database recovery and durability

## 9.1 The crash problem

Imagine a transaction updates a row. The database changes a page in
memory, tells the client "committed," and then the machine loses power
before the modified page reaches durable storage.

How can the database recover the committed update?

The central idea is **write-ahead logging (WAL)**: log records
describing changes are made durable before the corresponding dirty data
pages are allowed to be considered safely persisted.

## 9.2 WAL sequence

``` text
Transaction modifies a page in shared buffers
                 |
                 v
       WAL record is generated
                 |
                 v
 WAL is flushed to durable storage at commit
                 |
                 v
       COMMIT acknowledged
                 |
                 v
 Dirty data page is written later
                 |
                 v
       Checkpoint advances recovery point
```

The key rule: the WAL needed to recover a changed page must be durable
before that page is written to its data file.

This allows the database to avoid synchronously writing every changed
data page at commit.

## 9.3 Crash recovery

After a crash, PostgreSQL uses WAL and checkpoint information to bring
data files to a consistent state. Conceptually:

1.  Locate the latest usable checkpoint.
2.  Read WAL from the required recovery point.
3.  Redo logged changes as needed.
4.  Make the database consistent and available.
5.  Treat incomplete transactions as uncommitted.

The exact recovery algorithm is more sophisticated than this simplified
sequence.

## 9.4 Checkpoints

A checkpoint establishes a recovery point by ensuring required dirty
buffers have been written and recording checkpoint metadata. Frequent
checkpoints can increase write pressure; infrequent checkpoints can
increase crash-recovery time and WAL retention.

PostgreSQL settings such as `checkpoint_timeout`, `max_wal_size`, and
`checkpoint_completion_target` influence checkpoint behavior. Tune them
based on workload, storage, recovery objectives, and observed
metrics---not by copying a random configuration.

## 9.5 Durability is configurable

In PostgreSQL, `synchronous_commit` affects when commit is acknowledged
relative to WAL flushing. Disabling synchronous commit can improve
throughput but may lose recently acknowledged transactions after a
crash. It does not generally create database corruption; it changes the
durability guarantee.

Replication adds another dimension:

-   **Asynchronous replication:** primary may acknowledge before a
    replica has received the WAL; failover can lose recent transactions.
-   **Synchronous replication:** commit can wait for configured replica
    acknowledgement; this can improve durability guarantees but
    increases latency and can reduce availability depending on
    configuration.

A replica is not a backup. Deletes, accidental updates, and logical
corruption can replicate too.

## 9.6 Backup and point-in-time recovery

A production recovery plan usually combines:

-   Base backups.
-   Continuous WAL archiving.
-   Point-in-time recovery (PITR).
-   Replication for availability.
-   Periodic restore tests.

A backup that has never been restored is an assumption, not a proven
recovery plan.

Define:

-   **RPO (Recovery Point Objective):** maximum acceptable data loss
    measured in time.
-   **RTO (Recovery Time Objective):** maximum acceptable time to
    restore service.

Test the entire restore process, including credentials, network,
encryption keys, extensions, DNS, application configuration, and data
validation.

------------------------------------------------------------------------

# 10. Production-scale design and failure scenarios

Consider a commerce backend with millions of orders and high read/write
traffic.

## 10.1 Example workload

-   Customers list their latest orders.
-   Support agents search orders by phone/order reference.
-   Workers update delivery states.
-   A reporting process aggregates daily sales.
-   Payment webhooks may be retried.
-   Inventory must never become negative.

The same table serves multiple access patterns. One index rarely solves
all of them.

Possible indexes:

``` sql
-- Customer order history
CREATE INDEX idx_orders_customer_created
ON orders (customer_id, created_at DESC, id DESC);

-- Support lookup by external order reference
CREATE UNIQUE INDEX uq_orders_public_reference
ON orders (public_reference);

-- Queue-like lookup by status and creation time
CREATE INDEX idx_orders_status_created
ON orders (status, created_at)
WHERE status IN ('pending', 'confirmed');
```

The partial index is useful only when the query predicate implies the
index predicate. Confirm with `EXPLAIN`.

## 10.2 Hot rows and contention

A single inventory row for a very popular product can become a hotspot.
Many transactions compete to update the same row.

Potential strategies:

-   Keep the critical transaction very short.
-   Use a conditional atomic update.
-   Partition inventory by warehouse or stock location when that matches
    the business model.
-   Use reservation/hold records with expiration for checkout flows.
-   Queue high-contention operations when asynchronous processing is
    acceptable.
-   Consider controlled stock allocation across shards/regions only when
    the consistency model is explicitly designed.

Do not introduce distributed inventory counters merely to avoid a lock
without understanding overselling and reconciliation.

## 10.3 Large-table migrations

Adding an index or changing a column on a large, busy table can affect
availability.

PostgreSQL supports `CREATE INDEX CONCURRENTLY`, which avoids blocking
ordinary writes for the full build, but it takes longer, performs
multiple phases, and can leave an invalid index if it fails. It cannot
run inside a normal transaction block.

A safer migration process:

1.  Measure table size, write rate, and replica lag.
2.  Add nullable columns or compatible schema changes first.
3.  Backfill in bounded batches.
4.  Make application code compatible with both old and new
    representations.
5.  Build indexes using an appropriate online/concurrent method.
6.  Validate constraints.
7.  Switch reads/writes.
8.  Remove obsolete schema only after all application versions are
    compatible.

Never assume a migration that is instant on a development database will
be safe on a table with tens of millions of rows.

## 10.4 Partitioning

Partitioning divides a logical table into smaller physical relations,
often by time or tenant key.

Example monthly range partitioning:

``` sql
CREATE TABLE events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY,
    occurred_at TIMESTAMP NOT NULL,
    payload     JSONB NOT NULL
) PARTITION BY RANGE (occurred_at);

CREATE TABLE events_2026_11
PARTITION OF events
FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
```

Benefits:

-   Partition pruning can avoid irrelevant partitions.
-   Old data can be detached/dropped efficiently.
-   Maintenance can be scoped to partitions.
-   Large time-series workloads can be easier to manage.

Costs and limitations:

-   Queries need predicates compatible with the partition key for
    pruning.
-   Too many partitions increase planning and operational overhead.
-   Unique constraints have partition-key restrictions.
-   Partitioning does not automatically make a query faster.
-   It is not the same as sharding: partitions are generally within one
    database instance.

## 10.5 Read replicas and stale reads

Read replicas can scale read traffic, but replication is commonly
asynchronous. A user who writes and immediately reads from a lagging
replica may not see their own update.

Possible approaches:

-   Route read-after-write traffic to the primary for a short period.
-   Use session consistency/routing tokens.
-   Wait for a replication position to be replayed when strict behavior
    is required.
-   Make the product tolerate eventual consistency where appropriate.

Do not route every read to replicas without classifying consistency
requirements.

## 10.6 Failure scenarios to rehearse

  -----------------------------------------------------------------------
  Failure                 Likely symptom          Engineering response
  ----------------------- ----------------------- -----------------------
  Missing index           High I/O/CPU, slow      Inspect plan; add
                          query                   workload-justified
                                                  index

  Bad row estimate        Wrong join/scan         Refresh stats; inspect
                          strategy                skew/correlation

  Long transaction        Vacuum cannot clean old Find transaction owner;
                          versions                shorten transaction

  Lock contention         Requests wait, pool     Inspect
                          fills                   `pg_stat_activity` and
                                                  lock graph

  Deadlock                One transaction aborted Consistent lock order;
                                                  safe retry

  WAL/storage pressure    Writes stall or disk    Alert, provision
                          fills                   capacity, inspect
                                                  archiving/checkpoints

  Replica lag             Stale reads, delayed    Monitor replay lag;
                          failover                route
                                                  consistency-sensitive
                                                  reads

  Connection storm        Too many backend        Pool connections; cap
                          connections             worker concurrency

  Bad migration           Table lock or write     Online migration plan
                          amplification           and rollback

  Accidental deletion     Data missing on primary PITR/restore; validate
                          and replicas            backup process
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 11. Practical PostgreSQL lab

Use a disposable local database. Do not run destructive experiments on
production.

## 11.1 Start PostgreSQL with Docker

``` bash
docker run --name db-internals-lab \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=internals \
  -p 5432:5432 \
  -d postgres:16
```

Connect:

``` bash
psql "postgresql://postgres:postgres@localhost:5432/internals"
```

## 11.2 Create representative data

``` sql
CREATE TABLE customers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL,
    total NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO customers (email, country, city)
SELECT
    'customer' || n || '@example.test',
    CASE WHEN n % 10 = 0 THEN 'US' ELSE 'BD' END,
    CASE WHEN n % 10 = 0 THEN 'New York'
         WHEN n % 3 = 0 THEN 'Chattogram'
         ELSE 'Dhaka' END
FROM generate_series(1, 100000) AS n;

INSERT INTO orders (customer_id, status, total, created_at, metadata)
SELECT
    1 + (random() * 99999)::bigint,
    (ARRAY['pending', 'confirmed', 'delivered', 'cancelled'])
        [1 + (random() * 3)::int],
    round((10 + random() * 5000)::numeric, 2),
    now() - (random() * interval '365 days'),
    jsonb_build_object('source',
        CASE WHEN random() < 0.5 THEN 'web' ELSE 'mobile' END)
FROM generate_series(1, 1000000);

ANALYZE customers;
ANALYZE orders;
```

The random data is useful for experimentation, but it does not perfectly
model production skew. Later, deliberately create skewed data.

## 11.3 Experiment A: sequential scan versus index scan

``` sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = 8127;
```

Then create an index:

``` sql
CREATE INDEX idx_orders_customer
ON orders (customer_id);

ANALYZE orders;

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = 8127;
```

Observe:

-   Did the plan change?
-   How many rows were estimated and actually returned?
-   How many shared buffers were hit/read?
-   Did the query become faster?
-   What happens when you query a customer with many orders?

Do not use `SET enable_seqscan = off` as a production fix. It is a
diagnostic experiment, not an index strategy.

## 11.4 Experiment B: composite index and ordering

``` sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, created_at, total
FROM orders
WHERE customer_id = 8127
  AND status = 'delivered'
ORDER BY created_at DESC
LIMIT 20;
```

Create:

``` sql
CREATE INDEX idx_orders_customer_status_created
ON orders (customer_id, status, created_at DESC)
INCLUDE (total);
```

Run the plan again. Inspect whether the database avoids an explicit sort
and whether it uses an index-only scan. Remember that `id` is the
primary key but is not necessarily included in this index definition;
PostgreSQL's B-Tree secondary index does not automatically include the
table's primary key as InnoDB does.

If the selected output needs `id`, add it as an included column or
accept heap fetches, then compare index size and performance.

## 11.5 Experiment C: OFFSET versus keyset pagination

``` sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, created_at
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 500000;
```

Create:

``` sql
CREATE INDEX idx_orders_created_id
ON orders (created_at DESC, id DESC);
```

Now test keyset pagination using a real cursor from the previous page:

``` sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, created_at
FROM orders
WHERE (created_at, id) < (:cursor_created_at, :cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Compare buffers and execution time. A fair test uses the same data,
cache state, and equivalent page position.

## 11.6 Experiment D: observe MVCC versions

In session A:

``` sql
BEGIN;
SELECT * FROM orders WHERE id = 1;
-- Keep this transaction open.
```

In session B:

``` sql
UPDATE orders
SET total = total + 1
WHERE id = 1;

COMMIT;
```

Back in session A, run the `SELECT` again. Under PostgreSQL
`READ COMMITTED`, a new statement can see the committed update. Under
`REPEATABLE READ`, the transaction keeps its snapshot.

Inspect:

``` sql
SELECT
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname = 'orders';
```

Repeat updates, then observe dead tuples and vacuum behavior. Statistics
are estimates and may lag.

## 11.7 Experiment E: row locks and `SKIP LOCKED`

Session A:

``` sql
BEGIN;
SELECT id FROM orders WHERE id = 10 FOR UPDATE;
-- Keep transaction open.
```

Session B:

``` sql
BEGIN;
SELECT id FROM orders WHERE id = 10 FOR UPDATE;
-- This waits until A commits or rolls back.
```

Try `NOWAIT` in session B to fail immediately rather than wait:

``` sql
SELECT id FROM orders WHERE id = 10 FOR UPDATE NOWAIT;
```

Then try a queue-like query with `SKIP LOCKED`:

``` sql
SELECT id
FROM orders
WHERE status = 'pending'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 10;
```

Observe how a worker can skip rows another worker has locked. Build a
real job-claiming table to explore the full pattern.

## 11.8 Experiment F: inspect activity and locks

``` sql
SELECT
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    now() - xact_start AS transaction_age,
    query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY xact_start NULLS LAST;
```

Inspect locks:

``` sql
SELECT
    locktype,
    mode,
    granted,
    pid,
    relation::regclass
FROM pg_locks
WHERE pid IS NOT NULL
ORDER BY pid, granted;
```

Use these views during a controlled blocking experiment. Avoid exposing
raw query text to untrusted users because it may contain sensitive
values.

## 11.9 Experiment G: constraints under concurrent writes

Create a table with a unique business key:

``` sql
CREATE TABLE webhook_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_event_id TEXT NOT NULL UNIQUE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

From two sessions, attempt to insert the same `provider_event_id`.
Observe that the unique constraint arbitrates the race. This is the
foundation of idempotent webhook processing.

------------------------------------------------------------------------

# 12. Python experiments

These examples use `psycopg` (version 3). Install:

``` bash
pip install "psycopg[binary]"
```

## 12.1 Measure a query from Python

``` python
import time
import psycopg

DSN = "postgresql://postgres:postgres@localhost:5432/internals"

sql = """
SELECT id, created_at, total
FROM orders
WHERE customer_id = %s
  AND status = %s
ORDER BY created_at DESC
LIMIT 20
"""

with psycopg.connect(DSN) as conn:
    with conn.cursor() as cur:
        start = time.perf_counter()
        cur.execute(sql, (8127, "delivered"))
        rows = cur.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000

print(f"{len(rows)} rows in {elapsed_ms:.2f} ms")
```

This measures client-observed query round-trip plus result transfer and
fetching. It is not a pure server execution measurement. Use
`EXPLAIN ANALYZE` and database metrics to understand server-side work.

## 12.2 Demonstrate safe conditional inventory decrement

``` python
import psycopg

def reserve_one_unit(conn, product_id: int) -> bool:
    row = conn.execute(
        """
        UPDATE inventory
        SET available_quantity = available_quantity - 1
        WHERE product_id = %s
          AND available_quantity >= 1
        RETURNING available_quantity
        """,
        (product_id,),
    ).fetchone()

    return row is not None
```

Call it inside a transaction. The database statement performs the
condition and decrement atomically. Add a check constraint as another
layer of protection:

``` sql
ALTER TABLE inventory
ADD CONSTRAINT inventory_nonnegative
CHECK (available_quantity >= 0);
```

## 12.3 Retry serialization failures safely

At `SERIALIZABLE`, PostgreSQL may abort a transaction with SQLSTATE
`40001`. Retry the *whole transaction*, not just the last statement.
Only retry operations whose external side effects are not repeated or
are idempotent.

``` python
import random
import time
import psycopg
from psycopg.errors import SerializationFailure

def run_with_serialization_retry(operation, attempts=4):
    for attempt in range(attempts):
        try:
            with psycopg.connect(DSN) as conn:
                with conn.transaction():
                    return operation(conn)
        except SerializationFailure:
            if attempt == attempts - 1:
                raise
            time.sleep((0.02 * (2 ** attempt)) + random.random() * 0.02)
```

The `operation` function must contain only transaction-scoped database
work, or otherwise be designed so retrying does not duplicate external
actions.

------------------------------------------------------------------------

# 13. MySQL/InnoDB and Redis comparisons

## 13.1 PostgreSQL versus InnoDB

  -----------------------------------------------------------------------
  Topic                   PostgreSQL              MySQL InnoDB
  ----------------------- ----------------------- -----------------------
  Table organization      Heap                    Clustered by primary
                                                  key

  Primary-key lookup      B-Tree index points to  Clustered index leaf
                          heap tuple              contains row

  Secondary index leaf    Key + tuple locator     Secondary key +
                                                  primary-key value

  MVCC                    Tuple versions and      Undo records and read
                          transaction visibility  views
                          metadata                

  Redo/recovery           WAL                     Redo log plus undo for
                                                  transactional recovery

  Cleanup                 VACUUM reclaims dead    Purge removes obsolete
                          tuple space             undo/version history

  Index behavior          Multiple index access   Multiple index types;
                          methods                 B-Tree common
  -----------------------------------------------------------------------

Consequences:

-   In InnoDB, a wide primary key makes every secondary index larger
    because secondary entries carry the primary key.
-   In PostgreSQL, a heap fetch may be required after an index lookup;
    index-only scans depend on visibility-map state.
-   Both systems need careful transaction sizing, indexing, statistics,
    and monitoring.
-   Do not port tuning advice between engines without validating the
    implementation and version.

## 13.2 Redis is not a replacement for a relational storage engine

Redis is an in-memory data-structure server. It is excellent for
low-latency access patterns such as:

-   Cache entries.
-   Rate-limit counters.
-   Short-lived sessions.
-   Distributed coordination primitives (with careful correctness
    analysis).
-   Queues/streams for suitable workloads.
-   Leaderboards and counters.

A Redis sorted set is not a B+ Tree. Redis uses different internal data
structures depending on the data type and encoding. A Redis cache also
does not automatically provide the relational constraints, joins, and
transactional semantics of PostgreSQL.

### Cache-aside example

``` text
API request
    |
    v
Check Redis
  /     \
hit     miss
 |        |
return    query PostgreSQL
            |
            v
        store in Redis
            |
            v
          return
```

Important failure modes:

-   Stale cache after a database update.
-   Cache stampede when a popular key expires.
-   Cache outage causing a database traffic surge.
-   Inconsistent invalidation across multiple writers.
-   Treating cache presence as proof that a business transaction
    committed.

Use TTLs, request coalescing, bounded fallback behavior, and explicit
invalidation/versioning where appropriate. For correctness-critical
state such as account balance or inventory, the source of truth should
be explicit.

------------------------------------------------------------------------

# 14. Common engineering mistakes

1.  **Adding indexes without measuring.** Every index consumes storage
    and adds write work.
2.  **Indexing every filtered column separately.** A composite index may
    better match a frequent query, but the correct order depends on the
    workload.
3.  **Assuming an index must be used.** A sequential scan can be the
    cheapest plan.
4.  **Ignoring actual versus estimated rows.** Bad estimates often
    explain surprising plans.
5.  **Using OFFSET for deep pagination.** Keyset pagination is often
    better for sequential navigation.
6.  **Holding transactions open too long.** This increases lock duration
    and can delay vacuum cleanup.
7.  **Doing read-modify-write in application code.** Use atomic SQL,
    locks, version checks, and constraints.
8.  **Assuming `READ COMMITTED` prevents every race.** It does not
    protect arbitrary multi-row business invariants.
9.  **Catching database errors and continuing in a broken transaction.**
    Roll back or use a savepoint; many database errors abort the
    transaction.
10. **Retrying only one statement after a serialization failure.** Retry
    the complete transaction.
11. **Calling external services inside a database transaction.** This
    holds locks while waiting and creates dual-write hazards.
12. **Treating replicas as backups.** Logical mistakes replicate.
13. **Increasing `work_mem` globally without concurrency analysis.**
    Memory can multiply across operations and sessions.
14. **Running a large migration as if it were a local development
    change.** Plan lock behavior, backfill, write load, and rollback.
15. **Assuming Redis cache is always correct.** Cache invalidation and
    stampedes are production design problems.
16. **Benchmarking only warm-cache behavior.** Cold starts and real
    concurrency may tell a different story.
17. **Ignoring connection pooling.** Too many active database sessions
    can overwhelm memory and scheduling.
18. **Treating a successful backup job as proof of recoverability.**
    Restore and validate regularly.

------------------------------------------------------------------------

# 15. Decision-making checklist

Before adding an index:

-   [ ] Which exact query or workload needs it?
-   [ ] What is the query frequency and latency target?
-   [ ] What are the actual row counts and selectivity?
-   [ ] Does key order match equality predicates, range predicates, and
    ordering?
-   [ ] Can a partial or covering index help?
-   [ ] What is the expected index size?
-   [ ] What is the impact on insert/update/delete throughput?
-   [ ] How will it be deployed safely on the production table?
-   [ ] What metric will prove that it helped?

Before changing transaction isolation or locking:

-   [ ] What invariant must be protected?
-   [ ] Is it a single-row invariant or a cross-row invariant?
-   [ ] Can a unique/check/exclusion constraint express it?
-   [ ] Can one atomic `UPDATE ... WHERE ... RETURNING` solve it?
-   [ ] Is explicit row locking necessary?
-   [ ] Can the operation deadlock or be retried?
-   [ ] Are external side effects outside the retryable transaction?
-   [ ] What is the expected contention level?

Before a database scale change:

-   [ ] Is the bottleneck CPU, I/O, memory, locks, connections, or query
    design?
-   [ ] Have query plans and buffer statistics been inspected?
-   [ ] Are table statistics fresh?
-   [ ] Are replicas actually needed, and what consistency can the
    product tolerate?
-   [ ] Would partitioning solve a specific retention or pruning
    problem?
-   [ ] What are RPO and RTO?
-   [ ] Has point-in-time recovery been tested?

------------------------------------------------------------------------

# 16. System design interview exercise

## Scenario: Design an inventory reservation service

You are designing the inventory backend for a commerce platform.

-   10 million products.
-   Multiple warehouses.
-   Flash sales can produce thousands of reservation attempts per second
    for one popular SKU.
-   A customer can reserve stock for 10 minutes while completing
    payment.
-   A reservation must not cause overselling.
-   Payment providers may retry webhooks.
-   Workers can crash at any point.
-   The product page needs a fast approximate availability display, but
    checkout must be correct.

### Requirements

Design the schema, API, transaction boundaries, indexes, and background
processing.

At minimum, explain:

1.  What is the source of truth for available stock?
2.  What is the schema for inventory, reservations, and payment events?
3.  How do you prevent two requests from reserving the final unit?
4.  Would you use an atomic conditional update or `SELECT FOR UPDATE`?
    Why?
5.  How do reservations expire?
6.  How do you prevent a delayed expiry worker from releasing stock that
    has already been paid for?
7.  How do you make payment webhooks idempotent?
8.  Which indexes support customer reservation history and expiry
    workers?
9.  What happens if the database commits but the worker crashes before
    publishing an event?
10. How do you handle hot products and lock contention?
11. Would Redis be involved? Which data can safely be approximate?
12. What consistency guarantees do product pages and checkout receive?
13. How do you observe contention, deadlocks, queue age, and oversell
    attempts?
14. What is your recovery plan after a database outage?

### A useful starting schema

``` sql
CREATE TABLE inventory (
    warehouse_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    available_quantity BIGINT NOT NULL CHECK (available_quantity >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (warehouse_id, product_id)
);

CREATE TABLE reservations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity BIGINT NOT NULL CHECK (quantity > 0),
    status TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reservations_expiry
ON reservations (expires_at, id)
WHERE status = 'reserved';

CREATE INDEX idx_reservations_customer_created
ON reservations (customer_id, created_at DESC, id DESC);
```

This is only a starting point. You must decide how stock is decremented
on reservation, restored on expiry/cancellation, and finalized on
payment. The state transitions must be atomic and idempotent.

### Evaluation rubric

  -----------------------------------------------------------------------
  Area                                Strong answer demonstrates
  ----------------------------------- -----------------------------------
  Data model                          Clear source of truth, constraints,
                                      state transitions

  Concurrency                         Correct atomic reservation under
                                      simultaneous requests

  Transactions                        Small transaction boundaries and
                                      safe retry behavior

  Indexing                            Query-driven indexes with
                                      write/storage trade-offs

  Idempotency                         Unique provider event key and
                                      repeat-safe processing

  Async workflow                      Outbox or equivalent reliable event
                                      publication

  Expiration                          Race-safe state transition and
                                      bounded worker batches

  Scale                               Hot-key analysis, contention
                                      measurement, deliberate
                                      partitioning

  Consistency                         Explicit distinction between
                                      approximate display and
                                      authoritative checkout

  Operations                          Metrics, alerts, backup, PITR,
                                      restore testing
  -----------------------------------------------------------------------

Try answering the scenario before reading external solutions. A good
design is one where you can explain what happens under two simultaneous
requests, a process crash, a delayed webhook, and a database failover.

------------------------------------------------------------------------

# 17. Learning sequence and references

## Suggested 3-week sequence

### Week 1 --- Physical storage and indexing

-   Day 1: Pages, heap files, tuple identifiers, buffer cache.
-   Day 2: B+ Tree search, fan-out, split, range scan.
-   Day 3: Composite, partial, covering, and expression indexes.
-   Day 4: PostgreSQL index types and InnoDB clustered-index
    differences.
-   Day 5: Run lab experiments A and B; explain each plan aloud.
-   Weekend: Design indexes for five real API queries from a project you
    know.

**Deliverable:** A short note explaining why each index exists, which
query it serves, and its write cost.

### Week 2 --- Execution and optimization

-   Day 1: Parse, rewrite, plan, execute.
-   Day 2: Scan and join algorithms.
-   Day 3: Cardinality, statistics, selectivity, skew.
-   Day 4: Sorts, aggregates, memory, disk spills.
-   Day 5: OFFSET versus keyset, N+1, query-shape experiments.
-   Weekend: Take one slow query and write a before/after performance
    report.

**Deliverable:** Two execution plans annotated with estimated rows,
actual rows, buffers, and the reason for the chosen access path.

### Week 3 --- Transactions, concurrency, and recovery

-   Day 1: ACID and isolation anomalies.
-   Day 2: MVCC, tuple versions, vacuum.
-   Day 3: Locks, deadlocks, `SKIP LOCKED`, optimistic concurrency.
-   Day 4: WAL, checkpoints, replication, PITR.
-   Day 5: Implement a safe inventory reservation transaction.
-   Weekend: Answer the system design exercise and conduct a failure
    walkthrough.

**Deliverable:** A transaction design with schema constraints, SQL,
retry rules, and crash scenarios.

## Free, high-quality references

Prefer official documentation and source-level explanations:

-   PostgreSQL documentation: https://www.postgresql.org/docs/
    -   Indexes: https://www.postgresql.org/docs/current/indexes.html
    -   Using EXPLAIN:
        https://www.postgresql.org/docs/current/using-explain.html
    -   Transactions:
        https://www.postgresql.org/docs/current/tutorial-transactions.html
    -   Concurrency control:
        https://www.postgresql.org/docs/current/mvcc.html
    -   WAL: https://www.postgresql.org/docs/current/wal-intro.html
    -   Routine vacuuming:
        https://www.postgresql.org/docs/current/routine-vacuuming.html
    -   Monitoring statistics:
        https://www.postgresql.org/docs/current/monitoring-stats.html
-   MySQL 8.4 Reference Manual: https://dev.mysql.com/doc/refman/8.4/en/
    -   InnoDB storage engine:
        https://dev.mysql.com/doc/refman/8.4/en/innodb-storage-engine.html
    -   InnoDB indexes:
        https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html
    -   InnoDB transaction model:
        https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-model.html
-   Use The Index, Luke: https://use-the-index-luke.com/
-   CMU Database Systems course materials:
    https://15445.courses.cs.cmu.edu/
-   MIT 6.5840 Distributed Systems (for replication and
    distributed-system foundations): https://pdos.csail.mit.edu/6.824/
-   Redis documentation: https://redis.io/docs/latest/

For production work, use the documentation version matching your
deployed database version. Planner behavior, defaults, and available
features can change between releases.

------------------------------------------------------------------------

## Final engineering principle

The goal is not to make every query use an index, every transaction use
the strongest isolation level, or every database run with aggressive
tuning.

The goal is to select the **least expensive mechanism that correctly
satisfies the product's consistency, latency, throughput, and recovery
requirements**---and to verify that choice with measurements.

For every database design decision, be able to explain:

1.  Which problem are we solving?
2.  What does the database do internally?
3.  What does this cost on reads, writes, memory, storage, and
    concurrency?
4.  What fails under load or during a crash?
5.  Which metric or experiment would prove the design is working?


---

# 18. Deeper reference: index types, index design, and slow queries

This section expands the index and performance topics into a practical reference. The earlier sections introduce the concepts; this section focuses on choosing the right mechanism for real query patterns.

## 18.1 How an index works internally

An index is a separately maintained data structure that maps search keys to locations or values needed to find table rows. It is not a magical shortcut: it is another structure that must be stored, cached, traversed, updated, vacuumed, and recovered.

For a PostgreSQL B-Tree index, the simplified lookup path is:

```text
SQL predicate: WHERE customer_id = 8127
                  |
                  v
         B-Tree root page
                  |
                  v
        Internal index page(s)
                  |
                  v
             Leaf page
                  |
                  v
       Matching index tuple(s)
                  |
                  v
        Heap TID(s) / visibility
                  |
                  v
          Heap page(s), if needed
                  |
                  v
             Result rows
```

An index entry generally contains the indexed key and a reference to the table tuple. In PostgreSQL, that reference is a TID. A B-Tree leaf can contain multiple entries for duplicate keys.

The lookup cost is not simply “O(log N)” in an operational sense. A more useful production model is:

```text
Total query cost
  = index traversal
  + heap page visits
  + visibility checks
  + tuple filtering/projection
  + sorting/aggregation/join work
  + result transfer
```

The upper B-Tree levels are often cached, so a lookup may need only a small number of physical page reads. However, fetching many scattered heap tuples can dominate the cost.

### Why an index can be slower than expected

Imagine an index finds 300,000 matching rows spread across 200,000 heap pages. The index traversal may be cheap, but the heap access can be expensive. A sequential scan may read the table more efficiently.

This is why index existence does not guarantee index usage, and index usage does not guarantee a fast query.

## 18.2 Index types: what problem each one solves

PostgreSQL supports several index access methods. Choose based on the operators and data shape used by the query, not merely the column's SQL type.

| Type | Internal idea / strength | Typical workload | Important limitation |
|---|---|---|---|
| B-Tree | Balanced ordered tree | Equality, range, ordering, uniqueness | Not ideal for arbitrary substring or containment search |
| Hash | Hash table-style equality lookup | Equality comparisons | No range ordering; B-Tree is often more generally useful |
| GIN | Inverted index mapping component values to rows | Arrays, JSONB containment, full-text search | Can be large and write-intensive |
| GiST | Extensible balanced search tree with operator-specific behavior | Geometry, ranges, nearest-neighbor and specialized operators | Performance depends on operator class and data |
| SP-GiST | Space-partitioned tree | Data that partitions naturally, such as certain geometric or prefix spaces | Specialized; not a general replacement for B-Tree |
| BRIN | Summarizes ranges of physically adjacent heap pages | Very large append-oriented tables with physical correlation | Lossy summaries can require rechecking many rows |

### B-Tree

Use for common relational access patterns:

```sql
CREATE INDEX idx_orders_customer_id
ON orders (customer_id);

SELECT *
FROM orders
WHERE customer_id = 8127;
```

It also supports range predicates and ordered scans:

```sql
SELECT *
FROM orders
WHERE created_at >= now() - interval '7 days'
ORDER BY created_at DESC;
```

### Hash

Hash indexes are designed for equality:

```sql
CREATE INDEX idx_sessions_token_hash
ON sessions USING HASH (token);
```

A B-Tree can also support equality and offers ordering/range capabilities. Therefore, a Hash index should be chosen only after testing the actual workload and confirming the database/version behavior.

### GIN

GIN is useful when one row contains multiple searchable components:

```sql
CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    attributes JSONB NOT NULL
);

CREATE INDEX idx_products_attributes_gin
ON products USING GIN (attributes);

SELECT *
FROM products
WHERE attributes @> '{"brand": "Acme"}';
```

GIN is also commonly used for arrays and full-text search. Different GIN operator classes support different operators. A broad default JSONB GIN index and a more targeted `jsonb_path_ops` index have different supported operations and trade-offs.

### GiST

GiST is an extensible framework for indexing values using operator classes. For example, range types can use GiST to accelerate overlap and containment-related operations:

```sql
CREATE TABLE room_bookings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id BIGINT NOT NULL,
    occupied_during tstzrange NOT NULL
);

CREATE INDEX idx_room_bookings_range
ON room_bookings USING GIST (occupied_during);
```

A query can ask which bookings overlap a requested time range:

```sql
SELECT *
FROM room_bookings
WHERE occupied_during &&
      tstzrange('2026-11-10 10:00+06', '2026-11-10 11:00+06');
```

### BRIN

BRIN stores summaries for ranges of heap pages rather than an entry for every row. It can be extremely space-efficient for large tables where values correlate with physical row order:

```sql
CREATE INDEX idx_events_occurred_brin
ON events USING BRIN (occurred_at);
```

For an append-heavy event table where newer timestamps are physically near newer pages, a BRIN index may narrow the pages that need scanning. If values are randomly distributed, its summaries become less selective.

## 18.3 Composite indexes and indexing multiple columns

A composite (multicolumn) index stores a combined key made from more than one column.

```sql
CREATE INDEX idx_orders_customer_status_created
ON orders (customer_id, status, created_at DESC);
```

This index is designed for a query such as:

```sql
SELECT id, total, created_at
FROM orders
WHERE customer_id = 8127
  AND status = 'delivered'
ORDER BY created_at DESC
LIMIT 20;
```

The index key is ordered lexicographically:

```text
(customer_id, status, created_at)
        |
        +-- customer_id is the leading key
              |
              +-- status is ordered within customer_id
                    |
                    +-- created_at is ordered within that pair
```

For a B-Tree, the leading columns are especially important. An index on `(customer_id, status, created_at)` is naturally useful for predicates beginning with `customer_id`, and for predicates on both `customer_id` and `status`. It is generally not an equally good replacement for an index on `status` alone when a query filters only by `status`.

PostgreSQL versions have evolved in how they can use multicolumn B-Tree indexes, including skip-scan optimizations in newer releases for some distributions. Still, design the index around the dominant leading-prefix access patterns and validate with the deployed version's plan.

### Column order: practical method

Do not blindly sort columns by selectivity. Work through these questions:

1. Which predicates are equality conditions?
2. Which predicate is a range condition?
3. Which columns are used for ordering?
4. Which query patterns must this index serve?
5. Is the leading column constrained in the common query?
6. Does the index need to cover projected columns?
7. How many distinct values and how much skew exist?
8. What is the write cost of maintaining this index?

A common pattern is equality columns first, followed by a range/order column, but there are exceptions. The workload determines the correct order.

### Compare two candidate indexes

```sql
CREATE INDEX idx_a
ON orders (customer_id, status, created_at DESC);

CREATE INDEX idx_b
ON orders (status, customer_id, created_at DESC);
```

Test both against a representative workload. Compare plans, buffer reads, execution time, index size, and write throughput. Do not keep both merely because both seem plausible; redundant indexes increase maintenance cost.

## 18.4 Index selectivity and cardinality

**Selectivity** describes how narrowly a predicate filters a relation. A predicate matching 10 rows out of 10 million is highly selective. A predicate matching 8 million rows is not.

A simple estimate:

\[
\text{selectivity} =
\frac{\text{matching rows}}{\text{total rows}}
\]

The inverse concept, cardinality, is often used to describe the number of distinct values in a column or the number of rows estimated at a plan node. Be precise about which meaning is intended.

Example:

```sql
SELECT status, count(*)
FROM orders
GROUP BY status;
```

If 80% of rows have `status = 'delivered'`, an index on `status` may not help a query that retrieves all delivered rows. The engine may prefer a sequential scan.

But selectivity alone is not enough. The planner also considers:

- How many heap pages must be visited.
- Whether matching rows are physically clustered.
- Whether the query is index-only.
- Row width and projected columns.
- Cache state and I/O cost estimates.
- Whether an ordering can be provided by the index.

### Inspect the distribution

```sql
SELECT
    status,
    count(*) AS rows,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
FROM orders
GROUP BY status
ORDER BY rows DESC;
```

Inspect PostgreSQL's collected statistics:

```sql
SELECT
    attname,
    null_frac,
    n_distinct,
    most_common_vals,
    most_common_freqs,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename = 'orders';
```

`n_distinct` can be negative to represent a fraction of the table row count. Statistics are sampled estimates, not a live exact census.

## 18.5 Partial, expression, and covering indexes

### Partial index

Store entries only for rows satisfying a predicate:

```sql
CREATE INDEX idx_pending_orders_created
ON orders (created_at)
WHERE status = 'pending';
```

Useful when a small subset of rows is queried frequently. The query predicate must imply the partial-index predicate for the planner to use it.

### Expression index

Index the result of an expression:

```sql
CREATE INDEX idx_users_lower_email
ON users (lower(email));

SELECT *
FROM users
WHERE lower(email) = lower('person@example.com');
```

This can help when the query repeatedly uses the same expression. The expression and query semantics must match.

### Covering index

Include output columns that are not search keys:

```sql
CREATE INDEX idx_orders_customer_created_cover
ON orders (customer_id, created_at DESC)
INCLUDE (status, total);
```

This may allow an index-only scan for a query that filters by `customer_id` and returns the included columns. PostgreSQL still needs visibility-map information to avoid heap fetches in all cases.

## 18.6 Why database queries become slow

A slow query is usually the result of one or more resource costs, not simply “missing index.”

| Cause | What happens internally | How to investigate |
|---|---|---|
| Full table scan over large relation | Many heap pages are read and tuples checked | `EXPLAIN (ANALYZE, BUFFERS)` |
| Low-selectivity index | Index finds many rows, causing many heap visits | Compare sequential scan and index scan plans |
| Wrong composite index order | Query cannot efficiently narrow the leading key range | Match predicates/order to index key sequence |
| Stale or insufficient statistics | Planner estimates wrong row counts | `ANALYZE`, inspect `pg_stats`, extended stats |
| Data skew | Average statistics hide hot values | Test common and rare parameter values |
| Expensive join | Large intermediate result or unsuitable join algorithm | Inspect join nodes, row estimates, loops |
| Sort/hash spill | Operation exceeds memory and uses temporary files | Inspect plan and temp-file logging/statistics |
| Lock contention | Query waits rather than consuming CPU | `pg_stat_activity`, `pg_locks`, wait events |
| Too many round trips | ORM issues N+1 queries | Django query logging, tracing, query count |
| Large OFFSET | Engine walks and discards many rows | Keyset pagination |
| Network/result transfer | Too many or too-wide rows are returned | Reduce projection and result size |
| Connection saturation | Requests wait for a database connection | Pool metrics and connection counts |
| Storage saturation | I/O queue and latency increase | Host/cloud disk metrics and buffer reads |
| CPU saturation | Expression, join, sort, or concurrency work dominates | CPU metrics and query profiling |
| Long transactions | Old row versions cannot be cleaned up | `pg_stat_activity`, vacuum statistics |

### A disciplined diagnosis

When a query becomes slow, do not immediately add an index. Use this sequence:

1. Confirm whether the time is spent waiting for a connection, waiting on a lock, executing SQL, transferring rows, or processing results in the application.
2. Capture the exact SQL and representative parameter values.
3. Compare fast and slow parameter values; skew may be important.
4. Run a safe `EXPLAIN (ANALYZE, BUFFERS)` in an appropriate environment.
5. Find the plan node with the largest actual work, not just the largest-looking cost number.
6. Compare estimated and actual row counts.
7. Check buffer hits/reads, temp I/O, loops, rows removed, and heap fetches.
8. Inspect indexes and table statistics.
9. Change one thing and benchmark the same workload.
10. Verify write overhead, concurrency, and p95/p99 behavior after the change.

## 18.7 A practical index experiment: selectivity and column order

Use a disposable table with a deliberately skewed distribution:

```sql
CREATE TABLE index_lab (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id INT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload TEXT NOT NULL
);

INSERT INTO index_lab (tenant_id, state, created_at, payload)
SELECT
    1 + (random() * 999)::int,
    CASE
        WHEN random() < 0.90 THEN 'completed'
        WHEN random() < 0.98 THEN 'pending'
        ELSE 'failed'
    END,
    now() - (random() * interval '180 days'),
    repeat('x', 100)
FROM generate_series(1, 2000000);

ANALYZE index_lab;
```

Compare:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, created_at
FROM index_lab
WHERE tenant_id = 42
  AND state = 'pending'
ORDER BY created_at DESC
LIMIT 50;
```

Try candidate indexes:

```sql
CREATE INDEX idx_lab_tenant_state_created
ON index_lab (tenant_id, state, created_at DESC);

CREATE INDEX idx_lab_state_tenant_created
ON index_lab (state, tenant_id, created_at DESC);
```

Run the same query again and compare. Then test a query filtering only by `state`, and another filtering only by `tenant_id`. You should see that one index is not necessarily optimal for every query shape.

For a fair comparison, test with both warm and cold-ish cache conditions where feasible, repeat runs, and avoid drawing conclusions from one timing sample. Drop the unused candidate index after the experiment.

---

# 19. Deeper reference: transaction isolation, MVCC, and locks

## 19.1 Transaction isolation in practical terms

Isolation defines what a transaction can observe while other transactions are running. The isolation level is a correctness/performance choice, not a setting to maximize without reason.

### Common anomalies

| Anomaly | Meaning | Example |
|---|---|---|
| Dirty read | Read another transaction's uncommitted write | Read a balance that is later rolled back |
| Non-repeatable read | Same row returns different committed values within one transaction | Read account balance twice around another commit |
| Phantom | Repeating a predicate query returns a different row set | Count pending jobs twice while another transaction inserts one |
| Lost update | One writer overwrites another writer's change | Two read-modify-write increments result in one increment |
| Write skew | Concurrent snapshot-based decisions combine to violate an invariant | Two doctors each go off-call after each sees the other still on-call |

PostgreSQL does not allow dirty reads: its `READ UNCOMMITTED` behaves like `READ COMMITTED`. Other engines can differ.

### PostgreSQL isolation summary

| Level | Snapshot behavior | Important behavior |
|---|---|---|
| READ COMMITTED | New snapshot for each statement | A later statement can see another transaction's commit |
| REPEATABLE READ | Stable transaction snapshot | Prevents non-repeatable reads and phantoms in PostgreSQL; write skew can still occur |
| SERIALIZABLE | Serializable execution is enforced using dependency tracking | Transactions may be aborted and need full retry |

The SQL standard's anomaly descriptions and each database's implementation details are not identical. Always read the documentation for the exact engine and version.

## 19.2 Demonstrate isolation using two sessions

Create a small table:

```sql
CREATE TABLE isolation_demo (
    id INT PRIMARY KEY,
    value INT NOT NULL
);

INSERT INTO isolation_demo VALUES (1, 100);
```

### READ COMMITTED

Session A:

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT value FROM isolation_demo WHERE id = 1;
```

Session B:

```sql
UPDATE isolation_demo SET value = 200 WHERE id = 1;
COMMIT;
```

Session A:

```sql
SELECT value FROM isolation_demo WHERE id = 1;
COMMIT;
```

The second statement in A can see 200 because it gets a new statement snapshot.

### REPEATABLE READ

Repeat the sequence, but start A with:

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
```

A continues to see the version visible to its transaction snapshot. A transaction attempting to update a row changed since its snapshot may receive a serialization-related error.

### SERIALIZABLE

Try a multi-row business invariant under concurrent transactions. PostgreSQL may detect a dangerous dependency structure and abort one transaction. Your application must retry the entire transaction, not only the final SQL statement.

## 19.3 Write skew: why a stable snapshot is not enough

Suppose at least one doctor must remain on call. Two doctors are currently on call.

```text
Initial:
Doctor A: on_call = true
Doctor B: on_call = true

Transaction 1 reads: B is on call
Transaction 2 reads: A is on call

Transaction 1 sets A off call
Transaction 2 sets B off call

Both transactions may commit under snapshot isolation.
Final state: nobody is on call.
```

A transaction-level snapshot gives each transaction a consistent view, but does not automatically protect every cross-row invariant.

Possible solutions:

- Use `SERIALIZABLE` and retry serialization failures.
- Lock a shared guard row that represents the invariant.
- Redesign the data model so a constraint can enforce the invariant.
- Use an explicit, correctly ordered locking protocol.

Choose based on contention and the exact invariant.

## 19.4 MVCC: tuple versions and visibility

In PostgreSQL, an update generally creates a new tuple version. Tuple metadata records transaction identifiers used by visibility rules.

```text
Heap page (simplified over time)

Before update:
  tuple version V1
  value = 100

After transaction updates:
  old tuple V1 remains temporarily
  new tuple V2 is inserted
  V2 value = 200

Transaction snapshots decide:
  reader with older snapshot -> V1 may be visible
  reader with newer snapshot -> V2 may be visible
```

The exact visibility decision depends on transaction status and snapshot boundaries, not merely on comparing two version numbers.

### Why VACUUM exists

Old versions cannot be removed while an active transaction might still need them. Vacuum identifies versions that are no longer visible to any relevant transaction and makes their space reusable.

Monitor:

```sql
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    last_autovacuum,
    last_autoanalyze,
    vacuum_count,
    autovacuum_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

Find long-running transactions:

```sql
SELECT
    pid,
    usename,
    state,
    now() - xact_start AS transaction_age,
    wait_event_type,
    wait_event,
    left(query, 300) AS query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start;
```

A long-lived transaction can hold an old snapshot and delay cleanup. This is one reason to avoid wrapping an entire web request—including slow remote calls—in a database transaction.

## 19.5 Locks: what is actually being protected?

PostgreSQL uses multiple lock types:

- **Table-level locks:** protect relation-level operations and coordinate DDL/DML modes.
- **Row-level locks:** coordinate conflicting modifications to particular rows.
- **Advisory locks:** application-defined locks identified by keys.
- **Predicate locks:** used by Serializable Snapshot Isolation to detect read/write dependencies; they are not ordinary blocking row locks.

Ordinary `SELECT` statements generally do not take row locks that block updates. `SELECT ... FOR UPDATE` does.

### Row-lock example

Session A:

```sql
BEGIN;
SELECT *
FROM inventory
WHERE product_id = 42
FOR UPDATE;
```

Session B:

```sql
UPDATE inventory
SET available_quantity = available_quantity - 1
WHERE product_id = 42;
```

B waits for A to commit or roll back because the row is locked.

### Lock clauses

```sql
-- Fail instead of waiting for a conflicting lock.
SELECT *
FROM inventory
WHERE product_id = 42
FOR UPDATE NOWAIT;

-- Skip rows locked by other transactions.
SELECT id
FROM jobs
WHERE status = 'pending'
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT 20;
```

`SKIP LOCKED` is useful for queue consumers, but it intentionally provides an inconsistent view of the candidate set. It is not appropriate for ordinary user-facing reads that require a complete result.

## 19.6 Deadlock prevention and diagnosis

A classic deadlock:

```text
A: lock row 1 -------- wait for row 2
B: lock row 2 -------- wait for row 1
```

A database detects the cycle and aborts one transaction. The application must be prepared for this.

A practical prevention rule is to lock rows in a stable global order:

```sql
SELECT id
FROM accounts
WHERE id IN (10, 20)
ORDER BY id
FOR UPDATE;
```

All code paths that lock the same set of resources should use the same order.

Inspect active waits:

```sql
SELECT
    pid,
    state,
    wait_event_type,
    wait_event,
    pg_blocking_pids(pid) AS blocking_pids,
    now() - query_start AS query_age,
    left(query, 250) AS query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

Do not automatically terminate a blocking session without identifying its owner and transaction impact.

## 19.7 Choose a concurrency mechanism deliberately

| Requirement | Candidate mechanism |
|---|---|
| Prevent duplicate email or external event ID | Unique constraint |
| Prevent negative stock in a single row | Check constraint + conditional atomic update |
| Read and modify a row as a multi-step workflow | `SELECT FOR UPDATE` in a short transaction |
| Detect stale document edits | Version column / compare-and-swap update |
| Enforce complex cross-row invariant | Serializable transaction, guard row, or model redesign |
| Multiple workers claim different jobs | `FOR UPDATE SKIP LOCKED` with atomic claim |
| Avoid duplicate event processing | Unique idempotency key + transaction |
| Publish event after DB commit reliably | Transactional outbox |

---

# 20. Deeper reference: query planning and EXPLAIN ANALYZE

## 20.1 What the planner is deciding

The planner considers alternative physical strategies for the same logical query. For a join, alternatives can differ in:

- Join order.
- Join algorithm.
- Scan method.
- Whether to sort.
- Whether to aggregate before or after a join.
- Whether an index can provide ordering.
- Whether parallel workers are worthwhile.

For three joined tables, join order can change the size of intermediate results dramatically. The optimizer estimates the cost of alternatives and selects a plan it believes is cheapest.

A planner cost is a model unit, not wall-clock milliseconds. It is useful for comparing candidate plans under the same configuration, not as a direct latency prediction.

## 20.2 What EXPLAIN shows

```sql
EXPLAIN
SELECT *
FROM orders
WHERE customer_id = 8127;
```

This displays the estimated plan without executing the query.

## 20.3 What EXPLAIN ANALYZE adds

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS)
SELECT *
FROM orders
WHERE customer_id = 8127;
```

This executes the statement and reports actual execution behavior.

Important fields:

| Field | Interpretation |
|---|---|
| `cost=startup..total` | Estimated planner cost units |
| `rows` | Estimated output rows |
| `width` | Estimated average output row width |
| `actual time` | Measured time for the node |
| `actual rows` | Actual rows emitted per loop |
| `loops` | How many times the node executed |
| `Buffers: shared hit` | Shared-buffer blocks found in memory |
| `Buffers: shared read` | Shared-buffer blocks brought in from lower storage/cache layers |
| `temp read/written` | Temporary blocks read/written by the operation |
| `Rows Removed by Filter` | Rows rejected by a filter at that node |
| `Heap Fetches` | Heap visits during an index-only scan |
| `Workers Planned/Launched` | Parallel workers requested/started |

Node timings and row counts need to be interpreted with `loops`. A node executed 10,000 times can be expensive even if each execution is individually small.

`BUFFERS` counts PostgreSQL buffer activity, not necessarily physical device I/O. A shared-buffer read may still be served by the operating-system cache.

## 20.4 Example: identify a bad estimate

Imagine a plan reports:

```text
Nested Loop  (cost=... rows=10 ...)
             (actual ... rows=250000 loops=1)
```

The planner expected roughly 10 output rows but produced 250,000. That discrepancy can lead to a poor join algorithm or memory decision.

Investigate:

- Did `ANALYZE` run after a large data change?
- Is the column distribution highly skewed?
- Are two predicates correlated?
- Are parameter values atypical?
- Is a cast or function preventing accurate estimation?
- Would extended statistics help?

Do not force a join algorithm as the first response. Fix the information or query shape that caused the bad decision, when possible.

## 20.5 EXPLAIN ANALYZE safety

`EXPLAIN ANALYZE` actually executes the query. For a write statement, it performs the write:

```sql
BEGIN;

EXPLAIN (ANALYZE, BUFFERS)
UPDATE orders
SET status = 'archived'
WHERE created_at < now() - interval '2 years';

ROLLBACK;
```

A rollback can reverse transactional table changes, but the statement still consumes resources, acquires locks, generates WAL, and may trigger non-transactional side effects such as sequence advancement or external effects from functions/triggers. Use a disposable environment for risky experiments.

For production, start with plain `EXPLAIN`, a replica or staging environment, safe parameter ranges, and query monitoring. Do not run an unbounded expensive `ANALYZE` query during peak load without understanding the impact.

## 20.6 A plan-reading checklist

Read from the leaves upward:

1. What is the first scan reading?
2. Is it sequential, index, index-only, or bitmap?
3. How many rows are estimated and actual at each node?
4. Is a filter removing a large number of rows after reading them?
5. Are nested-loop inner nodes executing many times?
6. Is a sort or hash spilling to disk?
7. Is the join producing a large intermediate result?
8. Are buffers dominated by reads or hits?
9. Is time spent in the database, or does the application spend time after rows return?
10. Does the plan differ for common and rare parameter values?

The goal is to explain the work performed, not simply to identify whether the plan contains the word `Index`.

---

# 21. Deeper reference: replication

## 21.1 Why replication exists

Replication maintains copies of database changes on other database instances. It can support:

- High availability and failover.
- Read scaling.
- Geographic distribution.
- Disaster recovery.
- Maintenance with reduced downtime.

Replication is not a substitute for backups, and a replica does not automatically make writes scale horizontally.

## 21.2 PostgreSQL physical streaming replication

PostgreSQL physical replication sends WAL records from a primary to a standby. The standby replays WAL to reproduce the primary's physical database state.

```text
                 Applications
                      |
                      v
                Primary DB
                      |
             WAL records generated
                      |
              WAL sender process
                      |
              streaming connection
                      |
              WAL receiver process
                      |
                 Standby DB
                      |
                WAL replay
                      |
            Read-only queries (if enabled)
```

A physical standby is generally a copy of the cluster's physical state, not a separately writable database for normal application writes.

## 21.3 Asynchronous replication

With asynchronous replication:

1. Primary commits and acknowledges the client.
2. WAL is sent to the standby.
3. Standby receives and replays it later.

If the primary fails before the latest WAL reaches a promoted standby, some acknowledged transactions may be lost.

This creates a trade-off:

- Lower commit latency.
- Potential replication lag and non-zero data loss during failover.

## 21.4 Synchronous replication

Synchronous replication can make commit wait for acknowledgement from one or more configured standbys. Exact guarantees depend on settings such as `synchronous_commit`, `synchronous_standby_names`, and the selected acknowledgement level (write, flush, or apply).

Conceptually:

```text
Client
  |
  v
Primary executes transaction
  |
  v
WAL generated
  |
  +------> Standby receives / writes / flushes / replays
  |                            |
  +<--------- acknowledgement--+
  |
  v
Primary acknowledges commit
```

Waiting for remote acknowledgement can increase latency and can affect write availability if the required standby is unavailable. Synchronous replication is not one single guarantee; understand exactly what acknowledgement is required.

## 21.5 Replication lag and read-after-write consistency

Suppose a customer updates an address on the primary, then the next API request reads from a lagging replica. The customer may temporarily see the old address.

Common strategies:

- Send read-after-write requests to the primary.
- Use primary reads for correctness-sensitive workflows.
- Track a replication position and wait until a standby has replayed it when the product requires that guarantee.
- Allow eventual consistency for non-critical displays and analytics.
- Expose freshness explicitly where appropriate.

Do not assume a replica is current merely because it is connected.

## 21.6 Monitor replication

On the primary:

```sql
SELECT
    application_name,
    state,
    sync_state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    write_lag,
    flush_lag,
    replay_lag
FROM pg_stat_replication;
```

On a standby:

```sql
SELECT
    pg_is_in_recovery() AS is_standby,
    pg_last_wal_receive_lsn() AS receive_lsn,
    pg_last_wal_replay_lsn() AS replay_lsn,
    pg_last_xact_replay_timestamp() AS last_replay_timestamp;
```

A timestamp-based lag estimate can be misleading when the primary is idle. Compare LSN positions and monitor the full replication pipeline.

## 21.7 Replication versus backup

| Replication | Backup / PITR |
|---|---|
| Maintains a current or near-current copy | Preserves recoverable historical state |
| Helps availability and failover | Helps recover from deletion, corruption, or bad deployment |
| Can replicate accidental deletes | Can restore to a point before the mistake |
| May share failure domains | Can be isolated in separate storage/accounts/regions |
| Usually not a long-term history mechanism | Retention policy preserves historical recovery points |

A robust production system needs both an availability strategy and a tested recovery strategy.

## 21.8 Failover is a system design problem

A failover process must consider:

- How failure is detected.
- How a standby is selected and promoted.
- How split-brain is prevented.
- How applications discover the new primary.
- How connection pools reconnect.
- Whether the old primary is fenced from accepting writes.
- Whether the promoted node has all required WAL.
- How replicas are reconfigured after promotion.
- How data consistency is validated.

Automatic failover without fencing and a clear authority model can create two writable primaries. Use a well-understood orchestration solution and test failure scenarios.

---

## Updated study checklist

Use this checklist to verify that you can explain the requested topics without relying on memorized definitions.

- [ ] Draw how a B-Tree lookup reaches a heap tuple.
- [ ] Explain the difference between PostgreSQL heap storage and InnoDB clustered storage.
- [ ] Compare B-Tree, Hash, GIN, GiST, SP-GiST, and BRIN.
- [ ] Explain composite-index key ordering and leading-column behavior.
- [ ] Calculate basic selectivity and explain why a low-selectivity index may lose to a sequential scan.
- [ ] Explain why multiple indexes increase write amplification.
- [ ] Diagnose a slow query using actual rows, estimated rows, loops, and buffers.
- [ ] Explain the difference between `EXPLAIN` and `EXPLAIN ANALYZE`.
- [ ] Demonstrate non-repeatable reads and write skew using two sessions.
- [ ] Explain how PostgreSQL MVCC determines tuple visibility.
- [ ] Explain why long transactions delay vacuum cleanup.
- [ ] Demonstrate row locks, `NOWAIT`, `SKIP LOCKED`, and a deadlock.
- [ ] Explain asynchronous versus synchronous replication and the read-after-write problem.
- [ ] Distinguish replication, backup, and point-in-time recovery.
- [ ] Design an inventory reservation flow that remains correct under concurrent requests and worker crashes.

