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
def isPalindrome(l):    
    nums = []
    head = l.head

    while head:
        nums.append(head.data)
        head = head.next

    l,r = 0, len(nums)-1
    while l<=r:
        if nums[l]!=nums[r]:
            return False
        l+=1
        r-=1
    return True

l2 = Linklist()
l2.insertAtEnd(1)
l2.insertAtEnd(3)
l2.insertAtEnd(3)
l2.insertAtEnd(1)
print(f'list 2 : {printList(l2)}')

m = isPalindrome(l2)

print(f'is palindrome?: {m}')
