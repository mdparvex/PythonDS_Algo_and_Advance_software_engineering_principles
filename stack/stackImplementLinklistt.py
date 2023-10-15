# implement stack in linklist

class Node:
    def __init__(self, data, next=None):
        self.data = data
        self.next = next

class StackLinkList:
    def __init__(self):
        self.head = None

    def isEmpty(self):
        return True if self.head is None else False
    def push(self, data):
        node = Node(data)
        node.next = self.head
        self.head = node
        print(f'{data} pushed in the stack')
        return
    def pop(self):
        if self.isEmpty():
            return float('-inf')
        temp = self.head
        self.head = self.head.next
        print(f'{temp.data} is poped')
        return
    def peek(self):
        if self.isEmpty():
            return float('-inf')
        return self.head.data
    def printlist(self):
        if self.head==None:
            print('stack is empty')
            return 

        stackData=""
        itr= self.head
        while itr:
            stackData+= str(itr.data) + '->'
            itr = itr.next
        print(stackData)
        return
    
if __name__=='__main__':
    stack = StackLinkList()
    stack.push(10)
    stack.push(20)
    stack.push(30)
    stack.printlist()
    stack.pop()
    stack.printlist()
    stack.peek()
    stack.printlist()
    stack.pop()
    stack.printlist()
    stack.pop()
    stack.printlist()
    stack.pop()
    stack.printlist()
    