n = int(input())
a = list(map(int,input().split()))
 
s = sum(a)
 
left = 0
right = s
res = s
for i in range(n-1):
    left += a[i]
    right -= a[i]
    res = min(res,abs(left-right))
    if res == 0:
        break
    
print(res)

