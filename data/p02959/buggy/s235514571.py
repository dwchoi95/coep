n = int(input())
a = list(map(int, input().split()))
b = list(map(int, input().split()))

ans = 0

for i in range(n):
    ab = a[i] - b[i]
    if ab < 0:
        ans += a[i]
        b[i] -= a[i]
        ab = a[i+1] - b[i]
        
        if ab <= 0:
            ans += a[i+1]
            a[i+1] = 0
        else:
            ans += b[i]
           
    elif ab == 0:
        ans += b[i]
        
    else:
        ans += b[i]
        
print(ans)