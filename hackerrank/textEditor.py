#implement in class
def textEditor(S, ops):
    lis=[]
    for op in range(len(ops)):
        splitted_op = ops[op].split()
        operations = int(splitted_op[0])
        try:
            ch = splitted_op[1]
        except:
            ch = None
        
        if operations==1:
            S = S+ch
            lis.append('1 '+ch)
            #lis.pop() if lis else None
        elif operations==2:
            lis.append('2 '+S[len(S)-int(ch):])
            S= S[:-int(ch)]
            #lis.pop() if lis else None
        elif operations==3:
            print(S[int(ch)-1])
        elif operations==4:
            op = lis.pop().split()
            if int(op[0])==1:
                S=S.replace(op[1],'')
            elif int(op[0])==2:
                S=S+op[1]
                    
    return S
S= 'abcde'
ops = ['1 fg', '3 6', '2 5', '4', '3 7', '4', '3 4']
x = textEditor(S, ops)
print(f'last: {x}')