#You are given an array prices where prices[i] is the price of a given stock on the ith day.

#You want to maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell that stock.
def maxProfit(prices):
    min_price = float('inf')
    max_price = 0
    
    for price in prices:
        if price<min_price:
            min_price = price
        profit = price-min_price
        if profit>max_price:
            max_price=profit
    return max_price
print(maxProfit([2,1,2,1,0,1,2]))