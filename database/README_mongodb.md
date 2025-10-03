
# 📘 MongoDB Deep Dive Documentation

## 🧠 Understanding MongoDB in Depth

MongoDB is a **NoSQL**, **document-oriented** database designed for **scalability**, **flexibility**, and **developer agility**. It stores data in **JSON-like** documents (called BSON—Binary JSON), which allows for rich, hierarchical data representation.

---

## 🔍 1. MongoDB Overview

| Feature               | Description                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| Database Type         | NoSQL Document-based                                                       |
| Data Format           | BSON (Binary JSON)                                                         |
| Schema                | Schema-less (Flexible)                                                     |
| Query Language        | MongoDB Query Language (MQL, similar to JSON)                              |
| Scalability           | Horizontal (via sharding)                                                  |
| Transactions          | ACID-compliant multi-document transactions supported (since v4.0)          |
| Primary Use Cases     | Real-time analytics, content management, IoT, catalogs, event logging, etc.|

---

## 🛠 2. Core Concepts

| MongoDB Concept   | Equivalent in RDBMS | Description                                                                 |
|-------------------|---------------------|-----------------------------------------------------------------------------|
| Database          | Database            | A container for collections                                                |
| Collection        | Table               | A group of BSON documents                                                  |
| Document          | Row                 | A single BSON record (hierarchical, dynamic fields)                        |
| Field             | Column              | A key-value pair inside a document                                         |
| Index             | Index               | Improves read/query performance                                            |
| Aggregation       | SQL GROUP BY        | Data processing pipelines for transformation and summarization             |

---

## 📋 3. Example: MongoDB Document Structure

```json
{
  "_id": ObjectId("5fabc1234abcd"),
  "name": "John Doe",
  "email": "john@example.com",
  "address": {
    "street": "123 Main St",
    "city": "New York"
  },
  "orders": [
    {"item": "Book", "price": 12.99},
    {"item": "Pen", "price": 1.50}
  ]
}
```

---

## ⚖️ 4. MongoDB vs PostgreSQL – When to Choose What

| Factor                         | MongoDB                                              | PostgreSQL                                            |
|-------------------------------|------------------------------------------------------|-------------------------------------------------------|
| Data Structure                 | Flexible schema, hierarchical                       | Rigid schema, relational                             |
| Use Cases                      | Real-time apps, fast development, dynamic schemas    | Finance, ERP, analytics with strong consistency       |
| Query Flexibility              | Powerful document queries, aggregations             | Advanced joins, SQL analytics                        |
| Transactions                  | Yes (multi-document ACID since v4.0)                 | Yes, robust                                           |
| Scaling                        | Easy horizontal scaling via sharding                 | Primarily vertical scaling (with some sharding via Citus) |
| Schema Enforcement             | Optional (schema-less)                              | Mandatory                                             |
| Performance for Write-heavy   | Better for large, unstructured inserts               | Better for structured, transactional workloads        |
| Learning Curve                 | Easier for beginners                                 | Requires solid understanding of schema design         |

---

## 🚀 5. When Should You Use MongoDB Over PostgreSQL?

- Schema is dynamic or evolving quickly
- Building real-time analytics or IoT systems
- Need to store nested/hierarchical JSON
- Horizontal scalability required
- Quick prototyping (MVPs, startups)
- Microservices with independent DB schemas

---

## 📦 6. MongoDB Example in Django (with `mongoengine`)

### Installation

```bash
pip install mongoengine
```

### models.py

```python
from mongoengine import Document, StringField, ListField, EmbeddedDocument, EmbeddedDocumentField

class Order(EmbeddedDocument):
    item = StringField()
    price = StringField()

class User(Document):
    name = StringField()
    email = StringField()
    orders = ListField(EmbeddedDocumentField(Order))
```

### views.py

```python
from .models import User, Order

def create_user():
    order1 = Order(item="Book", price="12.99")
    order2 = Order(item="Pen", price="1.50")
    user = User(name="John", email="john@example.com", orders=[order1, order2])
    user.save()
```

---

## 🧪 7. Querying in MongoDB

```python
# Find a user
user = User.objects(name="John").first()

# Access embedded documents
for order in user.orders:
    print(order.item)
```

---

## 🧱 8. Limitations of MongoDB

- Lacks strong ACID transaction support prior to v4.0
- Not ideal for complex relational data
- Limited JOIN capabilities
- Data redundancy due to denormalization

---

## 🔄 9. Real-World Use Case Example

```json
{
  "title": "How to use MongoDB",
  "tags": ["mongodb", "nosql", "database"],
  "author": {
    "name": "Alice",
    "bio": "Senior DB Engineer"
  },
  "comments": [
    {"user": "Bob", "text": "Nice post!"},
    {"user": "John", "text": "Very helpful!"}
  ]
}
```

---

## ✅ 10. Summary

### Choose MongoDB If…
- You need flexible, evolving schemas.
- You want to store nested, hierarchical data.
- You're building real-time systems with high writes.
- You prefer JSON-like syntax and quick development.

### Stick to PostgreSQL If…
- You need relational integrity & complex joins.
- Your data model is consistent and normalized.
- You require advanced analytics and strong SQL.
- You need strong ACID compliance & transactions.



# MongoDB Technical Documentation

## 1. Introduction

MongoDB is a **NoSQL, document-oriented database** that stores data in
**BSON (Binary JSON)** format. It is designed for:\
- **High performance** (fast reads/writes with indexes)\
- **High availability** (replica sets, failover)\
- **Scalability** (horizontal scaling via sharding)\
- **Flexibility** (schema-less design, dynamic documents)

------------------------------------------------------------------------

## 2. Core Features of MongoDB

### 2.1 Document Model

-   Data is stored in **collections** (similar to tables).\
-   Each collection contains **documents** (similar to rows).\
-   Documents are stored in **BSON** (JSON-like with extra data types).

**Example document:**

``` json
{
  "name": "Alice",
  "age": 25,
  "email": "alice@example.com",
  "skills": ["Python", "MongoDB"],
  "address": {
    "city": "Dhaka",
    "country": "Bangladesh"
  }
}
```

------------------------------------------------------------------------

### 2.2 Flexible Schema

MongoDB collections do not enforce a strict schema. Different documents
in the same collection can have different fields.

``` json
{ "name": "Bob", "age": 30 }
{ "name": "Charlie", "age": 28, "department": "IT" }
```

------------------------------------------------------------------------

### 2.3 High Availability

-   **Replica Sets**: A group of MongoDB servers where one is the
    primary and others are secondaries. If the primary fails, an
    election occurs automatically.

------------------------------------------------------------------------

### 2.4 Horizontal Scalability

-   **Sharding**: Splitting large collections across multiple servers.
    Useful when handling **big data**.

------------------------------------------------------------------------

## 3. CRUD Operations in MongoDB

CRUD = **Create, Read, Update, Delete**

### 3.1 Create (Insert)

``` javascript
// Insert one document
db.users.insertOne({ name: "Alice", age: 25 })

// Insert multiple documents
db.users.insertMany([
  { name: "Bob", age: 30 },
  { name: "Charlie", age: 28 }
])
```

------------------------------------------------------------------------

### 3.2 Read (Query)

``` javascript
// Find all documents
db.users.find()

// Find one document
db.users.findOne({ name: "Alice" })

// Find with condition
db.users.find({ age: { $gt: 25 } })

// Projection (return specific fields)
db.users.find({}, { name: 1, age: 1, _id: 0 })
```

------------------------------------------------------------------------

### 3.3 Update

``` javascript
// Update one document
db.users.updateOne(
  { name: "Alice" },
  { $set: { age: 26 } }
)

// Update multiple documents
db.users.updateMany(
  { age: { $lt: 30 } },
  { $inc: { age: 1 } }
)
```

------------------------------------------------------------------------

### 3.4 Delete

``` javascript
// Delete one document
db.users.deleteOne({ name: "Alice" })

// Delete many documents
db.users.deleteMany({ age: { $gt: 40 } })
```

------------------------------------------------------------------------

## 4. Indexing in MongoDB

Indexes improve query performance by allowing MongoDB to **quickly
locate documents** without scanning the entire collection.

### 4.1 Types of Indexes

#### 1. Single Field Index

``` javascript
db.users.createIndex({ name: 1 })  // Ascending index on "name"
```

#### 2. Compound Index

``` javascript
db.users.createIndex({ name: 1, age: -1 })
```

-   Useful for queries filtering by multiple fields.

#### 3. Text Index

``` javascript
db.articles.createIndex({ content: "text" })
db.articles.find({ $text: { $search: "database" } })
```

#### 4. Unique Index

``` javascript
db.users.createIndex({ email: 1 }, { unique: true })
```

#### 5. TTL (Time-to-Live) Index

Automatically deletes documents after a specified time.

``` javascript
db.sessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 3600 })
```

------------------------------------------------------------------------

### 4.2 Viewing and Dropping Indexes

``` javascript
db.users.getIndexes()
db.users.dropIndex("name_1")
```

------------------------------------------------------------------------

## 5. Query Optimization

### 5.1 Explain Plans

Use `.explain("executionStats")` to analyze query performance.

``` javascript
db.users.find({ age: { $gt: 25 } }).explain("executionStats")
```

Key fields in output:\
- **nReturned** → Number of documents returned\
- **executionTimeMillis** → Query execution time\
- **totalDocsExamined** → Number of documents scanned\
- **totalKeysExamined** → Index entries scanned

------------------------------------------------------------------------

### 5.2 Optimization Best Practices

1.  **Use Indexes Effectively**

    -   Create indexes on frequently queried fields.\
    -   Example: If most queries use `{ email: "value" }`, create an
        index on `email`.

2.  **Avoid Collection Scans**

    -   Use filters that match existing indexes.

3.  **Use Projection**

    -   Return only required fields.\

    ``` javascript
    db.users.find({}, { name: 1, _id: 0 })
    ```

4.  **Avoid `$regex` on Non-Indexed Fields**

    ``` javascript
    db.users.find({ name: /^Al/ })  // Efficient if "name" has an index
    ```

5.  **Pagination with Indexes**\
    Instead of `.skip()` (which can be slow for large offsets), use
    range-based queries:

    ``` javascript
    db.users.find({ _id: { $gt: ObjectId("...") } }).limit(20)
    ```

6.  **Use Covered Queries**

    -   A query that can be answered **only using the index** without
        scanning documents.\

    ``` javascript
    db.users.createIndex({ name: 1, age: 1 })
    db.users.find({ name: "Alice" }, { name: 1, age: 1, _id: 0 })
    ```

------------------------------------------------------------------------

## 6. Example Use Case

### Scenario: User Management System

We want to store and efficiently query user data.

**Collection Example:**

``` json
{
  "name": "Alice",
  "email": "alice@example.com",
  "age": 25,
  "createdAt": ISODate("2025-10-03T10:00:00Z")
}
```

**Optimizations Applied:**\
1. **Indexes**:\
- `email` (unique index) → fast lookups, prevents duplicates.\
- `createdAt` (TTL index) → auto-delete inactive sessions.

2.  **Queries:**

    ``` javascript
    // Find user by email
    db.users.find({ email: "alice@example.com" })

    // Find users created in the last 7 days
    db.users.find({ createdAt: { $gte: ISODate("2025-09-26T00:00:00Z") } })
    ```

3.  **Explain Output:**

    ``` javascript
    db.users.find({ email: "alice@example.com" }).explain("executionStats")
    ```

    → Shows index usage, `totalDocsExamined: 1` (optimized).

------------------------------------------------------------------------

## 7. Conclusion

-   **CRUD operations** are simple and flexible in MongoDB.\
-   **Indexes** are essential for performance. Choose single, compound,
    text, or TTL indexes depending on use case.\
-   **Query optimization** relies on explain plans, projections, covered
    queries, and avoiding unnecessary collection scans.\
-   MongoDB provides **scalability, high availability, and flexible
    schema**, making it suitable for modern applications like
    **real-time analytics, content management systems, IoT, and
    recommendation engines**.
