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
    
def serialize(root):
    result = []
    def dfs(node):
        if not node:
            result.append('N')
            return
        result.append(str(node.data))
        dfs(node.left)
        dfs(node.right)
    dfs(root)
    return ','.join(result)

def deserialize(data):
    values = data.split(',')
    i = 0
    def dfs():
        nonlocal i
        if values[i] == 'N':
            i+=1
            return None
        node = TreeNode(int(values[i]))
        i+=1
        node.left = dfs()
        node.right = dfs()
        return node
    return dfs()
        
def print_tree(root):
    if not root:
        return
    print(root.data, end=' ')
    print_tree(root.left)
    print_tree(root.right)

def insert_data(arr):
    root = TreeNode(arr[0])
    for val in arr[1:]:
        root.add_child(val)
    return root
if __name__ == '__main__':
    data = [15,12,20,8,13,17,27,7,9,12,14]
    build_tree = insert_data(data)
    serialized_tree = serialize(build_tree)
    print("Serialized Tree:", serialized_tree)
    deserialized_tree = deserialize(serialized_tree)
    print("Deserialized Tree (Preorder):", end=' ')
    print_tree(deserialized_tree)
    