def printn(num,l,var):
    if (l >= num):
        return
    elif (l == 0):
        print("1")
        printn(num,l + 1,var)
    elif (l == 1):
        print(var)
        printn(num,l + 1,var)
    elif (l%2)==0:
        var = var+"1"
        print(var)
        printn(num,l + 1,var)
    elif (l%2)==1:
        var=var+"0"
        print(var)
        printn(num,l + 1,var)
    else:
        print('invalid')
        return



if __name__ == '__main__':
    n =6 
    #n is total row i want to print
    printn(n,0, "10")