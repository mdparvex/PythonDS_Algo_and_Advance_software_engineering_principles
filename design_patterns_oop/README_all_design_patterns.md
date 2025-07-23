Great! There are **23 classic design patterns** (known as the GoF or “Gang of Four” patterns), and you've asked for all of them with:

✅ **Consistent explanation structure**  
✅ **Python code examples**  
✅ **Real-world use cases**

I'll now begin generating them **category by category** with the following structure for **each pattern**:

- **🔹 Pattern Name**
- **Purpose**
- **Use Case**
- **Python Example**
- **Why Use It?**

**🏗️ 1. Creational Patterns**

**🔹 a) Singleton Pattern**

**Purpose:** Ensure a class has only one instance and provide a global point of access to it.

**Use Case:** Configuration managers, logging, DB connection.

```python
class Singleton:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

# Usage
s1 = Singleton()
s2 = Singleton()
print(s1 is s2)  # True

```
✅ **Why use it?**

- Avoid multiple initializations of a heavy object
- Maintain global state

**🔹 b) Factory Method**

**Purpose:** Define an interface for creating an object, but let subclasses alter the type of objects that will be created.

**Use Case:** GUI frameworks (ButtonFactory: WindowsButton, MacButton)

```python
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof"

class Cat(Animal):
    def speak(self):
        return "Meow"

class AnimalFactory:
    def get_animal(self, type):
        if type == 'dog':
            return Dog()
        if type == 'cat':
            return Cat()
        raise ValueError("Unknown animal")

# Usage
animal = AnimalFactory().get_animal('dog')
print(animal.speak())  # Woof

```

✅ **Why use it?**

- Abstract object creation logic
- Simplifies instantiation logic for clients

**🔹 c) Abstract Factory**

**Purpose:** Provide an interface for creating families of related or dependent objects without specifying their concrete classes.

**Use Case:** UI toolkits for different OS: WindowsFactory, MacFactory

```python
class Button:
    pass
class WindowsButton(Button):
    def click(self):
        return "Windows Button Clicked"
class MacButton(Button):
    def click(self):
        return "Mac Button Clicked"

class GUIFactory:
    def create_button(self):
        pass

class WindowsFactory(GUIFactory):
    def create_button(self):
        return WindowsButton()

class MacFactory(GUIFactory):
    def create_button(self):
        return MacButton()

# Usage
def get_factory(os_type):
    return WindowsFactory() if os_type == "Windows" else MacFactory()

factory = get_factory("Windows")
button = factory.create_button()
print(button.click())  # Windows Button Clicked

```

✅ **Why use it?**

- Produces related components
- Adds scalability for multiple families

**🔹 d) Builder Pattern**

**Purpose:** Separate the construction of a complex object from its representation.

**Use Case:** Constructing complex objects like documents, forms, or pizzas.

```python
class Car:
    def __init__(self):
        self.parts = []
    def add(self, part):
        self.parts.append(part)
    def show(self):
        print("Car Parts:", self.parts)

class CarBuilder:
    def __init__(self):
        self.car = Car()
    def build_engine(self):
        self.car.add("Engine")
    def build_wheels(self):
        self.car.add("Wheels")
    def get_car(self):
        return self.car

# Usage
builder = CarBuilder()
builder.build_engine()
builder.build_wheels()
car = builder.get_car()
car.show()  # Car Parts: ['Engine', 'Wheels']

```

✅ **Why use it?**

- Flexible object creation step-by-step
- Great for complex objects

**🔹 e) Prototype Pattern**

**Purpose:** Create new objects by copying an existing object, known as the prototype.

**Use Case:** Game dev (duplicate characters), document templates

```python
import copy

class Prototype:
    def clone(self):
        return copy.deepcopy(self)

class Document(Prototype):
    def __init__(self, name):
        self.name = name
    def show(self):
        print("Document:", self.name)

# Usage
doc1 = Document("Invoice Template")
doc2 = doc1.clone()
doc2.name = "Invoice #123"
doc1.show()  # Invoice Template
doc2.show()  # Invoice #123

```

✅ **Why use it?**

- Avoids expensive object creation
- Cloning is fast and customizable

## Now let’s move to the *Structural Design Patterns* — these patterns help organize classes and objects to form larger structures and ensure flexibility and efficiency.

**🧱 2. Structural Patterns**

**🔹 a) Adapter Pattern**

**Purpose:** Convert the interface of a class into another interface the client expects.

**Use Case:** Making incompatible interfaces work together, e.g., using a European plug in an American socket.

```python
class EuropeanPlug:
    def connect(self):
        return "220V Power"

class AmericanAdapter:
    def __init__(self, plug):
        self.plug = plug

    def connect(self):
        return f"Converted: {self.plug.connect()} to 110V"

# Usage
plug = EuropeanPlug()
adapter = AmericanAdapter(plug)
print(adapter.connect())  # Converted: 220V Power to 110V

```

✅ **Why use it?**

- Bridges mismatched interfaces
- Promotes reusability of legacy code

**🔹 b) Bridge Pattern**

**Purpose:** Decouple an abstraction from its implementation so the two can vary independently.

**Use Case:** UI rendering on multiple platforms (Windows, Linux, macOS)

```python
class Renderer:
    def render_circle(self, radius): pass

class VectorRenderer(Renderer):
    def render_circle(self, radius):
        print(f"Drawing Circle with radius {radius} using Vector")

class RasterRenderer(Renderer):
    def render_circle(self, radius):
        print(f"Drawing Circle with radius {radius} using Pixels")

class Circle:
    def __init__(self, renderer, radius):
        self.renderer = renderer
        self.radius = radius

    def draw(self):
        self.renderer.render_circle(self.radius)

# Usage
vector = VectorRenderer()
circle = Circle(vector, 5)
circle.draw()  # Drawing Circle with radius 5 using Vector

```

✅ **Why use it?**

- Supports multiple implementations
- Reduces class explosion (combination explosion)

**🔹 c) Composite Pattern**

**Purpose:** Compose objects into tree structures to represent part-whole hierarchies.

**Use Case:** Filesystem, HTML DOM, UI component trees

```python
class Component:
    def show(self, indent=0):
        pass

class File(Component):
    def __init__(self, name):
        self.name = name
    def show(self, indent=0):
        print("  " * indent + self.name)

class Folder(Component):
    def __init__(self, name): 
        self.name = name
        self.children = []

    def add(self, component):
        self.children.append(component)

    def show(self, indent=0):
        print("  " * indent + self.name)
        for child in self.children:
            child.show(indent + 1)

# Usage
root = Folder("root")
root.add(File("file1.txt"))
sub = Folder("subfolder")
sub.add(File("file2.txt"))
root.add(sub)
root.show()

```

✅ **Why use it?**

- Treat individual and group objects uniformly
- Elegant recursive structure

**🔹 d) Decorator Pattern**

**Purpose:** Add new functionality to an object dynamically without altering its structure.

**Use Case:** Adding logging, caching, validation

```python
def bold(func):
    def wrapper():
        return "<b>" + func() + "</b>"
    return wrapper

@bold
def greet():
    return "Hello"

print(greet())  # <b>Hello</b>

```

✅ **Why use it?**

- Avoids subclass explosion
- Dynamically enhances functionality

**🔹 e) Facade Pattern**

**Purpose:** Provide a simplified interface to a complex subsystem.

**Use Case:** Library management system, payment gateways, hotel booking APIs

```python
class CPU:
    def freeze(self):
        print("Freezing CPU...")
    def execute(self):
        print("Executing commands...")

class Memory:
    def load(self):
        print("Loading memory...")

class ComputerFacade:
    def __init__(self):
        self.cpu = CPU()
        self.memory = Memory()

    def start(self):
        self.cpu.freeze()
        self.memory.load()
        self.cpu.execute()

# Usage
computer = ComputerFacade()
computer.start()

```

✅ **Why use it?**

- Simplifies complex systems
- Hides low-level details

**🔹 f) Flyweight Pattern**

**Purpose:** Reduce memory usage by sharing as much data as possible with similar objects.

**Use Case:** Text editor character formatting, game particle systems

```python
class Character:
    def __init__(self, symbol):
        self.symbol = symbol

    def display(self, font):
        print(f"Displaying '{self.symbol}' with font {font}")

class CharacterFactory:
    _characters = {}

    def get_character(self, symbol):
        if symbol not in self._characters:
            self._characters[symbol] = Character(symbol)
        return self._characters[symbol]

# Usage
factory = CharacterFactory()
a1 = factory.get_character('A')
a2 = factory.get_character('A')
print(a1 is a2)  # True
a1.display("Arial")

```

✅ **Why use it?**

- Improves performance for large object sets
- Reduces memory footprint

**🔹 g) Proxy Pattern**

**Purpose:** Provide a placeholder to control access to another object.

**Use Case:** Virtual proxies (lazy loading), access control, logging

```python
class RealImage:
    def display(self):
        print("Displaying real image")

class ProxyImage:
    def __init__(self):
        self.real_image = None

    def display(self):
        if self.real_image is None:
            self.real_image = RealImage()
        print("Proxy controlling access...")
        self.real_image.display()

# Usage
image = ProxyImage()
image.display()  # Proxy + RealImage logic

```

✅ **Why use it?**

- Adds a layer of control
- Useful for lazy loading and access restrictions

**✅ Summary Table – Structural Patterns**

| **Pattern** | **Use Case Example** | **Why Use It?** |
| --- | --- | --- |
| Adapter | Plug/Socket conversion | Bridge incompatible interfaces |
| Bridge | Render engines | Decouple abstraction from implementation |
| Composite | File system tree | Treat individual and group objects equally |
| Decorator | Logging, validation | Dynamic behavior extension |
| Facade | Hotel booking API | Simplified interface |
| Flyweight | Text editor glyphs | Share data, reduce memory |
| Proxy | Virtual image loader | Controlled access to object |

## Let’s now dive into the *Behavioral Design Patterns*, which focus on communication between objects — how they interact and delegate responsibility.

**🧠 3. Behavioral Patterns**

**🔹 a) Chain of Responsibility**

**Purpose:** Pass a request along a chain of handlers. Each handler decides whether to process or pass it on.

**Use Case:** Logging levels, technical support escalation

```python
class Handler:
    def __init__(self, successor=None):
        self.successor = successor

    def handle(self, request):
        pass

class LowLevelHandler(Handler):
    def handle(self, request):
        if request < 10:
            print(f"LowLevelHandler handled: {request}")
        elif self.successor:
            self.successor.handle(request)

class HighLevelHandler(Handler):
    def handle(self, request):
        print(f"HighLevelHandler handled: {request}")

# Usage
chain = LowLevelHandler(HighLevelHandler())
chain.handle(5)   # LowLevelHandler handled: 5
chain.handle(15)  # HighLevelHandler handled: 15

```

✅ **Why use it?**

- Avoids coupling sender and receiver
- Adds flexibility in request handling

**🔹 b) Command**

**Purpose:** Encapsulate a request as an object, allowing undo, logging, and queuing of requests.

**Use Case:** Remote controls, UI button actions, task queues

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

# Usage
light = Light()
cmd = LightOnCommand(light)
remote = RemoteControl()
remote.submit(cmd)  # Light ON

```

✅ **Why use it?**

- Decouples invoker and receiver
- Supports undo/redo, logging

**🔹 c) Interpreter**

**Purpose:** Define a grammar and interpret sentences in that grammar.

**Use Case:** Mathematical expressions, scripting engines, SQL parsers

```python
class Number:
    def __init__(self, value):
        self.value = value
    def interpret(self):
        return self.value

class Add:
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def interpret(self):
        return self.left.interpret() + self.right.interpret()

# Usage: (3 + 4)
expr = Add(Number(3), Number(4))
print(expr.interpret())  # 7

```

✅ **Why use it?**

- Simplifies custom language processing
- Great for rule engines or DSLs

**🔹 d) Iterator**

**Purpose:** Provide a way to access elements of an aggregate object without exposing its structure.

**Use Case:** Iterating over custom collections

```python
class MyList:
    def __init__(self):
        self.items = []
    def add(self, item):
        self.items.append(item)
    def __iter__(self):
        return iter(self.items)

# Usage
my_list = MyList()
my_list.add("A")
my_list.add("B")

for item in my_list:
    print(item)

```

✅ **Why use it?**

- Uniform access to different collections
- Clean iteration abstraction

**🔹 e) Mediator**

**Purpose:** Define an object that encapsulates how a set of objects interact.

**Use Case:** UI widgets, chatroom participants, form coordination

```python
class ChatRoom:
    def show_message(self, user, message):
        print(f"[{user.name}]: {message}")

class User:
    def __init__(self, name, chatroom):
        self.name = name
        self.chatroom = chatroom

    def send(self, message):
        self.chatroom.show_message(self, message)

# Usage
room = ChatRoom()
u1 = User("Alice", room)
u2 = User("Bob", room)
u1.send("Hello Bob!")  # [Alice]: Hello Bob!

```

✅ **Why use it?**

- Reduces tight coupling between components
- Centralized control of communication

**🔹 f) Memento**

**Purpose:** Capture and restore an object’s internal state without violating encapsulation.

**Use Case:** Undo functionality in editors

```python
class Editor:
    def __init__(self):
        self.text = ""
    def write(self, word):
        self.text += word
    def save(self):
        return self.text
    def restore(self, memento):
        self.text = memento

# Usage
editor = Editor()
editor.write("Hello ")
memento = editor.save()
editor.write("World!")
print(editor.text)  # Hello World!
editor.restore(memento)
print(editor.text)  # Hello 

```

✅ **Why use it?**

- Enables undo/redo
- Restores previous state safely

**🔹 g) Observer**

**Purpose:** Define a one-to-many dependency so when one object changes, all dependents are notified.

**Use Case:** Event systems, UI updates, real-time dashboards

```python
class Subject:
    def __init__(self):
        self._observers = []
    def attach(self, obs):
        self._observers.append(obs)
    def notify(self, msg):
        for obs in self._observers:
            obs.update(msg)

class Observer:
    def update(self, msg):
        print(f"Observer got: {msg}")

# Usage
subject = Subject()
obs1 = Observer()
obs2 = Observer()
subject.attach(obs1)
subject.attach(obs2)
subject.notify("New Data")

```

✅ **Why use it?**

- Loose coupling
- Great for real-time updates

**🔹 h) State**

**Purpose:** Allow an object to alter its behavior when its internal state changes.

**Use Case:** Media players (play/pause/stop), traffic lights

```python
class State:
    def handle(self): pass

class Playing(State):
    def handle(self): print("Playing music")

class Paused(State):
    def handle(self): print("Paused music")

class Player:
    def __init__(self):
        self.state = Paused()
    def set_state(self, state):
        self.state = state
    def play(self):
        self.state.handle()

# Usage
player = Player()
player.play()  # Paused music
player.set_state(Playing())
player.play()  # Playing music

```

✅ **Why use it?**

- Removes big conditionals
- Behavior depends on state

**🔹 i) Strategy**

**Purpose:** Define a family of algorithms, encapsulate them, and make them interchangeable.

**Use Case:** Payment methods, sorting algorithms

```python
def strategy_upper(text):
    return text.upper()
def strategy_lower(text):
    return text.lower()

class Context:
    def __init__(self, strategy):
        self.strategy = strategy
    def execute(self, text):
        return self.strategy(text)

# Usage
context = Context(strategy_upper)
print(context.execute("Hello"))  # HELLO
context.strategy = strategy_lower
print(context.execute("Hello"))  # hello

```

✅ **Why use it?**

- Change behavior at runtime
- Clean separation of algorithms

**🔹 j) Template Method**

**Purpose:** Define the skeleton of an algorithm, letting subclasses override certain steps.

**Use Case:** Game frameworks, report generators, data parsers

```python
class Game:
    def play(self):
        self.initialize()
        self.start_play()
        self.end_play()

    def initialize(self):
        pass
    def start_play(self):
        pass
    def end_play(self):
        pass

class Chess(Game):
    def initialize(self):
        print("Setting up Chess board")
    def start_play(self):
        print("Chess started")
    def end_play(self):
        print("Game Over")

# Usage
game = Chess()
game.play()

```

✅ **Why use it?**

- Defines algorithm skeleton
- Promotes code reuse

**🔹 k) Visitor**

**Purpose:** Separate algorithms from the objects on which they operate.

**Use Case:** Compilers, AST traversal, tax calculation

```python
class Visitor:
    def visit(self, element):
        pass

class TaxVisitor(Visitor):
    def visit(self, item):
        print(f"Tax for {item.name}: {item.price * 0.1}")

class Item:
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def accept(self, visitor):
        visitor.visit(self)

# Usage
item = Item("Book", 100)
visitor = TaxVisitor()
item.accept(visitor)

```

✅ **Why use it?**

- Separate operations from objects
- Useful for new behaviors without modifying classes

**✅ Summary Table – Behavioral Patterns**

| **Pattern** | **Real-World Use Case** | **Why Use It?** |
| --- | --- | --- |
| Chain of Responsibility | Support escalation | Flexible request routing |
| Command | Button actions, undo | Encapsulates requests |
| Interpreter | Expression parser | Process grammar and languages |
| Iterator | Collection traversal | Abstract iteration logic |
| Mediator | Chat systems, forms | Centralized communication |
| Memento | Undo/Redo in editors | Restore object state |
| Observer | UI events, pub-sub | One-to-many notifications |
| State | Player modes, workflow | Dynamic behavior change |
| Strategy | Sorting, payment gateways | Interchangeable algorithms |
| Template Method | Game engine, reports | Algorithm skeleton |
| Visitor | AST traversal, reporting | Add operations without altering objects |