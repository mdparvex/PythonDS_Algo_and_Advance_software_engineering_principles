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
def diameter_of_tree(root):
    res = 0
    def dfs(curr):
        nonlocal res
        if not curr:
            return 0
        left_depth = dfs(curr.left)
        right_depth = dfs(curr.right)
        res= max(res, left_depth+right_depth)
        return max(left_depth, right_depth) + 1
    dfs(root)
    return res
        


def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [15,12,20,8,13,17,27,7,9,12,14]
    build_tree = insert_data(data)
    print(diameter_of_tree(build_tree))