#Queue implementation in array

class Queue:
    def __init__(self, capacity):
        self.size = 0
        self.rare = capacity -1
        self.front=0
        self.Q=[None]*capacity
        self.capacity = capacity

    def isEmpty(self):
        return self.size==0
    
    def isFull(self):
        return self.size==self.capacity
    
    def enQueue(self, data):
        if self.isFull():
            print('Queue is full')
            return
        self.rare = (self.rare+1) % self.capacity
        self.Q[self.rare]=data
        self.size = self.size + 1
        print(f'{data} is inserted in position of {self.rare}')
        return
    
    def deQueue(self):
        if self.isEmpty():
            print('Queue is empty')
            return
        print(f'deque element is: {self.Q[self.front]}')
        self.front = (self.front+1) % self.capacity
        self.size = self.size - 1
        return
    def qFront(self):
        if self.isEmpty():
            print('queue is empty')
            return
        print(f'Fron element of the queue is {self.Q[self.front]}')
        return
    def qRear9self(self):
        if self.isEmpty():
            print('Queue is empty')
            return
        print(f'Rare element if the queue is {self.Q[self.rare]}')


    
if __name__=='__main__':
    q = Queue(5)
    q.enQueue(10)
    q.enQueue(20)
    q.enQueue(30)
    q.enQueue(40)
    q.enQueue(50)
    q.enQueue(60)
    print(q.Q)
    q.deQueue()
    q.deQueue()
    q.deQueue()
    print(q.Q)
    q.enQueue(60)
    q.enQueue(70)
    print(q.Q)
    q.deQueue()
    q.deQueue()
    q.deQueue()
    print(q.Q)

