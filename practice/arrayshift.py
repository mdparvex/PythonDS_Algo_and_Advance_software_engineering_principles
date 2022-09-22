def arrayshift(arr):
    a=arr[len(arr)-1]
    for i in range(len(arr)-1,0,-1):
        arr[i]=arr[i-1]
    arr[0]=a
    return arr
        
    
print(arrayshift([2,3,4,5,6]))