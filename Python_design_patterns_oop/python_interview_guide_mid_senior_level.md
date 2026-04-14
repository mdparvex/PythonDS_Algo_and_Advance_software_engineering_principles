# Python Interview Guide (Mid/Senior Level)

## 1. Python Fundamentals

### Data Types
- Immutable: Numeric types: int, float, complex; Strings: str; Tuples: tuple ; Frozen Sets: frozenset; Bytes: bytes
    - An immutable object cannot be changed after it is created. If you try to "modify" an immutable object, Python actually creates a brand-new object in memory with the new value and points your variable name to it
- Mutable: Lists: list; Dictionaries: dict; Sets: set; Byte Arrays: bytearray; User-defined Classes: (Generally mutable unless designed otherwise)
    - A mutable object can be changed "in-place." This means you can update, add, or delete parts of the data without creating an entirely new object in memory.

```python
x = 10
print(id(x)) 
y = x
x += 1
print(id(x))
# both id(memory address) will be different
print(y)  # 10 (immutable behavior)

fruits = ["apple", "banana"]
print(id(fruits))

fruits.append("cherry") 
print(fruits)      # ["apple", "banana", "cherry"]
print(id(fruits))  # The memory address remains exactly the same!
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

### Closures : Closure is a function object that remembers values in the enclosing scope even if they are no longer present in memory.
#### closures are most commonly used in Decorators and Middleware
```python
def outer(x):
    def inner(y):
        return x + y
    return inner

add5 = outer(5)
print(add5(3))  # 8

# Real examples
from django.http import HttpResponseForbidden

def check_clearance(level_required):
    # The 'level_required' is trapped in the closure
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.profile.clearance_level < level_required:
                return HttpResponseForbidden("Access Denied")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

@check_clearance(level_required=5)
def secret_view(request):
    return HttpResponse("Welcome to the Vault.")
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
### Real Uses of Generators
Generators are used when you need to produce or transform data on the fly. Because they use "lazy evaluation," they don't calculate a value until you specifically ask for it. 

- Processing Massive Files: Reading a 10GB log file line-by-line. A normal function would try to load the whole file into RAM, while a generator yields one line at a time.
- Data Science Pipelines: In Machine Learning, generators (like those in Keras) load and preprocess images in small batches so you don't run out of GPU memory.
- Infinite Streams: Representing sequences that never end, such as a continuous stream of sensor data, real-time stock prices from an API, or mathematical sequences like Fibonacci.
- Web Scraping: Efficiently parsing through thousands of HTML elements one-by-one rather than storing every page's entire content at once. 

### Real Uses of Iterators
Iterators are used when you need precise control over state or need to add iteration capabilities to a complex custom object. 

- Custom Data Structures: If you build a custom database or tree-like data structure, you implement the Iterator Protocol (__iter__ and __next__) so other developers can use a standard for loop on your object.
- Stateful Traversal: Used when you need to "pause" and "resume" progress through a collection across different parts of your application. The iterator "remembers" its exact position.
- Memory-Efficient Transformations: Creating a class that takes an input (like a list of numbers) and iterates over their squares. This avoids creating a whole new "squared" list in memory. 

```python
# 1. GENERATOR EXAMPLE: Processing a 10GB Log File
# This is the most common real-world use case. 
# It only keeps ONE line in RAM at a time.

def log_reader(file_path):
    """A generator that yields lines from a file one by one."""
    with open(file_path, "r") as file:
        for line in file:
            # The 'yield' keyword pauses the function and returns the line
            yield line.strip()

# Usage:
# Even if 'large_log.txt' is 10GB, this loop uses almost no RAM
for log_entry in log_reader("large_log.txt"):
    if "ERROR" in log_entry:
        print(f"Found issue: {log_entry}")


# 2. ITERATOR EXAMPLE: Custom Data Structure
# This shows how to build the 'Iterator Protocol' manually using a class.

class Countdown:
    """A custom iterator class that counts down to zero."""
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        # An iterator must return itself
        return self

    def __next__(self):
        # Manually managing the state and raising StopIteration
        if self.current <= 0:
            raise StopIteration
        
        value = self.current
        self.current -= 1
        return value

# Usage:
counter = Countdown(3)
for num in counter:
    print(num) # Output: 3, 2, 1
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

