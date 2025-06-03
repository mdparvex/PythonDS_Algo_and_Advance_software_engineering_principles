from functools import *

#partial
def power(a,b):
    '''a to the power b'''
    return a**b
pw2 = partial(power, b=2)
print(pw2(3))
update_wrapper(pw2,power)
print(pw2.__doc__)

#partialmethod
class Demo():
    def __init__(self):
        self.color = 'black'
    def _set_color(self,type):
        self.color = type
    p_mathod = partialmethod(_set_color, 'red')

clss = Demo()
print(clss.color)
clss.p_mathod()
print(clss.color)

#cmp_to_key

def cmp_key(a,b):
    if a>b:
        return 1
    elif a<b:
        return -1
    else:
        return 0
    
data = [30,2,13,-3,16,80,1]
sorted_list = sorted(data, key=cmp_to_key(cmp_key))
print(f'sort of this {data} list is: {sorted_list}')

#reduce
list1 = [30,2,13,-3,16,80,1]
sum_of_list1 = reduce(lambda a,b:a+b, list1)
max_of_list1 = reduce(lambda a,b: a if a>b else b, list1)
print(f'sum of list1: {sum_of_list1}')
print(f'max of list1: {max_of_list1}')

#total_ordering
@total_ordering
class N():
    def __init__(self, value):
        self.value = value

    def __lt__(self,other):
        return self.value<other.value
    def __eq__(self, other):
        return self.value==other.value
    
print('6 > 2:', N(6) > N(2))
print('3 < 1:', N(3) < N(1))
print('2 <= 7:', N(2) <= N(7))
print('9 >= 10:', N(9) >= N(10))
print('5 == 5:', N(5) == N(5))

#lru cash
@lru_cache(maxsize=None)
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print([factorial(n) for n in range(7)])

#singledispatch
@singledispatch
def fun(s):
    print(s*2)

@fun.register(str)
def _(s):
    print(s)

fun("hello world")
fun(10.5)