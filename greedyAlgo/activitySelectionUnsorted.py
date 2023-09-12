# You are given n activities with their start and finish times.
#Select the maximum number of activities that can be performed by a single person
#Input: [[5, 9], [1, 2], [3, 4], [0, 6], [5, 7], [8, 9]]
#Output: 

def MaxActivities(activity, n):
    selected = []

    activity.sort(key=lambda x: x[1])

    i=0
    selected.append(activity[i])

    for j in range(1,n):
        if activity[j][0]>=activity[i][1]:
            selected.append(activity[j])
            i=j
    
    return selected


if __name__ == '__main__':
    Activity = [[5, 9], [1, 2], [3, 4], [0, 6], [5, 7], [8, 9]]
    n = len(Activity)
 
    # Function call
    selected = MaxActivities(Activity, n)
    print(selected)