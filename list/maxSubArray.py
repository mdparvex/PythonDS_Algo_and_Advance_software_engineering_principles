#used kadane's algorithm
def maxSubArray(nums):
        maxcurr=maxglob=nums[0]
        for i in range(1,len(nums)):
            maxcurr = max(nums[i], maxcurr+nums[i])
            if maxcurr>maxglob:
                  maxglob=maxcurr
        return maxglob

print(maxSubArray([-2,1,-3,4,-1,2,1,-5,4]))