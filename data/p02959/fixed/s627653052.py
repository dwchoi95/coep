n = int(input())
a = list(map(int, input().split()))
b = list(map(int, input().split()))
ans = 0

def f(n):
    nn = min(a[n], b[n])
    nnn = min(a[n+1], b[n] - nn)
    a[n+1] -= nnn
    return nn + nnn

for i in range(n):
    ans += f(i)

print(ans)