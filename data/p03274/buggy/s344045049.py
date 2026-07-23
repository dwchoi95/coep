N, K = map(int, input().split(' '))
a= list(map(int, input().split(' ')))

INF = float('inf')
ans = INF

for i in range(N-K):
    ans = min(ans, abs(a[i+K-1]-a[i])+min(abs(a[i+K-1]), abs(a[i])))

print(ans)