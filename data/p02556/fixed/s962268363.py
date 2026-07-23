n = int(input())
l = []
ll = []
for _ in range(n):
    x, y = map(int, input().split())
    l.append((x+y, x, y))
    ll.append((x-y, x, y))
l.sort()
ll.sort()
ans1 = 0
ans2 = 0



cnt = 0
while True:
    a = l[n-1-cnt]
    b = l[cnt]
    
    if a[1] >= b[1] and a[2] >= b[2]:
        ans1 = abs(b[0]-a[0])
        
        break
    if cnt >= n-1:
        break
    cnt += 1

cnt = 0
while True:
    a = ll[n-1-cnt]
    b = ll[cnt]
    if a[1] >= b[1] and b[2] >= a[2]:
        ans2 = abs(b[0]-a[0])
        
        break
    if cnt >= n-1:
        break
    cnt += 1

print(max(ans1, ans2))
