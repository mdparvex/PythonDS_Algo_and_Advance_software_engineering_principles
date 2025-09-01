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

def mergeKLists(lists):
        if not lists or len(lists)==0:
            return None
        while len(lists)>1:
            mergeList = []
            for i in range(0,len(lists),2):
                l1 = lists[i]
                l2 = lists[i+1] if (i+1)<len(lists) else None
                mergeList.append(mergeSortedLinklist(l1,l2))
            lists = mergeList
        merged_list = Linklist()
        merged_list.head = lists[0]
        return merged_list
    
def mergeSortedLinklist(l1,l2):
    dummy = Node()
    tail = dummy
    while l1 and l2:
        if l1.data<l2.data:
            tail.next=l1
            l1=l1.next
        else:
            tail.next = l2
            l2=l2.next
        tail = tail.next
    if l1 is not None:
        tail.next = l1
    elif l2 is not None:
        tail.next = l2

    return dummy.next

list1 = Linklist()
list1.insertAtEnd(1)
list1.insertAtEnd(2)
list1.insertAtEnd(4)
print(f'list 1 : {printList(list1)}')
list2 = Linklist()
list2.insertAtEnd(1)
list2.insertAtEnd(3)
list2.insertAtEnd(4)
list2.insertAtEnd(7)
print(f'list 2 : {printList(list2)}')
list3 = Linklist()
list3.insertAtEnd(10)
list3.insertAtEnd(30)
list3.insertAtEnd(40)
list3.insertAtEnd(70)
print(f'list 3 : {printList(list3)}')
list4 = Linklist()
list4.insertAtEnd(10)
list4.insertAtEnd(30)

m = mergeKLists([list1.head,list2.head,list3.head,list4.head])

print(f'merged: {printList(m)}')

