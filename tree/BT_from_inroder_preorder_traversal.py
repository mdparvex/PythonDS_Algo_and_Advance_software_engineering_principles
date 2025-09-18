class TreeNode():
    def __init__(self, data=0):
        self.data = data
        self.left = None
        self.right = None
def buildTree(preorder, inorder):
    indices = {val:idx for idx,val in enumerate(inorder)}
    pre_idx = 0

    def dfs(l,r,indices):
        nonlocal pre_idx
        if l>r:
            return None
        val = preorder[pre_idx]
        pre_idx +=1
        mid = indices[val]
        root = TreeNode(val)
        root.left = dfs(l,mid-1,indices)
        root.right = dfs(mid+1,r,indices)
        return root
    return dfs(0, len(inorder)-1,indices)
def printTree(root):
    data = []
    def dfs(root):
        if not root:
            return
        dfs(root.left)
        data.append(root.data)
        dfs(root.right)
    dfs(root)
    return data
x = buildTree([3,9,20,15,7],[9,3,15,20,7])
print(f'constructed tree is: {printTree(x)}')