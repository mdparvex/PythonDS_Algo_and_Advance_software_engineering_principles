# 📌 What is Indexing?

An **index** is a data structure (usually B-Tree, Hash, or GIN/GIST depending on DB type) maintained by the database to speed up queries. Without indexes, the DB does a **full table scan**. With indexes, it can locate rows faster.

Indexes trade **read speed** for **slower writes** (INSERT/UPDATE/DELETE), because the index must be updated every time the data changes.

# 📌 Types of Indexing & When to Use

Most databases (like PostgreSQL, MySQL) support multiple indexing algorithms. Django lets you declare them in your models.

## 1\. ****B-Tree Index (Default)****

- **Algorithm**: Balanced Tree (default in PostgreSQL & MySQL).
- **Use Case**: General-purpose, especially for:
  - Equality lookups (WHERE col = 'x')
  - Range queries (BETWEEN, &lt;, &gt;, &lt;=, &gt;=)
  - Sorting (ORDER BY col)
- **Example in Django**:
```python
from django.db import models

class Student(models.Model):
    name = models.CharField(max_length=100, db_index=True)  # B-Tree index
    age = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["age"]),  # Explicit index
        ]
```

👉 Behind the scenes: CREATE INDEX ... USING btree (age)

## 2\. ****Hash Index****

- **Algorithm**: Hash table.
- **Use Case**:
  - Exact equality lookups (WHERE email = '<abc@example.com>')
  - Not good for range queries (&lt;, &gt;)
- **Example in Django**:
```python
from django.contrib.postgres.indexes import HashIndex

class User(models.Model):
    email = models.EmailField(unique=True)

    class Meta:
        indexes = [
            HashIndex(fields=["email"]),  # Hash index
        ]
```

👉 Creates: CREATE INDEX ... USING hash (email)

## 3\. ****GIN Index (Generalized Inverted Index)****

- **Algorithm**: Inverted index (Postgres only).
- **Use Case**:
  - Full-text search
  - JSON field queries
  - Array fields
- **Example in Django**:
```python
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    search_vector = SearchVectorField(null=True)

    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"]),  # Full-text search
        ]
```

👉 Creates: CREATE INDEX ... USING gin (search_vector)

## 4\. ****GIST Index (Generalized Search Tree)****

- **Algorithm**: Balanced tree structure for complex datatypes.
- **Use Case**:
  - Geospatial queries (PostGIS)
  - Range types (int4range, daterange)
- **Example in Django**:
```python
from django.contrib.postgres.indexes import GistIndex
from django.contrib.gis.db import models as gis_models

class Location(models.Model):
    point = gis_models.PointField()

    class Meta:
        indexes = [
            GistIndex(fields=["point"]),  # Geospatial indexing
        ]
```

👉 Creates: CREATE INDEX ... USING gist (point)

## 5\. ****Partial Index****

- **Use Case**:
  - When you query only a subset of rows often (e.g., is_active = True)
- **Example in Django**:
```python
class Customer(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"], name="active_name_idx", condition=models.Q(is_active=True)),
        ]
```

👉 Creates: CREATE INDEX active_name_idx ON customer (name) WHERE is_active = TRUE;

## 6\. ****Unique Index****

- Ensures no duplicate values.
- Already created when you use unique=True in Django.
```python
class Employee(models.Model):
    employee_id = models.CharField(max_length=50, unique=True)
```

## 7\. ****Composite (Multi-Column) Index****

- **Use Case**:
  - When queries filter/order on multiple columns together.
- **Example in Django**:
```python
class Order(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),  # Composite index
        ]
```

# 📌 How to Define an Algorithm (like B-Tree) in Django

Django chooses **B-Tree** by default, but you can explicitly specify algorithms with PostgreSQL-specific indexes:

```python
from django.contrib.postgres.indexes import BTreeIndex, HashIndex

class Product(models.Model):
    sku = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [
            BTreeIndex(fields=["price"]),  # Explicit B-Tree
            HashIndex(fields=["sku"]),     # Explicit Hash
        ]
```

# 📌 Rule of Thumb (When to Use Which)

- **B-Tree (default)** → Most cases (=, &lt;, &gt;, ORDER BY)
- **Hash** → Exact matches only, faster for equality than B-Tree
- **GIN** → Full-text search, JSON, array fields
- **GIST** → Geospatial / range queries
- **Partial Index** → Optimize for frequent condition-based queries
- **Composite Index** → Queries with multiple fields together
- **Unique Index** → Enforce uniqueness

👉 In summary:  
You don’t usually “define an algorithm” like B-Tree manually for standard fields—Django defaults to it. You explicitly set indexing algorithms only for special cases (hash, gin, gist).