n = int(input())
a = list(map(int,input().split()))

a.sort()
li = [True] * (10**6 + 10)
ans = 0

for i in range(n):
    if not li[a[i]]:
        continue
    li[a[i]] = False
    tmp = a[i]
    while tmp < len(li):
        li[tmp] = False
        tmp += a[i]
    if i < n-1:
        if a[i+1] == a[i]:
            continue
    ans += 1


print(ans)
