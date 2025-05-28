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

    def level_order_traversal(self, elements, level):
        if len(elements)<=level:
            elements.append([])
        if self.data:
            elements[level].append(self.data)
        if self.left:
            self.left.level_order_traversal(elements, level+1)
        if self.right:
            self.right.level_order_traversal(elements, level+1)

        return elements

def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [15,12,20,8,13,17,27,7,9,12,14]
    build_tree = insert_data(data)
    print(build_tree.level_order_traversal([],0))