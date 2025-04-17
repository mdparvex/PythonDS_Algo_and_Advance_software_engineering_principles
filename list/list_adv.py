print('hello world')
def createList():
    l = list({'name':'bob', 'age': 42, 'gander':'male'}.keys())
    print(l)

def fibonaccigen(num):
    current, next_fib= 0,1

    for i in range(num):
        fib_number = current
        current, next_fib = next_fib, current+next_fib
        yield fib_number



if __name__=="__main__":
    print(list(fibonaccigen(10)))
    print([*fibonaccigen(10)])