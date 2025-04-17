# Consider two arrays a and b, where each consists of n integers. In one operation:
# Select two indices i and j (0≤i,j<n).
# Swap integers a[i] and b[i].
# This operation can be performed at most k times.
# Find the maximum number of distinct elements that can be achieved in array a after at most k operations.

def k_max(m,n,k):
    common =  list(set(n) - set(m))
    set_m = list(set(m))
    remove_common_from_n = []
    
    for v in n:
        if v not in common:
           remove_common_from_n.append(v)
    if (len(set_m)+k)<=len(m):
        if len(remove_common_from_n)<=k:
            return len(set_m)+len(remove_common_from_n)
        else:
            return len(set_m)+k
    else:
        return len(set_m)


x = k_max([1,2,3,3,6,6], [1,2,3,6,8,9], 1)
print(x)