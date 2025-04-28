class MinStack:

    def __init__(self):
        self.stack=[]
        self.min_stack=[]

    def push(self, val: int) -> None:
        self.stack.append(val)
        if not self.min_stack or val<=self.min_stack[-1]:
            self.min_stack.append(val)
        

    def pop(self) -> None:
        if not self.stack:
            return None
        if self.min_stack[-1]==self.stack[-1]:
            self.min_stack.pop()
        return self.stack.pop()
        

    def top(self) -> int:
        if not self.stack:
            return None
        return self.stack[-1]
        

    def getMin(self) -> int:
        return self.min_stack[-1] if self.min_stack else None
    
st = MinStack()
st.push(-1)
st.push(3)
st.push(-2)
print(st.stack)
print(st.pop())
print(st.getMin())