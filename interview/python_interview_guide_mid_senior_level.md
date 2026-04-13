# Python Interview Guide (Mid/Senior Level)

## 1. Python Fundamentals

### Data Types
- Immutable: int, float, str, tuple
- Mutable: list, dict, set

```python
x = 10
y = x
x += 1
print(y)  # 10 (immutable behavior)
```

### Deep vs Shallow Copy
```python
import copy
lst1 = [[1, 2], [3, 4]]
lst2 = copy.copy(lst1)
lst3 = copy.deepcopy(lst1)
```

---

## 2. Functions & Closures

### First-Class Functions
```python
def greet(name):
    return f"Hello {name}"

func = greet
print(func("Mamun"))
```

### Closures
```python
def outer(x):
    def inner(y):
        return x + y
    return inner

add5 = outer(5)
print(add5(3))  # 8
```

---

## 3. OOP (Object-Oriented Programming)

### Classes & Inheritance
```python
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Bark"
```

### Dunder Methods
```python
class Book:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
```

### Multiple Inheritance & MRO
```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print(D.__mro__)
```

---

## 4. Decorators

```python
def logger(func):
    def wrapper(*args, **kwargs):
        print("Calling function")
        return func(*args, **kwargs)
    return wrapper

@logger
def add(a, b):
    return a + b
```

---

## 5. Generators & Iterators

```python
def count_up(n):
    for i in range(n):
        yield i
```

### Generator Expression
```python
squares = (x*x for x in range(5))
```

---

## 6. Exception Handling

```python
try:
    x = int("abc")
except ValueError:
    print("Conversion failed")
finally:
    print("Done")
```

---

## 7. Python Internals

### Memory Management
- Reference counting
- Garbage collection

### GIL (Global Interpreter Lock)
- Only one thread executes Python bytecode at a time

---

## 8. Multithreading vs Multiprocessing

```python
from multiprocessing import Process

def task():
    print("Running task")

p = Process(target=task)
p.start()
p.join()
```

---

## 9. Async Programming

```python
import asyncio

async def fetch():
    await asyncio.sleep(1)
    return "data"

async def main():
    result = await fetch()
    print(result)

asyncio.run(main())
```

---

## 10. Data Structures & Algorithms

### Common Topics
- Arrays, Linked Lists, Stacks, Queues
- HashMaps (dict)
- Trees, Graphs

### Example: Two Sum
```python
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target-n], i]
        seen[n] = i
```

---

## 11. Pythonic Coding

### List Comprehension
```python
squares = [x*x for x in range(10) if x % 2 == 0]
```

### Tuple Comprehension
```python
squares = tuple(x*x for x in range(10) if x % 2 == 0)
```

### EAFP vs LBYL
```python
# EAFP
try:
    value = d["key"]
except KeyError:
    value = None
```

---

## 12. Testing

### unittest
```python
import unittest

class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1+1, 2)
```

---

## 13. Packaging & Virtual Environments

- venv
- pip
- requirements.txt

---

## 14. Django/DRF (Important for Backend Roles)

### Serializer Example
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
```

### ViewSet Example
```python
class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
```

---

## 15. Database Concepts

- Indexing
- Transactions (ACID)
- ORM vs Raw SQL

---

## 16. System Design (Python Backend)

### Topics to Cover
- Scalability
- Caching (Redis)
- Message Queues (Kafka, RabbitMQ)
- Load Balancing

---

## 17. Common Interview Questions

1. Difference between list and tuple?
2. What is GIL?
3. Explain decorators.
4. How does Python manage memory?
5. Difference between threading and multiprocessing?
6. What is async/await?
7. What is MRO?

---

## 18. Best Practices

- Follow PEP8
- Write readable code
- Use type hints

```python
def add(a: int, b: int) -> int:
    return a + b
```

---

## 19. Advanced Topics

- Metaclasses
- Context Managers

```python
from contextlib import contextmanager

@contextmanager
def open_file(name):
    f = open(name)
    yield f
    f.close()
```

---

## 20. Tips for Interview

- Explain trade-offs clearly
- Write clean code
- Think aloud
- Clarify requirements before coding

---

## 21. Advanced Python Internals (Deep Dive)

### 21.1 How Python Executes Code (CPython Execution Model)
- Source code → Bytecode (compiled by CPython)
- Bytecode runs on Python Virtual Machine (PVM)

```python
import dis

def add(a, b):
    return a + b

print(dis.dis(add))
```

Key Insight:
- Python is **interpreted but compiled to bytecode first**
- `.pyc` files store bytecode for faster loading

---

### 21.2 Memory Management Internals

#### Reference Counting
```python
import sys
x = []
print(sys.getrefcount(x))
```
- Every object keeps a reference count
- When it reaches 0 → memory is freed

#### Garbage Collector (GC)
- Handles **circular references**

```python
import gc
gc.collect()
```

Key Insight:
- Reference counting is fast
- GC is backup for cycles

---

### 21.3 GIL (Global Interpreter Lock) Deep Dive

- Ensures only **one thread executes Python bytecode at a time**
- Exists because CPython memory management is not thread-safe

#### Why GIL exists?
- Simplifies memory management
- Prevents race conditions in reference counting

#### When GIL is NOT a problem:
- I/O-bound tasks (API calls, DB queries)

#### When it IS a problem:
- CPU-bound tasks (heavy computation)

Solution:
- Use multiprocessing instead of threading

---

### 21.4 Mutable vs Immutable Internals

```python
a = 10
b = a
a += 1
```
- New object is created for immutable types

```python
lst = [1, 2]
lst.append(3)
```
- Same object is modified (mutable)

Key Insight:
- Impacts performance, memory, and thread safety

---

### 21.5 Object Model (Everything is an Object)

```python
x = 5
print(type(x))
print(id(x))
```

- Every object has:
  - Identity (`id`)
  - Type
  - Value

---

### 21.6 `__slots__` Optimization

```python
class A:
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y
```

Benefits:
- Reduces memory usage
- Faster attribute access

Trade-off:
- No dynamic attribute assignment

---

### 21.7 Descriptor Protocol

Core of Python internals (used in Django ORM, properties)

```python
class Descriptor:
    def __get__(self, obj, objtype):
        return "value"
```

Used in:
- `@property`
- ORM fields

---

### 21.8 Metaclasses

"Class of a class"

```python
class Meta(type):
    def __new__(cls, name, bases, dct):
        print("Creating class")
        return super().__new__(cls, name, bases, dct)

class MyClass(metaclass=Meta):
    pass
```

Use cases:
- Framework design (Django models)
- Enforcing rules

---

### 21.9 Context Managers Internals

```python
class FileManager:
    def __enter__(self):
        print("Enter")
        return self

    def __exit__(self, exc_type, exc, tb):
        print("Exit")
```

Used with:
```python
with FileManager():
    pass
```

---

### 21.10 Python Import System

Steps:
1. Check `sys.modules`
2. Built-in modules
3. Search in `sys.path`

Key Insight:
- Modules are cached after first import

---

### 21.11 Bytecode vs Machine Code

- Python → Bytecode
- Bytecode → Executed by PVM

Not compiled directly to machine code like C/C++

---

### 21.12 Function Call Stack & Frames

```python
import inspect

def func():
    frame = inspect.currentframe()
    print(frame.f_code.co_name)
```

- Each function call creates a **frame object**
- Stored in call stack

---

### 21.13 Interning & Optimization

```python
a = 256
b = 256
print(a is b)  # True (cached)
```

- Small integers & strings are cached

---

### 21.14 Deep Interview Questions (With Answers)

#### Q1: Why is Python slow?
- Interpreted
- Dynamic typing
- GIL

#### Q2: How does Python handle memory?
- Reference counting + GC

#### Q3: Why does GIL exist?
- Simplifies thread safety for memory management

#### Q4: Difference between `is` and `==`?
- `is` → identity
- `==` → value equality

#### Q5: What happens during `import`?
- Module search → compile → cache in `sys.modules`

#### Q6: How decorators work internally?
- Function wrapping + closures

---

End of Guide

