#encode a string and the decode that string . 
from typing import List
def encode(strs: List[str]) -> str:
        d = ''
        for st in strs:
            d += str(len(st))+'#'+st
        return d

def decode(s: str) -> List[str]:
    res = []
    i=0
    while i<len(s):
        j=i
        while s[j]!='#':
            j+=1
        l = int(s[i:j])
        res.append(s[j+1:j+1+l])
        i = j+1+l
    return res
en = encode(["python","code","love","you"])
print(f'encoaded string: {en}')
de = decode(en)
print(f'decoded string: {de}')
