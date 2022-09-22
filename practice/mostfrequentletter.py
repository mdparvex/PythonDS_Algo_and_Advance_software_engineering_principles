def mostfreq(string):
    freqstr={}
    for i in string:
        if i.isupper():
            continue
        if i not in freqstr:
            freqstr[i]=1
        else:
            freqstr[i]+=1
    lis = [(value, key) for key, value in freqstr.items()]
    #maxval= max(lis)[1]
    #res = maxval[1]
    lis.sort(key= lambda x: x[0])
    return lis[-1][1], lis[-2][1]
print(mostfreq('hellogolalllaa'))
