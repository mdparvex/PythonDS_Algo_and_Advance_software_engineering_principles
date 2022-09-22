def removeduplicate(ar):
    res=[]

    for i in ar:
        if i not in res:
            res.append(i)
    return res
print(removeduplicate([3,4,5,6,5,6,7,7,6,5]))