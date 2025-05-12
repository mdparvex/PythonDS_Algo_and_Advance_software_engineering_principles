#piles [3,6,7,11] h=8

#bruit force solution
import math
def kokoEating(nums, h):
    mx = max(nums)
    for speed in range(1, mx+1):
        time=0
        for banana in nums:
            time+= banana//speed

            if banana%speed !=0:
                time+=1
        if time<=h:
            return speed
    return mx
#print(kokoEating([3,6,7,11], 8))
#binary search
import math
def kokoEatingBinary(nums,h):
    l = 1
    r = max(nums)
    res = r
    while l<=r:
        speed = l + (r-l)//2
        time = 0
        for banana in nums:
            time+= math.ceil(banana/speed)
        if time<=h:
            r = speed-1
            res = min(speed,res)
        else:
            l = speed+1
    return res
print(kokoEating([3,6,7,11], 8))


