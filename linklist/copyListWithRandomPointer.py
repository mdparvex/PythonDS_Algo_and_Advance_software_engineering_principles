class Node:
    def __init__(self, data=None, next=None, random = None):
        self.data = data
        self.next=next
        self.random = random
def copyListWithRandomPointer(head):
    dic = {None:None}
    h = head
    while h:
        copy = Node(h.data)
        dic[h] = copy
        h = h.next
    h = head
    while h:
        copy = dic[h]
        copy.next = dic[h.next]
        copy.random = dic[h.random]
        h =h.next
    return dic[head]

def printList(l):
    head = l
    if head is None:
        return "None"
    list_str = ''
    while head:
        list_str = list_str + str(head.data) + "-->"
        if head.random:
            list_str += str(head.random.data)+ " (random)--->"
        head = head.next

    return list_str


N1 = Node(1)
N2 = Node(2)
N3 = Node(3)
N4 = Node(4)
N1.next = N2
N2.next = N3
N3.next = N4

N1.random = N3
N2.random = None
N3.random = N1
N4.random = N2
print(f'list 2 : {printList(N1)}')

print(f'After copy list with random pointer: {printList(copyListWithRandomPointer(N1))}')