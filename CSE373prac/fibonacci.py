
def fibonacci(n):
    if n<1:
        print("Invalid")
    if n==0:
        return 0
    if n==1 or n==2:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
    
if __name__=='__main__':
    print(fibonacci(9))