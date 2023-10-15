#Queue implementation by Linklist

class Node:
    def __init__(self, data, next=None):
        self.data = data
        self.next = next

class Queue:
    def __init__(self):
        self.front = None
        self.rare = None

    def isEmpty(self):
        return self.front==None
    
    def enQueue(self, data):
        node = Node(data)

        if self.isEmpty():
            self.front = self.rare = node
        self.rare.next = node
        self.rare = node
        print(f'{data} is inserted in queue')
        return
    
    def deQueue(self):
        if self.isEmpty():
            print('queue is empty')
            return
        temp = self.front
        self.front = temp.next
        print(f'{temp.data} is picked from queue')

        if self.front==None:
            self.rare=None

        return
    def printlinklist(self):
        if self.isEmpty():
            print('link list is empty')
            return
        lis = ""
        itr = self.front
        while itr:
            lis += str(itr.data) + "-->"
            itr = itr.next
        print(lis)

        return
    
if __name__=='__main__':
    q = Queue()
    q.enQueue(10)
    q.enQueue(20)
    q.printlinklist()
    q.deQueue()
    q.deQueue()
    q.deQueue()
    q.printlinklist()
