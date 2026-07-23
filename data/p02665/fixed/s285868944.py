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
b = 1
ans = 0
for i in range(n+1):
    if b < a[i]:
        print(-1)
        exit()
    else: 
        b = min(b,l[i])
        ans += b
        b = (b-a[i])*2   
print(ans)

