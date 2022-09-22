class Node():
    def __init__(self, data=None, next=None, prev=None):
        self.data=data
        self.next=next
        self.prev=prev
        
class linklist():
    def __init__(self):
        self.head = None
    def addbeg(self,data):
        node=Node(data=data, next=self.head)

        if self.head is not None:
            self.head.prev=node
        self.head=node
        return
    def addlast(self, data):
        node = Node(data) 
        itr = self.head
        if self.head==None:
            return self.addbeg(data)

        while itr.next:
            itr=itr.next
        itr.next=node
        node.prev=itr
    def addpos(self, pos, data):
        node= Node(data)
        itr = self.head
        count=1
        while itr:
            if count==pos:
                break
            count+=1
            itr=itr.next
        itr.next = node
        node.prev=itr.next 
        node.next=itr.next.next.prev
        
        
    
    def printlist(self):
        
        if self.head is None:
            print('empty')
            return
        itr = self.head
        res=''
        while itr:
            res += str(itr.data) + '->'
            itr=itr.next
        print(res)
l=linklist()
l.addbeg(20)
l.addbeg(30)
l.addbeg(40)
l.addlast(70)
l.addlast(80)
#l.addpos(1,90)
l.printlist()