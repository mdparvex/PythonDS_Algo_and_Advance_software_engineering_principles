# 🧭 Technical Documentation: **Database Partitioning**

## ****1\. Introduction****

**Database partitioning** is the process of **dividing a large database table into smaller, more manageable pieces** called **partitions**, while maintaining them as part of a single logical table.

Each partition stores a **subset of data** (e.g., by date, region, or range of IDs), which improves:

- Query performance
- Maintenance efficiency
- Data management (archiving, purging)
- Scalability and concurrency

Unlike **sharding**, partitioning happens **within the same database instance**, not across multiple databases.

## ****2\. Why Partition a Database?****

| **Problem** | **Without Partitioning** | **With Partitioning** |
| --- | --- | --- |
| Query speed | Full table scans on billions of rows | Only relevant partitions scanned |
| Data deletion | Deletes millions of rows (slow) | Drop old partitions instantly |
| Maintenance | Indexes grow large | Smaller, per-partition indexes |
| Storage | All data on one file/table | Distributed across partitions |

## ****3\. Types of Partitioning****

### ****3.1 Range Partitioning****

- Data divided by range values (e.g., dates or numeric ranges)
- Example: Sales data partitioned by year or month

| **Partition** | **Range** |
| --- | --- |
| sales_2023 | date BETWEEN '2023-01-01' AND '2023-12-31' |
| sales_2024 | date BETWEEN '2024-01-01' AND '2024-12-31' |

✅ Best for time-series or sequential data.

### ****3.2 List Partitioning****

- Data divided by specific values in a column.
- Example: Data by region or category.

| **Partition** | **Region** |
| --- | --- |
| customers_us | 'US' |
| customers_eu | 'EU' |
| customers_asia | 'ASIA' |

✅ Best for categorical data.

### ****3.3 Hash Partitioning****

- Data distributed based on the **hash of a key column**.
- Provides **even data distribution**.

```sql
CREATE TABLE orders PARTITION BY HASH (customer_id);
```

✅ Best for load balancing and parallel processing.

### ****3.4 Composite Partitioning****

- Combines two partitioning methods.
- Example: Range + Hash (partition by year, then hash within each year).

✅ Best for very large datasets.

## ****4\. Partitioning vs Sharding vs Replication****

| **Feature** | **Partitioning** | **Sharding** | **Replication** |
| --- | --- | --- | --- |
| **Location** | Within one database | Across multiple databases | Copies of same data |
| **Purpose** | Performance, manageability | Scalability | Availability, redundancy |
| **Data Distribution** | Subsets within one schema | Subsets across databases | Identical copies |
| **Writes** | Directed to the correct partition | Directed to correct shard | To primary only |
| **Reads** | Partition pruning optimizes reads | Routed to correct shard | Read from replicas |

## ****5\. How Partitioning Works in PostgreSQL****

PostgreSQL supports **declarative partitioning** since version 10+.

When you query a partitioned table:

- PostgreSQL determines which partitions are relevant.
- It executes the query only on those partitions (**partition pruning**).
- The result is combined transparently.

### Example Flow

```sql
SELECT * FROM sales WHERE sale_date BETWEEN '2024-01-01' AND '2024-01-31';
```

→ PostgreSQL checks sale_date, selects only the sales_2024 partition.

## ****6\. Architecture Overview****
```yaml
                 ┌─────────────────────────┐
                 │       Application       │
                 └────────────┬────────────┘
                              │
                              ▼
                ┌────────────────────────────┐
                │  Partitioned Table (sales) │
                └──────┬──────────┬──────────┘
                       ▼          ▼
         ┌────────────────┐ ┌────────────────┐
         │ sales_2023     │ │ sales_2024     │
         │ Range: 2023    │ │ Range: 2024    │
         └────────────────┘ └────────────────┘
```

## ****7\. Production-Level Example: Partitioning in PostgreSQL (AWS + Django)****

Let's implement **range-based partitioning** for a **Sales** table.

### ****7.1 PostgreSQL Setup (AWS RDS)****

- Create a PostgreSQL instance in **Amazon RDS**.
- Enable access using **pgAdmin** or **psql**.
- Connect to your RDS instance:
    ```bash
    psql -h <rds-endpoint> -U <username> -d <database>
    ```

### ****7.2 Create Partitioned Table****

#### Parent Table

```sql
CREATE TABLE sales (
    id BIGSERIAL PRIMARY KEY,
    customer_id INT,
    amount NUMERIC,
    sale_date DATE NOT NULL
)
PARTITION BY RANGE (sale_date);
```

#### Child Partitions

```sql
CREATE TABLE sales_2023 PARTITION OF sales
FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE sales_2024 PARTITION OF sales
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### Optional Future Partition

```sql
CREATE TABLE sales_default PARTITION OF sales DEFAULT;
```

✅ **Tip:** The DEFAULT partition catches data outside existing ranges.

### ****7.3 Insert and Query****

```sql
INSERT INTO sales (customer_id, amount, sale_date)
VALUES (101, 120.5, '2024-05-12');
```

✅ PostgreSQL automatically routes this record to sales_2024.

Query example:

```sql
SELECT * FROM sales WHERE sale_date BETWEEN '2024-01-01' AND '2024-06-30';
```

✅ PostgreSQL prunes irrelevant partitions and queries only sales_2024.

### ****7.4 Verify Partition Routing****

```sql
SELECT tableoid::regclass AS partition_name, * FROM sales;
```

Output:

```bash
 partition_name | id | customer_id | amount | sale_date
----------------+----+-------------+--------+------------
 sales_2024     | 1  | 101         | 120.5  | 2024-05-12
```

## ****8\. Partitioning in Django ORM****

### ****8.1 Approach 1: Database-Level Partitioning (Recommended)****

Partitioning is **handled by PostgreSQL**, not Django.

In models.py:

```python
class Sale(models.Model):
    customer_id = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateField()

    class Meta:
        db_table = 'sales'
```

Django ORM works as usual:

```python
Sale.objects.create(customer_id=101, amount=150.75, sale_date='2024-04-15')
```

PostgreSQL automatically routes the data to the right partition.

✅ **No ORM modification needed.**

### ****8.2 Approach 2: Application-Controlled Partitioning****

You can define **custom database routers** if you want Django to manage partitions manually.

Example database_router.py:

```python
class SalesPartitionRouter:
    def db_for_write(self, model, **hints):
        if model._meta.db_table == 'sales':
            if hints.get('sale_date').year == 2023:
                return 'sales_2023'
            else:
                return 'sales_2024'
        return None
```

This is rarely needed if PostgreSQL handles partitions natively.

## ****9\. How Reads and Writes Work****

| **Operation** | **Flow** | **Description** |
| --- | --- | --- |
| **Write (INSERT)** | App → Parent Table → Partition | PostgreSQL checks the partition key and routes automatically. |
| **Read (SELECT)** | App → Parent Table → Relevant Partitions | PostgreSQL prunes irrelevant partitions for optimized queries. |
| **Delete** | App → Parent Table → Drop Partition | You can drop old partitions for instant deletion of large data. |
| **Indexing** | Per partition | Each partition can have its own index for local optimization. |

## ****10\. Example: Query Optimization with Partition Pruning****

Without partitioning:

```sql
SELECT * FROM sales WHERE sale_date BETWEEN '2023-01-01' AND '2023-12-31';
```

→ Full table scan over billions of rows.

With partitioning:

```sql
EXPLAIN SELECT * FROM sales WHERE sale_date BETWEEN '2023-01-01' AND '2023-12-31';
```

→ PostgreSQL automatically prunes irrelevant partitions (sales_2024 etc.), drastically reducing I/O.

## ****11\. Maintenance and Scaling****

| **Task** | **Command** | **Description** |
| --- | --- | --- |
| **Add New Partition** | CREATE TABLE sales_2025 ... | Add for new year |
| **Drop Old Partition** | DROP TABLE sales_2023; | Archive or delete old data instantly |
| **Index Management** | CREATE INDEX ON sales_2024 (customer_id); | Optimize per-partition queries |
| **Vacuum/Analyze** | ANALYZE sales_2024; | Maintain query planner statistics |

## ****12\. Monitoring and Troubleshooting****

- Check partitions:
    ```sql
        \d+ sales
    ```
- Identify large partitions:
```sql
    SELECT inhrelid::regclass AS partition, pg_total_relation_size(inhrelid)
    FROM pg_inherits WHERE inhparent = 'sales'::regclass;
```
- Monitor slow queries with:
```sql
EXPLAIN ANALYZE SELECT ...
``

## ****13\. Real-World AWS Example****

Using **Amazon RDS for PostgreSQL**:

- Create a standard RDS PostgreSQL instance.
- Create partitioned tables as shown above.
- Enable **performance insights** to monitor query execution per partition.
- Optionally use **AWS Lambda** for automated partition rotation (creating next month/year partition).
- Store older partitions on **Amazon S3** using **AWS DMS (Data Migration Service)**.

## ****14\. Best Practices****

✅ Use **range partitioning** for time-based data.  
✅ Always **create a DEFAULT partition** to catch unexpected data.  
✅ Maintain **consistent indexes** across all partitions.  
✅ Use **partition pruning-friendly queries** (must include partition key).  
✅ Automate **partition management scripts** (cron or AWS Lambda).  
✅ Monitor query performance and repartition when partitions grow large.

## ****15\. Summary****

| **Concept** | **Description** |
| --- | --- |
| **Partitioning** | Dividing a large table into smaller logical segments. |
| **Partition Types** | Range, List, Hash, Composite. |
| **Performance Benefit** | Faster queries and maintenance via partition pruning. |
| **PostgreSQL Support** | Built-in since version 10+. |
| **AWS Integration** | Fully supported in RDS and Aurora PostgreSQL. |
| **Django Integration** | Transparent - ORM works normally with PostgreSQL partitioning. |

## ****16\. References****

- [PostgreSQL Partitioning Documentation](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [AWS RDS for PostgreSQL User Guide](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Django ORM with PostgreSQL](https://docs.djangoproject.com/en/stable/ref/databases/#postgresql-notes)
- [AWS Blog: Automating PostgreSQL Partition Management](https://aws.amazon.com/blogs/database/automating-postgresql-table-partition-management-on-aws/)