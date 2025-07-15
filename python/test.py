import re

def _normalize_transcript_words( text):
    text = re.sub(r'\d+', lambda x: num2words(int(x.group())), text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower().split()
    
print(_normalize_transcript_words('1/2 of the 1st and 2nd and 3rd'))