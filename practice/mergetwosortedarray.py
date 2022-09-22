
def mergetwo(arr1, arr2):
    lenarr1 = len(arr1)
    lenarr2 = len(arr2)
    farr=[]
    i=0
    j=0
    while i<lenarr1 and j<lenarr2:
        if arr1[i]<=arr2[j]:
            farr.append(arr1[i])
            i+=1
        elif arr2[j]<=arr1[i]:
            farr.append(arr2[j])
            j+=1
    if i == lenarr1-1:
        farr.append(arr1[lenarr1-1])
    if j == lenarr2-1:
        farr.append(arr2[lenarr2-1])

    return farr

arr1=[3,5,5,7,8]
arr2 = [2,4,6,8]
print(mergetwo(arr1,arr2))