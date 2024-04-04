# search element from list, binary search

def binarySearch(lis,toFind, hi,low):
    if low>hi:
        return "Does not exist"
    elif low==hi:
        if lis[low]==toFind:
            return lis[low]
        
        return "Does not exist"
    mid = (low+hi)//2
    if lis[mid]== toFind:
        return lis[mid]
    elif lis[mid]<toFind:
        return binarySearch(lis, toFind, hi, mid+1)
    else:
        return binarySearch(lis, toFind, mid-1, low)

if __name__=='__main__':
    lis = [2,7,56,34,89,13,54,78,33]
    lis.sort()
    toFind = 76
    hi = len(lis)-1
    low = 0
    print(binarySearch(lis, toFind, hi, low))

# time complesity O(logn)