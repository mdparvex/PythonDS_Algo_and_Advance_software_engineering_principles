class TreeNode():
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None

    def add_child(self, data):
        if data == self.data or data==None:
            return
        if data<self.data:
            if self.left:
                self.left.add_child(data)
            else:
                self.left = TreeNode(data)
        else:
            if self.right:
                self.right.add_child(data)
            else:
                self.right = TreeNode(data)
    
def rightSideView(root, res, level):
    if not root:
        return []
    if len(res)== level:
        res.append(root.data)
    rightSideView(root.right, res, level+1)
    rightSideView(root.left, res, level+1)
    return res
    
        


def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [6,7,4,5,3,1]
    build_tree = insert_data(data)
    print(rightSideView(build_tree, [], 0))