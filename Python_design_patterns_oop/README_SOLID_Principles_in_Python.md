
# 🧱 SOLID Principles in Object-Oriented Programming (OOP)

> **Author**: Md. Abdulla Al Mamun  
> **Purpose**: To understand and apply SOLID principles in Python for writing clean, scalable, and maintainable code.

---

## 📌 What is SOLID?

**SOLID** is an acronym for five design principles intended to make object-oriented designs more understandable, flexible, and maintainable.

| Acronym | Principle Name                   |
|---------|----------------------------------|
| S       | Single Responsibility Principle  |
| O       | Open/Closed Principle            |
| L       | Liskov Substitution Principle    |
| I       | Interface Segregation Principle  |
| D       | Dependency Inversion Principle   |

---

## 1️⃣ Single Responsibility Principle (SRP)

### 📖 Definition:
A class should have **only one reason to change**, meaning it should have **only one job/responsibility**.

### ❌ Bad Example:

```python
class Report:
    def __init__(self, text):
        self.text = text

    def save_to_file(self, filename):
        with open(filename, 'w') as f:
            f.write(self.text)
```

> ✅ Problem: The class is handling **both data** and **file operations**.

### ✅ Good Example (SRP Applied):

```python
class Report:
    def __init__(self, text):
        self.text = text

class ReportSaver:
    def save_to_file(self, report, filename):
        with open(filename, 'w') as f:
            f.write(report.text)
```

> 🎯 Now, each class has **only one responsibility**.

---

## 2️⃣ Open/Closed Principle (OCP)

### 📖 Definition:
Software entities should be **open for extension**, but **closed for modification**.

### ❌ Bad Example:

```python
class Discount:
    def calculate(self, price, customer_type):
        if customer_type == 'regular':
            return price * 0.9
        elif customer_type == 'vip':
            return price * 0.8
```

> 🚨 You need to **edit** this class each time you add a new customer type.

### ✅ Good Example (OCP Applied):

```python
class DiscountStrategy:
    def apply_discount(self, price):
        return price

class RegularDiscount(DiscountStrategy):
    def apply_discount(self, price):
        return price * 0.9

class VIPDiscount(DiscountStrategy):
    def apply_discount(self, price):
        return price * 0.8

# Usage
def checkout(price, strategy: DiscountStrategy):
    return strategy.apply_discount(price)

price = 100
print(checkout(price, VIPDiscount()))  # 80.0
```

> 🎯 Now you can **extend** discount types without **modifying existing code**.

---

## 3️⃣ Liskov Substitution Principle (LSP)

### 📖 Definition:
**Subtypes** must be **substitutable** for their **base types** without altering program correctness.

### ❌ Bad Example:

```python
class Bird:
    def fly(self):
        pass

class Ostrich(Bird):
    def fly(self):
        raise NotImplementedError("Ostriches can't fly!")
```

> 🚨 Violates LSP – a subclass shouldn't **break behavior** of the base class.

### ✅ Good Example (LSP Applied):

```python
class Bird:
    pass

class FlyingBird(Bird):
    def fly(self):
        print("Flying...")

class Ostrich(Bird):
    def run(self):
        print("Running...")

# Usage
def move_bird(bird: Bird):
    if isinstance(bird, FlyingBird):
        bird.fly()
    elif isinstance(bird, Ostrich):
        bird.run()
```

> 🎯 Subclasses maintain expected behavior of the base class.

---

## 4️⃣ Interface Segregation Principle (ISP)

### 📖 Definition:
Clients should **not be forced** to depend on interfaces they do not use.

### ❌ Bad Example:

```python
class Machine:
    def print(self): pass
    def scan(self): pass
    def fax(self): pass

class OldPrinter(Machine):
    def print(self): print("Printing")
    def scan(self): raise NotImplementedError
    def fax(self): raise NotImplementedError
```

> 🚨 `OldPrinter` is **forced** to implement methods it doesn't use.

### ✅ Good Example (ISP Applied):

```python
class Printer:
    def print(self): pass

class Scanner:
    def scan(self): pass

class PrintOnlyMachine(Printer):
    def print(self):
        print("Printing only")

class MultiFunctionMachine(Printer, Scanner):
    def print(self):
        print("Printing")

    def scan(self):
        print("Scanning")
```

> 🎯 Clients **only implement** what they need.

---

## 5️⃣ Dependency Inversion Principle (DIP)

### 📖 Definition:
**High-level modules** should not depend on **low-level modules**. Both should depend on **abstractions**.

### ❌ Bad Example:

```python
class MySQLDatabase:
    def connect(self):
        print("Connecting to MySQL")

class Application:
    def __init__(self):
        self.db = MySQLDatabase()  # Tight coupling
```

> 🚨 Application is tightly coupled to **MySQLDatabase**.

### ✅ Good Example (DIP Applied):

```python
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def connect(self):
        pass

class MySQLDatabase(Database):
    def connect(self):
        print("Connecting to MySQL")

class PostgreSQLDatabase(Database):
    def connect(self):
        print("Connecting to PostgreSQL")

class Application:
    def __init__(self, db: Database):
        self.db = db

    def start(self):
        self.db.connect()

# Usage
app = Application(PostgreSQLDatabase())
app.start()  # Connecting to PostgreSQL
```

> 🎯 High-level module (`Application`) is now **decoupled** from low-level modules.

---

## ✅ Conclusion

| Principle | Goal |
|-----------|------|
| **SRP** | One class = One responsibility |
| **OCP** | Extend without modifying |
| **LSP** | Subclass should substitute parent class |
| **ISP** | Avoid fat interfaces |
| **DIP** | Rely on abstractions, not concrete implementations |

Applying SOLID leads to:

- Better **code readability**
- Greater **testability**
- Easier **maintenance**
- Improved **extensibility**
