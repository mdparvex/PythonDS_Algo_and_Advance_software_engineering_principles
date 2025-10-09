## 📘 Time Complexity Analysis of Recursion

### 1. Introduction

Recursion is a programming technique where a function calls itself to solve smaller subproblems. While recursion simplifies code and logic, it often makes time complexity analysis less intuitive.

Understanding recursion complexity requires identifying:
1. Number of recursive calls
2. Work done outside the recursive calls
3. Combination of results

The general recurrence relation for a recursive algorithm is:

$$
T(n)=a⋅T(n/b​)+f(n)
$$

Where:
- **a** → number of subproblems per recursion  
- **b** → factor by which input size decreases  
- **f(n)** → non-recursive work per call (e.g., loops, constant work)

---

## 🧩 2. Types of Recursion and Their Time Complexities

### 2.1. Linear Recursion

#### Example 1 — Factorial
```python
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)
```

#### Analysis:
- Each call makes one recursive call (`a = 1`)
- Input reduces by 1 each time (`b = 1`)
- Constant work per call (`f(n) = O(1)`)

\[
T(n) = T(n - 1) + O(1)
\]

Expanding gives: `T(n) = O(n)`

**Time Complexity:** `O(n)`  
**Space Complexity:** `O(n)`

---

### 2.2. Tail Recursion

#### Example 2 — Tail Recursive Factorial
```python
def factorial_tail(n, acc=1):
    if n == 0:
        return acc
    return factorial_tail(n - 1, acc * n)
```

Same recurrence: `T(n) = T(n - 1) + O(1)`

**Time Complexity:** `O(n)`  
**Space Complexity:** `O(1)` with tail call optimization

---

### 2.3. Binary Recursion

#### Example 3 — Fibonacci
```python
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

#### Analysis:
- Each call makes 2 recursive calls (`a = 2`)
- Input decreases by 1 (`b = 1`)
- Constant work per call (`f(n) = O(1)`)

\[
T(n) = T(n - 1) + T(n - 2) + O(1)
\]

Every level roughly doubles the number of calls.

**Time Complexity:** `O(2^n)`  
**Space Complexity:** `O(n)`

---

### 2.4. Divide and Conquer Recursion

#### Example 4 — Binary Search
```python
def binary_search(arr, target, low, high):
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search(arr, target, mid + 1, high)
    else:
        return binary_search(arr, target, low, mid - 1)
```

#### Analysis:
- One recursive call per step (`a = 1`)
- Input reduces by half (`b = 2`)
- Constant work (`f(n) = O(1)`)

Using Master Theorem: `T(n) = O(log n)`

**Time Complexity:** `O(log n)`  
**Space Complexity:** `O(log n)`

---

### 2.5. Tree Recursion

#### Example 5 — Merge Sort
```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)
```

#### Analysis:
- Two recursive calls (`a = 2`)
- Input divided by 2 (`b = 2`)
- Merge step costs linear time (`f(n) = O(n)`)

By Master Theorem: `T(n) = O(n log n)`

**Time Complexity:** `O(n log n)`  
**Space Complexity:** `O(n)`

---

### 2.6. Multi-Branch Recursion

#### Example 6 — Generating All Subsets
```python
def subsets(nums, index=0, current=[]):
    if index == len(nums):
        print(current)
        return
    subsets(nums, index + 1, current + [nums[index]])
    subsets(nums, index + 1, current)
```

Two recursive calls per level, total calls \( 2^n \)

**Time Complexity:** `O(2^n)`  
**Space Complexity:** `O(n)`

---

### 2.7. Recursion with Loops

#### Example 7 — Tower of Hanoi
```python
def hanoi(n, source, helper, destination):
    if n == 1:
        print(f"Move disk 1 from {source} to {destination}")
        return
    hanoi(n-1, source, destination, helper)
    print(f"Move disk {n} from {source} to {destination}")
    hanoi(n-1, helper, source, destination)
```

#### Analysis:
`T(n) = 2T(n-1) + O(1)`  → Expands to `O(2^n)`

**Time Complexity:** `O(2^n)`  
**Space Complexity:** `O(n)`

---

## 3. Summary Table

| Recursion Type        | Example               | Recurrence Relation                 | Time Complexity | Space Complexity |
|------------------------|-----------------------|-------------------------------------|-----------------|------------------|
| Linear                | Factorial             | T(n) = T(n-1) + O(1)               | O(n)            | O(n)             |
| Tail Recursive        | Factorial (tail)      | T(n) = T(n-1) + O(1)               | O(n)            | O(1)*            |
| Binary Recursion      | Fibonacci             | T(n) = T(n-1) + T(n-2) + O(1)      | O(2^n)          | O(n)             |
| Divide and Conquer    | Binary Search         | T(n) = T(n/2) + O(1)               | O(log n)        | O(log n)         |
| Tree Recursion        | Merge Sort            | T(n) = 2T(n/2) + O(n)              | O(n log n)      | O(n)             |
| Multi-Branch          | Subsets               | T(n) = 2T(n-1) + O(1)              | O(2^n)          | O(n)             |
| Recursion + Loops     | Tower of Hanoi        | T(n) = 2T(n-1) + O(1)              | O(2^n)          | O(n)             |

\* Tail call optimization applies only in certain languages.

---

## 4. Key Takeaways

- Always express recursive problems as a **recurrence relation**.
- Simplify using **substitution**, **recursion tree**, or **Master Theorem**.
- Recursive algorithms often trade **space** for **simplicity**.
- Memoization or dynamic programming can reduce exponential recursion to polynomial time.

