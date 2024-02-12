# flip marix with maximum value in left qudrant and add them

def flippingMatrix(matrix):
    # Write your code here
    n = int(len(matrix)/2)
    l= 2*n-1
    s=0
    for i in range(n):
        for j in range(n):
            s += max(matrix[i][j], matrix[i][l-j], matrix[l-i][j],matrix[l-i][l-j])
    return s
if __name__=='__main__':

    a = flippingMatrix([[112,42,83,19],[56,125,56,49],[15,78,101,43],[104,20,400,12]])
    print(a)