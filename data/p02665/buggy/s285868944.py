n = int(input())
a = list(map(int,input().split()))
ans = 0

l = [0]*(n+1)
l[-1] = a[-1]
for i in range(n-1,-1,-1):
    l[i] += l[i+1]+a[i]

if a[0] == 1:
    if n > 0:
        print(-1)
        exit()
    else:
        print(1)
        exit()
b = 2
ans = 1
for i in range(1,n+1):
    if b*2 < a[i]:
        print(-1)
        exit()
    else:
        if i == n:
            ans += a[-1]
        else:
            b = (b-a[i])*2
            ans += min(b,l[i+1])

print(ans)

