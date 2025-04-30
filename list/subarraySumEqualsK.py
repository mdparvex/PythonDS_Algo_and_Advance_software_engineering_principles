#how many subarray has sum=k
def subarraySum(nums, k):
    res=0
    curr_sum=0
    prev_diff={0:1}

    for v in nums:
        curr_sum+=v
        diff = curr_sum-k
        res += prev_diff.get(diff,0)
        prev_diff[curr_sum] = prev_diff.get(curr_sum,0)+1
    return res

print(subarraySum([1,2,1,2,1],3))