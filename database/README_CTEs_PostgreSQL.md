# Common Table Expressions (CTEs) — PostgreSQL Technical Documentation

**Audience:** SQL developers, backend engineers, Django developers working with PostgreSQL.

**Scope:** full explanation of CTEs (WITH), types (simple, recursive, writable), materialization control, advanced patterns, performance considerations, and practical examples — including many PostgreSQL SQL examples and Django+PostgreSQL usage patterns.

---

## Table of Contents
1. What is a CTE?
2. Basic CTE syntax
3. Chained CTEs
4. Recursive CTEs (`WITH RECURSIVE`)
   - tree/graph traversal
   - factorial / sequence generation
   - cycle detection
5. Writable CTEs (data-modifying in `WITH`)
   - `INSERT ... RETURNING` used in subsequent CTEs
   - update/delete flows
6. Materialization control: `MATERIALIZED` vs `NOT MATERIALIZED` (Postgres 12+)
7. Common advanced patterns
   - pagination (seek method)
   - top-N per group
   - running totals / window + CTEs
   - gaps-and-islands
   - deduplication and de-dup + keep-first/last
   - upsert flows and complex idempotent writes
   - analytic pipelines & pre-aggregation
8. Performance considerations & EXPLAIN guidance
9. Security and transactional properties
10. Using CTEs from Django
    - raw SQL via connection.cursor and `cursor.mogrify`
    - `Model.objects.raw()` for read-only queries
    - recommended third-party libs: `django-cte` and `django-postgres` patterns (examples)
    - using CTE results with ORM `Subquery` and `Exists` where appropriate
11. Complete example suite (PostgreSQL SQL)
12. Django examples (practical code snippets)
13. Best practices checklist
14. Appendix: useful Postgres functions and operators used in examples

---

## 1. What is a CTE?
A Common Table Expression (CTE) is a named temporary result set that you can reference within a single SQL statement. CTEs are declared using the `WITH` clause and can make complex queries easier to read and maintain. In PostgreSQL, CTEs can be **read-only** (select-only), **recursive** (generate row sequences/hierarchies), or **writable** (perform `INSERT`, `UPDATE`, `DELETE` and expose their results to later CTEs in the same statement).

CTEs are scoped only to the statement that defines them.

---

## 2. Basic CTE syntax
```sql
WITH cte_name AS (
  -- any SELECT query
  SELECT id, title, author_id
  FROM books
  WHERE published_at >= '2020-01-01'
)
SELECT c.id, c.title
FROM cte_name c
WHERE c.author_id = 42;
```

Simple CTEs are convenient for breaking down queries into named steps, avoiding repeated subqueries, and improving readability.

---

## 3. Chained CTEs
CTEs can reference earlier CTEs defined in the same `WITH` clause. This allows building a pipeline of transformations.

```sql
WITH recent_books AS (
  SELECT id, title, author_id FROM books WHERE published_at >= '2024-01-01'
),
authors_with_recent AS (
  SELECT a.id, a.name, COUNT(b.id) AS recent_count
  FROM authors a
  JOIN recent_books b ON b.author_id = a.id
  GROUP BY a.id, a.name
)
SELECT * FROM authors_with_recent WHERE recent_count > 5;
```

---

## 4. Recursive CTEs (`WITH RECURSIVE`)
A recursive CTE allows a CTE to reference itself to produce recursive results such as hierarchical traversals or sequence generation.

### Generic structure
```sql
WITH RECURSIVE name(column_list) AS (
  -- anchor member
  SELECT ...
  UNION ALL
  -- recursive member (references name)
  SELECT ... FROM name JOIN ...
)
SELECT * FROM name;
```

### Example: adjacency-list tree traversal (finding descendants)
Assume `categories(id, parent_id, name)`.

```sql
WITH RECURSIVE descendants AS (
  SELECT id, parent_id, name, 1 AS depth
  FROM categories
  WHERE id = 10 -- root
  UNION ALL
  SELECT c.id, c.parent_id, c.name, d.depth + 1
  FROM categories c
  JOIN descendants d ON c.parent_id = d.id
)
SELECT * FROM descendants ORDER BY depth, id;
```

### Cycle detection
Postgres won't stop you from infinite recursion unless you guard it. To detect cycles and avoid revisiting nodes, maintain a path array.

```sql
WITH RECURSIVE traverse(id, parent_id, path, depth, cycle) AS (
  SELECT id, parent_id, ARRAY[id], 1 AS depth, false
  FROM categories WHERE id = 10
  UNION ALL
  SELECT c.id, c.parent_id, t.path || c.id, t.depth + 1,
         c.id = ANY(t.path)
  FROM categories c
  JOIN traverse t ON c.parent_id = t.id
  WHERE NOT (c.id = ANY(t.path)) -- avoid cycles
)
SELECT * FROM traverse;
```

### Example: generating a series (factorial-like) — sequence generation
```sql
WITH RECURSIVE nums(n) AS (
  SELECT 1
  UNION ALL
  SELECT n + 1 FROM nums WHERE n < 10
)
SELECT * FROM nums;
```

---

## 5. Writable CTEs (data-modifying in `WITH`)
PostgreSQL supports data-modifying statements inside `WITH`. These can be chained so the `RETURNING` of one can feed the next.

### Example: insert then log
```sql
WITH ins AS (
  INSERT INTO users (email, name)
  VALUES ('alice@example.com', 'Alice')
  RETURNING id
),
log AS (
  INSERT INTO audit (user_id, action)
  SELECT id, 'created' FROM ins
  RETURNING *
)
SELECT * FROM ins; -- returns newly created user id
```

### Upsert-like pattern using CTEs
```sql
WITH up AS (
  UPDATE products
  SET price = 9.99
  WHERE sku = 'X123'
  RETURNING *
), ins AS (
  INSERT INTO products (sku, price)
  SELECT 'X123', 9.99
  WHERE NOT EXISTS (SELECT 1 FROM up)
  RETURNING *
)
SELECT * FROM up UNION ALL SELECT * FROM ins;
```

This guarantees that a single statement will either update or insert and return the affected row(s).

---

## 6. Materialization control: `MATERIALIZED` vs `NOT MATERIALIZED`
From PostgreSQL 12 onwards, the planner can choose to inline (not materialize) or materialize a CTE. You can hint explicitly:

```sql
WITH data AS MATERIALIZED (
  SELECT ... -- heavy computation
)
SELECT ... FROM data JOIN ...;

WITH data AS NOT MATERIALIZED (
  SELECT ...
)
SELECT ... FROM data;
```

- `MATERIALIZED` forces the CTE to be executed and stored (like a temp result). This is useful when you want to avoid re-computation or to fix query planning decisions.
- `NOT MATERIALIZED` allows the planner to inline the CTE (treat it like a subquery), which can lead to better plans for some queries.

Use `EXPLAIN` to see what the planner does.

---

## 7. Common advanced patterns

### A. Top-N per group (find top 2 reviews per book)
```sql
WITH ranked AS (
  SELECT r.*, ROW_NUMBER() OVER (PARTITION BY book_id ORDER BY rating DESC, created_at DESC) rn
  FROM reviews r
)
SELECT * FROM ranked WHERE rn <= 2;
```

### B. Running totals / cumulative sums
```sql
WITH ordered AS (
  SELECT id, book_id, amount, created_at,
         SUM(amount) OVER (PARTITION BY book_id ORDER BY created_at ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
  FROM sales
)
SELECT * FROM ordered WHERE book_id = 123;
```

### C. Gaps and islands (consecutive ranges)
Find consecutive day ranges for a user activity table `activity(user_id, day)`.

```sql
WITH numbered AS (
  SELECT user_id, day,
         ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) rn
  FROM activity
),
islands AS (
  SELECT user_id, day, rn, (day::date - (rn || ' days')::interval) AS grp
  FROM numbered
)
SELECT user_id, MIN(day) AS start_day, MAX(day) AS end_day
FROM islands
GROUP BY user_id, grp
ORDER BY user_id, start_day;
```

### D. Deduplication — keep latest row per key
```sql
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY external_id ORDER BY updated_at DESC) rn
  FROM imported_records
)
DELETE FROM imported_records r
USING ranked
WHERE r.id = ranked.id AND ranked.rn > 1;
```

### E. Complex ETL pipelines in one statement
Use chained CTEs to transform incoming data, validate, insert, and log in one transaction.

---

## 8. Performance considerations & EXPLAIN guidance
- CTEs historically (pre-12) were optimization fences — the planner would materialize them. This could be helpful or harmful depending on the workload.
- From Postgres 12+, CTEs are inlined by default unless `MATERIALIZED` is specified.
- Use `EXPLAIN (ANALYZE, BUFFERS)` to observe whether a CTE was materialized and to see I/O costs.
- For expensive repeated subqueries within a single statement, materializing (explicit `MATERIALIZED`) can reduce total work.
- For queries where the planner can do better join reordering or push-down filters, `NOT MATERIALIZED` (or default in PG12+) is preferable.
- Writable CTEs are executed as part of the transaction and follow normal locking rules: watch for locks when updating large datasets.

---

## 9. Security and transactional properties
- CTEs are part of the single SQL statement and therefore part of the same transaction scope.
- Data-modifying CTEs will observe transactional semantics — either everything succeeds or the statement rolls back.
- Be cautious with user-supplied values in dynamic SQL; use parameterized queries to avoid SQL injection.

---

## 10. Using CTEs from Django
You have several options to run CTEs from Django:

### A. `connection.cursor()` (raw SQL)
Use the Django DB API to execute arbitrary SQL safely with parameters.

```python
from django.db import connection

sql = '''
WITH recent_books AS (
  SELECT id, title FROM books WHERE published_at >= %s
)
SELECT * FROM recent_books WHERE title ILIKE %s;
'''
params = ['2024-01-01', '%GraphQL%']
with connection.cursor() as cur:
    cur.execute(sql, params)
    rows = cur.fetchall()
```

Use `cursor.mogrify(sql, params)` for debugging parameter interpolation safely.

### B. `Model.objects.raw()` for read-only queries
If your query returns model columns, `raw()` can map results to models.

```python
qs = MyModel.objects.raw('WITH q AS (SELECT * FROM myapp_mymodel WHERE ...) SELECT * FROM q')
for obj in qs:
    print(obj)
```

### C. Third-party libraries: `django-cte` (recommended for cleaner integration)
- `django-cte` provides a QuerySet-friendly API to build CTEs in Python.
- It integrates with `QuerySet.with_cte(...)` style patterns.

*Example using `django-cte` (pseudocode)*

```python
from django_cte import With

c = With(MyModel.objects.filter(...).values('id', 'score'))
qs = c.join(OtherModel, id=c.col('id')).with_cte(c)
qs = qs.filter(...)
```

### D. Using ORM `Subquery`, `Exists`, and `Window` when possible
Often what you'd write as a CTE for readability can be expressed with `Subquery`/`Exists` or `annotate` using `Window` functions. Use ORM expressions when you want type safety and migrations support.

---

## 11. Complete example suite (PostgreSQL SQL)
Below is a curated set of ready-to-run examples (DDL + queries). Run in psql or pgAdmin.

### Schema for examples
```sql
CREATE TABLE authors (id serial PRIMARY KEY, name text);
CREATE TABLE books (id serial PRIMARY KEY, title text, author_id int REFERENCES authors(id), published_at date);
CREATE TABLE reviews (id serial PRIMARY KEY, book_id int REFERENCES books(id), rating int, text text, created_at timestamptz default now());
CREATE TABLE categories (id serial PRIMARY KEY, parent_id int NULL REFERENCES categories(id), name text);
```

### Example 1 — simple read CTE
```sql
WITH recent AS (
  SELECT id, title FROM books WHERE published_at >= '2024-01-01'
)
SELECT * FROM recent WHERE title ILIKE '%SQL%';
```

### Example 2 — chained CTE + aggregation
```sql
WITH recent AS (
  SELECT id, title, author_id FROM books WHERE published_at >= '2024-01-01'
),
counts AS (
  SELECT author_id, COUNT(*) as cnt FROM recent GROUP BY author_id
)
SELECT a.name, c.cnt FROM authors a JOIN counts c ON c.author_id = a.id WHERE c.cnt > 3;
```

### Example 3 — recursive categories
(see section 4)

### Example 4 — writable CTE: safe insert-or-update
(see section 5 upsert example)

### Example 5 — dedupe delete
(see section 7.D)

---

## 12. Django examples (practical code snippets)

### Example A — run a recursive CTE and map to dicts
```python
from django.db import connection

sql = '''WITH RECURSIVE descendants AS (
  SELECT id, parent_id, name FROM categories WHERE id = %s
  UNION ALL
  SELECT c.id, c.parent_id, c.name FROM categories c JOIN descendants d ON c.parent_id = d.id
)
SELECT id, parent_id, name FROM descendants;'''

with connection.cursor() as cur:
    cur.execute(sql, [root_id])
    cols = [col[0] for col in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
```

### Example B — insert and use RETURNING with CTE inside a transaction
```python
from django.db import transaction, connection

with transaction.atomic():
    sql = '''WITH ins AS (
      INSERT INTO users (email, name) VALUES (%s, %s) RETURNING id
    )
    INSERT INTO audit (user_id, action)
    SELECT id, 'created' FROM ins RETURNING *;'''
    params = ['bob@example.com', 'Bob']
    with connection.cursor() as cur:
        cur.execute(sql, params)
        created_audit = cur.fetchone()
```

### Example C — using `django-cte` (if installed)
Pseudocode (install and read package docs for exact API):
```python
from django_cte import With
from myapp.models import Book

books_cte = With(Book.objects.filter(published_at__gte='2024-01-01'))
qs = books_cte.queryset().with_cte(books_cte).filter(title__icontains='SQL')
for b in qs:
    print(b.title)
```

---

## 13. Best practices checklist
- Use CTEs to improve readability and isolate logical steps.
- For heavy repeated subqueries, consider `MATERIALIZED` to avoid recomputation.
- For queries where the planner can push filters or reorder joins for efficiency, prefer `NOT MATERIALIZED` (or default behavior on PG12+).
- Use recursive CTEs carefully — always provide a termination condition and consider cycle detection when traversing graphs.
- For data-modifying CTEs, be aware of locking and transactional behavior.
- Prefer parameterized queries in Django to avoid SQL injection.
- Add `EXPLAIN (ANALYZE, BUFFERS)` while tuning.

---

## 14. Appendix: useful Postgres features used
- `RETURNING` clause
- `ROW_NUMBER(), RANK(), SUM() OVER (...)` window functions
- arrays: `ARRAY[...]`, `ANY()`
- `EXPLAIN (ANALYZE, BUFFERS)`
- `jsonb_agg` / `jsonb_build_object` for nested JSON output

---

If you want, I can:
- add runnable SQL files and a Docker Compose + init script to spin a Postgres instance and run all examples automatically;
- convert specific SQL examples to Django ORM equivalents (where possible) with tested code for a particular Django version you use;
- generate tests that assert query results using pytest + `pytest-django`.

Which of those would you like next?

---

# PostgreSQL CTEs (Common Table Expressions) — with Django ORM Examples

## 1. Introduction
A **Common Table Expression (CTE)** is a temporary result set defined within the execution scope of a single SQL statement. It enhances readability, modularity, and enables recursive queries.

Syntax:
```sql
WITH cte_name AS (
    SELECT ...
)
SELECT * FROM cte_name;
```

CTEs can be **non-recursive**, **recursive**, or **writable** (used with `INSERT`, `UPDATE`, `DELETE`).

---

## 2. Basic CTE Example in PostgreSQL

```sql
WITH recent_books AS (
    SELECT *
    FROM books
    WHERE published_date >= NOW() - INTERVAL '1 year'
)
SELECT title, author FROM recent_books ORDER BY published_date DESC;
```

### Equivalent Django ORM Example

```python
from django.db.models import F, Q, Subquery
from django_cte import With
from books.models import Book
from datetime import timedelta
from django.utils.timezone import now

recent_books_cte = With(
    Book.objects.filter(published_date__gte=now() - timedelta(days=365))
)

queryset = recent_books_cte.join(Book, id=recent_books_cte.col.id)
queryset = queryset.with_cte(recent_books_cte).order_by('-published_date')

for book in queryset:
    print(book.title, book.author)
```

Here, `django-cte` provides ORM-level support for building and composing CTEs.

---

## 3. Chained CTEs (Multiple CTEs)

### PostgreSQL Example
```sql
WITH top_authors AS (
    SELECT author_id, COUNT(*) AS book_count
    FROM books
    GROUP BY author_id
),
ranked AS (
    SELECT *, RANK() OVER (ORDER BY book_count DESC) AS rank
    FROM top_authors
)
SELECT * FROM ranked WHERE rank <= 5;
```

### Django ORM Equivalent
```python
from django_cte import With
from django.db.models import Count, Window, F
from django.db.models.functions import Rank

# First CTE: Count books per author
top_authors_cte = With(
    Book.objects.values('author_id').annotate(book_count=Count('id'))
)

# Second CTE: Rank authors by book count
ranked_cte = With(
    top_authors_cte.join(Book, id=top_authors_cte.col.author_id)
    .annotate(rank=Window(expression=Rank(), order_by=F('book_count').desc()))
)

final_qs = ranked_cte.with_cte(top_authors_cte).with_cte(ranked_cte).filter(rank__lte=5)
```

---

## 4. Recursive CTEs

### PostgreSQL Example (Employee Hierarchy)
```sql
WITH RECURSIVE employee_tree AS (
    SELECT id, name, manager_id, 1 AS level
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    SELECT e.id, e.name, e.manager_id, et.level + 1
    FROM employees e
    JOIN employee_tree et ON e.manager_id = et.id
)
SELECT * FROM employee_tree;
```

### Django ORM Equivalent (Recursive using django-cte)
```python
from employees.models import Employee
from django_cte import With

base = Employee.objects.filter(manager__isnull=True).annotate(level=1)
recursive = With.recursive(lambda cte: Employee.objects.filter(manager__in=cte).annotate(level=F('level') + 1))

qs = recursive.join(Employee, id=recursive.col.id).with_cte(recursive)

for emp in qs:
    print(emp.name, emp.level)
```

---

## 5. Writable CTEs (UPDATE, INSERT, DELETE)

### PostgreSQL Example
```sql
WITH updated AS (
    UPDATE books
    SET stock = stock - 1
    WHERE id = 5
    RETURNING *
)
SELECT * FROM updated;
```

### Django ORM Equivalent
While Django ORM doesn’t natively support writable CTEs, you can run them via `RawSQL`:

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute('''
        WITH updated AS (
            UPDATE books
            SET stock = stock - 1
            WHERE id = %s
            RETURNING *
        )
        SELECT * FROM updated;
    ''', [5])
    rows = cursor.fetchall()
```

---

## 6. Materialized vs Non-Materialized CTEs

**PostgreSQL 12+** supports control over whether the CTE should be materialized (computed once) or not.

```sql
WITH MATERIALIZED recent_books AS (
    SELECT * FROM books WHERE published_date >= NOW() - INTERVAL '1 year'
)
SELECT * FROM recent_books;
```

In Django ORM (via `django-cte`):
```python
recent_books_cte = With(Book.objects.filter(published_date__gte=now() - timedelta(days=365)), materialized=True)
```

---

## 7. Advanced Example: Running Totals per Author

### PostgreSQL Example
```sql
WITH sales AS (
    SELECT author_id, SUM(sales) AS total_sales
    FROM book_sales
    GROUP BY author_id
)
SELECT *, SUM(total_sales) OVER (ORDER BY author_id) AS running_total
FROM sales;
```

### Django ORM Equivalent
```python
from sales.models import BookSales
from django_cte import With
from django.db.models import Sum, Window

sales_cte = With(BookSales.objects.values('author_id').annotate(total_sales=Sum('sales')))

qs = sales_cte.join(BookSales, author_id=sales_cte.col.author_id)
qs = qs.with_cte(sales_cte).annotate(running_total=Window(Sum('total_sales'), order_by=F('author_id').asc()))
```

---

## 8. Best Practices

✅ Use `MATERIALIZED` for complex reusable queries.

✅ Avoid recursive CTEs when a single-level query or ORM `prefetch_related` suffices.

✅ Monitor performance using `EXPLAIN ANALYZE`.

✅ Use `RawSQL` or `django-cte` for advanced capabilities beyond ORM.

✅ Keep recursive CTE depth limited to prevent long-running queries.

---

## 9. References
- [PostgreSQL Docs — WITH Queries (CTEs)](https://www.postgresql.org/docs/current/queries-with.html)
- [django-cte package](https://github.com/dimagi/django-cte)
- [Django ORM RawSQL Documentation](https://docs.djangoproject.com/en/stable/ref/models/expressions/#rawsql)

