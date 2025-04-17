#get max value from list of tuple
'''
prices = [('banana', 2), ('mango',7), ('melon',8),('apple',1)]
copy_prices = prices.copy()
by_letter = lambda x:x[0]
prices.sort(key=by_letter)

by_number = lambda x:x[1]
copy_prices.sort(key = by_number)
print(copy_prices)
print(prices)

#get max value from dictionary
from operator import itemgetter

birth_year = {"Ben": 1997, "Alex": 2000, "Oliver": 1995}
print(max(birth_year)) ## Returns "Oliver"

max_val = max(birth_year, key=lambda k: birth_year[k])
print(max_val)
'''
def sortListOfTuple(lis):
    copy_lis = lis.copy()
    by_number = lambda x:x[1]
    copy_lis.sort(key=by_number)
    return copy_lis
def reverseName(name):
    name = name[::-1]
    return name

prices = [('banana', '2'), ('mango',7), ('melon',8),('apple',1)]
x = sortListOfTuple(prices)
print(x)