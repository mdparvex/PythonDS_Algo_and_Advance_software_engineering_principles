def revword(string):
    ar=string.split()
    res=''
    for s in ar:
        res+=s[::-1] + " "
    return res
print(revword('my name is kashem'))