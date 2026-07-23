n = int(input())
a = list(map(int, input().split()))
L = sum(a)
l = 0
i = 0
while l < L / 2:
    l += a[i]
    i += 1
print(min(abs(sum(a[:i - 1]) - sum(a[i - 1:])), abs(sum(a[:i]) - sum(a[i:]))))
