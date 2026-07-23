import heapq

n = int(input())
A = list(map(int,input().split()))

sa = 0
sb = 0
hf = []
hb = []
for i in range(n):
    sa += A[i]
    heapq.heappush(hf,A[i])
for i in range(2*n,3*n):
    sb += A[i]
    heapq.heappush(hb,-A[i])

ans = sa-sb
for i in range(n,2*n):
    now = A[i]
    
    l = -heapq.heappop(hb)
    
    if now < l:
        ans = sa-sb+l-now
    heapq.heappush(hb,-l)
    h = heapq.heappop(hf)
    
    if now > h:
        sa += now-h
        heapq.heappush(hf,now)
        ans = max(ans,sa-sb)
    else:
        heapq.heappush(hf,h)
    
ans = max(ans,sa-sb)
print(ans)
