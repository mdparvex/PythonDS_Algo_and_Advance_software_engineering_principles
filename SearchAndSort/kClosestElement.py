def kcolsestelement(arr, k, n):
    arr.sort()
    idx = 0
    count = 0
    li=0
    ri=0
    res=[]
    for i in range(len(arr)):
        if arr[i]==k:
            idx=i
            li=i-1
            ri=i+1
            break
    while count!=n:
        if (arr[idx]-arr[li])<(arr[ri]-arr[idx]):
            res.append(arr[li])
            li -=1
            count +=1
        elif (arr[idx]-arr[li])>(arr[ri]-arr[idx]):
            res.append(arr[ri])
            ri +=1
            count +=1
    return res

arr=[12, 16, 22, 30, 35, 39, 42, 45, 48, 50, 53, 55, 56]

result = kcolsestelement(arr, 35, 4)
print(result)