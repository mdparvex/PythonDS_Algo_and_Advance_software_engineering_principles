"""The LinkedList code from before is provided below.
Add three functions to the LinkedList.
"get_position" returns the element at a certain position.
The "insert" function will add an element to a particular
spot in the list.
"delete" will delete the first element with that
particular value.
Then, use "Test Run" and "Submit" to run the test cases
at the bottom."""

class Element(object):
    def __init__(self, value):
        self.value = value
        self.next = None
        
class LinkedList(object):
    def __init__(self, head=None):
        self.head = head
        
    def append(self, new_element):
        current = self.head
        if self.head:
            while current.next:
                current = current.next
            current.next = new_element
        else:
            self.head = new_element
            
    def get_position(self, position):
        
        count = 0
        current = self.head
        while current.next:
            if count==position:
                return current.value
                
            current = current.next
            count +=1
        return None
    
    def insert(self, new_element, position):
        
        if position == 1:
            new_element.next = self.head
            self.head = new_element
        else:
            before = self.get_position(position-1)
            if before is None:
                raise ValueError("invalid position")
            new_element.next = before.next
            before.next = new_element
    
    
    def delete(self, value):
        """Delete the first node with a given value."""
        pass

# Test cases
# Set up some Elements
e1 = Element(1)
e2 = Element(2)
e3 = Element(3)
e4 = Element(4)

# Start setting up a LinkedList
ll = LinkedList(e1)
ll.append(e2)
ll.append(e3)

# Test get_position
# Should print 3
print(ll.head.next.next.value)
# Should also print 3
print(ll.get_position(3))

# Test insert
ll.insert(e4,3)
# Should print 4 now
print(ll.get_position(3))

# Test delete
#ll.delete(1)
# Should print 2 now
print(ll.get_position(1))
# Should print 4 now
print(ll.get_position(2))
# Should print 3 now
print(ll.get_position(3))