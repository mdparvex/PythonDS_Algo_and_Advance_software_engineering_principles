def maxactivites(activity):
    res = []
    activity.sort(key = lambda x: x[1])
    i=0

    for j in range(len(s)):
        if activity[j][0]>=activity[i][1]:
            res.append(activity[j])
            i=j
    return res
s= [[1,8],[2,3],[5,7],[4,5],[8,10]]
result = maxactivites(s)
print(result)