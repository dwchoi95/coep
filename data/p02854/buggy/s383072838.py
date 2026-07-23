n = int(input())
a = list(map(int, input().split()))
L = sum(a)
l = 0
i = 0
while l < L / 2:
    l += a[i]
    i += 1
if i + 1 <= len(a):
    ans = min(abs(sum(a[:i]) - sum(a[i:])), abs(sum(a[:i + 1]) - sum(a[i + 1:])))
else:
    ans = abs(sum(a[:i]) - sum(a[i:]))
print(ans)
