
def topKElement(nums,k):
    dic={}
    for n in nums:
        dic[n] = 1+ dic.get(n,0)
    sorted_dic = sorted(dic.items(), key=lambda x:x[1], reverse=True)

    return [sorted_dic[i][0] for i in range(k) ]
print(topKElement([1,1,1,2,2,3],2))