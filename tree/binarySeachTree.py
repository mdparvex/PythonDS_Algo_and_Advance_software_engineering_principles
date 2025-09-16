#create a binary search tree

class BinaryTree:
    def __init__(self, data):
        self.left=None
        self.right=None
        self.data=data

    def insertData(self, data):
        if self.data:
            if data < self.data:
                if self.left is None:
                    self.left = BinaryTree(data)
                else:
                    self.left.insertData(data)
            elif data > self.data:
                if self.right is None:
                    self.right = BinaryTree(data)
                else:
                    self.right.insertData(data)
        else:
            self.data=data

    #left -> root -> right
    def inorder_traversal(self, root):
        data = []
        if root:
            data = self.inorder_traversal(root.left)
            #print(root.data)
            data.append(root.data)
            data = data + self.inorder_traversal(root.right)
        return data
    
    #root -> left -> right
    def preorder_traversal(self,root):
        data = []
        if root:
            data.append(root.data)
            #print(root.data)
            data = data + self.preorder_traversal(root.left)
            data = data + self.preorder_traversal(root.right)
        return data
    #letf -> right -> root
    def postorder_traversal(self,root):
        data = []
        if root:
            data = self.postorder_traversal(root.left)
            data = data + self.postorder_traversal(root.right)
            data.append(root.data)
            #print(root.data)
        return data
    
    def find_value(self, val):
        if self.data==val:
            print(f'{ val} is found')
            return True
        if val< self.data:
            if self.left is None:
                print(f'{val} is Not found')
                return False
            self.left.find_value(val)
        if val> self.data:
            if self.right is None:
                print(f'{val} is not found')
                return False
            self.right.find_value(val)

    def find_max(self):
        if self.right is None:
            return self.data
        return self.right.find_max()
    def find_min(self):
        if self.left is None:
            return self.data
        return self.left.find_min()

    def delete_value(self, value):
        if value < self.data:
            self.left = self.left.delete_value(value)
        elif value > self.data:
            self.right = self.right.delete_value(value)
        else:
            if self.left is None and self.right is None:
                return
            if self.left is None:
                return self.right
            if self.right is None:
                return self.left
            else:
                min_val = self.right.find_min()
                self.data = min_val
                self.right = self.right.delete_value(min_val)
        return self
    
def printTree(root):
    tree_data = []
    if root:
        if root.left:
            tree_data = printTree(root.left)
        tree_data.append(root.data)
        if root.right:
            tree_data += printTree(root.right)
    return tree_data

if __name__=='__main__':
    root = BinaryTree(20)
    root.insertData(15)
    root.insertData(10)
    root.insertData(17)
    root.insertData(18)
    root.insertData(16)
    root.insertData(25)
    root.insertData(23)
    root.insertData(30)
    print(f'print tree: {printTree(root)}')
    print(f'inorder traversal: {root.inorder_traversal(root)}')
    print(f' preorder traversal: {root.preorder_traversal(root)}')
    print(f' postorder traversal: {root.postorder_traversal(root)}')
    root.find_value(17)
    print(f'maximum value of tree is: {root.find_max()}')
    print(f'Minimum value of tree is: {root.find_min()}')
    root.delete_value(16)
    print(f'print tree: {printTree(root)}')
