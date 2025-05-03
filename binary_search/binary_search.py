
def binartSearch(arr, x):
    left = 0
    right = len(arr)-1
    while left <= right:
        mid = left + (right-left)//2
        if arr[mid]==x:
            return mid
        elif arr[mid]<x:
            left=mid+1
        else:
            right=mid-1
    return -1
x=9
search = binartSearch([2,3,5,7,9],x)
if search==-1:
    print("Not found")
else:
    print(f'x fount in this {search} index')