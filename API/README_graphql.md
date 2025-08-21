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