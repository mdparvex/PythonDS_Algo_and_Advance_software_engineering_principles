class TreeNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
class WordDictionary:
    def __init__(self):
        self.root = TreeNode()

    def addWord(self, word: str) -> None:
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TreeNode()
            node = node.children[char]
        node.is_end_of_word = True

    def search(self, word: str) -> bool:
        def dfs(node, i):
            if i == len(word):
                return node.is_end_of_word
            if word[i] == '.':
                for child in node.children.values():
                    if dfs(child, i + 1):
                        return True
                return False
            else:
                if word[i] not in node.children:
                    return False
                return dfs(node.children[word[i]], i + 1)
        return dfs(self.root, 0)

# Your WordDictionary object will be instantiated and called as such:
obj = WordDictionary()
obj.addWord('day')
param_2 = obj.search('ma.')
print(param_2)  # Output: True
