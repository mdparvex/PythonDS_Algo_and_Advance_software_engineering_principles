def isVal(s):
    opening = '({['
    br = ['()', '{}','[]']
    stack = []

    for b in s:
        if b in opening:
            stack.append(b)
        elif not stack or stack.pop()+b not in br:
            return False
    return not stack

print(isVal('()[(){}]'))