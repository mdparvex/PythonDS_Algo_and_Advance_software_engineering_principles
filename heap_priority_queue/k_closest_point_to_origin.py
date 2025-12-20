def kClosest(points, k):
    import heapq

    # Create a max heap with the first k points
    max_heap = []
    for i in range(k):
        x, y = points[i]
        dist = -(x * x + y * y)  # Use negative distance for max heap
        heapq.heappush(max_heap, (dist, points[i]))

    # Process the remaining points
    for i in range(k, len(points)):
        x, y = points[i]
        dist = -(x * x + y * y)
        if dist > max_heap[0][0]:  # Compare with the largest distance in the heap
            heapq.heappop(max_heap)
            heapq.heappush(max_heap, (dist, points[i]))

    # Extract the k closest points from the heap
    return [point for (_, point) in max_heap]