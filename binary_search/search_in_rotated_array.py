
def search(nums, target):
    l=0
    r=len(nums)-1

    while l<=r:
        mid = l+(r-l)//2

        if nums[mid]==target:
            return mid
        if nums[l]<=nums[mid]:
            if target>=nums[l] and target<nums[mid]:
                r= mid-1
            else:
                l=mid+1
        else:
            if target>nums[mid] and target<= nums[r]:
                l=mid+1
            else:
                r=mid-1
    return -1


print(search([4,5,6,7,0,1,2], 1))