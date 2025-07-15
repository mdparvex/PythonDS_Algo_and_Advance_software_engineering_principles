
def rotate(nums, k):
    """
    Do not return anything, modify nums in-place instead.
    """
    def reverse(l,r,nums):
        while l<r:
            nums[l], nums[r] = nums[r], nums[l]
            l,r=l+1, r-1

    k = k%len(nums)
    reverse(0,len(nums)-1, nums)
    reverse(0,k-1, nums)
    reverse(k, len(nums)-1,nums)
    return nums

print(rotate([1,2,3,4,5,6,7], 3))