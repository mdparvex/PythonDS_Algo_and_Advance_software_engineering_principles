here’s a **well-structured technical documentation** covering **Typing & Type Hints, Mypy, and Regular Expressions** in Python, with explanations and examples.

# 📘 Technical Documentation: Typing, Type Hints, Mypy & Regular Expressions

## 1\. Introduction

Python is a dynamically typed language, but with the introduction of **type hints** (PEP 484), developers can annotate code with types to improve **readability, maintainability, and tooling support**.  
Additionally, **mypy** allows static type checking, and **regular expressions (regex)** provide powerful pattern matching for strings.

This document covers:

- **Typing & Type Hints**
- **Mypy (static type checking)**
- **Regular Expressions**

## 2\. Typing & Type Hints

### 2.1 What are Type Hints?

- Type hints allow specifying the **expected data type** of variables, function parameters, and return values.
- They do **not** enforce types at runtime, but help tools like mypy or IDEs detect type mismatches.

### 2.2 Function Type Hints

```python
def add(x: int, y: int) -> int:
    return x + y

result: int = add(5, 10)
```

✅ Here, both parameters and return value are explicitly typed.

### 2.3 Variable Annotations

```python
name: str = "Alice"
age: int = 25
scores: list[int] = [90, 85, 78]
```

### 2.4 Complex Types (typing module)

Python’s **typing** module provides advanced type annotations.

#### 2.4.1 Lists, Tuples, Dicts, Sets

```python
from typing import List, Tuple, Dict, Set

nums: List[int] = [1, 2, 3]
point: Tuple[int, int] = (10, 20)
user: Dict[str, int] = {"Alice": 25}
unique: Set[str] = {"a", "b"}
```

#### 2.4.2 Optional & Union

```python
from typing import Optional, Union

def greet(name: Optional[str]) -> str:
    if name:
        return f"Hello, {name}"
    return "Hello, Guest"

def parse(data: Union[str, int]) -> str:
    return str(data)
```

#### 2.4.3 Callable

```python
from typing import Callable

def apply(func: Callable[[int, int], int], a: int, b: int) -> int:
    return func(a, b)

print(apply(lambda x, y: x + y, 2, 3))
```

#### 2.4.4 Custom Types with TypedDict and NewType

```python
from typing import TypedDict, NewType

class User(TypedDict):
    id: int
    name: str

UserId = NewType('UserId', int)

def get_user(user_id: UserId) -> User:
    return {"id": user_id, "name": "Alice"}
```

## 3\. Mypy: Static Type Checking

### 3.1 What is mypy?

- **mypy** is a static type checker for Python.
- It analyzes your code based on type hints without running it.
- Helps detect bugs early and enforce consistency.

### 3.2 Installation
```bash
pip install mypy
```
### 3.3 Running mypy

File: example.py

```python
def add(x: int, y: int) -> int:
    return x + y

result = add("hello", "world")  # ❌ wrong types
```

Run:
```bash
mypy example.py
```
Output:
```go
error: Argument 1 to "add" has incompatible type "str"; expected "int"
```
✅ Mypy catches type mismatches at **compile-time**, not runtime.

### 3.4 Type Inference

Mypy can infer types if not explicitly provided, but explicit annotations are recommended.

```python
x = 10  # inferred as int
y = "Python"  # inferred as str
```

### 3.5 Gradual Typing

- You don’t need to annotate everything at once.
- You can **add hints gradually** in large codebases.

## 4\. Regular Expressions (Regex)

### 4.1 What is Regex?

- A **regular expression** (regex) is a sequence of characters defining a **search pattern**.
- Python provides the re module for regex operations.

### 4.2 Basic Usage

```python
import re

pattern = r"\d+"  # one or more digits
text = "Order 1234 confirmed"

match = re.search(pattern, text)
print(match.group())  # 1234
```

### 4.3 Common Regex Functions

- re.match(pattern, text) → checks match at **start** of string.
- re.search(pattern, text) → finds **first occurrence**.
- re.findall(pattern, text) → returns **all matches**.
- re.sub(pattern, repl, text) → replaces matches.
- re.split(pattern, text) → splits text by regex.

### 4.4 Example: Find All Emails

```python
import re

emails = "Contact: alice@example.com, bob@test.org"
pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}"

print(re.findall(pattern, emails))
```

✅ Output: \['<alice@example.com>', '<bob@test.org>'\]

### 4.5 Regex Special Characters

| **Symbol** | **Meaning** |
| --- | --- |
| .   | Any character except newline |
| ^   | Start of string |
| $   | End of string |
| \\d | Digit |
| \\w | Word character (letters, digits, \_) |
| \\s | Whitespace |
| \*  | 0 or more |
| +   | 1 or more |
| ?   | 0 or 1 |
| {n,m} | Between n and m occurrences |
| \`  | \`  |

### 4.6 Example: Phone Number Validation

```python
import re

pattern = r"^\+?[0-9]{10,13}$"

numbers = ["+1234567890", "9876543210", "12345"]

for num in numbers:
    print(num, "=>", bool(re.match(pattern, num)))
```

✅ Output:

```graphql
+1234567890 => True
9876543210 => True
12345 => False
```

## 5\. Best Practices

- Use **type hints** in all functions for readability and tooling support.
- Use **mypy** in CI/CD pipelines to catch type errors early.
- Compile regex patterns with re.compile() if reused multiple times.
- Always use **raw strings (r"...")** for regex patterns to avoid escaping issues.

## 6\. Summary

- **Typing & Type Hints** → Improve code clarity and enable static checking.
- **Mypy** → Enforces type correctness at development time.
- **Regular Expressions** → Provide powerful tools for text processing and validation.