
from math import gcd 
from functools import reduce # Python version 3.x
def lcm(denominators):
    return reduce(lambda a,b: a*b // gcd(a,b), denominators)
    
def factors(lst):
    output = []
    for i in range(1, min(lst) + 1):
        if all(x % i == 0 for x in lst):
            output.append(i)
    return output
def getTotalX(a, b):
    # Write your code here
    x = lcm(a)
    fac = []
    v = 0
    i=0
    while v<max(b):
        v = x*i
        fac.append(v)
        i+=1
    factor = factors(b)
    seta = set(fac)
    setb = set(factor)
    if seta & setb:
        return len(seta & setb)
    else:
        return 0
    
if __name__=='__main__':
    x = getTotalX([2,6],[24,36])
    print(x)