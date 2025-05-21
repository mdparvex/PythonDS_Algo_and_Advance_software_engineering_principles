#time complexity O(n logn), space logn
def quicksort(array):
    less=[]
    equal=[]
    greter=[]
    
    if len(array)>1:
        pivot=array[0]
        for x in array:
            if x<pivot:
                less.append(x)
            elif x==pivot:
                equal.append(x)
            elif x>pivot:
                greter.append(x)
        return quicksort(less) + equal + quicksort(greter)
    else:
        return array

test = [21, 4, 1, 3, 9, 20, 25, 6, 21, 14]
print(quicksort(test))