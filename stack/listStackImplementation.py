# create a steck using array and linklist

from sys import maxsize

def creatStack():
    stack =[]
    return stack
def isEmpty(stack):
    return len(stack)==0
def push(stack, item):
    stack.append(item)
    print(f'{item} is pushed in the stack')
    return
def pop(stack):
    if isEmpty(stack):
        return str(-maxsize - 1)
    return stack.pop()
def peek(stack):
    if isEmpty(stack):
        return str(-maxsize-1)
    return stack[len(stack)-1]
if __name__=='__main__':
    stack = creatStack()
    push(stack,10)
    push(stack,20)
    push(stack,30)
    print(f'{pop(stack)} poped from the stack')
    print(f'{peek(stack)} peek from the stack')
    print(f'remaining values in stack: {stack}')