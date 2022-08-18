def search(arr, n, x):
	for i in range(0,n-1):
		if arr[i]==x:
			return i
	return -1

def search1(arr, n, x):
	left = 0
	right = n-1
	position = -1

	for left in range(0,n-1):
		if arr[left]==x:
			position = left
			print(f"{x} is found in position {position+1} and attempt {left+1}")
			break
		if arr[right]==x:
			position=right
			print(f"{x} is found in position {position+1} and attempt {n-right}")
			break

		left +=1
		right -=1

	if position == -1:
		print(f"{x} is not found in this array")

search1(arr,n,x)

'''
result = search(arr, x, n)
if result==-1:
	print(f"{x} is not found in this list")
else:
	print(f"{x} is found {result}th position in this list")'''

		