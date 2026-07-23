N,M = map(int,input().split())
xyz = [list(map(int,input().split())) for _ in range(N)]

ans = 0
state = [0,0,0]
for s in range(1<<3):
    for i in range(3):
        if s%2 == 1:
            state[i] = 1
        else:
            state[i] = 0
        s = s>>1
    
    
    totalList = [0] * N
    
    for k in range(N):
        t = 0
        for i in range(3):
            if state[i]:
                t -= xyz[k][i]
            else:
                t += xyz[k][i]
        totalList[k] = t
        
    totalList.sort(reverse = True)
    cur = sum(totalList[:M])
    ans = max(ans,cur)
    cur = sum(totalList[M:])
    ans = max(ans,cur)

print(ans)
    
    