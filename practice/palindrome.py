
def palindrome(string):
    l = -1
    r=len(string)

    while l<r:
        l+=1
        r-=1
        if string[l] != string[r]:
            print("not palindrome")
            return
 
    print('palindrome')

palindrome('aabbaa')

def maxpal(strings):

    pal = []
    arrstrings = strings.split()
    for string in arrstrings:
        if string==string[::-1]:
            pal.append(string)
    return max(pal, key=len)
print(maxpal('abba aabbbbaa kakakakakakk'))

def palindromnum(num):
    temp=num 
    rev = 0
    while num>0:
        n = num%10
        rev = rev*10+n 
        num=num//10
    if rev==temp:
        print('palindrome')
    else:
        print('not palindrome')
palindromnum(5005)