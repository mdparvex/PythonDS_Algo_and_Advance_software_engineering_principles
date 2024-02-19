
def anagram(s):
    # Write your code here
    l = len(s)
    if l%2!=0:
        return -1
    h=int(l/2)
    s1 = s[:h]
    s2 = s[h:]
    l = list(s2)
    num = 0
    for i in range(len(s1)):
        try:
            l.remove(s1[i])
        except:
            num +=1
    return num

if __name__=='__main__':
    x = anagram('xaxbbbxx')
    print(x)