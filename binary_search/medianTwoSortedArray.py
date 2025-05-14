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
    
# O(log(m+n))
def findMedianSortedArrays(nums1, nums2):
    A, B = nums1, nums2
    total = len(nums1)+len(nums2)
    half = total//2

    if len(A)>len(B):
        A, B = B, A
    l, r = 0, len(A)-1

    while True:
        i = (l + r)//2
        j = half - i - 2

        Aleft = A[i] if i>=0 else float("-infinity")
        Aright = A[i+1] if (i+1) < len(A) else float("infinity")
        Bleft = B[j] if j>=0 else float("-infinity")
        Bright = B[j+1] if (j+1) < len(B) else float("infinity")

        if Aleft <= Bright and Bleft <= Aright:
            if total%2:
                return min(Aright, Bright)
            return (max(Aleft, Bleft)+min(Aright,Bright))/2
        elif Aleft>Bright:
            r = i-1
        else:
            l = i+1