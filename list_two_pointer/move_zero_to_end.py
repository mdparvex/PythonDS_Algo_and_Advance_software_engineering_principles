#two pinter
def move_zero_to_end(num_list):
    fast = 0
    for slow in range(len(num_list)):
        if num_list[slow]!=0:
            num_list[fast], num_list[slow]=num_list[slow], num_list[fast]
            fast=fast+1
    return num_list

print(move_zero_to_end([2,0,0,0,3,2,0,1,0,0,0,7]))