import functools
def largest_num(nums):
    for i,n in enumerate(nums):
        nums[i] = str(n)
    # def compare(n1,n2):
    #     if n1+n2>n2+n1:
    #         return -1
    #     else:
    #         return 1
    
    nums = sorted(nums, key=functools.cmp_to_key(lambda n1,n2: -1 if n1+n2>n2+n1 else 1))
    print(nums)
    
    return str(int("".join(nums)))
print(largest_num([3,30,34,5,9]))