from abc import ABC, abstractmethod

class Animal(ABC):
    def __init__(self,name):
        self.name = name
        super().__init__()

    @abstractmethod
    def sound(self):
        pass
class Dog(Animal):
    def __init__(self, name,age):
        self.name = name
        self.age = age
        super().__init__(name)
    def sound(self):
        print(f'sound of {self.name} is awwwaw, and age is {self.age}')

class Cat(Animal):
    def __init__(self, name,color):
        self.color = color
        super().__init__(name)

    def sound(self):
        print(f'sound of {self.name} is meww, and color is {self.color}')

dog = Dog('donkey', 20)
dog.sound()
cat = Cat('monkey')
cat.sound()