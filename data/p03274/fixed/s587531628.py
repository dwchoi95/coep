n, k = map(int, input().split())
x = list(map(int, input().split()))

ans = 10 ** 9

if k == 1:
    for i in range(n):
        ans = min(ans, abs(x[i]))
elif n == k:
    ans = min(abs(x[0]-x[n-1]) + abs(x[n-1]), abs(x[0]) + abs(x[0] - x[n-1]))
else:
    for i in range(n-k+1):
        ans = min(ans, abs(x[i]-x[i+k-1]) + abs(x[i+k-1]), abs(x[i]) + abs(x[i] - x[i+k-1]))

print(ans)