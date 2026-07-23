n = int(input())
a = list(map(int,input().split()))
ans = 0
befor = a[0]
for i in range(1,n-1):
    after = a[i+1]
    if a[i] == befor:
        ans += 1
        for j in range(1,10001):
            if j != after:
                a[i] = j
                break
    befor = a[i]
if befor == a[-1]:
    ans += 1
print(ans)
