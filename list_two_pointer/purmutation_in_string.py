def purmutationInString(s1,s2):
    n1 = len(s1)
    n2 = len(s2)
    if n1>n2:
        return False
    s1count = [0]*26
    s2count = [0]*26
    for i in range(n1):
        s1count[ord(s1[i])-ord('a')] +=1
        s2count[ord(s2[i])-ord('a')] +=1
    if s1count==s2count:
        return True
    for j in range(n1,n2):
        s2count[ord(s2[j])-ord('a')] +=1
        s2count[ord(s2[j-n1])-ord('a')] -=1

        if s1count==s2count:
            return True
    return False
print(purmutationInString("ab", "eidbaooo"))