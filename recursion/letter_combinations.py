def letterCombinations(digits):
    if not digits:
        return []
    digit_to_letters = {
        '2': 'abc',
        '3': 'def',
        '4': 'ghi',
        '5': 'jkl',
        '6': 'mno',
        '7': 'pqrs',
        '8': 'tuv',
        '9': 'wxyz'
    }
    res = []
    def backtrack(i, curstr):
        if len(curstr) == len(digits):
            res.append(curstr)
            return
        for c in digit_to_letters[digits[i]]:
            backtrack(i + 1, curstr + c)
    backtrack(0, "")
    return res
print(letterCombinations("23"))  # Example usage
# Output: ['ad', 'ae', 'af', 'bd', 'be', '