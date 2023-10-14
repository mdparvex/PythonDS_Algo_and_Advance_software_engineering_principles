class Node:
    def __init__(self, data=None, next=None):
        self.data = data
        self.next = next

class Linklist:
    def __init__(self):
        self.head = None

    def insertBegaining(self, data):
        new_node = Node(data)
        new_node.next = self.head
        self.head = new_node

        return
    def insertEnd(self, data):
        new_node = Node(data)

        if self.head==None:
            self.head = new_node
            return
        
        itr = self.head
        while itr.next:
            itr = itr.next
        itr.next = new_node
        return
    
    def insertAtPosition(self, data, pos):
        new_node = Node(data)

        if pos<1:
            print('Invalid position')
            return
        if pos==1:
            self.insertBegaining(data)

        itr = self.head
        count = 1 
        while itr.next:
            count+=1
            if count==pos:
                print(f'value of {count} position is {itr.data}')
                new_node.next = itr.next
                itr.next = new_node
                return
            
            itr = itr.next

    def searchElement(self, element):

        itr = self.head
        count = 0

        while itr.next:
            if itr.data==element:
                print(f'{itr.data} is placed in {count}th position')
                return
            
            itr = itr.next
            count+=1
        print(f'{element} is missing in the linklist')
        return
    
    def getLength(self):
        count=0
        itr = self.head
        while itr.next:
            count+=1
            itr = itr.next
        print(f'length of linklist is {count}')
        return count
    
    def deleteAtPosition(self,pos):

        if pos<0 or pos >= self.getLength():
            print("invalid length")
            return
        if pos==0:
            self.head = self.head.next

        itr=self.head
        count=0
        while itr.next:
            if count==pos-1:
                itr.next=itr.next.next
                return
            count+=1
            itr=itr.next
            
    def reverse(self):
        prev = None
        itr = self.head
        while itr.next:
            next=itr.next
            itr.next=prev
            prev=itr
            itr=next
        self.head=prev
        return

    def printlinklist(self):
        if self.head == None:
            print('link list is empty')
            return
        lis = ""
        itr = self.head
        while itr:
            lis += str(itr.data) + "-->"
            itr = itr.next
        print(lis)

        return
    
if __name__=='__main__':
    linklist = Linklist()
    linklist.insertBegaining(5)
    print('5 inserted')
    linklist.insertBegaining(6)
    print('6 inserted')
    linklist.insertBegaining(7)
    print('7 inserted')
    print('--------')
    linklist.insertEnd(8)
    print('8 inserted end')
    linklist.insertEnd(9)
    print('9 inserted end')

    linklist.printlinklist()

    linklist.insertAtPosition(3, 1)
    print('pos printed')

    linklist.searchElement(8)
    linklist.getLength()

    linklist.printlinklist()

    linklist.deleteAtPosition(0)
    linklist.printlinklist()

    linklist.reverse()
    linklist.printlinklist()
