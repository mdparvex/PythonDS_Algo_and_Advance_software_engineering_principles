#Given an integer array nums, return an array answer such that answer[i] is equal to the product of all the elements of nums except nums[i].

def productExceptSelf(nums):
    l = len(nums)
    preProduct = [1]*l
    posProduct= [1]*l
    res = [0]*l
    for i in range(1,l):
        preProduct[i] = nums[i-1]*preProduct[i-1]

    for j in range(l-2, -1, -1):
        posProduct[j] = nums[j+1]*posProduct[j+1]
    for k in range(l):
        res[k]=preProduct[k]*posProduct[k]
    return res

print(productExceptSelf([1,2,3,4]))