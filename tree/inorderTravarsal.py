class BinarySearchTreeNode():
    def __init__(self,data):
        self.data = data
        self.left = None
        self.right = None

    def add_child(self, data):
        if data == self.data:
            return
        if data<self.data:
            if self.left:
                self.left.add_child(data)
            else:
                self.left = BinarySearchTreeNode(data)
        else:
            if self.right:
                self.right.add_child(data)
            else:
                self.right = BinarySearchTreeNode(data)
    
    #left -> root -> right
    def inorder(self):
        elements = []
        
        #traverse left
        if self.left:
            elements += self.left.inorder()
        #traverse root
        elements.append(self.data)
        #traverse right
        if self.right:
            elements += self.right.inorder()
        
        return elements
    
def insert_data(arr):
    root = BinarySearchTreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [27,6,23,4,14,35,6,8,9]
    build_tree = insert_data(data)
    print(build_tree.inorder())


