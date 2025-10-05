# FastAPI Dependency Injection: Technical Documentation

This document provides a comprehensive guide to **Dependency Injection (DI)** in FastAPI, with code examples, outputs, and detailed explanations.

---

## 1. Introduction
Dependency Injection (DI) is a design pattern where objects or functions receive their dependencies from external sources rather than creating them directly. In FastAPI, DI is a core feature and is achieved using the `Depends` utility.

### Benefits of DI
- Promotes clean and modular code
- Enhances reusability of logic
- Simplifies testing
- Reduces code duplication

---

## 2. Basic Dependency Injection

### Example
```python
from fastapi import FastAPI, Depends

app = FastAPI()

def common_parameters(q: str = None, skip: int = 0, limit: int = 10):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
def read_items(commons: dict = Depends(common_parameters)):
    return commons
```

### Explanation
- `common_parameters` defines a dependency.
- `Depends(common_parameters)` injects it into `read_items`.
- FastAPI automatically calls `common_parameters` and passes its return value.

### Output Example
```
GET /items?q=test&skip=5&limit=20
Response: {"q": "test", "skip": 5, "limit": 20}
```

---

## 3. Class-Based Dependencies
Dependencies can also be structured as classes.

### Example
```python
from fastapi import FastAPI, Depends

app = FastAPI()

class CommonQueryParams:
    def __init__(self, q: str = None, skip: int = 0, limit: int = 10):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/users/")
def read_users(commons: CommonQueryParams = Depends()):
    return {"q": commons.q, "skip": commons.skip, "limit": commons.limit}
```

### Explanation
- A class with an `__init__` method can serve as a dependency.
- FastAPI instantiates the class and injects it.

---

## 4. Sub-Dependencies
Dependencies can depend on other dependencies.

### Example
```python
from fastapi import FastAPI, Depends

app = FastAPI()

def query_extractor(q: str = None):
    return q

def query_or_cookie_extractor(q: str = Depends(query_extractor), last_query: str = None):
    if not q:
        return last_query
    return q

@app.get("/search")
def search(query: str = Depends(query_or_cookie_extractor)):
    return {"query": query}
```

### Explanation
- `query_or_cookie_extractor` depends on `query_extractor`.
- This chaining is called **sub-dependency**.

---

## 5. Dependencies with Yield (Context Managers)
For dependencies that require setup and teardown, `yield` is used.

### Example
```python
from fastapi import FastAPI, Depends

app = FastAPI()

def get_db():
    db = {"connection": "Database Connected"}
    try:
        yield db
    finally:
        db["connection"] = "Database Disconnected"

@app.get("/db")
def read_db(db: dict = Depends(get_db)):
    return db
```

### Explanation
- `yield` provides the dependency value.
- After the request, cleanup runs after the `yield` statement.

---

## 6. Security Dependencies
Dependencies can enforce authentication and authorization.

### Example
```python
from fastapi import FastAPI, Depends, HTTPException, status

app = FastAPI()

def get_current_user(token: str):
    if token != "secrettoken":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )
    return {"user": "admin"}

@app.get("/profile")
def read_profile(user: dict = Depends(get_current_user)):
    return user
```

### Explanation
- Dependencies can validate tokens or sessions.
- Prevents code duplication in multiple routes.

---

## 7. Dependency Injection in Path Operations, Sub-Applications, and Routers
You can apply dependencies globally at:
- **Path operation level**
- **Router level**
- **Application level**

### Example
```python
from fastapi import FastAPI, Depends, APIRouter

app = FastAPI()

async def verify_token(token: str):
    if token != "validtoken":
        raise HTTPException(status_code=403, detail="Invalid Token")

router = APIRouter(
    prefix="/items",
    dependencies=[Depends(verify_token)],
)

@router.get("/")
async def get_items():
    return ["item1", "item2"]

app.include_router(router)
```

---

## 8. Advanced Example: Combining Multiple Dependencies

```python
from fastapi import FastAPI, Depends

app = FastAPI()

def dependency_a():
    return "A"

def dependency_b():
    return "B"

def dependency_c(a: str = Depends(dependency_a), b: str = Depends(dependency_b)):
    return f"Combined: {a} + {b}"

@app.get("/combine")
def combine(result: str = Depends(dependency_c)):
    return {"result": result}
```

### Output
```
GET /combine
Response: {"result": "Combined: A + B"}
```

---

## 9. Best Practices
- Keep dependencies small and focused.
- Use classes for grouping related parameters.
- Use `yield` for setup/teardown tasks.
- Reuse dependencies for authentication, logging, and DB sessions.
- Apply dependencies at router/application level for cross-cutting concerns.

---

## 10. Conclusion
FastAPI's dependency injection system is a powerful and flexible way to manage common functionality across endpoints. It supports simple functions, classes, sub-dependencies, security checks, and even resource management with `yield`.

In production, DI helps ensure modular, testable, and maintainable applications.

