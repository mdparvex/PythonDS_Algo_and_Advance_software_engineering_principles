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

def isSameTree(p, q) -> bool:
        if not p and not q:
            return True
        if p and q and p.data==q.data:
            return isSameTree(p.left,q.left) and isSameTree(p.right, q.right)
        else:
            return False
def is_subtree(root, subroot):
    if not subroot: return True
    if not root: return False
    if isSameTree(root, subroot):
        return True
    return is_subtree(root.left, subroot) or is_subtree(root.right, subroot)
def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    build_tree1 = insert_data([15,12,20,8,13,17,27,7,9,12,14])
    build_tree2 = insert_data([8,7,9])
    print(is_subtree(build_tree1, build_tree2))