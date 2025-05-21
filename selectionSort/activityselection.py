def maxactivites(activity):
    res = []
    activity.sort(key = lambda x: x[1])
    i=0
    res.append(activity[0])
    for j in range(1,len(s)):
        if activity[j][0]>=activity[i][1]:
            res.append(activity[j])
            i=j
    return res
s= [[1,8],[2,7],[5,7],[4,5],[8,10]]
result = maxactivites(s)
print(result)