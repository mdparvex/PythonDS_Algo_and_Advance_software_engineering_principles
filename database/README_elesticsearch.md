
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