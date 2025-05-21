def longstpal(stri):
    pal={}
    spllitedsrtind=stri.split()
    for s in spllitedsrtind:
        if s==s[::-1]:
            if s not in pal:
                pal[s]=len(s)
            else:
                continue
    inv = [(value, key) for key,value in pal.items()]
    return max(inv)[1]


x = 'redivider deified civic radar level'
print(longstpal(x))

    
