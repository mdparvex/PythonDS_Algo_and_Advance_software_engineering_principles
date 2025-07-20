from typing import List
def evalRPN(tokens: List[str]) -> int:
    num_stack = []
    op = ['+','-','*','/']

    for t in tokens:
        if t not in op:
            num_stack.append(int(t))
        else:
            num2 = num_stack.pop()
            num1 = num_stack.pop()
            if t=='+':
                res = num1+num2
            if t=='-':
                res = num1-num2
            if t=='*':
                res = num1*num2
            if t=='/':
                res = num1/num2
            num_stack.append(int(res))
    return num_stack.pop()

print(evalRPN(["10","6","9","3","+","-11","*","/","*","17","+","5","+"]))
    