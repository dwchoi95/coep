N = int(input())
P = list(map(int,input().split()))

b = [0] * (N + 1)
l1 = [max(i-1,-1) for i in range(N)]
r1 = [min(i+1,N) for i in range(N)]
l2 = [max(i-2,-1) for i in range(N)]
r2 = [min(i+2,N) for i in range(N)]

ans = 0
for i in range(N):
    b[P[i]-1] = i 
for i in range(N):
    m = b[i] 
    x1,y1,x2,y2 = l1[m] , r1[m] , l2[m] ,r2[m]
    ans += (i+1) * ((x1-x2) * (y1-m+1) + (y1-y2) * (m-x1))
    
    
    
    if x2 >=0:
        r1[x2] = x1
        r2[x2] = y1
    
    if x1 >= 0:
        r1[x1] = y1 
        r2[x1] = y2
    
    if y1 < N:
        l2[y1] = x2 
        l1[y1] = x1    
    
    if y2 < N:
        l2[y2] = x1
        l1[y2] = y1
print(ans)