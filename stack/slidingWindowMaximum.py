from collections import deque
def slidingMax(arr, k):
    res=[]
    l=r=0
    q= deque()

    while r<len(arr):
        while q and arr[q[-1]]<arr[r]:
            q.pop()
        q.append(r)
        if l>q[0]:
            q.popleft()
        if (r+1)>=k:
            res.append(arr[q[0]])
            l+=1
        r+=1
    return res
print(slidingMax([1,3,-1,-3,5,3,6,7], 3))