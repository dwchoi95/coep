import bisect
n, k = map(int, input().split())
X = list(map(int, input().split()))

ans = float('inf')
if n == 1:
    ans = abs(X[0])
for i in range(n):
    temp = 0
    
    if X[i] <= 0:
        if not 0 <= i+k-1 < n-1: continue
        temp+= -X[i]*2
        if X[i+k-1] >= 0:
            temp += X[i+k-1]
        ans = min(ans, temp)
    
    elif X[i] > 0:
        if not 0 <= i-k+1 < n-1: continue
        temp+=X[i]*2
        if X[i-k+1] <= 0:
            temp -= X[i-k+1]
        ans  = min(ans, temp)

st = bisect.bisect_left(X, 0)
if st+k-1 < n-1: ans = min(ans, X[st+k-1])


st = bisect.bisect_left(X, 0)-1
if 0 <= st-k+1 < n-1: ans = min(ans, X[st-k+1])

print(ans)