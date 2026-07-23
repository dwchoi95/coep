
N,W = map(int,input().split())
WV = [list(map(int,input().split())) for i in range(N)]


w1 = WV[0][0]
WV.sort()

vlist = [[] for i in range(4)]
for i in range(N):
    w,v = WV[i][0],WV[i][1]
    d = w-w1
    vlist[d].append(v)
    
vrui = [[0] for i in range(4)]
for i in range(4):
    vlist[i].sort(reverse=True)
    for v in vlist[i]:
        vrui[i].append(vrui[i][-1]+v)
        


MAX = 0
for i in range(min(N+1,len(vlist[0])+1)):
    for j in range(min(N-i+1,len(vlist[1])+1)):
        for k in range(min(N-i-j+1,len(vlist[2])+1)):
            l = min(N-(i+j+k),len(vlist[3]))
            
            
            if (w1*i+(w1+1)*j+(w1+2)*k+(w1+3)*l) <= W:
                MAX = max(MAX,(vrui[0][i]+vrui[1][j]+vrui[2][k]+vrui[3][l]))

print(MAX)
            