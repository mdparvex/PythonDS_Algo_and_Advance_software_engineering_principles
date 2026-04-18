# Python Problem Solving Interview Questions (Mid/Senior Level)

# 1. Two Sum (HashMap)
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i

# Key Insight
# Trade space for time
# Avoid nested loops (O(n²) → O(n))

# 2. Longest Substring Without Repeating Characters (Sliding Window)
def longest_unique(s):
    seen = set()
    left = 0
    max_len = 0

    for right in range(len(s)):
        while s[right] in seen:
            seen.remove(s[left])
            left += 1
        seen.add(s[right])
        max_len = max(max_len, right - left + 1)

    return max_len

# Key Insight
# Use sliding window
# Expand → contract


# 3. Merge Intervals (Greedy)
def merge_intervals(intervals):
    intervals.sort()
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_end = merged[-1][1]
        if start <= last_end:
            merged[-1][1] = max(last_end, end)
        else:
            merged.append([start, end])

    return merged

# Key Insight
# Sort first
# Greedy merging


# 4. LRU Cache
#Design LRU cache with O(1) operations.
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# Key Insight
# HashMap + Doubly Linked List concept
# OrderedDict handles both

# 5. Binary Search
#Find element in sorted array.
def binary_search(nums, target):
    left, right = 0, len(nums) - 1

    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1

# Key Insight
# Divide and conquer → O(log n)

# 6. Detect Cycle in Linked List
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def has_cycle(head):
    slow = fast = head

    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False

# Key Insight
# Fast pointer catches slow pointer

# 7. Top K Frequent Elements
from collections import Counter
import heapq


def top_k(nums, k):
    count = Counter(nums)
    return heapq.nlargest(k, count.keys(), key=count.get)

# Key Insight
# Heap → efficient top-k extraction

# 8. Valid Parentheses (Stack)
def is_valid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}

    for char in s:
        if char in mapping:
            if not stack or stack.pop() != mapping[char]:
                return False
        else:
            stack.append(char)

    return not stack

# Key Insight
# LIFO structure → stack

# 9. Number of Islands (DFS)
def num_islands(grid):
    def dfs(r, c):
        if r < 0 or c < 0 or r >= len(grid) or c >= len(grid[0]) or grid[r][c] == '0':
            return
        grid[r][c] = '0'
        dfs(r+1, c)
        dfs(r-1, c)
        dfs(r, c+1)
        dfs(r, c-1)

    count = 0
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == '1':
                dfs(r, c)
                count += 1

    return count

# Key Insight
# Graph traversal problem

# 10. Kth Largest Element (Quickselect)
import random


def find_kth(nums, k):
    def quickselect(left, right):
        pivot = nums[random.randint(left, right)]
        l, r = left, right

        while l <= r:
            while nums[l] > pivot:
                l += 1
            while nums[r] < pivot:
                r -= 1
            if l <= r:
                nums[l], nums[r] = nums[r], nums[l]
                l += 1
                r -= 1

        if left + k - 1 <= r:
            return quickselect(left, r)
        if left + k - 1 >= l:
            return quickselect(l, right)
        return nums[r + 1]

    return quickselect(0, len(nums) - 1)

#11. Move all zeros to the end of the array without using any sorting/default function algorithm.
arr = [1, 2, 4, 0, 8, 0, 2, 0]

def move_zero_to_end(arr):
	l =0
	for i in range(len(arr)):
		if arr[i]!=0:
			arr[l], arr[i] = arr[i], arr[l]
			l+=1
	return arr
	
print(move_zero_to_end(arr))

# Key Insight
# Average O(n)
# Better than sorting (O(n log n))

# | Pattern        | Problems           |
# | -------------- | ------------------ |
# | HashMap        | Two Sum, Frequency |
# | Sliding Window | Substring problems |
# | Two Pointers   | Sorted arrays      |
# | Stack          | Parentheses        |
# | DFS/BFS        | Graph/Matrix       |
# | Heap           | Top K              |
# | Binary Search  | Sorted data        |
# | Greedy         | Intervals          |


# In interviews, don’t just code. Always say:

# Brute force approach
# Optimized approach
# Time & space complexity
# Trade-offs
