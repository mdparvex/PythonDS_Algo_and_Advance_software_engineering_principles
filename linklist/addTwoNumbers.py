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
def addTwoList(l1,l2):
    res = r = Node()
    carry = 0

    while l1 or l2 or carry:
        val1 = l1.data if l1 else 0
        val2 = l2.data if l2 else 0
        val = val1+val2+carry
        carry = val//10
        val = val%10

        r.next = Node(val)
        r = r.next

        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None
    res_list = Linklist()
    res_list.head = res.next
    return res_list

l1 = Linklist()
l1.insertAtEnd(4)
l1.insertAtEnd(3)
l1.insertAtEnd(2)
l1.insertAtEnd(1)

l2 = Linklist()
l2.insertAtEnd(1)
l2.insertAtEnd(2)
l2.insertAtEnd(3)
l2.insertAtEnd(4)
print(f'list 1: {printList(l1)}')
print(f'list 2 : {printList(l2)}')

print(f'sum of  two linklist: {printList(addTwoList(l1.head,l2.head))}')