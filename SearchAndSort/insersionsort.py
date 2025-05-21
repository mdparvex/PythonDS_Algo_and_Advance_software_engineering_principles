#time complexity O(n*n), space complexity constant
def insersionSort(arr):
    for i in range(1,len(arr)):
        key = arr[i]
        j = i-1

        while j>=0 and arr[j]>key:
            arr[j+1] = arr[j]
            j-=1
        arr[j+1]=key
    return arr

print(insersionSort([5,2,6,7,1,0]))
