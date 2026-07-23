N, K = map(int, input().split(' '))
a= list(map(int, input().split(' ')))

INF = float('inf')
ans = INF

if N == K:
    ans = abs(a[N-1]-a[0])+min(abs(a[0]), abs(a[N-1]))
else:
    for i in range(N-K+1):
        ans = min(ans, abs(a[i+K-1]-a[i])+min(abs(a[i+K-1]), abs(a[i])))

print(ans)