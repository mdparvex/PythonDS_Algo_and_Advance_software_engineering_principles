def bubblesort(arr):
    l = len(arr)
    for i in range(l):
        for j in range(0, l-i-1):
            if arr[j]>arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
arr=[45,3,7,56,8,34,1]
res = bubblesort(arr)
print(res)