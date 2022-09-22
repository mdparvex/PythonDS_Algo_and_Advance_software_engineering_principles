def anagram(str1, str2):
    if sorted(str1)==sorted(str2):
        return "anagram"
    else:
        return "not anagram"

print(anagram('listen', 'silent'))

def an(str1,str2):
    if len(str1) != len(str2):
        return "not anagram"
    for i in str1:
        if i not in str2:
            return "not anagram"
    return "anagram"
print(an('listen', 'silent'))


    