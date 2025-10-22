# GraphQL — Advanced Technical Documentation

**Audience:** Backend engineers, Django developers, API architects.

**Scope:** advanced resolvers, federation, caching strategies, and a practical Django-based example with an advanced GraphQL strategy (queries, mutations, subscriptions, security and optimization).

---

## Table of Contents
1. Overview & architecture
2. Advanced resolver patterns
   - resolver anatomy
   - batching & DataLoader pattern
   - pipeline / composed resolvers / middleware
   - field-level caching & memoization
   - deferred/async resolvers and subscriptions
   - error handling & partial results
3. Federation
   - what it is and when to use it
   - core concepts: @key, @requires, @provides, schema composition, gateway
   - patterns for service boundaries and ownership
   - integration options (Apollo Gateway, other gateways)
4. Caching strategies
   - caching layers and decisions
   - HTTP (CDN) + GraphQL interplay
   - response-level caching & cache-control hints
   - field-level & object-level caching (Redis / in-process)
   - persisted queries & query whitelisting
   - invalidation strategies & cache coherence
5. Security & performance hardening
   - depth limits, complexity analysis, timeouts, rate limits
   - auth/authorization patterns
   - avoiding N+1, smart pagination, cursor vs offset
6. Django example (Graphene-Django) — full walk-through
   - models
   - settings (Redis cache, channels)
   - schema, advanced resolvers with DataLoader and caching
   - mutations with optimistic updates & idempotency
   - subscriptions sample using Django Channels
   - notes on federating a Django GraphQL service
7. Example advanced GraphQL strategy
   - recommended queries, mutations, subscriptions
   - persisted & monitored operations
   - CI checks (query complexity tests)
8. Observability & testing
   - tracing, metrics, logs
   - unit & integration tests for resolvers
9. Appendix: useful libraries & references

---

## 1. Overview & architecture
GraphQL is a query language + runtime for APIs that lets clients request exactly the data they need. For medium/large systems, GraphQL is often used as a consolidated API layer that sits above multiple microservices and data stores. As traffic, schema size, and team size grow, simple resolver implementations are no longer sufficient — you must apply patterns for batching, caching, ownership, and reliability.

Key architectural roles:
- **Gateway** (optional): receives client GraphQL requests, composes federated subgraphs, applies cross-cutting policies.
- **Subgraphs / services**: own pieces of the graph (entities) and expose schemas. When federated, each service contributes to a single global graph.
- **Downstream services/datastores**: databases, REST APIs, RPCs, search indices.

---

## 2. Advanced resolver patterns

### Resolver anatomy (single-field)
A resolver typically receives `(parent, info, **args)` and returns the requested value. In Django/graphene, a resolver is a method on the `Query`/`Type` or a standalone function. Keep resolvers thin: they should orchestrate calls to well-tested service-layer functions or repositories.

### Batching & DataLoader pattern
**Problem:** naively resolving nested fields often causes N+1 queries against a DB or downstream API.

**Solution:** use a DataLoader: collect many requested keys during a single execution tick and resolve them in a single batch.

Principles:
- Create a DataLoader per request (store it on `info.context`), so caches are only per-request.
- Each DataLoader exposes `.load(key)` and `.load_many(keys)`; internally it buffers keys and calls a batch function once per tick.
- Use async implementations for async GraphQL servers.

**Example benefits:** fetching `author` for 100 books becomes 1 `SELECT ... WHERE id IN (...)` instead of 100 queries.

### Pipeline / composed resolvers & middleware
- Use middleware to implement cross-cutting concerns: authentication, logging, metrics, caching hooks.
- Composable resolvers: small functions that transform or validate arguments before the final data fetch.

### Field-level caching & memoization
- Cache heavy computations or 3rd-party requests at object-level (e.g., `book:book_id` cache key). Use TTLs and keys that include version/ETag when possible.\- Use per-request memoization for repeated loads inside the same GraphQL request.

### Deferred/async resolvers & subscriptions
- Subscriptions often use WebSockets. Break responsibilities: publish events from mutations; brokers (Redis/PG/streaming) deliver to subscription services.
- For long-running field resolution, consider returning a placeholder and resolving later with a subscription or polling.

### Error handling & partial results
- GraphQL supports returning `data` alongside `errors`. For resilient APIs, return partial data with field-level errors when possible; map system errors to helpful client-facing messages.

---

## 3. Federation

### What is Federation?
Federation is a specification/pattern (popularized by Apollo) to compose a single graph from multiple services. Each subgraph is responsible for a distinct set of types and fields, and the gateway composes them into a single queryable schema.

### Core concepts
- **Entities & @key:** Services mark types they own with a `@key` so the gateway can identify and reference entities across services.
- **@requires / @provides:** let services declare which fields from other services are required or provided to compute a field.
- **Schema composition:** the gateway merges subgraph SDLs and builds routing for queries that touch multiple services.

### Service boundaries & ownership
- Design entities so each service owns a small, cohesive set of types.
- Use `extends` to augment types owned elsewhere.
- Keep cross-service calls coarse-grained to avoid chatty communication.

### Implementation options
- **Gateway:** Apollo Gateway, other community gateways.
- **Subgraph libraries:** many GraphQL libraries provide federation helpers (Apollo Federation spec implementations exist across languages).

**Operational notes:** composition and schema changes should be part of CI — validating composed schema before deploy.

---

## 4. Caching strategies
Caching must be considered at several levels.

### Layers
1. **CDN / HTTP caching**: cache responses at the edge for public, read-heavy queries.
2. **Gateway response cache**: cache entire GraphQL responses for common queries (use cache key derived from query+variables+auth-scope).
3. **Object / field cache**: Redis or in-process caches per-object (e.g., `book:123`), usually with TTLs.
4. **Downstream cache**: cache results of expensive downstream calls (search, payments).

### HTTP + GraphQL
Because GraphQL uses POST for most requests, HTTP caching is less straightforward than REST. Options:
- Use GET for cacheable queries (persisted queries) and set `Cache-Control` headers.
- Implement CDN rules that inspect GraphQL operations and apply caching only to whitelisted operations.

### Response-level caching & cache-control hints
- Some GraphQL implementations support `@cacheControl` hints (cache-control extension) that let the gateway/CDN decide TTL.
- Persisted queries + GET + CDN = easiest path to effective CDN caching.

### Field-level caching
- Use Redis to cache specific heavy fields (e.g., `user.profile_score`) by key. When using the DataLoader pattern, the batch loader can consult Redis as the first check.

### Persisted queries & whitelisting
- Persisted queries (store the exact query server-side and give clients an ID) enable safe CDN caching and prevent expensive ad-hoc queries.

### Invalidation strategies
- **Time-based TTL:** easiest but can serve stale data.
- **Event-driven invalidation:** publish an invalidation event on writes (mutation) to clear cached objects or tags.
- **Versioned keys:** add a version token to keys that increments on writes.

---

## 5. Security & performance hardening

### Safety checks
- **Depth limiting** to prevent arbitrarily nested queries.
- **Query complexity analysis** (assign cost to fields and reject queries beyond a threshold).
- **Timeouts** for resolvers and request-level cancellation.
- **Rate limiting** at the gateway per client/API key.

### Authz patterns
- **Authentication** in middleware (adds current user to `context`).
- **Authorization** inside resolvers or using field-level directives (role/permission checks).

### Pagination & large lists
- Use **cursor-based pagination** (Relay-style) for stable, efficient pagination.
- Avoid returning arbitrarily large lists—enforce `limit` and `offset/after`.

---

## 6. Django example (Graphene-Django)
This example shows a Django project exposing a GraphQL API with advanced resolver patterns: batching using a DataLoader, object-level caching via Redis, a mutation that publishes subscription events, and a subscription implemented via Channels.

> **Assumptions & packages** (examples)
> - Django >= 4.x
> - graphene-django
> - django-redis
> - promise (for DataLoader) or `aiodataloader` for async
> - channels, channels_redis (for subscriptions)
> - channels_graphql_ws or similar to implement GraphQL subscriptions

### a) Models (simplified)
```python
# books/models.py
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=200)

class Book(models.Model):
    title = models.CharField(max_length=400)
    author = models.ForeignKey(Author, related_name='books', on_delete=models.CASCADE)
    published_at = models.DateField(null=True, blank=True)

class Review(models.Model):
    book = models.ForeignKey(Book, related_name='reviews', on_delete=models.CASCADE)
    text = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### b) Settings (Redis cache + Channels)
```python
# settings.py (relevant parts)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': { 'CLIENT_CLASS': 'django_redis.client.DefaultClient', },
    }
}

# Channels
ASGI_APPLICATION = 'myproject.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': { 'hosts': [('127.0.0.1', 6379)], },
    }
}
```

### c) Request-scoped DataLoader pattern
Create a small DataLoader utility (sync example using promise):

```python
# utils/dataloader.py
from promise import Promise
from collections import defaultdict

class SimpleDataLoader:
    def __init__(self, batch_load_fn):
        self.batch_load_fn = batch_load_fn
        self._queue = []
        self._futures = []

    def load(self, key):
        # return a Promise that resolves once batch function returns
        index = len(self._queue)
        self._queue.append(key)
        promise = Promise(lambda resolve, reject: self._futures.append((resolve, reject)))
        # schedule flush - in simple sync world, flush immediately
        return promise

    def flush(self):
        if not self._queue:
            return
        keys = self._queue
        futures = self._futures
        self._queue = []
        self._futures = []
        try:
            results = self.batch_load_fn(keys)
            for (resolve, _), res in zip(futures, results):
                resolve(res)
        except Exception as e:
            for (_, reject) in futures:
                reject(e)
```

**Note:** In production you'll want a battle-tested library (e.g., `aiodataloader` for async or `graphql-python/dataloader` implementations).

### d) Putting loader on context in the view
```python
# schema/view.py (or urls.py GraphQL view wrapper)
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from books.models import Author
from utils.dataloader import SimpleDataLoader

# batch loader implementation
def batch_get_authors(keys):
    authors = Author.objects.filter(id__in=keys)
    # preserve input order
    authors_by_id = {a.id: a for a in authors}
    return [authors_by_id.get(k) for k in keys]

class CustomGraphQLView(GraphQLView):
    def get_context(self, request):
        ctx = super().get_context(request)
        ctx.dataloaders = {}
        ctx.dataloaders['author_by_id'] = SimpleDataLoader(batch_get_authors)
        return ctx

# urls.py
# path('graphql/', csrf_exempt(CustomGraphQLView.as_view(graphiql=True)))
```

### e) Schema & resolvers with cache and dataloader
```python
# schema/schema.py
import graphene
from graphene_django.types import DjangoObjectType
from django.core.cache import cache
from books.models import Book, Author, Review

CACHE_TTL = 60 * 5

class AuthorNode(DjangoObjectType):
    class Meta:
        model = Author
        fields = ('id', 'name')

class BookNode(DjangoObjectType):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'published_at')

class ReviewNode(DjangoObjectType):
    class Meta:
        model = Review
        fields = ('id', 'text', 'rating', 'created_at')

class Query(graphene.ObjectType):
    book = graphene.Field(BookNode, id=graphene.Int(required=True))
    books = graphene.List(BookNode, limit=graphene.Int(), offset=graphene.Int())

    def resolve_book(root, info, id):
        cache_key = f'book:{id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        obj = Book.objects.select_related('author').filter(id=id).first()
        cache.set(cache_key, obj, CACHE_TTL)
        return obj

    def resolve_books(root, info, limit=20, offset=0):
        qs = Book.objects.all().order_by('-published_at')[offset:offset + limit]
        return qs

# field-level resolver for author that uses DataLoader
class BookNode(DjangoObjectType):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'published_at')

    def resolve_author(self, info):
        loader = info.context.dataloaders['author_by_id']
        promise = loader.load(self.author_id)
        # flush immediately for sync example
        loader.flush()
        return promise

schema = graphene.Schema(query=Query)
```

### f) Mutation with publish & optimistic update
```python
# schema/mutations.py
import graphene
from books.models import Review
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class AddReview(graphene.Mutation):
    class Arguments:
        book_id = graphene.Int(required=True)
        text = graphene.String(required=True)
        rating = graphene.Int(required=True)

    ok = graphene.Boolean()
    review = graphene.Field(ReviewNode)

    def mutate(root, info, book_id, text, rating):
        # create review
        review = Review.objects.create(book_id=book_id, text=text, rating=rating)
        # invalidate book-level cache
        from django.core.cache import cache
        cache.delete(f'book:{book_id}')
        # publish to subscribers via channels
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)('book_reviews_%s' % book_id, {
            'type': 'review.created',
            'review_id': review.id,
        })
        return AddReview(ok=True, review=review)
```

### g) Subscriptions (conceptual)
Use `channels_graphql_ws` or implement a minimal consumer that accepts GraphQL subscriptions. Subscriptions typically listen to channels groups, and on mutation you broadcast changes to groups matching `book_reviews_{book_id}`.

---

## 7. Example advanced GraphQL strategy
A recommended approach for large/critical GraphQL APIs:
- **Operation classification:** maintain a registry of important queries/mutations (persisted queries) for CDN and monitoring.
- **Cost & depth rules:** run cost analysis during CI and at runtime.
- **Client contracts:** use an internal SDK or GraphQL client that references persisted query IDs.
- **Schema ownership:** split responsibilities by domain and, if needed, enable federation for independent deploys.
- **Caching:** combine persisted queries + GET + CDN for read-heavy public operations, and use Redis for object caches with event-driven invalidation.

Example operation policy:
- `GET /graphql?queryId=abc123` used for `TopBooks` query and cached at CDN for 60s.
- Non-persisted arbitrary queries are disabled in production.

---

## 8. Observability & testing
- Add tracing (OpenTelemetry) for resolvers and batch loaders.
- Export resolver latencies, DB query counts, cache hit rates to monitor N+1 regressions.
- Unit test resolvers by mocking DataLoader and cache.
- Integration tests: run an in-memory DB or test DB, exercise complex queries and verify query counts.

---

## 9. Appendix: useful libraries & references
- **Python/Django GraphQL libraries:** `graphene-django`, `ariadne`, `strawberry-graphql`.
- **DataLoader:** `aiodataloader` or the JS DataLoader concept ported to Python.
- **Subscriptions:** `channels_graphql_ws`, `ariadne` subscriptions with ASGI.
- **Federation:** Apollo Federation spec (and community implementations per language).

---

## Final notes & recommendations
1. **Start small:** adopt DataLoader and per-request caches first — they solve the most common N+1 pain.
2. **Persist common read operations** when you need CDN caching.
3. **Automate schema composition checks** and gate schema changes with CI.
4. **Measure before optimizing:** use tracing and metrics to find real hotspots.

---

*If you'd like, I can:*
- convert the Django example to use `ariadne` or `strawberry` instead of `graphene`;
- provide a ready-to-run repository scaffold with Docker and Redis for local testing;
- give a concrete example of federation SDL and gateway configuration.



---

# 📘 Technical Documentation: GraphQL

## 1\. Introduction

APIs are the backbone of communication between client applications (like web, mobile, IoT) and backend services. While **RESTful APIs** dominate most applications, modern apps with **complex and relational data needs** often run into REST’s limitations (over-fetching and under-fetching data).

To address these, **Facebook introduced GraphQL in 2015**. GraphQL is not a replacement for REST but a **query language for APIs** and a **runtime for fulfilling those queries**. It provides flexibility by allowing clients to request exactly the data they need.

## 2\. What is GraphQL?

**GraphQL** is an API query language and execution engine that enables clients to define the structure of the response they need. Unlike REST, which relies on multiple endpoints, GraphQL typically uses a **single endpoint** for all queries and mutations.

### Key Principles of GraphQL

1. **Single Endpoint** → All queries and mutations are sent to a single endpoint (/graphql).
2. **Strongly Typed Schema** → APIs are defined using a schema (types, queries, mutations).
3. **Declarative Data Fetching** → Clients specify exactly what fields they want.
4. **Hierarchical Structure** → Queries mimic the structure of the data returned.
5. **Introspection** → Clients can query the schema to know what operations are supported.
6. **Real-Time Support** → Subscriptions enable real-time updates over WebSockets.

## 3\. GraphQL API Example

Imagine the same **Bookstore API** using GraphQL.

### Schema Definition (simplified)

```graphql
type Book {
  id: ID!
  title: String!
  author: Author!
}

type Author {
  id: ID!
  name: String!
}

type Query {
  books: [Book]
  book(id: ID!): Book
}
```

### Example Query

```graphql
{
  book(id: 1) {
    title
    author {
      name
    }
  }
}
```

### Example Response

```graphql
{
  "data": {
    "book": {
      "title": "The Pragmatic Programmer",
      "author": {
        "name": "Andrew Hunt"
      }
    }
  }
}
```

👉 Notice that the **client decides what fields** (title, author.name) should be returned. No extra fields are fetched.

## 4\. Why Use GraphQL?

### Advantages

- **Flexible Data Fetching** → Avoids over-fetching and under-fetching by returning exactly what is requested.
- **Single Endpoint** → No need for multiple endpoints for related data.
- **Typed Schema** → Provides strong validation and documentation.
- **Faster Development** → Frontend teams can query only the data they need without waiting for backend changes.
- **Real-Time Updates** → Subscriptions allow pushing updates to clients instantly.

## 5\. GraphQL vs Other API Technologies

### 5.1 GraphQL vs REST

| **Feature** | **REST** | **GraphQL** |
| --- | --- | --- |
| Endpoints | Multiple (e.g., /books, /authors) | Single (/graphql) |
| Data Fetching | Fixed structure per endpoint | Client specifies fields |
| Over-fetching | Common (extra unused fields) | Avoided |
| Under-fetching | Common (need multiple requests) | Avoided |
| Learning Curve | Easier | Steeper |
| Best Use Case | CRUD apps, simple data models | Complex, relational data needs |

👉 Example:

- **REST** → GET /books/1 returns entire book object, even if you only need title.
- **GraphQL** → Query only title field.

### 5.2 GraphQL vs SOAP

| **Feature** | **GraphQL** | **SOAP** |
| --- | --- | --- |
| Data Format | JSON | XML |
| Protocol | HTTP only | Multiple (HTTP, SMTP, etc.) |
| Flexibility | High (client chooses fields) | Low (fixed WSDL contract) |
| Performance | Efficient data fetching | Heavy, verbose XML payloads |
| Use Case | Modern web/mobile apps | Enterprise workflows (finance, healthcare) |

### 5.3 GraphQL vs gRPC

| **Feature** | **GraphQL** | **gRPC** |
| --- | --- | --- |
| Data Format | JSON | Protocol Buffers (binary) |
| Transport | HTTP/1.1 (can use HTTP/2) | HTTP/2 |
| Streaming | Limited (via subscriptions) | Strong support (bi-directional) |
| Performance | Good (but JSON parsing overhead) | Excellent (low latency) |
| Use Case | APIs for clients with variable data needs | Microservices, internal services |

## 6\. When to Choose GraphQL?

You should choose **GraphQL** when:

- Your app has **complex, relational data** (e.g., social media, e-commerce).
- You want to **minimize network calls** (mobile apps with limited bandwidth).
- Different clients (web, mobile, IoT) need **different data views**.
- You need **faster frontend iteration** without waiting for backend endpoints.
- Real-time data updates are important (chat apps, live dashboards).

## 7\. Conclusion

GraphQL is a powerful API technology that solves key limitations of REST by giving **flexibility, efficiency, and strong typing**. While REST is still simpler for CRUD-based applications, GraphQL shines when dealing with **complex data requirements, multiple client types, and real-time interactions**.

However, GraphQL also introduces challenges:

- Steeper learning curve.
- Possible performance issues if queries are too large.
- More complex server setup compared to REST.

✅ **In short**:

- Use **GraphQL** when clients need **flexible and efficient data fetching**.
- Use **REST** for simpler apps with standard CRUD operations.
- Use **SOAP** for enterprise, contract-driven integrations.
- Use **gRPC** for **high-performance microservices**.


# 🌐 GraphQL in Django – A Complete Guide

## ✅ What is GraphQL?

**GraphQL** is a query language and runtime for APIs. It allows clients to **request exactly the data they need** and nothing more. It was developed by Facebook in 2012 and released publicly in 2015.

## 🔁 REST vs. GraphQL (Why Choose GraphQL?)

| **Feature** | **REST** | **GraphQL** |
| --- | --- | --- |
| Data Fetching | Fixed endpoints (often over-fetch or under-fetch) | Single endpoint; fetch exactly what’s needed |
| Versioning | Requires versioning (v1, v2) | No versioning; schema evolves |
| Query Flexibility | Not flexible; defined per endpoint | Fully customizable by client |
| Nested Resources | Requires multiple roundtrips | Fetch nested data in one call |
| Overhead | More endpoints, more HTTP calls | One endpoint, less network usage |

**Why use GraphQL in Django?**

- Django's ORM (Object Relational Mapping) makes mapping data to GraphQL types very efficient.
- With graphene-django, you can auto-generate GraphQL types based on Django models.
- Great for building front-end-heavy apps (e.g., React, Angular, Vue).

## 🔧 GraphQL Setup in Django

### 1\. Install dependencies

```bash
pip install graphene-django
```
### 2\. Add to INSTALLED_APPS

```python

INSTALLED_APPS = [

...

'graphene_django',

]
```
### 3\. Add GraphQL endpoint to urls.py

```python
from django.urls import path
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
]

```
## 📁 Recommended File Structure

```lua
project/
├── countries_info_api/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── countries.py
│   │   ├── capitals.py
│   │   └── ...
│   ├── schema/
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── queries.py
│   │   ├── mutations.py
│   │   └── schema.py
├── project/
│   ├── settings.py
│   └── urls.py

```
## 🔠 Define GraphQL Types (types.py)

```python
import graphene
from graphene_django.types import DjangoObjectType
from countries_info_api.models.countries import Country
from countries_info_api.models.capitals import Capital

class CountryType(DjangoObjectType):
    class Meta:
        model = Country

class CapitalType(DjangoObjectType):
    class Meta:
        model = Capital

```
## 🔍 Queries (queries.py)

```python
class Query(graphene.ObjectType):
    all_countries = graphene.List(CountryType)
    country_by_code = graphene.Field(CountryType, cca2=graphene.String(required=True))

    def resolve_all_countries(root, info):
        return Country.objects.all()

    def resolve_country_by_code(root, info, cca2):
        return Country.objects.filter(cca2=cca2).first()

```

### Sample Query

```graphql
query {
  allCountries {
    cca2
    name
    region {
      name
    }
    capitals {
      name
    }
  }
}

```

## ✍️ Mutations (mutations.py)

### Add Country (Create)

```python
class CreateCountry(graphene.Mutation):
    class Arguments:
        cca2 = graphene.String(required=True)
        name = graphene.JSONString(required=True)

    country = graphene.Field(CountryType)

    def mutate(self, info, cca2, name):
        country = Country.objects.create(cca2=cca2, name=name)
        return CreateCountry(country=country)

```
### Update Country

```python
class UpdateCountry(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.JSONString()

    country = graphene.Field(CountryType)

    def mutate(self, info, id, name=None):
        country = Country.objects.get(pk=id)
        if name:
            country.name = name
        country.save()
        return UpdateCountry(country=country)

```
### Delete Country

```python
class DeleteCountry(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        country = Country.objects.get(pk=id)
        country.delete()
        return DeleteCountry(ok=True)

```
### Register Mutation

```python
class Mutation(graphene.ObjectType):
    create_country = CreateCountry.Field()
    update_country = UpdateCountry.Field()
    delete_country = DeleteCountry.Field()

```
## 🔗 Connect Schema (schema.py)

```python
import graphene
from countries_info_api.schema.queries import Query
from countries_info_api.schema.mutations import Mutation

schema = graphene.Schema(query=Query, mutation=Mutation)

```
## 🧪 Sample Mutation Requests

### Create

```graphql
mutation {
  createCountry(cca2: "BD", name: "{\"en\": \"Bangladesh\"}") {
    country {
      cca2
      name
    }
  }
}

```

### Update

```graphql
mutation {
  updateCountry(id: 1, name: "{\"en\": \"New Bangladesh\"}") {
    country {
      name
    }
  }
}

```
### Delete

```graphql
mutation {
  deleteCountry(id: 1) {
    ok
  }
}

```
## 🔄 Reverse Relationships

If Capital has a ForeignKey to Country, Graphene Django will automatically generate a reverse relationship field like capitalSet.

You can alias it:

```python
class CountryType(DjangoObjectType):
    class Meta:
        model = Country

    capitals = graphene.List(CapitalsType)

    def resolve_capitals(self, info):
        return self.capital_set.all()

```
## ✅ Advanced Best Practices

1. **Avoid N+1 Queries**: Use select_related and prefetch_related.
2. **Pagination**: Use graphene_django_extras or custom connection.
3. **Authorization**: Use info.context.user for per-user filtering.
4. **Validation**: Always validate input in mutations.
5. **Modularize Code**: Break types, queries, mutations into files.

## 📌 Summary (Why GraphQL?)

- 📚 **Single Endpoint** for all data interactions.
- ⚡ **Optimized performance** (avoid over-fetching).
- 🎯 **Client-controlled queries** (great for frontend apps).
- 📖 **Schema-based**, auto-documented API.

## 🚀 Tools to Explore

- **GraphQL Playground** or **GraphiQL** – to interact with your schema
- **Apollo Client** – frontend integration
- **Django Debug Toolbar** – for query performance
- **graphene-django-extras** – for pagination, filtering


# Technical Documentation: Authentication & Security in GraphQL

## 1\. Introduction

Authentication and security are critical in any API. In **REST**, authentication is often tied to multiple endpoints, while in **GraphQL**, there is typically a **single endpoint** (/graphql) serving all queries and mutations. Despite the single endpoint, **GraphQL fully supports HTTP headers**, so authentication works in a very similar way to REST.

This document explains **how authentication works in GraphQL**, common strategies, implementation examples in **Python/Django**, and a **reference comparison with REST**.

## 2\. Authentication in GraphQL

### 2.1 HTTP Headers in GraphQL

GraphQL queries are transported over HTTP(S), so you can use standard HTTP headers:

- **Authorization** → Bearer token or API key.
- **Content-Type** → Usually ```text application/json ```.
- **Custom headers** → e.g., ```text X-Client-ID ```, ```text X-Request-ID ```.

#### Example HTTP Request

```http
POST /graphql
Host: api.example.com
Content-Type: application/json
Authorization: Bearer <your_token>

{
  "query": "{ me { id name email } }"
}
```

The server extracts the token from the Authorization header and authenticates the user.

### 2.2 Authentication Points

Authentication can be applied at two levels:

1. **Middleware (Global)**
    - Authenticates every request before executing any resolver.
    - Example: Django middleware parses JWT and attaches user to request.context.
2. **Resolver (Fine-grained)**
    - Individual fields or queries can enforce access control.
    - Example: Only allow a user to fetch **their own profile**.

#### Example in Django (Graphene)

```python
import graphene
from graphql_jwt.decorators import login_required

class Query(graphene.ObjectType):
    me = graphene.Field(UserType)

    @login_required
    def resolve_me(self, info):
        user = info.context.user
        return user
```

- login_required decorator checks the Authorization header.
- Invalid or missing token → returns authentication error.

## 3\. Common Authentication Strategies in GraphQL

| **Strategy** | **How It Works** | **Use Case** |
| --- | --- | --- |
| **Bearer Token (JWT/OAuth2)** | Client sends Authorization: Bearer &lt;token&gt; header | Mobile apps, Single-page apps |
| **API Keys** | Sent via header or query param | Server-to-server or public API |
| **Session Cookies** | Uses browser cookies for authentication | Web apps, browser-based GraphQL clients |
| **Custom Headers** | Pass additional metadata in headers | Multi-tenant APIs, client identification |

## 4\. Authorization & Field-Level Security

GraphQL allows **fine-grained authorization**:

- Each resolver can check the user’s permissions.
- Example: Restrict access to a user’s own data.

class Query(graphene.ObjectType):

```python
class Query(graphene.ObjectType):
    my_courses = graphene.List(CourseType)

    @login_required
    def resolve_my_courses(self, info):
        user = info.context.user
        return Course.objects.filter(student=user)
```

This ensures even with one endpoint, different users only access their authorized resources.

## 5\. Common Security Best Practices

1. **Use HTTPS** for encrypted communication.
2. **Validate Authorization tokens** at the middleware level.
3. **Apply field-level authorization** in resolvers.
4. **Set query depth limits** to prevent abuse.
5. **Rate-limit requests** to prevent brute-force attacks.

## 6\. REST vs GraphQL Authentication Flows

| **Feature / Aspect** | **REST** | **GraphQL** |
| --- | --- | --- |
| Endpoint | Multiple (/users, /posts) | Single (/graphql) |
| Header Usage | Standard (Authorization) | Standard (Authorization) |
| Authentication Location | Per endpoint | Middleware (global) & resolvers (fine-grained) |
| Authorization Granularity | Coarse (per endpoint) | Fine-grained (per field/resolver) |
| Token Extraction | From request headers | From request headers (same as REST) |
| Session / Cookie Support | Yes | Yes (browser-based) |
| Use Case Examples | RESTful web APIs | Web/mobile apps, single endpoint, microservices |
| Security Complexity | Low-moderate | Moderate-high (fine-grained access control) |

## 7\. Example Authentication Flow in GraphQL

1. Client sends query with Authorization header.
2. Middleware extracts and validates the token.
3. Middleware attaches user object to info.context.
4. Resolver accesses info.context.user to enforce field-level permissions.
5. Server returns data or an authentication/authorization error.

## 8\. Conclusion

- GraphQL **supports HTTP headers just like REST**, so all familiar authentication mechanisms work.
- Single endpoint does not reduce security — **middleware + resolver-level checks** provide robust protection.
- Fine-grained field-level authorization is easier in GraphQL compared to REST.
- Properly implemented, GraphQL authentication and authorization can be **as secure or more secure** than REST.

✅ **Key Takeaways**:

- Use **Authorization headers** in GraphQL like REST.
- Apply **middleware for global authentication**.
- Use **resolver-level checks for fine-grained access**.
- Always secure **transport (HTTPS)** and validate tokens.