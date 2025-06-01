class TreeNode():
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None

    def add_child(self,data):
        if data==self.data:
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
    def find_min(self):
        if self.left is None:
            return self.data
        return self.left.find_min()

    def delete_child(self, data):
        if data <self.data:
            self.left = self.left.delete_child(data)
        if data> self.data:
            self.right = self.right.delete_child(data)
        else:
            if self.left is None and self.right is None:
                return
            if self.left is None:
                return self.right
            if self.right is None:
                return self.right
            else:
                val = self.right.find_min()
                self.data = val
                self.right = self.right.delete_child(data)
        return self

def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [15,12,20,8,13,17,27,7,9,12,14]
    build_tree = insert_data(data)
    print(build_tree.delete_child(7))