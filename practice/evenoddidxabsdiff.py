def absdif(ar):
    ev=[]
    od=[]
    for i in ar:
        if i%2==0:
            ev.append(i)
        else:
            od.append(i)
    evendif = abs(ev[0]-ev[1])
    oddif =abs(od[0]-od[1])
    return evendif,oddif
print(absdif([1,2,7,6,13,10,19,14,25]))