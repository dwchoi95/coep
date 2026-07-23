n = int(input())
a = [0] * n
b = [int(i) for i in input().split()]
a[0] = b[0]
for i in range(1, n-1):
    a[i] = min(b[i], b[i-1])
a[-1] = b[-1]
print(sum(a))
