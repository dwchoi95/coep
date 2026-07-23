import bisect
n, k = map(int, input().split())
X = list(map(int, input().split()))

ans = float('inf')

for i in range(n):
    
    if X[i] <= 0:
        if 0 <= i+k-1 < n:
            temp = 0
            temp+= -X[i]*2
            if X[i+k-1] >= 0:
                temp += X[i+k-1]
                ans = min(ans, temp)
        if 0 <= i-k+1 < n:
            ans = min(ans, -X[i-k+1])

    
    else:
        if 0 <= i-k+1 < n:
            temp = 0
            temp+=X[i]*2
            if X[i-k+1] <= 0:
                temp -= X[i-k+1]
                ans  = min(ans, temp)
        if 0 <= i+k-1 < n:
            ans = min(ans, X[i+k-1])

if n == 1:
    ans = abs(X[0])

print(ans)