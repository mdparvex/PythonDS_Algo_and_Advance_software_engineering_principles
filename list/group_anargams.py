#input: strs = ["eat","tea","tan","ate","nat","bat"]

#Output: [["bat"],["nat","tan"],["ate","eat","tea"]]

from collections import defaultdict
def groupAnargams(strs):
    dic = defaultdict(list)

    for st in strs:
        cnt = [0]*26

        for c in st:
            cnt[ord(c)-ord("a")]+=1
        dic[tuple(cnt)].append(st)

    return list(dic.values())

print(groupAnargams(["eat","tea","tan","ate","nat","bat"]))