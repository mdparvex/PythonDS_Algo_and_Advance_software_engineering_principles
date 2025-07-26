# REST vs GraphQL vs gRPC

## 🔍 Overview

| Feature        | REST                      | GraphQL                             | gRPC                                 |
|----------------|---------------------------|--------------------------------------|--------------------------------------|
| Protocol       | HTTP                      | HTTP                                 | HTTP/2                               |
| Data Format    | JSON                      | JSON                                 | Protocol Buffers (binary)            |
| Interface Style| Resource-based            | Query-based                          | Service-based (RPC)                  |
| Flexibility    | Fixed endpoints & fields  | Client specifies fields needed       | Predefined methods/messages          |
| Performance    | Medium (some overfetch)   | Efficient (no overfetch/underfetch) | High performance (binary transport)  |
| Browser-native | ✅ Yes                    | ✅ Yes                                | ❌ Not browser-native                 |
| Tooling        | Mature ecosystem           | Growing tooling ecosystem            | Requires specific tools              |

---

## 🟩 1. REST API (Representational State Transfer)

### 📌 Concept:
- Endpoints defined per resource.
- Uses HTTP methods (`GET`, `POST`, etc.)
- Often returns more data than needed.

### ✅ Django Example:
```python
# views.py
from rest_framework import viewsets
from .models import Book
from .serializers import BookSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

# urls.py
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = router.urls
```

📥 Request:
```
GET /books/1/
```

📤 Response:
```json
{
  "id": 1,
  "title": "Django for Beginners",
  "author": "Jane Doe",
  "published_year": 2021
}
```

✅ Pros:
- Simple and familiar
- Cacheable
- Widely adopted

❌ Cons:
- Over/under-fetching
- Multiple round trips

---

## 🟦 2. GraphQL

### 📌 Concept:
- Single endpoint `/graphql`
- Client specifies what data it wants
- Schema-based querying

### ✅ Django (Graphene) Example:
```python
# schema.py
import graphene
from graphene_django.types import DjangoObjectType
from .models import Book

class BookType(DjangoObjectType):
    class Meta:
        model = Book

class Query(graphene.ObjectType):
    all_books = graphene.List(BookType)

    def resolve_all_books(self, info):
        return Book.objects.all()

schema = graphene.Schema(query=Query)
```

📥 Query:
```graphql
query {
  allBooks {
    title
    author
  }
}
```

📤 Response:
```json
{
  "data": {
    "allBooks": [
      {
        "title": "Django for Beginners",
        "author": "Jane Doe"
      }
    ]
  }
}
```

✅ Pros:
- Only fetch needed fields
- Strongly typed schema

❌ Cons:
- Caching is tricky
- Complex nesting may slow performance

---

## 🟥 3. gRPC

### 📌 Concept:
- Uses Protocol Buffers over HTTP/2
- Service and message definitions via `.proto` files

### ✅ gRPC Example:
```proto
// book.proto
syntax = "proto3";

service BookService {
  rpc GetBook (BookRequest) returns (BookResponse);
}

message BookRequest {
  int32 id = 1;
}

message BookResponse {
  string title = 1;
  string author = 2;
}
```

✅ Pros:
- High performance
- Strongly typed
- Great for microservices

❌ Cons:
- Not browser-friendly
- Requires code generation and special tooling

---

## 🧠 When to Use What?

| Use Case                              | Recommended |
|---------------------------------------|-------------|
| Public APIs, simple resources         | REST        |
| Flexible frontend data needs          | GraphQL     |
| High-performance internal services    | gRPC        |

---

## ✅ Summary Table

| Feature         | REST         | GraphQL      | gRPC         |
|----------------|--------------|--------------|--------------|
| Simplicity      | ✅ High      | ⚠️ Medium    | ❌ Complex   |
| Performance     | ⚠️ Medium   | ✅ Good       | ✅ Excellent |
| Use in browser  | ✅ Yes       | ✅ Yes       | ❌ No        |
| Schema required | ❌ No        | ✅ Yes       | ✅ Yes       |
| Real-time support| ⚠️ Basic   | ✅ Available | ✅ Streaming |