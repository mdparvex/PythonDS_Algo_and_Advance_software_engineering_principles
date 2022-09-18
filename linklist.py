class Node:
    def __init__(self, data=None, next=None):
        self.data = data
        self.next = next

class linklist:
    def __init__(self):
        self.head = None

    def insert_at_beganing(self, data):
        node = Node(data, self.head)
        self.head = node
        return
    def insert_at_end(self, data):
        
        if self.head is None:
            self.head= Node(data, None)
            return
        itr = self.head
        while itr.next: 
            itr = itr.next
        itr.next == Node(data, None)
        
    def printlist(self):
        if self.head == None:
            print('linklist is empty')

        strl=''
        itr = self.head
        while itr:
            strl += str(itr.data)+'-->'
            itr = itr.next
        print(strl)
    def remove(self, index):
        if index<0 or index>= self.get_length():
            raise Exception('invalid index')
        if index == 0:
            self.head = self.head.next 
            return 
        count=0
        itr=self.head
        while itr:
            if count == index-1:
                itr.next=itr.next.next
                break
            itr = itr.next
            count+=1
    def get_position(self, position):
        """Get an element from a particular position.
        Assume the first position is "1".
        Return "None" if position is not in the list."""
        count = 0
        current = self.head
        while current.next:
            if count==position:
                return current.data
                
            current = current.next
            count +=1
        return None


if __name__=='__main__':
    l=linklist()
    l.insert_at_beganing(4)
    l.insert_at_beganing(2)
    l.insert_at_beganing(1)
    print(l.get_position(1))
    l.printlist()
    