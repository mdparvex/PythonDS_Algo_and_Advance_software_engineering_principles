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
    
def isBalanced(root):
    
    def dfs(curr):
        if not curr:
            return [True,0]
        left_depth = dfs(curr.left)
        right_depth = dfs(curr.right)
        diff = left_depth[0] and right_depth[0] and abs(left_depth[1]-right_depth[1])<=1
        return [diff,max(left_depth[1], right_depth[1]) + 1]
    
    return dfs(root)[0]
        


def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [1,None,2,None,3] #[15,12,20,8,13,17,27,7,9,12,14]
    build_tree = insert_data(data)
    print(isBalanced(build_tree))