
#build a min-heap priority queue using a list
#time complexity O(n) and space complexity O(1)
A = [3, 1, 4, 1, 5, 9, 2, -6, 5, 3, 5]
import heapq
heapq.heapify(A)
print(f'output after heapify: {A}')  # Output will be a min-heap representation of the list A

#push an element into the heap
#time complexity O(log n) and space complexity O(1)
heapq.heappush(A, 2)
print(f'output after heappush: {A}')  # Output will show the new min-heap with the element 2 added

#pop the smallest element from the heap
#time complexity O(log n) and space complexity O(1)
smallest = heapq.heappop(A)
print(f'output after heappop: {A}, popped element: {smallest}')

#heap sort
#time complexity O(n log n) and space complexity O(n)
def heap_sort(array):
    heapq.heapify(array)
    sorted_array = []
    while array:
        sorted_array.append(heapq.heappop(array))
    return sorted_array
unsorted_array = [3, 1, 4, 1, 5, 9, 2, -6, 5, 3, 5]
sorted_array = heap_sort(unsorted_array)
print(f'output after heapsort: {sorted_array}')  # Output will be the sorted version of unsorted_array

#max-heap implementation
#time complexity O(n) and space complexity O(1)
B = [3, 1, 4, 1, 5, 9, 2, -6, 5, 3, 5]
max_heap = [-x for x in B]
heapq.heapify(max_heap)
print(f'output after max-heapify: {[-x for x in max_heap]}')  # Output will be a max-heap representation of the list B

#push an element into the max-heap
#time complexity O(log n) and space complexity O(1)
heapq.heappush(max_heap, -2)
print(f'output after max-heappush: {[-x for x in max_heap]}')  # Output will show the new max-heap with the element 2 added

#push tuple into the heap
#time complexity O(log n) and space complexity O(1)
# The heap will prioritize based on the first element of the tuple
tuple_heap = []
heapq.heappush(tuple_heap, (2, 'task2'))
heapq.heappush(tuple_heap, (1, 'task1'))
heapq.heappush(tuple_heap, (3, 'task3'))

print(f'output after pushing tuples: {tuple_heap}')  # Output will show the heap with tuples prioritized by the first element
    