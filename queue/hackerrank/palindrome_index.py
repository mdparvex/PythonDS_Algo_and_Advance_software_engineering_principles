
def palindromeIndex(s):
    if s == s[::-1]:
        return -1
    
    ind = 0
    l = len(s)
    
    while ind<len(s)//2:
        if s[ind] != s[l-ind-1]:
            if s[ind+1]==s[l-ind-1] and s[ind+2]==s[l-ind-2]:
                return ind
            else:
                return l-ind-1
        ind +=1
        
if __name__=='__main__':
    x = palindromeIndex('bcbc')
    print(x)