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
11. Method Resolution Order (MRO)
12. Composition vs Inheritance
13. Duck Typing and EAFP vs LBYL
14. Example Use Cases in Python
15. Best Practices
16. Glossary
17. Further Reading

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

```python
from abc import ABC, abstractmethod

# Abstract Class for Abstraction
class Animal(ABC):
    @abstractmethod
    def make_sound(self):
        pass

    def sleep(self):
        print("Zzz...")

# ABC acting as an Interface
class Flyable(ABC):
    @abstractmethod
    def fly(self):
        pass

class Dog(Animal):
    def make_sound(self):
        print("Woof!")

class Bird(Animal, Flyable): # Inheriting from both
    def make_sound(self):
        print("Chirp!")

    def fly(self):
        print("Flying high!")

# d = Animal() # This would raise a TypeError as Animal is abstract
dog = Dog()
dog.make_sound()
dog.sleep()

bird = Bird()
bird.make_sound()
bird.sleep()
bird.fly()
```

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
```
```python
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
```python
class DimensionsDescriptor:
    def __init__(self, name_width, name_height):
        self.name_width = name_width
        self.name_height = name_height

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.name_width), getattr(obj, self.name_height)

    def __set__(self, obj, value):
        # Unpack the multiple values from the 'value' iterable
        width, height = value

        # Perform any validation or logic here
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
            raise ValueError("Dimensions must be numeric.")
        if width <= 0 or height <= 0:
            raise ValueError("Dimensions must be positive.")

        # Set the individual attributes on the instance
        setattr(obj, self.name_width, width)
        setattr(obj, self.name_height, height)

class Rectangle:
    # Create an instance of the descriptor
    dimensions = DimensionsDescriptor('_width', '_height')

    def __init__(self, width, height):
        # When assigning to 'dimensions', the descriptor's __set__ is called
        self.dimensions = (width, height)

    def get_area(self):
        # Accessing 'dimensions' calls the descriptor's __get__
        width, height = self.dimensions
        return width * height

# Example usage
rect = Rectangle(10, 5)
print(f"Initial dimensions: {rect.dimensions}")
print(f"Area: {rect.get_area()}")

# Set new dimensions using a tuple
rect.dimensions = (20, 10)
print(f"New dimensions: {rect.dimensions}")
print(f"New area: {rect.get_area()}")

try:
    rect.dimensions = (-5, 10) # This will raise a ValueError
except ValueError as e:
    print(f"Error setting dimensions: {e}")
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
### 5.6 methoad overriding and methoad overloading
✅ Key Points of overriding:
- Involves inheritance.
- Subclass method replaces the parent method.
- Enables runtime polymorphism.
```python
class Animal:
    def speak(self):
        return "Some generic sound"

class Dog(Animal):
    def speak(self):  # Overriding parent method
        return "Bark"

class Cat(Animal):
    def speak(self):
        return "Meow"

# Usage
animals = [Dog(), Cat()]
for animal in animals:
    print(animal.speak())
#output
#"Bark"
#"Meow
```
✅ Key Points of overloading:
- Python uses the last defined method if multiple methods have the same name.
- Overloading is simulated using optional or variable arguments.
```python
class Calculator:
    def add(self, a, b=0, c=0):
        return a + b + c

calc = Calculator()
print(calc.add(5))       # 5
print(calc.add(5, 10))   # 15
print(calc.add(5, 10, 15)) # 30
```
```python
class Calculator:
    def add(self, *args):
        return sum(args)

calc = Calculator()
print(calc.add(5))            # 5
print(calc.add(5, 10))        # 15
print(calc.add(5, 10, 15, 20)) # 50

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
**8.1. String Representations:**
```python
class Book:
    def __init__(self, title, author):
        self.title, self.author = title, author

    def __repr__(self):  # Developer-friendly
        return f"Book(title={self.title!r}, author={self.author!r})"

    def __str__(self):  # User-friendly
        return f"{self.title} by {self.author}"

b = Book("1984", "Orwell")
print(repr(b))  # Book(title='1984', author='Orwell')
print(str(b))   # 1984 by Orwell

```
**8.2. Comparisn Operators:**
```python
class Number:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other): return self.value == other.value
    def __lt__(self, other): return self.value < other.value
    def __le__(self, other): return self.value <= other.value
    def __gt__(self, other): return self.value > other.value
    def __ge__(self, other): return self.value >= other.value
    def __ne__(self, other): return self.value != other.value

print(Number(5) == Number(5))  # True
print(Number(3) < Number(7))   # True

```
**8.3. Arithmatic operators**
```python
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other): return Vector(self.x + other.x, self.y + other.y)
    def __sub__(self, other): return Vector(self.x - other.x, self.y - other.y)
    def __mul__(self, scalar): return Vector(self.x * scalar, self.y * scalar)
    def __truediv__(self, scalar): return Vector(self.x / scalar, self.y / scalar)

    def __repr__(self): return f"Vector({self.x}, {self.y})"

print(Vector(2, 3) + Vector(1, 1))  # Vector(3, 4)
print(Vector(2, 3) * 2)             # Vector(4, 6)
```
**8.4. Container and Iteretor Protocols**
```python
class MyList:
    def __init__(self, items):
        self.items = items

    def __len__(self): return len(self.items)
    def __getitem__(self, index): return self.items[index]
    def __setitem__(self, index, value): self.items[index] = value
    def __delitem__(self, index): del self.items[index]
    def __iter__(self): return iter(self.items)
    def __contains__(self, item): return item in self.items

lst = MyList([1, 2, 3])
print(len(lst))       # 3
print(lst[1])         # 2
lst[1] = 99
print(lst.items)      # [1, 99, 3]
print(99 in lst)      # True

```
**8.5. Iterator Protocols**
```python
class Counter:
    def __init__(self, limit):
        self.limit = limit
        self.current = 0

    def __iter__(self): return self
    def __next__(self):
        if self.current < self.limit:
            self.current += 1
            return self.current
        raise StopIteration

for num in Counter(3):
    print(num)  # 1, 2, 3

```
**8.6. Context manager example:**
```python
class FileManager:
    def __init__(self, filename, mode):
        self.filename, self.mode = filename, mode

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()
        return False  # re-raise exceptions if any

with FileManager("test.txt", "w") as f:
    f.write("Hello World")
```
**8.7. Callable Objects:**
```python
class Adder:
    def __init__(self, n): self.n = n
    def __call__(self, x): return x + self.n

add5 = Adder(5)
print(add5(10))  # 15

```
**8.8. Attribute Access:**
```python
class Person:
    def __init__(self, name): self.name = name

    def __getattr__(self, item):  # only if attribute not found
        return f"{item} not found"

    def __setattr__(self, key, value): 
        print(f"Setting {key} = {value}")
        super().__setattr__(key, value)

    def __delattr__(self, item): 
        print(f"Deleting {item}")
        super().__delattr__(item)

p = Person("Alice")
print(p.age)   # age not found
p.city = "NY"  # Setting city = NY
del p.city     # Deleting city
```
**8.9. Objects Lifecycle:**
```python
class Demo:
    def __new__(cls, *args, **kwargs):
        print("Allocating memory for object")
        return super().__new__(cls)

    def __init__(self, value):
        print("Initializing object")
        self.value = value

    def __del__(self):
        print(f"Destroying {self.value}")

obj = Demo(10)
del obj
```
**8.10. Hasjing and Turthiness:**
```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __hash__(self): return hash((self.x, self.y))
    def __bool__(self): return bool(self.x or self.y)

p = Point(0, 0)
print(bool(p))       # False
print(hash(Point(1, 2)))
```
**8.11. Descriptor Protocol:**
```python
class Celsius:
    def __get__(self, obj, objtype=None):
        return obj._celsius
    def __set__(self, obj, value):
        if value < -273.15:
            raise ValueError("Below absolute zero!")
        obj._celsius = value

class Temperature:
    celsius = Celsius()
    def __init__(self, celsius): self.celsius = celsius

t = Temperature(25)
print(t.celsius)  # 25
t.celsius = -300  # ValueError

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
## 11. Method Resolution Order (MRO)
Defines the order Python uses to search for methods in multiple inheritance.
You can inspect the MRO of a class using either:
- The `__mro__` attribute: This is a tuple containing the class and its ancestors in MRO order.
- The `mro()` class method: This returns a list of the class and its ancestors in MRO order.

```python
class A:
    def method(self):
        print("Method from A")

class B(A):
    def method(self):
        print("Method from B")

class C(A):
    def method(self):
        print("Method from C")

class D(B, C):
    pass

# Get the MRO of class D
print(D.__mro__)
# Output: (<class '__main__.D'>, <class '__main__.B'>, <class '__main__.C'>, <class '__main__.A'>, <class 'object'>)

# Calling the method on an instance of D
d_instance = D()
d_instance.method()
# Output: Method from B (because B comes before C in D's MRO)
```
---
## Section 12: Composition vs Inheritance (Expanded)

### **12.1 Inheritance**
Inheritance is a mechanism where a class (child/subclass) derives attributes and methods from another class (parent/superclass). It represents an **“is-a” relationship**.

✅ **When to Use:**
- When a subclass is a more specific type of the parent class.
- To reuse common functionality from a base class.
- To apply polymorphism — allowing different subclasses to share the same interface but implement their own behaviors.

**Example: Animal Hierarchy**
```python
class Animal:
    def speak(self):
        return "Some generic sound"

class Dog(Animal):  # Dog "is an" Animal
    def speak(self):
        return "Bark"

class Cat(Animal):  # Cat "is an" Animal
    def speak(self):
        return "Meow"

# Usage
animals = [Dog(), Cat(), Animal()]
for animal in animals:
    print(animal.speak())
```
**Output:**
```
Bark
Meow
Some generic sound
```
Here, both `Dog` and `Cat` inherit from `Animal` but override the `speak()` method.

---

### **12.2 Composition**
Composition means creating complex types by combining objects of other classes. Instead of inheriting from another class, a class **contains** an instance of another class and delegates work to it. It represents a **“has-a” relationship**.

✅ **When to Use:**
- To promote flexibility and avoid rigid inheritance hierarchies.
- When classes share functionality but don’t have a true “is-a” relationship.
- To replace or swap components dynamically.

**Example: Car and Engine**
```python
class Engine:
    def start(self):
        return "Engine started"

class Car:
    def __init__(self):
        self.engine = Engine()  # Car "has an" Engine

    def start(self):
        return self.engine.start() + " in Car"

# Usage
my_car = Car()
print(my_car.start())
```
**Output:**
```
Engine started in Car
```
Here, `Car` is not an `Engine`, but it **has one**.

---

### **12.3 Key Differences Between Inheritance and Composition**

| Aspect                | Inheritance (IS-A)               | Composition (HAS-A)                  |
|------------------------|-----------------------------------|--------------------------------------|
| Relationship           | Child is a type of parent        | Class contains other classes         |
| Coupling               | Tightly coupled                  | Loosely coupled                      |
| Flexibility            | Less flexible (fixed hierarchy)  | More flexible (swap components)      |
| Example                | Dog **is an** Animal             | Car **has an** Engine                |
| Code Reuse             | Via base/parent class            | Via delegation                       |

---

### **12.4 When to Prefer Composition Over Inheritance**
- When behavior is **shared but not specialized**.
- When you want **looser coupling** between components.
- When deep inheritance trees create complexity.
- When using **dependency injection** for testing.

---

### **12.5 Real-World Examples**

#### **Inheritance Example: GUI Widgets**
```python
class Widget:
    def render(self):
        return "Rendering Widget"

class Button(Widget):  # Button "is a" Widget
    def render(self):
        return "Rendering Button"

class TextBox(Widget):  # TextBox "is a" Widget
    def render(self):
        return "Rendering TextBox"

# Usage
widgets = [Button(), TextBox()]
for w in widgets:
    print(w.render())
```
**Output:**
```
Rendering Button
Rendering TextBox
```
Here, `Button` and `TextBox` are specialized `Widget`s.

#### **Composition Example: Game Development**
```python
class Position:
    def __init__(self, x, y):
        self.x, self.y = x, y

class Velocity:
    def __init__(self, dx, dy):
        self.dx, self.dy = dx, dy

class GameObject:
    def __init__(self, position, velocity):
        self.position = position  # HAS a Position
        self.velocity = velocity  # HAS a Velocity

    def move(self):
        self.position.x += self.velocity.dx
        self.position.y += self.velocity.dy
        return (self.position.x, self.position.y)

# Usage
obj = GameObject(Position(0, 0), Velocity(5, 2))
print(obj.move())  # (5, 2)
```
Here, `GameObject` is **not** a `Position` or `Velocity`, but it **uses them** to provide behavior.

---

### **12.6 Combining Inheritance and Composition**
In practice, both can be combined.

**Example: Web Application**
```python
class Database:
    def query(self):
        return "Fetching data from database"

class Logger:
    def log(self, msg):
        print(f"LOG: {msg}")

class Service:
    def __init__(self, db, logger):
        self.db = db        # Composition
        self.logger = logger

    def execute(self):
        self.logger.log("Service executing")
        return self.db.query()

class UserService(Service):  # Inheritance
    def execute(self):
        self.logger.log("User service executing")
        return "User Data: " + self.db.query()

# Usage
service = UserService(Database(), Logger())
print(service.execute())
```

**Output:**
```
LOG: User service executing
User Data: Fetching data from database
```
Here:
- `UserService` inherits from `Service` (**inheritance**).
- `Service` uses `Database` and `Logger` via **composition**.

---

✅ **Rule of Thumb:**
- Use **inheritance** when classes share a strict “is-a” relationship.
- Use **composition** for flexible and modular design.
- Favor composition when unsure — it leads to looser coupling and easier maintainability.

---
## Section 13: Duck Typing and EAFP vs LBYL (Expanded)

### **13.1 Duck Typing**
Duck typing is a concept in Python where the type or class of an object is less important than the methods or behaviors it supports. The name comes from the saying:

**“If it looks like a duck, swims like a duck, and quacks like a duck, then it probably is a duck.”**

✅ **Key idea:** Instead of checking an object’s type, just use it as long as it behaves as expected.

**Example: Duck Typing in Action**
```python
class Duck:
    def quack(self):
        return "Quack!"

class Person:
    def quack(self):
        return "I'm imitating a duck!"

def make_it_quack(duck_like):
    print(duck_like.quack())

# Usage
make_it_quack(Duck())    # Quack!
make_it_quack(Person())  # I'm imitating a duck!
```
Here, both `Duck` and `Person` have a `quack()` method. The function doesn’t care about the type — only that the object responds to `.quack()`.

---

### **13.2 EAFP (Easier to Ask for Forgiveness than Permission)**
Python encourages the **EAFP** style:
- Assume an object can do what you expect.
- If it doesn’t, **catch the exception**.

This is idiomatic in Python because exceptions are relatively cheap, and it avoids excessive condition checks.

**Example: Dictionary Lookup (EAFP)**
```python
def get_item(dictionary, key):
    try:
        return dictionary[key]  # Assume key exists
    except KeyError:
        return "Key not found"

data = {"name": "Alice"}
print(get_item(data, "name"))  # Alice
print(get_item(data, "age"))   # Key not found
```
Here, we try to use the dictionary directly and handle missing keys with `except`.

---

### **13.3 LBYL (Look Before You Leap)**
The opposite of EAFP is **LBYL**:
- Check conditions in advance before performing an operation.
- Common in languages like Java and C.

**Example: Dictionary Lookup (LBYL)**
```python
def get_item(dictionary, key):
    if key in dictionary:   # Check first
        return dictionary[key]
    else:
        return "Key not found"

data = {"name": "Alice"}
print(get_item(data, "name"))  # Alice
print(get_item(data, "age"))   # Key not found
```
Here, we check whether the key exists before accessing it.

---

### **13.4 Comparison: EAFP vs LBYL**

| Aspect                 | EAFP (Pythonic)                        | LBYL (Defensive style)         |
|-------------------------|-----------------------------------------|--------------------------------|
| Approach               | Try and catch exceptions                | Check conditions first         |
| Language Influence     | Preferred in Python                     | Common in Java, C, C++         |
| Readability            | Often shorter, cleaner                  | Can lead to nested conditions  |
| Race Conditions        | Safer in multi-threaded scenarios       | May fail if state changes after check |
| Example                | `try/except`                            | `if condition:`                |

---

### **13.5 Real-World Example: File Handling**

**EAFP (Pythonic):**
```python
try:
    with open("data.txt") as f:
        print(f.read())
except FileNotFoundError:
    print("File not found, please create it first.")
```

**LBYL:**
```python
import os

if os.path.exists("data.txt"):
    with open("data.txt") as f:
        print(f.read())
else:
    print("File not found, please create it first.")
```

- EAFP is shorter and more idiomatic.
- LBYL avoids exceptions but may miss race conditions (file could be deleted between the `exists()` check and the `open()` call).

---

### **13.6 Another Example: Attribute Access**

**EAFP:**
```python
def get_attribute(obj):
    try:
        return obj.name
    except AttributeError:
        return "No attribute 'name'"

class User:
    def __init__(self, name):
        self.name = name

print(get_attribute(User("Alice")))  # Alice
print(get_attribute(object()))        # No attribute 'name'
```

**LBYL:**
```python
def get_attribute(obj):
    if hasattr(obj, "name"):
        return obj.name
    else:
        return "No attribute 'name'"

print(get_attribute(User("Alice")))  # Alice
print(get_attribute(object()))        # No attribute 'name'
```

---

### **13.7 When to Use Which**
- ✅ Use **EAFP** in most Python code for clean, readable style.
- ✅ Use **LBYL** when checks are cheap and exceptions are expensive (e.g., network calls).
- ✅ For **concurrency/multithreading**, EAFP is safer because conditions can change after a check.

---

✅ **Rule of Thumb:**
- Prefer **Duck Typing + EAFP** in idiomatic Python.
- Use LBYL when performance or clarity demands pre-checks.

---


## 14. Example Use Cases in Python
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

## 15. Best Practices
- Prefer composition over inheritance for flexible designs.
- Use `@staticmethod` for utilities that don't need `cls`/`self` and `@classmethod` for alternative constructors or class-level behavior.
- Use `@property` for controlled attribute access; avoid public mutable attributes when invariants must be enforced.
- Implement `__repr__` for debugging and `__str__` for user-friendly output.
- Keep classes focused on a single responsibility.
- Document expected method contracts (params, return, exceptions).

---

## 16. Glossary
- **Bound method:** Function object that has `self` pre-bound to an instance.
- **Descriptor:** Object with `__get__`, `__set__`, or `__delete__` used for attribute access control.
- **Abstract method:** Method declared but not implemented at the abstract base class level.
- **Dunder:** Double underscore methods that implement special behavior (magic methods).

---

## 17. Further Reading
- Official Python docs: https://docs.python.org/3/tutorial/classes.html and https://docs.python.org/3/library/abc.html
- Book: *Fluent Python* by Luciano Ramalho (excellent coverage of descriptors, metaclasses, and advanced OOP)
- PEP 8: Style guide for Python code

---

If you want, I can now:
- Add concrete exercises and unit tests for each concept, or
- Expand this into a printable DOCX/PDF, or
- Add examples of metaclasses and advanced descriptor patterns.
Which would you like next?

