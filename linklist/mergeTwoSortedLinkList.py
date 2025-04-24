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
    
def mergeSortedLinklist(l1,l2):
    dummy = Node()
    tail = dummy
    head1 = l1.head
    head2= l2.head
    while head1 and head2:
        if head1.data<head2.data:
            tail.next=head1
            head1=head1.next
        else:
            tail.next = head2
            head2=head2.next
        tail = tail.next
    if head1 is not None:
        tail.next = head1
    elif head2 is not None:
        tail.next = head2

    merged_list = Linklist()
    merged_list.head = dummy.next
    return merged_list

l1 = Linklist()
l1.insertAtEnd(1)
l1.insertAtEnd(2)
l1.insertAtEnd(4)
print(f'list 1 : {printList(l1)}')
l2 = Linklist()
l2.insertAtEnd(1)
l2.insertAtEnd(3)
l2.insertAtEnd(4)
l2.insertAtEnd(7)
print(f'list 2 : {printList(l2)}')

m = mergeSortedLinklist(l1,l2)

print(f'merged: {printList(m)}')

