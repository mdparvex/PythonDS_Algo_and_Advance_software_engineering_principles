#unpacking
nested_arr = [[1,2,3],['hello','world'], 56]

#unpack
arr, string, num = nested_arr
print(f'array: {arr}, string: {string} and number is {num}')

#igonre multiple value during unpacking
l=[2,4,5,7,9]

a,b,*_, c = l
print(f'a: {a}, b:{b}, c:{c}, left: {_}')