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

def kThSmallest(root,k) :
        data = []
        def dfs(root):
            if root is None:
                return
            dfs(root.left)
            data.append(root.data)
            dfs(root.right)
        dfs(root)
        return data[k-1]
def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    build_tree1 = insert_data([20,15,10,17,18,16,25,23,30])
    k = 3
    print(f'{k}th smallest value of the binary search tree is : {kThSmallest(build_tree1, k)}')