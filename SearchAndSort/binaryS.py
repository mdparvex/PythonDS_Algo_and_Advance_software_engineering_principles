#only use for sorted array
def binarysearch(arr, l, r, x):
	if r>=l:
		mid = l+(r-l)//2
		if arr[mid]==x:
			return mid

		elif arr[mid]>x:
			return binarysearch(arr, l, mid-1, x)

		else:
			return binarysearch(arr, mid+1, r, x)
	else:
		return -1

def iterative(arr, l, r, x):
	while l<=r:
		mid = l+(r-l)//2

		if arr[mid]==x:
			return mid
		elif arr[mid]<x:
			l = mid+1
		else:
			r = mid-1
	return -1

arr=[2,4,7,9,16,30,45,67]
x=45

if __name__ == '__main__':
	result = iterative(arr, 0, len(arr)-1, x)
	if result== -1:
		print('Not fount')

	else:
		print(f'found {result}th position')
		