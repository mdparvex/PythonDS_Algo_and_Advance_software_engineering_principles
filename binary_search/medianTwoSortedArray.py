#broot force
import math
def medianOfTwoSortedArray(nums1, nums2):
    merged = nums1 + nums2
    merged.sort()
    l = len(merged)
    mid = l//2
    if l%2 !=0:
        return merged[mid]
    else:
        return (merged[mid-1] + merged[mid])/2
print(medianOfTwoSortedArray([1,2,5,6], [4,7,3,9]))

#optimal
def findMedianSortedArrays(nums1, nums2):
    mergedArr = []
    l1 = len(nums1)
    l2 = len(nums2)
    i = j = 0
    while i<l1 and j<l2:
        if nums1[i]<nums2[j]:
            mergedArr.append(nums1[i])
            i+=1
        else:
            mergedArr.append(nums2[j])
            j+=1
    while l1>i:
        mergedArr.append(nums1[i])
        i+=1
    while l2>j:
        mergedArr.append(nums2[j])
        j+=1
    l = len(mergedArr)
    mid = l//2
    if l%2 !=0:
        return mergedArr[mid]
    else:
        return (mergedArr[mid-1] + mergedArr[mid])/2