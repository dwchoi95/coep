
board=[[0]*10 for i in range(10)]
ink=[[[0,0,0,0,0],[0,0,1,0,0],[0,1,1,1,0],[0,0,1,0,0],[0,0,0,0,0]],
[[0,0,0,0,0],[0,1,1,1,0],[0,1,1,1,0],[0,1,1,1,0],[0,0,0,0,0]],
[[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]]]

while True:
    try:
        x,y,s=map(int,input().split(","))
    except:
        break
    for i in range(5):
        for j in range(5):
            if 0<=i+y-2<=9 and 0<=j+x-2<=9:
                board[i+y-2][j+x-2]+=ink[s-1][i][j]

flat=sum(board,[])
print(flat.count(0))
print(flat.count(max(flat)))