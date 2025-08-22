I’ll prepare a **comprehensive, structured technical documentation** that covers **Iterators, Generators, Context Managers, Decorators, functools, itertools, Collections, and Advanced Python features**.

# 📘 Technical Documentation: Advanced Python Features

## 1\. Introduction

Python provides a rich set of **advanced features** that help developers write **clean, efficient, and Pythonic code**. This documentation explains core concepts like **iterators, generators, context managers, decorators, functools, itertools, collections**, and other advanced features, with examples for practical understanding.

## 2\. Iterators

### 2.1 What is an Iterator?

- An **iterator** is an object that implements two methods:
  - \__iter_\_() → returns the iterator object itself.
  - \__next_\_() → returns the next item or raises StopIteration when finished.

### 2.2 Example: Custom Iterator

```python
class Counter:
    def __init__(self, start, end):
        self.current = start
        self.end = end

    def __iter__(self):
        return self

    def __next__(self):
        if self.current <= self.end:
            value = self.current
            self.current += 1
            return value
        else:
            raise StopIteration

for num in Counter(1, 5):
    print(num)
```

✅ Prints: 1 2 3 4 5

## 3\. Generators

### 3.1 What is a Generator?

- A **generator** is a simpler way to create iterators using the yield keyword.
- Generators save memory since values are **generated lazily**.

### 3.2 Example: Fibonacci Generator

```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

for num in fibonacci(5):
    print(num)
```

✅ Output: 0 1 1 2 3

## 4\. Context Managers

### 4.1 What is a Context Manager?

- A **context manager** manages resources (like files, database connections).
- Implements:
  - \__enter_\_() → setup
  - \__exit_\_() → cleanup

### 4.2 Example: File Context Manager

```python
with open("example.txt", "w") as f:
    f.write("Hello, Python!")
```

✅ Automatically closes file after use.

### 4.3 Custom Context Manager

```python
class ManagedResource:
    def __enter__(self):
        print("Resource acquired")
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Resource released")

with ManagedResource():
    print("Using resource")
```

## 5\. Decorators

### 5.1 What is a Decorator?

- A **decorator** is a function that takes another function and extends/modifies its behavior without changing the function itself.
- Implemented using **@ syntax**.

### 5.2 Example: Logging Decorator

```python
def logger(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@logger
def greet(name):
    print(f"Hello, {name}")

greet("Alice")
```

✅ Output:

Calling greet

Hello, Alice

## 6\. functools Module

The **functools** module provides higher-order functions and decorators.

### 6.1 lru_cache

Caches results of expensive function calls.

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def factorial(n):
    return 1 if n == 0 else n * factorial(n-1)

print(factorial(10))
```

### 6.2 partial

Fixes some arguments of a function.

```python
from functools import partial

def power(base, exp):
    return base ** exp

square = partial(power, exp=2)
print(square(5))  # 25
```

### 6.3 reduce

Performs cumulative operations.

```python
from functools import reduce

nums = [1, 2, 3, 4]
result = reduce(lambda x, y: x + y, nums)
print(result)  # 10
```

## 7\. itertools Module

The **itertools** module provides efficient looping utilities.

### 7.1 Infinite Iterators

```python
import itertools

for i in itertools.count(10, 2):  # start=10, step=2
    if i > 20: break
    print(i)
```

### 7.2 Combinatorics

```python
import itertools

nums = [1, 2, 3]
print(list(itertools.permutations(nums, 2)))
print(list(itertools.combinations(nums, 2)))
```

✅ Output:

- Permutations: \[(1,2),(1,3),(2,1),(2,3),(3,1),(3,2)\]
- Combinations: \[(1,2),(1,3),(2,3)\]

## 8\. collections Module

### 8.1 Counter

```python
from collections import Counter
words = ["apple", "banana", "apple", "orange"]
print(Counter(words))
```

✅ Output: Counter({'apple': 2, 'banana': 1, 'orange': 1})

### 8.2 defaultdict

```python
from collections import defaultdict
d = defaultdict(int)
d["a"] += 1
print(d)  # defaultdict(<class 'int'>, {'a': 1})
```

### 8.3 deque

Efficient double-ended queue.

```python
from collections import deque
dq = deque([1,2,3])
dq.appendleft(0)
dq.append(4)
print(dq)  # deque([0,1,2,3,4])
```

### 8.4 namedtuple

```python
from collections import namedtuple
Point = namedtuple("Point", ["x", "y"])
p = Point(10, 20)
print(p.x, p.y)
```

## 9\. Advanced Python Features

### 9.1 List/Dict Comprehensions

```python
squares = [x*x for x in range(5)]
print(squares)
```

### 9.2 Generators & Lazy Evaluation

```python
gen = (x*x for x in range(5))
print(next(gen))  # 0
```

### 9.3 \*args and \*\*kwargs

```python
def func(*args, **kwargs):
    print("Args:", args)
    print("Kwargs:", kwargs)

func(1,2,3, a=10, b=20)
```

### 9.4 Metaclasses

Metaclasses define how classes behave.

```python
class Meta(type):
    def __new__(cls, name, bases, dct):
        print(f"Creating class {name}")
        return super().__new__(cls, name, bases, dct)

class MyClass(metaclass=Meta):
    pass
```

### 9.5 Coroutines (async/await)

```python
import asyncio

async def greet():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

asyncio.run(greet())
```

## 10\. Best Practices

- Use **generators** for large data to save memory.
- Use **context managers** to ensure resource cleanup.
- Use **decorators** for cross-cutting concerns (logging, caching, auth).
- Prefer **itertools/collections** for cleaner and faster code.
- Use **functools.lru_cache** for memoization in expensive computations.

## 11\. Summary

- **Iterators & Generators** → Lazy iteration and memory efficiency.
- **Context Managers** → Manage resources cleanly.
- **Decorators** → Enhance functions without modifying code.
- **functools, itertools, collections** → Provide advanced utilities for functional programming, iteration, and data handling.
- **Advanced features** (comprehensions, coroutines, metaclasses) → Make Python highly expressive and powerful.