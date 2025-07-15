

def longestConsecutive(nums):
    res=0
    nums = set(nums)

    for n in nums:
        if n-1 not in nums:
            curr=0
            while n+curr in nums:
                curr+=1
            res = max(res, curr)
    return res