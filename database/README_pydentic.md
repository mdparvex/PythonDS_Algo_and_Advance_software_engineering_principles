Pydantic — Complete Technical Documentation
===========================================

This document explains **all features of Pydantic (v2)** with examples, outputs, and explanations. Where relevant, Pydantic v1 differences are also noted.

---

Contents
--------
1. Introduction  
2. Quick Start  
3. Core Concepts  
4. Fields & Constraints  
5. Validation (field, model, root)  
6. Serialization & Parsing  
7. Settings & Environment Variables  
8. Dataclasses & ORM Mode  
9. Generics & TypeAdapter  
10. Advanced Topics (Custom Types, Error Handling, Performance)  
11. Migration from v1 to v2  
12. Examples & Recipes  
13. FAQ & Best Practices  

---

1. Introduction
---------------
Pydantic is a Python library that uses **type hints** for:
- Data validation (incoming data → validated Python objects)
- Automatic type coercion
- Settings management
- Serialization / deserialization

**Key advantages:**
- Clear data contracts
- Automatic error messages
- JSON schema generation
- Fast performance (v2 is up to 5x faster than v1)

---

2. Quick Start
--------------
```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class User(BaseModel):
    id: int
    name: str
    signup_ts: Optional[date] = None
    friends: List[int] = []

# Example input
data = {"id": "123", "name": "Alice", "signup_ts": "2025-10-01", "friends": [1, "2", 3]}

user = User.model_validate(data)
print(user)
```
**Output:**
```
id=123 name='Alice' signup_ts=datetime.date(2025, 10, 1) friends=[1, 2, 3]
```
Explanation: Pydantic **coerces types** automatically: string "123" → int, string "2" → int.

---

3. Core Concepts
----------------
- **BaseModel**: A class with typed attributes.
- **Field**: Extra metadata and constraints.
- **Validation**: Runs at initialization or via `model_validate`.
- **Serialization**: Use `model_dump` (dict) and `model_dump_json` (JSON string).
- **Errors**: Pydantic raises `ValidationError` with detailed messages.

---

4. Fields & Constraints
-----------------------
```python
from pydantic import BaseModel, Field
from typing import Annotated

class Product(BaseModel):
    name: Annotated[str, Field(min_length=1)]
    price: Annotated[float, Field(gt=0)]
    stock: Annotated[int, Field(ge=0, le=100)]

product = Product(name="Pen", price="12.5", stock="10")
print(product)
```
**Output:**
```
name='Pen' price=12.5 stock=10
```
Explanation: `Annotated` + `Field` allow you to specify constraints.

---

5. Validation
-------------
### Field Validator
```python
from pydantic import BaseModel, field_validator

class Person(BaseModel):
    name: str
    age: int

    @field_validator('age')
    def check_age(cls, v):
        if v < 0:
            raise ValueError("Age must be positive")
        return v

p = Person(name="John", age=30)
print(p)
```
**Output:**
```
name='John' age=30
```

### Model Validator (cross-field)
```python
from pydantic import BaseModel, model_validator

class Interval(BaseModel):
    start: int
    end: int

    @model_validator(mode="after")
    def validate_interval(cls, values):
        if values.start >= values.end:
            raise ValueError("start must be less than end")
        return values

interval = Interval(start=1, end=5)
print(interval)
```
**Output:**
```
start=1 end=5
```

---

6. Serialization & Parsing
--------------------------
```python
class User(BaseModel):
    id: int
    name: str

u = User(id=1, name="Alice")
print(u.model_dump())
print(u.model_dump_json())
```
**Output:**
```
{'id': 1, 'name': 'Alice'}
{"id":1,"name":"Alice"}
```
Explanation: `.model_dump()` returns dict, `.model_dump_json()` returns JSON string.

---

7. Settings & Environment Variables
-----------------------------------
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "MyApp"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
print(settings)
```
Explanation: Values are read from environment variables or `.env` file.

---

8. Dataclasses & ORM Mode
--------------------------
### Dataclasses
```python
from pydantic.dataclasses import dataclass

@dataclass
class Item:
    id: int
    name: str
```

### ORM Mode
```python
class UserModel(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
```
Explanation: `from_attributes=True` allows loading from ORM objects.

---

9. Generics & TypeAdapter
--------------------------
```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class Response(BaseModel, Generic[T]):
    data: T
    errors: List[str] = []

resp = Response[int](data=123)
print(resp)
```
**Output:**
```
data=123 errors=[]
```

TypeAdapter:
```python
from pydantic import TypeAdapter

adapter = TypeAdapter(List[int])
validated = adapter.validate_python(["1", "2"])
print(validated)
```
**Output:**
```
[1, 2]
```

---

10. Advanced Topics
-------------------
### Custom Types
```python
class EvenInt:
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        v = int(v)
        if v % 2 != 0:
            raise ValueError("Number must be even")
        return v

class Model(BaseModel):
    x: EvenInt

m = Model(x="4")
print(m)
```
**Output:**
```
x=4
```

### Error Handling
```python
from pydantic import ValidationError

try:
    User(id="x", name="Bob")
except ValidationError as e:
    print(e.errors())
```
**Output:**
```
[{'type': 'int_parsing', 'loc': ('id',), 'msg': 'Input should be a valid integer', 'input': 'x'}]
```

---

11. Migration from v1 to v2
----------------------------
- `.dict()` → `.model_dump()`
- `.parse_obj()` → `.model_validate()`
- `@validator` → `@field_validator`
- `@root_validator` → `@model_validator`
- `Config` → `model_config`
- `orm_mode = True` → `from_attributes=True`

---

12. Examples & Recipes
-----------------------
### Normalizing Input
```python
class Word(BaseModel):
    expected: str
    spoken: str

    @field_validator("spoken", mode="before")
    def normalize(cls, v):
        return v.strip().lower()

    @model_validator(mode="after")
    def compare(cls, m):
        m.correct = (m.spoken == m.expected.lower())
        return m

word = Word(expected="Apple", spoken=" apple ")
print(word.correct)
```
**Output:**
```
True
```

---

13. FAQ & Best Practices
-------------------------
- Use **field validators** for single-field checks.
- Use **model validators** for cross-field validation.
- Prefer **Annotated + Field** for constraints.
- Use **TypeAdapter** for runtime validation without models.
- For configs, use **pydantic-settings**.
- Always choose **v2** for new projects.

---

**Closing Note:**  
Pydantic brings type safety, validation, and serialization together. It is widely used in **FastAPI** and backend services. With v2’s speed and cleaner API, it should be the default choice for new Python projects.

