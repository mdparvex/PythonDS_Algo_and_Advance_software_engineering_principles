
# 📚 Database Partitioning and Sharding in Django

Database partitioning and sharding are techniques used to **manage large datasets** efficiently, **improve query performance**, and **scale applications**. Let’s break them down with clear definitions, comparisons, and Django-focused examples.

---

## 🔹 What is Database Partitioning?

### ✅ Definition:
Partitioning is the process of **dividing a large database table into smaller, more manageable pieces (partitions)**. All the partitions remain in the same database system. Same table but multiple copy. Suppose, If user come from asia we can put them in a partion, it will help to lookup efficiently. 

### ✅ Why It's Used:
- Improves performance (queries can scan only relevant partitions)
- Easier maintenance (e.g., archiving old data)
- Helps avoid table size limits or performance bottlenecks

### ✅ Types of Partitioning:
1. **Range Partitioning**: Rows are partitioned based on a range of column values.
2. **List Partitioning**: Partitioned by predefined lists of values.
3. **Hash Partitioning**: Rows are distributed across partitions using a hash function.

### ✅ PostgreSQL Example:
```sql
CREATE TABLE student_results (
    id SERIAL PRIMARY KEY,
    student_id INT,
    exam_date DATE,
    score INT
) PARTITION BY RANGE (exam_date);

CREATE TABLE student_results_2023 PARTITION OF student_results
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE student_results_2024 PARTITION OF student_results
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### ✅ In Django (with PostgreSQL):
While Django ORM does not natively support database partitioning, you can still use PostgreSQL partitioning by executing raw SQL during migrations or using third-party libraries. Below is a realistic example to show how you can implement range-based partitioning in Django using PostgreSQL.
You can use the `django-postgres-extra` or `django-partial-index` packages, or handle it via raw SQL migrations.

1.Create Model:
```python
# models.py
class UserLog(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    log_date = models.DateField()
    activity = models.TextField()

    class Meta:
        managed = False  # Very important! Let PostgreSQL manage the table
        db_table = 'user_log'


```
managed = False tells Django not to manage this table (we’ll handle it manually with SQL)

2. Create a schema migration to generate the partitioned parent table and partitions:
```bash
python manage.py makemigrations --empty your_app_name

```
3. Edit Migrations

```python
# migrations/000X_partition_userlog.py

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('your_app_name', '000X_previous'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE TABLE user_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES auth_user(id),
                log_date DATE NOT NULL,
                activity TEXT NOT NULL
            ) PARTITION BY RANGE (log_date);

            -- Partition for 2024
            CREATE TABLE user_log_2024 PARTITION OF user_log
            FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

            -- Partition for 2025
            CREATE TABLE user_log_2025 PARTITION OF user_log
            FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
            """
        ),
    ]

```
```bash
python manage.py migrate

```
Use in django
```python
from your_app.models import UserLog
from django.utils import timezone

UserLog.objects.create(
    user=request.user,
    log_date=timezone.now().date(),
    activity="Logged in from Chrome browser"
)

```
✅ Django will write the data into the correct partition based on log_date.
Imagine you’re logging millions of rows per year — searching or deleting logs in a single user_log table would get slower over time.

## With partitioning:
- You can query only a specific partition (e.g., WHERE log_date >= '2025-01-01')
- PostgreSQL skips scanning other partitions (thanks to constraint exclusion).
- You can drop/archive old partitions (e.g., drop user_log_2020).


## 🔹 What is Database Sharding?

### ✅ Definition:
Sharding is the practice of **splitting a database into multiple independent databases (shards)**. Each shard holds a portion of the data, and they may even live on separate servers or geographic regions.

### ✅ Why It's Used:
- Horizontally scales databases for very large applications
- Distributes load across multiple servers
- Reduces contention and lock conflicts

### ✅ When to Use:
- Millions of users or records
- Performance bottlenecks in single-node DB
- High availability or geo-distribution needed

### ✅ Django Sharding Example (using `django-sharding` or manual routing):
You define multiple databases in `settings.py`:
```python
DATABASES = {
    'default': {},
    'shard_1': {...},
    'shard_2': {...},
}
```

Then, route models manually:
```python
class ShardedRouter:
    def db_for_read(self, model, **hints):
        user_id = hints.get('user_id')
        if user_id % 2 == 0:
            return 'shard_1'
        return 'shard_2'

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)
```

And in your views:
```python
User.objects.using('shard_1').filter(name='Mamun')
```

---

## 🧠 Partitioning vs Sharding

| Feature           | Partitioning                       | Sharding                                |
|-------------------|------------------------------------|------------------------------------------|
| Scope             | Inside a single database           | Across multiple databases/servers        |
| Managed by        | Database engine                    | Application or DB proxy layer            |
| Use Case          | Table-level performance boost      | Application-scale horizontal scaling     |
| Query Simplicity  | Transparent to query engine        | Requires routing logic                   |

---

## 🎯 Summary in Django Context:

| Scenario                          | Recommended Approach |
|----------------------------------|----------------------|
| You have 100 million logs/year   | Use PostgreSQL range partitioning |
| Your app has 5M+ users worldwide | Shard users by region (e.g., EU, US) |
| Your tables grow vertically fast | Partition by date or ID |
| You want fault isolation         | Shard across independent databases |

---

### ✅ Partitioning vs Sharding — Clarification

You're almost correct, and here's a clearer distinction:

#### ✅ Database Partitioning
- **What:** Divides one large table into smaller partitions (chunks).
- **Where Stored:** Same database instance.
- **Why:** For performance and maintenance efficiency.
- **How:** Commonly partitioned by ranges (e.g., date, region).
- **Example:** 
    - `users_asia`, `users_europe` under the same PostgreSQL DB.
- **Django:** PostgreSQL handles partitioning; ORM is unaware.

#### ✅ Database Sharding
- **What:** Splits data across completely separate databases.
- **Where Stored:** Different database instances (e.g., multiple AWS RDS).
- **Why:** For large-scale horizontal scaling and isolation.
- **How:** Routing logic based on shard key (e.g., user_id).
- **Example:**
    - Users with ID < 50000 → DB1; ID ≥ 50000 → DB2
- **Django:** Use [database routers](https://docs.djangoproject.com/en/stable/topics/db/multi-db/) for routing.

#### ✅ Key Differences

| Feature               | Partitioning                           | Sharding                              |
|-----------------------|----------------------------------------|----------------------------------------|
| Storage location      | Same database                          | Different databases                    |
| Purpose               | Query speed, performance tuning        | Scalability, high availability         |
| Setup complexity      | Lower                                  | Higher (needs routing logic)           |
| Django support        | Indirect (via raw SQL or 3rd party)    | Supported via database routers         |

