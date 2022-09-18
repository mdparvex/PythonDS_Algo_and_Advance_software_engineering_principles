class Node(object):
    def __init__(self, data=None, next=None):
        self.data = data
        self.next= next
        

class linklist():
    def __init__(self):
        self.head=None
        
    def insertbeg(self, val):
        node= Node(val, self.head)
        self.head=node
    def insertend(self, val):
        head= self.head
        if head==None:
            node=Node(val,self.head)
            self.head=node
            return
        while head.next:
            head=head.next
        head.next = Node(val)
    def printlist(self):
        if self.head == None:
            print('linklist is empty')

        strl=''
        itr = self.head
        while itr:
            strl += str(itr.data)+'-->'
            itr = itr.next
        print(strl)
                
l=linklist()
l.insertbeg(4)
l.insertbeg(3)
l.insertbeg(2)
l.insertend(9)
l.insertend(8)
l.insertend(7)
l.printlist()
        
