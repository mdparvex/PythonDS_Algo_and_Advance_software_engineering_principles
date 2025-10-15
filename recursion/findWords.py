def findWords(board, words):
    def backtrack(i, j, node, path):
        if '#' in node:
            result.add(path)
        if not (0 <= i < len(board)) or not (0 <= j < len(board[0])):
            return
        temp = board[i][j]
        if temp not in node:
            return
        board[i][j] = '@'  # mark as visited
        for x, y in [(i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)]:
            backtrack(x, y, node[temp], path + temp)
        board[i][j] = temp  # unmark

    trie = {}
    for word in words:
        node = trie
        for char in word:
            node = node.setdefault(char, {})
        node['#'] = True  # end of a word

    result = set()
    for i in range(len(board)):
        for j in range(len(board[0])):
            backtrack(i, j, trie, '')

    return list(result)