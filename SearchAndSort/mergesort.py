#time complexity O(n logn), space constant
def mergesort(arr):
	if len(arr)>1:

		length = len(arr)
		mid = length//2

		l = arr[:mid]
		r =arr[mid:]

		mergesort(l)
		mergesort(r)
		i=0
		j=0
		k=0

		while i<len(l) and j<len(r):
			if l[i]<r[j]:
				arr[k]=l[i]
				i+=1
			else:
				arr[k]=r[j]
				j+=1
			k+=1

		while i<len(l):
			arr[k]=l[i]
			i+=1
			k+=1
		while j<len(r):
			arr[k]=r[j]
			j+=1
			k+=1

	return arr

arr = [2,0,2,1,1,0]
res = mergesort(arr)
print(arr)