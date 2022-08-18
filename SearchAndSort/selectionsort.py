
def selectionsort(arr):
    for i in range(len(arr)):
        min_idx =i

        for j in range(i+1, len(arr)):
            if arr[min_idx]>arr[j]:
                min_idx=j 
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr
arr = [56,7,23,89,27,4]
res = selectionsort(arr)
print(res)