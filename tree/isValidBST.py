class TreeNode():
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None

    def add_child(self,data):
        if data==self.data:
            return
        if data>self.data: #invelid condition for a binary search tree
            if self.left:
                return self.left.add_child(data)
            else:
                self.left = TreeNode(data)
        else:
            if self.right:
                return self.right.add_child(data)
            else:
                self.right = TreeNode(data)

    def isValid(self):
        def valid(node, left, right):
            if node.left is None and node.right is None:
                return True
            if not (node.data>left and node.data<right):
                return False
            return (valid(node.left, left, node.data) and valid(node.right, node.data, right))
        return valid(self, float('-inf'), float('inf'))

def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [15,12,20,13,21]
    build_tree = insert_data(data)
    print(build_tree.isValid())