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