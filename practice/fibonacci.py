def fibonacci(num):
    if num<0:
        return "invalid input"
    elif num==0:
        return 0
    elif num==1 or num==2:
        return 1
    else:
        return fibonacci(num-1)+fibonacci(num-2)

print(fibonacci(9))

def loopfib(num):
    a = 0
    b = 1
    res=[0,1]
    if num<0:
        return "invalid input"
    elif num==0:
        return 0
    elif num==1:
        return b
    else:
        for i in range(1,num):
            c=a+b 
            a=b 
            b=c
            res.append(c)
        return res
print(loopfib(9))
