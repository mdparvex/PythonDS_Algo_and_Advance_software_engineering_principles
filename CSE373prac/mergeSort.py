# merge sort python list

def mergeSort(lis):
    if len(lis)>1:
        mid = len(lis)//2
        L = lis[:mid]
        R = lis[mid:]
        mergeSort(L)
        mergeSort(R)
        i=j=k=0
        
        while i<len(L) and j<len(R):
            if L[i]<=R[j]:
                lis[k]=L[i]
                i+=1
            else:
                lis[k]=R[j]
                j+=1
            k+=1
        while i<len(L):
            lis[k]=L[i]
            i+=1
            k+=1
        while j<len(R):
            lis[k]=R[j]
            j+=1
            k+=1
    

if __name__=='__main__':
    l = [2,56,12,34,87,23,54]
    print(f'unsorted array is : {l}')
    sortList = mergeSort(l)
    print(f'sorted array: {sortList}')
