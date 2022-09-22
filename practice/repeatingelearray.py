def repeatarr(arr):
    dic={}

    for val in arr:
        if val not in dic:
            dic[val]=0
        else:
            dic[val] +=1
    for key, value in dic.items():
        if value>0:
            print(key)

arr=[2,3,4,4,5,6,7,7,8,5,9,9,0]
repeatarr(arr)