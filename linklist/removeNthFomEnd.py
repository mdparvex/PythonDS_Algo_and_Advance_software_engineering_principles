class Node:
    def __init__(self, data=None, next=None):
        self.data = data
        self.next=next
class Linklist:
    def __init__(self):
        self.head = None

    def insertAtBegining(self, data):
        node = Node(data, self.head)
        self.head = node
        return node
    def insertAtEnd(self, data):
        node =Node(data)
        if self.head == None:
            self.head=node
            return
        
        itr = self.head
        while itr.next:
            itr=itr.next
        itr.next=node
        return
def printList(l):
    head = l.head
    if l.head is None:
        return "None"
    list_str = ''
    while head:
        list_str = list_str + str(head.data) + "-->"
        head = head.next

    return list_str
def removeNthFromEnd(l, n):
    head = l.head
    dummy = Node(0,head)
    left = dummy
    right = head

    while n>0 and right:
        right = right.next
        n-=1
    while right:
        right = right.next
        left = left.next
    left.next = left.next.next
    merged_list = Linklist()
    merged_list.head = dummy.next
    return merged_list

l2 = Linklist()
l2.insertAtEnd(1)
l2.insertAtEnd(2)
l2.insertAtEnd(3)
l2.insertAtEnd(4)
print(f'list 2 : {printList(l2)}')
n=2
print(f'new linklist after remove {n}th node from end: {printList(removeNthFromEnd(l2,n))}')