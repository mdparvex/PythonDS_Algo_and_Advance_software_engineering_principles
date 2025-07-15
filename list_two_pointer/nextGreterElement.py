def nextGreaterElement(nums1, nums2):
    res = [-1]*len(nums1)
    l2=len(nums2)
    idx_nums1 = {n:i for i,n in enumerate(nums1)}
    for i in range(l2):
        if nums2[i] not in idx_nums1:
            continue
        for j in range(i+1,l2):
            if nums2[j]>nums2[i]:
                res[idx_nums1[nums2[i]]]=nums2[j]
                break
    return res

print(nextGreaterElement([4,1,2],[1,3,4,2]))