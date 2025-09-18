# Object-Oriented Programming (OOP) in Python — Technical Documentation

## Table of Contents
1. Executive Summary
2. What is Object-Oriented Programming?
3. Core Principles of OOP
   - Encapsulation
   - Abstraction
   - Inheritance
   - Polymorphism
4. Python Classes and Objects
5. Types of Methods
   - Instance methods
   - Class methods
   - Static methods
   - Abstract methods
   - Special methods (dunder)
   - Properties and descriptors
6. Constructors and Object Lifecycle
7. Method Binding and Callables (bound/unbound)
8. Special / Magic Methods (detailed)
9. Access Modifiers and Name Mangling
10. OOP Design Patterns (Overview)
11. Example Use Cases in Python
12. Best Practices
13. Glossary
14. Further Reading

---

## 1. Executive Summary
Object-Oriented Programming (OOP) models software as collections of interacting objects that combine state (attributes) and behavior (methods). This document covers Python-specific details including all method types (instance/class/staticmethod/abstract), object construction and lifecycle, property and descriptor protocols, binding, magic methods, and practical examples.

---

## 2. What is Object-Oriented Programming?
OOP organizes code into objects and classes to improve modularity, reuse, and maintainability. In Python, classes are first-class objects and the language provides flexible support for OOP idioms.

---

## 3. Core Principles of OOP
- **Encapsulation:** Group related data and behavior; hide internal state where appropriate.
- **Abstraction:** Expose a simple public interface while hiding complex internals.
- **Inheritance:** Reuse and extend behavior from parent classes.
- **Polymorphism:** Use a common interface to operate on different types.

---

## 4. Python Classes and Objects
```python
class Student:
    def __init__(self, name, grade):
        self.name = name
        self.grade = grade

    def introduce(self):
        return f"Hi, I'm {self.name} and I'm in grade {self.grade}."

s = Student('Alice', 10)
print(s.introduce())
```

---

## 5. Types of Methods
This section explains different method types, how and when to use them, and examples.

### 5.1 Instance methods
- The most common method type. The first parameter is typically `self`, which is the instance.
- Use instance methods when the behavior depends on instance state.

**Example:**
```python
class Counter:
    def __init__(self):
        self._count = 0

    def increment(self):            # instance method
        self._count += 1

    def value(self):
        return self._count
```

Usage:
```python
c = Counter()
c.increment()
print(c.value())  # 1
```


### 5.2 Class methods
- Decorated with `@classmethod` and receive the class as the first argument (`cls`).
- Useful for factory methods, alternative constructors, and methods that operate on the class state rather than instance state.

**Example — alternative constructor:**
```python
class User:
    def __init__(self, username, email):
        self.username = username
        self.email = email

    @classmethod
    def from_dict(cls, d):           # class method
        return cls(d['username'], d['email'])

u = User.from_dict({'username': 'bob', 'email': 'bob@example.com'})
```

**Class-level state example:**
```python
class Plugin:
    _registry = {}

    @classmethod
    def register(cls, name, plugin_cls):
        cls._registry[name] = plugin_cls
```


### 5.3 Static methods
- Decorated with `@staticmethod`. They behave like plain functions stored inside the class namespace and do not receive `self` or `cls`.
- Useful for utility functions logically grouped with the class.

**Example:**
```python
class Math:
    @staticmethod
    def add(a, b):
        return a + b

print(Math.add(2, 3))  # 5
```


### 5.4 Abstract methods
- Provided by the `abc` module using `ABC` and the `@abstractmethod` decorator.
- Abstract classes define an interface; concrete subclasses must implement abstract methods.

**Example:**
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        pass

class Circle(Shape):
    def __init__(self, r):
        self.r = r

    def area(self):
        return 3.14159 * self.r * self.r
```

Trying to instantiate `Shape()` or a subclass that does not implement `area` will raise `TypeError`.


### 5.5 Special methods (dunder)
- Special methods (like `__str__`, `__repr__`, `__len__`, `__eq__`) customize built-in behavior.
- See Section 8 for expanded examples.


### 5.6 Properties and descriptors
- `@property` converts a method into a getter; pair with `@<prop>.setter` and `@<prop>.deleter` to control access.
- Encapsulation → hiding implementation details while exposing a clean API.
- Data validation → control how attributes are set or retrieved.
- Read-only attributes → prevent direct modification of values.

**Property example:**
```python
class Person:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not value:
            raise ValueError('name cannot be empty')
        self._name = value

class Circle:
    def __init__(self, radius):
        self._radius = radius  # Conventionally, use a leading underscore for internal attributes

    @property
    def radius(self):
        """The radius property."""
        print("Getting radius...")
        return self._radius

    @radius.setter
    def radius(self, value):
        print("Setting radius...")
        if value < 0:
            raise ValueError("Radius cannot be negative")
        self._radius = value

    @radius.deleter
    def radius(self):
        print("Deleting radius...")
        del self._radius

# Usage
my_circle = Circle(5)
print(my_circle.radius)  # Calls the getter
my_circle.radius = 10    # Calls the setter
del my_circle.radius     # Calls the deleter
```

**Descriptor example (simple typed attribute):**
- Descriptors are objects that implement `__get__`, `__set__`, or `__delete__` and underlie property behavior.
- `__get__(self, instance, owner)` → defines behavior when the attribute is read.
- `__set__(self, instance, value)` → defines behavior when the attribute is assigned.
- `__delete__(self, instance)` → defines behavior when the attribute is deleted.

Descriptors are the foundation of:
- `property`
- `classmethod`
- `staticmethod`
- Many parts of Python’s internals.

```python
class Typed:
    def __init__(self, name, expected_type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f'Expected {self.expected_type}')
        instance.__dict__[self.name] = value

class Point:
    x = Typed('x', int)
    y = Typed('y', int)

p = Point()
p.x = 1
# p.x = 1.5  # would raise TypeError
```
```python
class PositiveNumber:
    def __get__(self, instance, owner):
        return instance._value
    
    def __set__(self, instance, value):
        if value < 0:
            raise ValueError("Value must be positive")
        instance._value = value

    def __delete__(self, instance):
        print("Deleting value...")
        del instance._value


class Account:
    balance = PositiveNumber()   # using descriptor

    def __init__(self, balance):
        self.balance = balance


a = Account(100)
print(a.balance)   # 100
a.balance = 200    # valid
print(a.balance)
# a.balance = -50  # ❌ raises ValueError
del a.balance # "Deleting value..."
```
```python
class ReadOnly:
    def __get__(self, instance, owner):
        return "This value cannot be changed"
    
    def __set__(self, instance, value):
        raise AttributeError("This attribute is read-only")


class Config:
    version = ReadOnly()


c = Config()
print(c.version)     # works
# c.version = "2.0"  # ❌ AttributeError

```
**Descriptor vs @property**
Both achieve similar goals.
- `property` → simple, best for one attribute.
- `descriptor` → reusable, powerful when you need shared behavior across multiple attributes.
- `@property` is a special case of descriptor.
- Use `@property` → simple encapsulation for one attribute.
- Use `descriptors` → when you want reusable attribute logic for many attributes.
- Descriptors give low-level control over attribute access in Python.

With property:
```python
class Employee:
    def __init__(self, salary):
        self._salary = salary

    @property
    def salary(self):
        return self._salary

    @salary.setter
    def salary(self, value):
        if value < 0:
            raise ValueError("Salary cannot be negative")
        self._salary = value

```
With Descriptor:
```python
class Positive:
    def __get__(self, instance, owner):
        return instance._value

    def __set__(self, instance, value):
        if value < 0:
            raise ValueError("Value must be positive")
        instance._value = value


class Employee:
    salary = Positive()

    def __init__(self, salary):
        self.salary = salary

```
---

## 6. Constructors and Object Lifecycle
- `__new__` is the low-level constructor that allocates the object (rarely overridden).
- `__init__` initializes the allocated instance.
- `__del__` is the destructor that runs when an object is garbage-collected (use with caution).

**Example:**
```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, value):
        self.value = value
```

---

## 7. Method Binding and Callables (bound/unbound)
- Accessing a function on an instance returns a *bound method* where `self` is implicitly provided.
- Accessing the same function on the class returns a *function object*; you must pass an instance explicitly.

**Example:**
```python
class A:
    def f(self, x):
        return self, x

a = A()
bound = a.f            # bound method — calling bound(1) auto-passes `a`
print(bound(1))

unbound = A.f           # function — requires explicit instance: unbound(a, 1)
print(unbound(a, 1))
```

---

## 8. Special / Magic Methods (detailed)
- `__repr__` / `__str__` — string representations.
- `__eq__`, `__lt__`, etc. — comparisons.
- `__len__`, `__iter__`, `__next__` — container/iterator protocol.
- `__enter__`, `__exit__` — context manager protocol.

**Example:**
```python
class RangeLike:
    def __init__(self, n):
        self.n = n

    def __len__(self):
        return self.n

    def __iter__(self):
        i = 0
        while i < self.n:
            yield i
            i += 1

r = RangeLike(3)
print(len(r))
for x in r:
    print(x)
```

**Context manager example:**
```python
class Managed:
    def __enter__(self):
        print('enter')
        return self
    def __exit__(self, exc_type, exc, tb):
        print('exit')

with Managed():
    print('inside')
```

---

## 9. Access Modifiers and Name Mangling
- Python uses naming conventions: public (`name`), protected (`_name`), private (`__name`).
- Private names are **name-mangled** to `_ClassName__name` to reduce accidental access, not to provide security.

**Example:**
```python
class Secret:
    def __init__(self):
        self.__secret = 'hidden'

s = Secret()
# s.__secret  # AttributeError
print(s._Secret__secret)  # access via name-mangled attribute
```

---

## 10. OOP Design Patterns (Overview)
- **Singleton** (shown above with `__new__`).
- **Factory / Abstract Factory** (use classmethods to return different concrete types).
- **Strategy** (inject behavior objects).
- **Observer** (publish/subscribe patterns with method hooks).

**Example — Factory with classmethod:**
```python
class Animal:
    @classmethod
    def create(cls, kind, *args, **kwargs):
        if kind == 'dog':
            return Dog(*args, **kwargs)
        elif kind == 'cat':
            return Cat(*args, **kwargs)
        raise ValueError('unknown')
```

---

## 11. Example Use Cases in Python
### Use Case A — Employee Management (instance/class/staticmethods)
```python
class Employee:
    payroll = []                 # class-level data

    def __init__(self, name, salary):
        self.name = name
        self.salary = salary
        Employee.payroll.append(self)

    @classmethod
    def average_salary(cls):
        return sum(e.salary for e in cls.payroll) / len(cls.payroll)

    @staticmethod
    def validate_salary(salary):
        return salary >= 0
```

### Use Case B — Abstract Base Classes (plugin interface)
```python
from abc import ABC, abstractmethod

class PluginBase(ABC):
    @abstractmethod
    def run(self, data):
        pass

class MyPlugin(PluginBase):
    def run(self, data):
        return data.upper()
```

---

## 12. Best Practices
- Prefer composition over inheritance for flexible designs.
- Use `@staticmethod` for utilities that don't need `cls`/`self` and `@classmethod` for alternative constructors or class-level behavior.
- Use `@property` for controlled attribute access; avoid public mutable attributes when invariants must be enforced.
- Implement `__repr__` for debugging and `__str__` for user-friendly output.
- Keep classes focused on a single responsibility.
- Document expected method contracts (params, return, exceptions).

---

## 13. Glossary
- **Bound method:** Function object that has `self` pre-bound to an instance.
- **Descriptor:** Object with `__get__`, `__set__`, or `__delete__` used for attribute access control.
- **Abstract method:** Method declared but not implemented at the abstract base class level.
- **Dunder:** Double underscore methods that implement special behavior (magic methods).

---

## 14. Further Reading
- Official Python docs: https://docs.python.org/3/tutorial/classes.html and https://docs.python.org/3/library/abc.html
- Book: *Fluent Python* by Luciano Ramalho (excellent coverage of descriptors, metaclasses, and advanced OOP)
- PEP 8: Style guide for Python code

---

If you want, I can now:
- Add concrete exercises and unit tests for each concept, or
- Expand this into a printable DOCX/PDF, or
- Add examples of metaclasses and advanced descriptor patterns.
Which would you like next?

