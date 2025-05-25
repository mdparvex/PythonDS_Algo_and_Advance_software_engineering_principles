def merge(arr):
    res = []
    j = 0
    arr.sort(key = lambda x: x[0])
    res.append(arr[0])

    for i in range(1, len(arr)):
        if arr[j][1]>=arr[i][0]:
            res[-1][1]= max(res[-1][1], arr[i][1])
        else:
            res.append(arr[i])
            j=i
    return res

print(merge([[1,4],[0,4]]))