def hello(*args):
    for i in args:
        print(i)

hello('hello', 'go', 'check')

# *kwargs
def kwargscheck(**kwargs):
    for i,j in kwargs.items():
        print(f"key: {i} value: {j}")

kwargscheck(a=20, b=32, d=56)

class argsAndKwargs:
    def __init__(self, *args, **kwargs):
        self.name=args[0]
        self.age=args[1]
        self.gender=kwargs['g']
        self.edu=kwargs['e']
    def getValue(self):
        print(f"name: {self.name}, age:{self.age}, gender:{self.gender}, edu:{self.edu}")

res = argsAndKwargs('mamun', '25', g='male', e='BSC')
res.getValue()