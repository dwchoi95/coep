N = int(input())
P = [0]+list(map(int,input().split()))+[N+1]
ans = 0
b = [0]*(N+2)
for i in range(N+2):
    b[P[i]] = i
l1 = [max(0,i-1) for i in range(N+2)]
l2 = [max(0,i-2) for i in range(N+2)]
r1 = [min(N+1,i+1) for i in range(N+2)]
r2 = [min(N+1,i+2) for i in range(N+2)]

for i in range(N+1):
    m = b[i]
    x2,x1,y1,y2 = l2[m],l1[m],r1[m],r2[m]
    hoge= i*(abs((m-x1)*(y2-y1)) + abs((y1-m)*(x1-x2)))
    ans += hoge
    
    r1[x1] = y1
    r2[x1] = y2
    
    l1[y1] = x1
    l2[y1] = x2
    
    r1[x2] = x1
    r2[x2] = y1
    
    l1[y2] = y1
    l2[y2] = x1
print(ans)