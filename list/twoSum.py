def twoSum(nums, target):
    look_up={}
    for i, num in enumerate(nums):
        if target - num in look_up:
            return look_up[target-num], i
        look_up[num]=i

print(twoSum([2,3,1,5,6,4], 7))