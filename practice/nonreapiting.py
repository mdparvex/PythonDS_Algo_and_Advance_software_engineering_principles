def nonrep():
    ar=[]
    for i in range(0,12):
        if i==11:
            
            finalarr = ar + ar[9::-1]
            return finalarr
        else:
            ar.append(i)
    return finalarr
print(nonrep())

