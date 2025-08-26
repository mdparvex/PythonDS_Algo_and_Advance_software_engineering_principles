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
def reorderList(l):
    slow, fast = l.head, l.head.next
    while fast:
        slow = slow.next
        fast = fast.next.next
    second = slow.next
    prev = slow.next = None
    while second:
        next = second.next
        second.next = prev
        prev = second
        second = next
    first, second = l.head, prev
    while second:
        temp1, temp2 = first.next, second.next
        print(f'first valuee: {first.data}, second value: {second.data}')
        first.next = second
        second.next = temp1
        first, second = temp1,temp2
    rl = Linklist()
    rl.head = l.head
    return rl




l2 = Linklist()
l2.insertAtEnd(1)
l2.insertAtEnd(2)
l2.insertAtEnd(3)
l2.insertAtEnd(4)
l2.insertAtEnd(5)
print(f'list : {printList(l2)}')
print(f'reordered list: {printList(reorderList(l2))}')
