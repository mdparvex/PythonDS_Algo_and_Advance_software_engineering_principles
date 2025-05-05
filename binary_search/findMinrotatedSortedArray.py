
def findMin(nums):
    l=0
    r=len(nums)-1

    while l<=r:
        if nums[l]<=nums[r]:
            return nums[l]
        mid = l+(r-l)//2

        if nums[r]<nums[mid]:
            l=mid+1
        else:
            r=mid

print(findMin([1,2,3,0]))