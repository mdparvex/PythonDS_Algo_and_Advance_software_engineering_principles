
def indecesOftwoNums(nums, target):
    dic = {}

    for i, val in enumerate(nums):
        if target-val in dic:
            return dic[target-val],i
        else:
            dic[val]=i

print(indecesOftwoNums([2,3,4,5], 9))