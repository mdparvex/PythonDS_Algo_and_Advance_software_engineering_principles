# Heap is a complete binary data structure.
from heapq import heappush, heappop, heapify
class Heap:
    def __init__(self):
        self.heap = []

    def parent(self, i):
        return (i-1)/2
    
    def insertKey(self, key):
        heappush(self.heap, key)

    def decreaseKey(self, i, new_val):
        self.heap[i]=new_val

        while i !=0 and self.heap[self.parent(i)]>self.heap[i]:
            self.heap[i], self.heap[self.parent(i)]= self.heap[self.parent(i)], self.heap[i]

    def extractMin(self):
        return heappop(self.heap)
    
    def deleteKey(self, i):
        self.decreaseKey(i, float("-inf"))
        self.extractMin()

    def getMin(self):
        return self.heap[0]
    
    def printHeap(self):
        print(self.heap)
        return
    
if __name__=="__main__":
    heapObj = Heap()
    heapObj.insertKey(3)
    heapObj.insertKey(2)
    heapObj.deleteKey(1)
    heapObj.insertKey(15)
    heapObj.insertKey(5)
    heapObj.insertKey(4)
    heapObj.insertKey(45)

    heapObj.printHeap()


    