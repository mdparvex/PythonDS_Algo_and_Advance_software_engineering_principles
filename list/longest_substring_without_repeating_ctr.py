#sliding window
def longestSubstring(word):
    l=0
    res = 0
    arr = []
    for r in range(len(word)):
        if word[r] in arr:
            arr.pop(0)
            l+=1
        arr.append(word[r])
        res = max(res, r-l+1)
    return res


length = longestSubstring('ababx')
print(length)