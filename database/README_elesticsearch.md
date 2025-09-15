# Elasticsearch — Technical Documentation

## Table of Contents
1. Executive Summary
2. What is Elasticsearch?
3. Core Concepts and Terminology
4. Elasticsearch Architecture
5. Data Modeling and Indexing
6. Querying and Searching
7. Aggregations and Analytics
8. Scaling, Sharding, and Replication
9. Fault Tolerance and High Availability
10. Performance Optimization
11. Security and Access Control
12. Monitoring and Observability
13. Example Use Cases
14. Design Checklist and Best Practices
15. Glossary
16. Further Reading

---

## 1. Executive Summary
Elasticsearch is a **distributed search and analytics engine** designed for speed, scalability, and near real-time data retrieval. It is commonly used for full-text search, log and metrics analytics, and complex querying of structured/unstructured data.

---

## 2. What is Elasticsearch?
- Open-source, part of the Elastic Stack (Elasticsearch, Logstash, Kibana, Beats).
- Built on **Apache Lucene** for text indexing and search.
- Provides RESTful APIs for storing, searching, and analyzing data.

**Key benefits:**
- Near real-time search.
- Distributed by design.
- Rich full-text search capabilities.
- Horizontal scalability.

---

## 3. Core Concepts and Terminology
- **Cluster:** A collection of nodes working together.
- **Node:** A single Elasticsearch server instance.
- **Index:** A collection of documents, similar to a database in RDBMS.
- **Document:** A JSON object stored in an index.
- **Field:** A key-value pair inside a document.
- **Shard:** A partition of an index.
- **Replica:** A copy of a shard for high availability.
- **Mapping:** Schema definition of documents (data types, analyzers).
- **Analyzer:** Processes text during indexing and searching (tokenizer + filters).

---

## 4. Elasticsearch Architecture
- **Cluster:** Consists of one or more nodes.
- **Master node:** Manages cluster state (index creation, shard allocation).
- **Data node:** Stores data and handles CRUD/search requests.
- **Ingest node:** Preprocesses documents before indexing.
- **Coordinating node:** Routes requests, aggregates results.

**Diagram (conceptual):**
```
Client -> Coordinating Node -> Data Nodes -> Shards -> Lucene Indexes
```

---

## 5. Data Modeling and Indexing
### Document example:
```json
{
  "user": "alice",
  "message": "Elasticsearch is powerful",
  "timestamp": "2025-09-15T10:00:00"
}
```

### Mapping example:
```json
PUT /messages
{
  "mappings": {
    "properties": {
      "user": {"type": "keyword"},
      "message": {"type": "text", "analyzer": "standard"},
      "timestamp": {"type": "date"}
    }
  }
}
```

### Indexing a document:
```json
POST /messages/_doc/1
{
  "user": "alice",
  "message": "Elasticsearch is powerful",
  "timestamp": "2025-09-15T10:00:00"
}
```

---

## 6. Querying and Searching
### Full-text search example:
```json
GET /messages/_search
{
  "query": {
    "match": {
      "message": "Elasticsearch"
    }
  }
}
```

### Boolean query:
```json
GET /messages/_search
{
  "query": {
    "bool": {
      "must": [{"match": {"user": "alice"}}],
      "filter": [{"range": {"timestamp": {"gte": "2025-09-01"}}}]
    }
  }
}
```

---

## 7. Aggregations and Analytics
Elasticsearch provides **aggregations** for analytics similar to SQL `GROUP BY`.

### Example: Count messages per user
```json
GET /messages/_search
{
  "size": 0,
  "aggs": {
    "messages_per_user": {
      "terms": { "field": "user" }
    }
  }
}
```

### Example: Average message length
```json
GET /messages/_search
{
  "size": 0,
  "aggs": {
    "avg_length": {
      "avg": { "script": "doc['message'].value.length()" }
    }
  }
}
```

---

## 8. Scaling, Sharding, and Replication
- **Shards:** Index split into multiple pieces for scalability.
- **Replicas:** Ensure redundancy and high availability.

**Example:**
```json
PUT /logs
{
  "settings": {
    "number_of_shards": 5,
    "number_of_replicas": 1
  }
}
```

---

## 9. Fault Tolerance and High Availability
- Automatic shard reallocation if a node fails.
- Replicas ensure queries continue even if primary shards are unavailable.
- Snapshots and restores for disaster recovery.

---

## 10. Performance Optimization
- Use appropriate analyzers (keyword vs text).
- Tune shard count: too many small shards hurts performance.
- Use filters and cached queries.
- Prefer bulk indexing for high throughput.
- Monitor query latency and index size.

---

## 11. Security and Access Control
- TLS for data in transit.
- Role-based access control (RBAC).
- API key or token authentication.
- Field and document-level security.

---

## 12. Monitoring and Observability
- **Elastic Stack:** Use Kibana for visualizing metrics and logs.
- **Monitoring:** Track node health, JVM memory, query latency, shard distribution.
- **Alerting:** Trigger alerts when thresholds are exceeded.

---

## 13. Example Use Cases
### Use Case A — Log Analytics
- Collect logs via Logstash/Beats.
- Index logs in Elasticsearch.
- Use Kibana dashboards for visualization.

### Use Case B — E-commerce Search
- Product catalog indexed in Elasticsearch.
- Search queries with filters (price, category, brand).
- Aggregations for faceted navigation.

### Use Case C — Real-time Security Analytics
- Stream security events into Elasticsearch.
- Build dashboards to detect anomalies.
- Use alerting to notify security teams.

### Use Case D — Recommendation Engines
- Store user interactions in Elasticsearch.
- Query for similar items using `more_like_this`.
- Combine with ML models for personalization.

---

## 14. Design Checklist and Best Practices
- Define index lifecycle management (ILM) to manage hot/warm/cold storage.
- Choose proper shard/replica settings upfront.
- Apply schema design carefully (keyword vs text).
- Avoid mapping explosions (too many fields).
- Regularly monitor and tune cluster performance.

---

## 15. Glossary
- **Analyzer:** Breaks down text into tokens.
- **Replica:** A copy of a shard.
- **Shard:** A horizontal partition of an index.
- **Inverted index:** Data structure for full-text search.
- **Cluster state:** Metadata about indices, shards, and nodes.

---

## 16. Further Reading
- Elastic official documentation: https://www.elastic.co/guide/
- Book: *Elasticsearch: The Definitive Guide* by Clinton Gormley and Zachary Tong
- Tools: Kibana, Logstash, Beats, Elastic APM

---

### Appendix: Hands-on Example
#### Bulk indexing
```json
POST /products/_bulk
{"index": {"_id": 1}}
{"name": "Laptop", "price": 1000, "category": "electronics"}
{"index": {"_id": 2}}
{"name": "Phone", "price": 500, "category": "electronics"}
```

#### Search with filters and sorting
```json
GET /products/_search
{
  "query": {
    "bool": {
      "must": {"match": {"category": "electronics"}},
      "filter": {"range": {"price": {"lte": 800}}}
    }
  },
  "sort": [ {"price": "asc"} ]
}
```




------

Here is a complete and **well-structured technical documentation** for **Elasticsearch**, including **concepts, architecture, setup, and Django integration with examples**.

# 📘 Elasticsearch Documentation with Django Integration

## 🔍 What is Elasticsearch?

**Elasticsearch** is a distributed, RESTful search and analytics engine built on **Apache Lucene**. It enables fast, scalable, and full-text search on structured and unstructured data. Elasticsearch is schema-less, document-oriented, and optimized for performance.

## 📦 Core Concepts

| **Concept** | **Description** |
| --- | --- |
| **Index** | Logical namespace for documents (like a database in RDBMS). |
| **Document** | A JSON object stored in an index (like a row in a table). |
| **Field** | A key-value pair in a document (like a column). |
| **Shard** | A horizontal partition of an index. |
| **Replica** | A copy of a shard for fault tolerance. |
| **Inverted Index** | Data structure that maps terms to document IDs (used for fast full-text search). |

## ⚙️ How Elasticsearch Works

### 1\. ****Indexing Data****

When a document is added to an index, Elasticsearch:

- Parses the JSON
- Tokenizes text fields (if configured)
- Builds an inverted index for search

### 2\. ****Searching Data****

- Uses a powerful **query DSL (domain-specific language)** to match documents.
- Combines **full-text search** with **filtering** and **aggregations**.

## 🚀 Installation & Setup

### 🔧 Install Elasticsearch (Locally with Docker)

```bash
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.13.0
```

- Access UI at: <http://localhost:9200>
- Use tools like **Kibana** or **Postman** to test queries.

## 🧑‍💻 Django Integration with Elasticsearch

### 🛠 Tools Required

Install the Python client:

```bash
pip install elasticsearch==8.13
```
### 🌐 Project Structure (Example)

```pgsql
myproject/
├── books/
│   ├── models.py
│   ├── search.py
│   ├── views.py
```

### ✅ Step-by-Step Django Integration

### 1\. Define a Django Model (models.py)

```python
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    description = models.TextField()
    published_date = models.DateField()

```

### 2\. Create Index and Insert Data to Elasticsearch (search.py)

```python
from elasticsearch import Elasticsearch
from .models import Book

es = Elasticsearch("http://localhost:9200")

INDEX_NAME = "books"

def create_index():
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body={
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "author": {"type": "text"},
                    "description": {"type": "text"},
                    "published_date": {"type": "date"}
                }
            }
        })

def index_book(book: Book):
    doc = {
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "published_date": book.published_date.isoformat()
    }
    es.index(index=INDEX_NAME, id=book.id, document=doc)

def reindex_all_books():
    for book in Book.objects.all():
        index_book(book)

```

### 3\. Search View in Django (views.py)

```python
from django.http import JsonResponse
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

def search_books(request):
    query = request.GET.get("q", "")
    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "author", "description"]
            }
        }
    }
    res = es.search(index="books", body=body)
    hits = res["hits"]["hits"]
    results = [hit["_source"] for hit in hits]
    return JsonResponse(results, safe=False)

```

### 4\. URL Configuration (urls.py)

```python
from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_books),
]

```

## 📊 Example Usage

### Add Books

Use Django Admin or shell to create book entries:

```bash
python manage.py shell
>>> from books.models import Book
>>> Book.objects.create(title="Elasticsearch Basics", author="John Doe", description="Intro to search", published_date="2023-01-01")

```
### Index Books

```python
from books.search import create_index, reindex_all_books
create_index()
reindex_all_books()

```

### Search Books

Visit:

```bash

<http://localhost:8000/search/?q=search>
```
## 📚 Advanced Features

- **Pagination** using from and size
- **Fuzzy Search** with fuzziness: "AUTO"
- **Filtering** using bool and must, filter
- **Highlighting** matched terms
- **Aggregations** for stats

Example fuzzy search:

```json
{
  "query": {
    "match": {
      "title": {
        "query": "elastikserch",
        "fuzziness": "AUTO"
      }
    }
  }
}

```

## 🛡️ Best Practices

- Use **aliases** for versioned indices
- Optimize mappings and analyzers
- Use **bulk indexing** for large datasets
- Monitor cluster health and storage
- Secure access using **Elastic Shield** or API keys

## 🧪 Testing Elasticsearch Queries

You can test directly using:

```bash

curl -X GET "localhost:9200/books/\_search?q=title:elasticsearch&pretty"
```
Or use **Postman** / **Kibana Dev Tools**.

## 🧱 When to Use Elasticsearch

✅ Use Elasticsearch when:

- You need full-text search
- You need fast filtering and ranking
- Your dataset is large and requires distributed search

❌ Avoid if:

- You only need CRUD and simple filtering
- You need strong ACID transactions

## 🔚 Conclusion

Elasticsearch is a powerful search engine that works beautifully with Django for building scalable and fast search applications. By indexing your Django models into Elasticsearch, you gain full-text search, performance, and rich query support.