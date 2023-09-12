# You are given n activities with their start and finish times.
#Select the maximum number of activities that can be performed by a single person
#Input: start[]  =  {10, 12, 20}, finish[] =  {20, 25, 30}
#Output: 0 2
#10->20, 20->30

def printMaxActivities(s, f):
    print("Following activities are selected")

    l= len(f)
    i=0
    print(i, end=" ")

    for j in range(1,l):
        if s[j]>=f[i]:
            print(j, end=" ")
            i=j

if __name__ == '__main__':
    s = [1, 3, 0, 5, 8, 5]
    f = [2, 4, 6, 7, 9, 9]
 
    # Function call
    printMaxActivities(s, f)
