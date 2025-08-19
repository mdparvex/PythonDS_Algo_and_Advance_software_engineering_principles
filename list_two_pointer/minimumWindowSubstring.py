def minimumWindowSubstring(s,t):
    if t=="":
        return ""
    l=0
    s_count = {}
    t_count = {}
    res = [-1,-1]
    resNum = float('infinity')

    for c in t:
        t_count[c] = 1 + t_count.get(c,0)
    total = len(t_count)
    need = 0

    for r in range(len(s)):
        ch = s[r]
        s_count[ch] = 1 + s_count.get(ch,0)
        if ch in t_count and t_count[ch]==s_count[ch]:
            need +=1
        while total==need:
            if resNum>(r-l+1):
                res =  [l,r]
                resNum = r-l+1
            s_count[s[l]] -=1
            if s[l] in t_count and s_count[s[l]]<t_count[s[l]]:
                need -=1
            l+=1
    l,r = res
    return s[l:r+1] if resNum != float('infinity') else ""

print(minimumWindowSubstring("OUZODYXAZV", "XYZ"))