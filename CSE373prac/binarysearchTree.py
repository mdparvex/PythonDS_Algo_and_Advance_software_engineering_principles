#binary search tree

class BST:
    def __init__(self,data):
        self.left = None
        self.right = None
        self.data = data

    def insertVal(self, data):
        if self.data:
            if data<self.data:
                if self.left is None:
                    self.left = BST(data)
                else:
                    self.left.insertVal(data)
            elif data>self.data:
                if self.right is None:
                    self.right = BST(data)
                else:
                    self.right.insertVal(data)
        else:
            self.data = data


    def printTree(self):
        if self.left:
            self.left.printTree()
        print(self.data)
        if self.right:
            self.right.printTree()

    def findValue(self,val):
        if self.data==val:
            print(f'{val} is found')
            return True
        elif val<self.data:
            if self.left is None:
                print(f'{val} is not found')
                return False
            self.left.findValue(val)
        elif val>self.data:
            if self.right is None:
                print(f'{val} is not found')
                return False
            self.right.findValue(val)
            

if __name__=='__main__':
    b = BST(11)
    b.insertVal(10)
    b.insertVal(12)
    b.insertVal(7)
    b.insertVal(8)
    b.insertVal(9)
    b.insertVal(17)

    b.printTree()
    b.findValue(20)
