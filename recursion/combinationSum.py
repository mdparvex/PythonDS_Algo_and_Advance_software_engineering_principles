def combinationSum(candidate, target):
    res = []

    def dfs(i, cur, total):
        if total == target:
            res.append(cur.copy())
            return
        if i>=len(candidate) or total>target:
            return
        cur.append(candidate[i])
        dfs(i, cur, total+candidate[i])
        cur.pop()
        dfs(i+1, cur, total)
    dfs(0,[],0)
    return res

#print(combinationSum([2,3,6,7], 7))

#alternate
def combinationSum1(candidate, target):
    res = []
    curr = []

    def backtrat(index, remainingsum):
        if remainingsum==0:
            res.append(curr.copy())
            return
        if remainingsum<0:
            return
        
        for i in range(index, len(candidate)):
            curr.append(candidate[i])
            backtrat(i, remainingsum-candidate[i])
            curr.pop()
    backtrat(0,target)
    return res

print(combinationSum1([2,3,6,7], 7))