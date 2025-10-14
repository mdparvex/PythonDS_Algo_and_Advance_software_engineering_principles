Design patterns are proven solutions to common software design problems. They're not code per se, but templates or blueprints that can be customized to solve a recurring design problem in your codebase.

Here are the most **usable and common design patterns**, grouped into **Creational**, **Structural**, and **Behavioral** categories — with explanation, **real-world use case**, and **Python code examples** for each.

---
**Creational patterns**

- These patterns provide flexible ways to create objects, often by decoupling the creation logic from the client code.
- Examples include the Singleton pattern, which ensures only one instance of a class exists, and the Factory Method pattern.

**Structural patterns**

- These patterns focus on how to assemble classes and objects to form larger structures and provide new functionalities.
- They are concerned with class and object composition, using inheritance to compose interfaces and define ways to compose objects.

**Behavioral patterns**

- These patterns are about algorithms and the assignment of responsibilities between objects to create efficient communication.
- They handle how objects interact with each other, helping to make programs more flexible and maintainable.
- Examples include the State pattern, which allows an object to alter its behavior when its internal state changes, and the Proxy pattern.

---

**🏗️ 1. Creational Patterns**

**🔹 a) Singleton Pattern**

**Purpose:** Ensure a class has only one instance and provide a global point of access to it.

**Use Case:** Database connections, configuration managers.

**Python Example:**

```python

class Singleton:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

# Usage
config1 = Singleton()
config2 = Singleton()
print(config1 is config2) # True
```

✅ **Why use it?**

- Avoid multiple initializations of a heavy object (like DB connection).
- Ensure consistency across the app.

**🔹 b) Factory Pattern**

**Purpose:** Create objects without specifying the exact class of object to be created.

**Use Case:** When object creation is complex or depends on input.

**Python Example:**

```python

class Dog:
    def speak(self):
        return "Woof!"

class Cat:
    def speak(self):
        return "Meow!"

class AnimalFactory:
    def create_animal(self, animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
        raise ValueError("Unknown animal")

# Usage
factory = AnimalFactory()
animal = factory.create_animal("dog")
print(animal.speak()) # Woof!

class Burger:
    def __init__(self, ingredients):
        self.ingradients = ingrediants
    def print(self):
        print(self.ingrediants)
class BurgerFactory:
    def createCheaseBurger(self):
        ingradients = ["bun", "cheese", "beef-patty"]
        return Burger(ingredients)
    def createDelucCheaseBurger(self):
        ingradients = ["bun", "tomato","lettuce", "cheese", "beef-patty"]
        return Burger(ingredients)
burgerfactory = BurgerFactory()
burgerfactory.createCheaseBurger().print()
burgerfactory.createDelucCheaseBurger().print()
```

✅ **Why use it?**

- Encapsulates object creation logic.
- Promotes scalability.

**🏗️ 2. Structural Patterns**

**🔹 a) Adapter Pattern**

**Purpose:** Convert the interface of a class into another interface clients expect.

**Use Case:** When integrating incompatible interfaces (e.g., third-party libraries).

**Python Example:**

```python

class EuropeanPlug:
    def connect(self):
        return "220V power"

class AmericanAdapter:
    def __init__(self, device):
        self.device = device
    def connect(self):
        return f"Adapter converts -> {self.device.connect()} -> 110V power"

# Usage
e_plug = EuropeanPlug()
adapter = AmericanAdapter(e_plug)
print(adapter.connect())
```

✅ **Why use it?**

- Reuse existing classes without modifying their code.

**🔹 b) Decorator Pattern**

**Purpose:** Add responsibilities to objects at runtime.

**Use Case:** Logging, security, validation, caching.

**Python Example:**

```python

def make_bold(func):
    def wrapper():
        return "<b>" + func() + "</b>"
    return wrapper

@make_bold
def greet():
    return "Hello"

print(greet()) # <b>Hello</b>
```

✅ **Why use it?**

- Clean and flexible way to add behavior dynamically without altering original code.

**🧠 3. Behavioral Patterns**

**🔹 a) Observer Pattern**

**Purpose:** Define a one-to-many dependency so that when one object changes state, all dependents are notified.

**Use Case:** Event systems, UI frameworks, real-time updates.

**Python Example:**

```python

class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def notify(self, message):
        for obs in self._observers:
            obs.update(message)

class Observer:
    def update(self, message):
        print(f"Received: {message}")

# Usage

subject = Subject()
obs1 = Observer()
obs2 = Observer()
subject.attach(obs1)
subject.attach(obs2)
subject.notify("New update available")
```

✅ **Why use it?**

- Decouples subjects from observers.
- Suitable for event-driven applications.

**🔹 b) Strategy Pattern**

**Purpose:** Define a family of algorithms, encapsulate each one, and make them interchangeable.

**Use Case:** Sorting, payment methods, compression strategies.

**Python Example:**

```python
class Context:
    def __init__(self, strategy):
        self.strategy = strategy

    def execute(self, data):
        return self.strategy(data)

def strategy_upper(text):
    return text.upper()

def strategy_lower(text):
    return text.lower()

# Usage
ctx = Context(strategy_upper)
print(ctx.execute("Hello")) # HELLO
ctx.strategy = strategy_lower
print(ctx.execute("Hello")) # hello
```

✅ **Why use it?**

- Easily switch algorithms without modifying client code.

**🔹 c) Command Pattern**

**Purpose:** Encapsulate a request as an object.

**Use Case:** Undo operations, task queues, macro recording.

**Python Example:**

```python
class Light:
    def on(self):
        print("Light ON")

    def off(self):
        print("Light OFF")

class LightOnCommand:

    def __init__(self, light):
        self.light = light

    def execute(self):
        self.light.on()

class RemoteControl:
    def submit(self, command):
        command.execute()

\# Usage
light = Light()
cmd = LightOnCommand(light)
remote = RemoteControl()
remote.submit(cmd) # Light ON
```
✅ **Why use it?**

- Decouples sender from receiver.
- Supports operations like undo/redo or logging.

**🧩 Summary Table**

| **Pattern** | **Type** | **Real-World Use Case** | **Why Use It?** |
| --- | --- | --- | --- |
| Singleton | Creational | DB Connection, Config Manager | Single instance |
| Factory | Creational | Object creation logic abstraction | Scalable and clean |
| Adapter | Structural | API compatibility layer | Interface bridging |
| Decorator | Structural | Logging, auth, formatting | Dynamic behavior |
| Observer | Behavioral | UI updates, pub-sub model | Loose coupling |
| Strategy | Behavioral | Switchable algorithms | Interchangeable behavior |
| Command | Behavioral | Queues, macros, undo | Encapsulation of operations |