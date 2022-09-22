def revarray(arr):
    res =[]
    l = len(arr)
    for i in range(l-1,-1,-1):
        res.append(arr[i])
    return res 

print(revarray([2,3,4,5,6,7,8]))