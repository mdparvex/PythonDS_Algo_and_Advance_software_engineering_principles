def subsets(nums):
    if not nums:
        return [[]]
    
    first_element = nums[0]
    rest_element = nums[1:]

    subset_without_first = subsets(rest_element)

    subset_with_first = []

    for set in subset_without_first:
        subset_with_first.append([first_element] +set)
    return subset_without_first + subset_with_first

print(subsets([2,3,6,7]))