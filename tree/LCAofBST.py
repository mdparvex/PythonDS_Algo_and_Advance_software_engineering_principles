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

def lowestCommonAncestor(root,p, q):
        if not root and not p and not q:
            return None
        if max(p.data, q.data)<root.data:
            return lowestCommonAncestor(root.left, p,q)
        elif min(p.data, q.data)>root.data:
            return lowestCommonAncestor(root.right, p, q)
        return root.data
def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    root_tree = insert_data([6,2,8,0,4,7,9,3,5])
    p = insert_data([2])
    q = insert_data([4])
    print(lowestCommonAncestor(root_tree,p,q))