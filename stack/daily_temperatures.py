def dailyTemperatures(temperatures):
    res = [0]*len(temperatures)
    stack = []

    for i,val in enumerate(temperatures):
        while stack and val>stack[-1][0]:
            item, idx = stack.pop()
            res[idx] = i-idx
        stack.append((val,i))

    return res
print(dailyTemperatures([73,74,75,71,69,72,76,73]))