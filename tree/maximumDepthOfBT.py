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
    def depth_of_tree(self):
        left_depth = self.left.depth_of_tree() if self.left else 0
        right_depth = self.right.depth_of_tree() if self.right else 0
        return max(left_depth, right_depth) + 1
        


def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [15,12,20,8,13,17,27,7,9,12,14]
    build_tree = insert_data(data)
    print(build_tree.depth_of_tree())