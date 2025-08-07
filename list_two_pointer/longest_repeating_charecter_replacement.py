def longestRepeatingCharacterReplacement(s, k):
    count ={}
    res = 0
    l = 0
    maxc = 0

    for r in range(len(s)):
        count[s[r]] = 1 + count.get(s[r],0)
        maxc = max(maxc, count[s[r]])

        while (r-l+1)-maxc > k:
            count[s[l]] =- 1
            l+=1
        res = max(res, r-l+1)
    return res

print(longestRepeatingCharacterReplacement("AABABBA",1))